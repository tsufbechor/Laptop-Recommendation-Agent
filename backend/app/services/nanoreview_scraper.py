"""Simplified scraper specifically for nanoreview.net."""

from __future__ import annotations

import asyncio
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

import httpx
from bs4 import BeautifulSoup
import google.generativeai as genai

from ..models import Product, ProductKnowledge


class NanoReviewScraper:
    """Simple scraper for nanoreview.net laptop reviews."""

    def __init__(self, gemini_api_key: str, knowledge_cache_path: Optional[Path] = None):
        self.gemini_api_key = gemini_api_key
        self.knowledge_cache_path = knowledge_cache_path or Path("backend/app/data/product_knowledge.json")
        self.knowledge_cache: Dict[str, ProductKnowledge] = {}
        genai.configure(api_key=self.gemini_api_key)
        self._load_cache()

    def _load_cache(self) -> None:
        """Load existing knowledge base from cache."""
        if self.knowledge_cache_path.exists():
            try:
                with open(self.knowledge_cache_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.knowledge_cache = {
                        sku: ProductKnowledge(**kb) for sku, kb in data.items()
                    }
                print(f"Loaded {len(self.knowledge_cache)} entries from cache")
            except Exception as e:
                print(f"Failed to load cache: {e}")

    def _save_cache(self) -> None:
        """Save knowledge base to cache."""
        self.knowledge_cache_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(self.knowledge_cache_path, "w", encoding="utf-8") as f:
                data = {sku: kb.model_dump() for sku, kb in self.knowledge_cache.items()}
                json.dump(data, f, indent=2, default=str)
            print(f"Saved {len(self.knowledge_cache)} entries to cache")
        except Exception as e:
            print(f"Failed to save cache: {e}")

    def _normalize_name(self, name: str) -> str:
        """Normalize product name for URL search."""
        # Remove year/generation indicators
        name = re.sub(r'\(20\d{2}\)', '', name)
        name = re.sub(r'\(Gen \d+\)', '', name)
        name = re.sub(r'Gen \d+', '', name)
        # Remove special characters
        name = re.sub(r'[^\w\s-]', '', name)
        # Replace spaces with hyphens
        name = '-'.join(name.lower().split())
        return name

    async def scrape_nanoreview(self, product: Product) -> Optional[str]:
        """Scrape product info from nanoreview.net."""
        normalized_name = self._normalize_name(product.name)
        vendor_lower = product.vendor.lower()

        # Try different URL patterns
        potential_urls = [
            f"https://nanoreview.net/en/laptop/{vendor_lower}-{normalized_name}",
            f"https://nanoreview.net/en/laptop/{normalized_name}",
        ]

        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }

            for url in potential_urls:
                try:
                    print(f"  Trying: {url}")
                    response = await client.get(url, headers=headers)

                    if response.status_code == 200:
                        soup = BeautifulSoup(response.text, "html.parser")

                        # Extract text content
                        content_parts = []

                        # Get main description
                        desc = soup.select_one(".laptop-description, .description, article p")
                        if desc:
                            content_parts.append(desc.get_text(strip=True))

                        # Get pros/cons
                        pros = soup.select(".pros li, .advantages li")
                        if pros:
                            content_parts.append("Pros: " + "; ".join([p.get_text(strip=True) for p in pros[:5]]))

                        cons = soup.select(".cons li, .disadvantages li")
                        if cons:
                            content_parts.append("Cons: " + "; ".join([c.get_text(strip=True) for c in cons[:5]]))

                        # Get any paragraphs
                        paragraphs = soup.select("article p, .content p")
                        for p in paragraphs[:3]:
                            text = p.get_text(strip=True)
                            if len(text) > 50:
                                content_parts.append(text)

                        if content_parts:
                            print(f"  [OK] Found content ({len(' '.join(content_parts))} chars)")
                            return " ".join(content_parts)[:2000]  # Limit size

                except Exception as e:
                    print(f"  Error with {url}: {e}")
                    continue

        print(f"  [SKIP] No content found on nanoreview.net")
        return None

    async def generate_summary_with_llm(self, product: Product, scraped_content: Optional[str]) -> str:
        """Generate a 2-paragraph summary using Gemini."""
        model = genai.GenerativeModel("gemini-2.5-flash")

        if scraped_content:
            prompt = f"""Based on the following review content about the {product.name}, write a concise 2-paragraph summary (max 150 words total).

Product: {product.name}
Vendor: {product.vendor}
CPU: {product.cpu}
GPU: {product.gpu}
RAM: {product.ram}
Storage: {product.storage}
Price: ${product.price}

Review content:
{scraped_content[:1500]}

Write exactly 2 paragraphs that summarize this laptop's key features, performance characteristics, and ideal use cases. Be specific and informative."""
        else:
            # Fallback when no content found
            prompt = f"""Write a concise 2-paragraph summary (max 150 words total) about the {product.name} laptop based on its specifications.

Product: {product.name}
Vendor: {product.vendor}
CPU: {product.cpu}
GPU: {product.gpu}
RAM: {product.ram}
Storage: {product.storage}
Price: ${product.price}

Write exactly 2 paragraphs describing what this laptop is good for, its performance level, and who should consider it."""

        try:
            response = model.generate_content(prompt)
            summary = response.text.strip()
            print(f"  [OK] Generated summary ({len(summary)} chars)")
            return summary
        except Exception as e:
            print(f"  [ERROR] LLM generation failed: {e}")
            return f"The {product.name} features {product.cpu} processor with {product.gpu} graphics. This configuration offers solid performance for professional and creative workloads."

    async def build_knowledge_for_product(self, product: Product, force_refresh: bool = False) -> ProductKnowledge:
        """Build knowledge for a single product."""
        # Check cache
        if not force_refresh and product.sku in self.knowledge_cache:
            cached = self.knowledge_cache[product.sku]
            age_days = (datetime.utcnow() - cached.last_updated).days
            if age_days < 30:
                print(f"[CACHE] {product.name} (age: {age_days} days)")
                return cached

        print(f"\n[BUILD] {product.name}")

        # Try to scrape nanoreview.net (optional - will use LLM fallback if fails)
        scraped_content = await self.scrape_nanoreview(product)

        # Generate summary (works with or without scraped content)
        summary = await self.generate_summary_with_llm(product, scraped_content)

        # Create knowledge object
        knowledge = ProductKnowledge(
            sku=product.sku,
            summary=summary,
            strengths=[],
            weaknesses=[],
            use_cases=[],
            last_updated=datetime.utcnow(),
        )

        # Cache it
        self.knowledge_cache[product.sku] = knowledge
        self._save_cache()

        return knowledge

    async def build_knowledge_base_batch(
        self,
        products: list[Product],
        max_concurrent: int = 1,
        force_refresh: bool = False,
    ) -> Dict[str, ProductKnowledge]:
        """Build knowledge base for multiple products sequentially."""
        # Process products one by one for reliability
        for product in products:
            try:
                await self.build_knowledge_for_product(product, force_refresh)
            except Exception as e:
                print(f"[ERROR] Failed for {product.name}: {e}")
                import traceback
                traceback.print_exc()

        return self.knowledge_cache
