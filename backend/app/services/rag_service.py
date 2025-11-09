"""Retrieval-Augmented Generation (RAG) service."""

from __future__ import annotations

import json
import logging
import math
import re
import time
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np
import google.generativeai as genai
from tenacity import retry, stop_after_attempt, wait_exponential

from ..config import AppSettings, settings
from ..models import Product, ProductKnowledge, RetrievedProduct


logger = logging.getLogger(__name__)


@dataclass
class RetrievalResult:
    """Container for RAG retrieval outputs."""

    products: List[RetrievedProduct]
    latency_ms: float
    applied_filters: Dict[str, Any]


class RAGService:
    """Semantic retrieval over the product catalogue."""

    def __init__(self, app_settings: Optional[AppSettings] = None) -> None:
        self.settings = app_settings or settings
        self._configure_gemini()
        self.products: List[Product] = self._load_products()
        self.knowledge_base: Dict[str, ProductKnowledge] = self._load_knowledge_base()
        self._embedding_lock = Lock()
        self._embedding_dim: Optional[int] = None
        self._product_text_cache: Dict[str, str] = {}
        self._normalized_embeddings: Optional[np.ndarray] = None
        self._keyword_index = self._build_keyword_index(self.products)
        self._embedding_model_name = self.settings.embedding_model
        self._default_embedding_model = "models/embedding-001"
        self._load_or_build_index()

    # --------------------------------------------------------------------- utils
    def _configure_gemini(self) -> None:
        self._offline_mode = False
        if not self.settings.gemini_api_key:
            self._offline_mode = True
            return
        genai.configure(api_key=self.settings.gemini_api_key)

    @staticmethod
    def _load_products_from_file(path: Path) -> List[Dict[str, Any]]:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def _load_products(self) -> List[Product]:
        raw_products = self._load_products_from_file(self.settings.products_path)
        return [Product(**item) for item in raw_products]

    def _load_knowledge_base(self) -> Dict[str, ProductKnowledge]:
        """Load product knowledge base from cache."""
        kb_path = Path("app/data/product_knowledge.json")

        if not kb_path.exists():
            logger.info("Knowledge base not found at %s. Product recommendations will use basic specs only.", kb_path)
            return {}

        try:
            with kb_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
                knowledge_base = {
                    sku: ProductKnowledge(**kb) for sku, kb in data.items()
                }
            logger.info("Loaded knowledge base for %d products", len(knowledge_base))
            return knowledge_base
        except Exception as exc:
            logger.warning("Failed to load knowledge base: %s. Continuing without it.", exc)
            return {}

    def get_product_knowledge(self, sku: str) -> Optional[ProductKnowledge]:
        """Get knowledge base entry for a product."""
        return self.knowledge_base.get(sku)

    def _product_text(self, product: Product) -> str:
        cached = self._product_text_cache.get(product.sku)
        if cached:
            return cached

        # Base product information
        text = (
            f"SKU: {product.sku}\n"
            f"Vendor: {product.vendor}\n"
            f"Family: {product.family}\n"
            f"Name: {product.name}\n"
            f"Description: {product.description}\n"
            f"CPU: {product.cpu}\n"
            f"GPU: {product.gpu}\n"
            f"RAM: {product.ram}\n"
            f"Storage: {product.storage}\n"
            f"Price: {product.price}"
        )

        # Enrich with knowledge base if available
        knowledge = self.knowledge_base.get(product.sku)
        if knowledge:
            text += f"\n\nProduct Summary: {knowledge.summary}"
            if knowledge.strengths:
                text += f"\nStrengths: {', '.join(knowledge.strengths[:3])}"
            if knowledge.use_cases:
                text += f"\nBest for: {', '.join(knowledge.use_cases[:3])}"

        self._product_text_cache[product.sku] = text
        return text

    # -------------------------------------------------------------- keyword index
    def _build_keyword_index(self, products: Sequence[Product]) -> Dict[str, set[str]]:
        keyword_index: Dict[str, set[str]] = {}
        for product in products:
            keywords = self._extract_keywords(product)
            for keyword in keywords:
                keyword_index.setdefault(keyword, set()).add(product.sku)
        return keyword_index

    @staticmethod
    def _extract_keywords(product: Product) -> List[str]:
        base_fields = " ".join(
            [product.name, product.description, product.cpu, product.gpu, product.ram, product.storage]
        )
        tokens = re.findall(r"[a-zA-Z0-9\-\+\.]+", base_fields.lower())
        unique_tokens = sorted(set(tokens))
        return [token for token in unique_tokens if len(token) > 2]

    # ------------------------------------------------------------------ embeddings
    def _load_or_build_index(self) -> None:
        path = self.settings.vector_store_path
        meta_path = path.with_suffix(".meta.json")

        if path.exists() and meta_path.exists():
            try:
                stored_embeddings = np.load(path)
                with meta_path.open("r", encoding="utf-8") as handle:
                    metadata = json.load(handle)
                if stored_embeddings.shape[0] != len(self.products):
                    raise ValueError("Stored embeddings do not match product catalogue length.")
                self._embedding_dim = int(stored_embeddings.shape[1])
                self._normalized_embeddings = self._normalize_embeddings(stored_embeddings)
                if metadata.get("sku_order") != [product.sku for product in self.products]:
                    raise ValueError("Stored embeddings metadata does not match product ordering.")
                return
            except Exception as exc:
                logger.warning("Failed to load cached embeddings (%s); rebuilding index.", exc, exc_info=True)

        self._build_index()

    def _build_index(self) -> None:
        logger.info("Building embedding index for %d products.", len(self.products))
        embeddings = []
        for product in self.products:
            vector = self._embed_text(self._product_text(product))
            embeddings.append(vector)

        embedding_matrix = np.vstack(embeddings)
        self._embedding_dim = embedding_matrix.shape[1]
        self._normalized_embeddings = self._normalize_embeddings(embedding_matrix)
        self._persist_embeddings(embedding_matrix)

    @staticmethod
    def _normalize_embeddings(embedding_matrix: np.ndarray) -> np.ndarray:
        norms = np.linalg.norm(embedding_matrix, axis=1, keepdims=True)
        norms[norms == 0.0] = 1.0
        return embedding_matrix / norms

    def _persist_embeddings(self, embedding_matrix: np.ndarray) -> None:
        path = self.settings.vector_store_path
        meta_path = path.with_suffix(".meta.json")
        path.parent.mkdir(parents=True, exist_ok=True)
        np.save(path, embedding_matrix)
        metadata = {"sku_order": [product.sku for product in self.products]}
        with meta_path.open("w", encoding="utf-8") as handle:
            json.dump(metadata, handle)

    @retry(wait=wait_exponential(multiplier=1, min=2, max=10), stop=stop_after_attempt(5))
    def _embed_text(self, text: str) -> np.ndarray:
        if self._offline_mode:
            target_dim = self._embedding_dim or 768
            vector = self._hash_embed(text, dim=target_dim)
            if self._embedding_dim is None:
                self._embedding_dim = len(vector)
            return vector
        try:
            logger.debug("Embedding text using model '%s'.", self._embedding_model_name)
            response = genai.embed_content(model=self._embedding_model_name, content=text)
        except ValueError as exc:
            logger.warning(
                "Embedding failed with model '%s': %s", self._embedding_model_name, exc, exc_info=True
            )
            if "Invalid model name" in str(exc) and self._embedding_model_name != self._default_embedding_model:
                self._embedding_model_name = self._default_embedding_model
                logger.info(
                    "Retrying embedding with fallback model '%s'.", self._embedding_model_name
                )
                response = genai.embed_content(model=self._embedding_model_name, content=text)
            else:
                raise
        embedding = np.array(response["embedding"], dtype=np.float32)

        if self._embedding_dim is None:
            self._embedding_dim = len(embedding)
        elif len(embedding) != self._embedding_dim:
            raise ValueError("Embedding dimension mismatch detected.")
        norm = np.linalg.norm(embedding)
        if norm == 0.0:
            return embedding
        return embedding / norm

    @staticmethod
    def _hash_embed(text: str, dim: int = 768) -> np.ndarray:
        import hashlib

        digest = hashlib.sha256(text.encode("utf-8")).digest()
        repeats = math.ceil(dim * 4 / len(digest))
        raw = (digest * repeats)[: dim * 4]
        array = np.frombuffer(raw, dtype=np.uint32).astype(np.float32)
        array = array.reshape(-1)
        array = array[:dim]
        norm = np.linalg.norm(array)
        if norm == 0.0:
            return array
        array = array / norm
        return array

    # ------------------------------------------------------------------- filtering
    @staticmethod
    def _parse_filters(user_preferences: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        if not user_preferences:
            return {}
        filters: Dict[str, Any] = {}
        min_value = user_preferences.get("price_min")
        max_value = user_preferences.get("price_max")
        has_min = min_value is not None and str(min_value).strip() != ""
        has_max = max_value is not None and str(max_value).strip() != ""
        if has_min or has_max:
            low = float(min_value) if has_min else 0.0
            high = float(max_value) if has_max else None
            filters["price_range"] = (low, high)
        if vendor := user_preferences.get("vendor"):
            filters["vendor"] = str(vendor).lower()
        if gpu := user_preferences.get("gpu"):
            filters["gpu"] = str(gpu).lower()
        if family := user_preferences.get("family"):
            filters["family"] = str(family).lower()
        return filters

    def _passes_filters(self, product: Product, filters: Dict[str, Any]) -> bool:
        price_range = filters.get("price_range")
        if price_range:
            low, high = price_range
            if product.price < low:
                return False
            if high is not None and product.price > high:
                return False
        vendor = filters.get("vendor")
        if vendor and vendor not in product.vendor.lower():
            return False
        gpu = filters.get("gpu")
        if gpu and gpu not in product.gpu.lower():
            return False
        family = filters.get("family")
        if family and family not in product.family.lower():
            return False
        return True

    # --------------------------------------------------------------------- keyword
    def _keyword_score(self, query: str, product: Product) -> Tuple[float, List[str]]:
        query_tokens = set(self._extract_terms(query))
        matched_tokens = [
            token for token in query_tokens if token in self._keyword_index and product.sku in self._keyword_index[token]
        ]
        if not matched_tokens:
            return 0.0, []
        score = min(len(matched_tokens) * 0.05, 0.2)  # cap keyword bonus
        return score, matched_tokens

    @staticmethod
    def _extract_terms(text: str) -> List[str]:
        return re.findall(r"[a-zA-Z0-9\-\+\.]+", text.lower())

    # --------------------------------------------------------------------- search
    def search(
        self, query: str, user_preferences: Optional[Dict[str, Any]] = None, top_k: Optional[int] = None
    ) -> RetrievalResult:
        if not query.strip():
            raise ValueError("Query text must not be empty.")
        if self._normalized_embeddings is None:
            raise RuntimeError("Embedding index not initialised.")

        filters = self._parse_filters(user_preferences)
        top_k = top_k or self.settings.rag_top_k

        start_time = time.perf_counter()
        query_embedding = self._embed_text(query)
        similarities = self._normalized_embeddings @ query_embedding

        scored_products: List[Tuple[float, RetrievedProduct]] = []
        for idx, semantic_score in enumerate(similarities):
            product = self.products[idx]
            if not self._passes_filters(product, filters):
                continue
            keyword_score, matched_keywords = self._keyword_score(query, product) if self.settings.enable_hybrid_search else (0.0, [])
            combined_score = float(semantic_score + keyword_score)
            retrieved = RetrievedProduct(
                **product.model_dump(),
                similarity=combined_score,
                matched_keywords=matched_keywords or None,
            )
            scored_products.append((combined_score, retrieved))

        scored_products.sort(key=lambda item: item[0], reverse=True)
        top_products = [item[1] for item in scored_products[:top_k]]

        latency_ms = (time.perf_counter() - start_time) * 1000
        return RetrievalResult(products=top_products, latency_ms=latency_ms, applied_filters=filters)
