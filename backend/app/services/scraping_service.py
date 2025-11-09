"""Web scraping service for building product knowledge base."""

from __future__ import annotations

import asyncio
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import httpx
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential

from ..models import Product, ProductKnowledge


class ProductScrapingService:
    """Service to scrape and build knowledge base for products."""

    def __init__(self, gemini_api_key: str, knowledge_cache_path: Optional[Path] = None):
        self.gemini_api_key = gemini_api_key
        self.knowledge_cache_path = knowledge_cache_path or Path("backend/app/data/product_knowledge.json")
        self.knowledge_cache: Dict[str, ProductKnowledge] = {}
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
                print(f"Loaded {len(self.knowledge_cache)} products from knowledge base cache")
            except Exception as e:
                print(f"Failed to load knowledge base cache: {e}")

    def _save_cache(self) -> None:
        """Save knowledge base to cache."""
        self.knowledge_cache_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(self.knowledge_cache_path, "w", encoding="utf-8") as f:
                data = {
                    sku: kb.model_dump() for sku, kb in self.knowledge_cache.items()
                }
                json.dump(data, f, indent=2, default=str)
            print(f"Saved {len(self.knowledge_cache)} products to knowledge base cache")
        except Exception as e:
            print(f"Failed to save knowledge base cache: {e}")

    async def search_product_info(self, product: Product) -> List[str]:
        """Search for product information online using DuckDuckGo HTML."""
        # Build search queries
        search_queries = [
            f"{product.vendor} {product.name} review",
            f"{product.name} specs benchmark performance",
        ]

        urls = []

        # Trusted review sites for tech products
        trusted_domains = [
            "pcmag.com",
            "tomshardware.com",
            "notebookcheck.net",
            "techradar.com",
            "laptopmag.com",
            "pcworld.com",
            "theverge.com",
            "engadget.com",
        ]

        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            for query in search_queries:
                try:
                    # Use DuckDuckGo HTML search (no API key needed)
                    search_url = f"https://html.duckduckgo.com/html/?q={query.replace(' ', '+')}"

                    headers = {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                    }

                    response = await client.get(search_url, headers=headers)
                    soup = BeautifulSoup(response.text, "html.parser")

                    # Extract URLs from DuckDuckGo results
                    for link in soup.select(".result__url"):
                        href = link.get("href", "")

                        # Check if URL contains any trusted domain
                        if any(domain in href for domain in trusted_domains):
                            # Clean up the URL
                            if href.startswith("//duckduckgo.com/l/?uddg="):
                                continue
                            urls.append(href)

                except Exception as e:
                    print(f"Search failed for '{query}': {e}")
                    continue

                # Limit results per query
                if len(urls) >= 3:
                    break

        # Return unique URLs, limit to 5
        unique_urls = list(dict.fromkeys(urls))[:5]
        print(f"Found {len(unique_urls)} URLs for {product.name}")
        return unique_urls

    @retry(stop=stop_after_attempt(2), wait=wait_exponential(min=1, max=5))
    async def scrape_url_content(self, url: str) -> str:
        """Scrape content from a URL."""
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            try:
                response = await client.get(
                    url,
                    headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
                )

                soup = BeautifulSoup(response.text, "html.parser")

                # Remove unwanted elements
                for element in soup(["script", "style", "nav", "footer", "aside", "ad"]):
                    element.decompose()

                # Try to find main content areas
                main_content = (
                    soup.find("article")
                    or soup.find("main")
                    or soup.find("div", class_=re.compile(r"content|article|post"))
                    or soup
                )

                # Get text content
                text = main_content.get_text(separator=" ", strip=True)

                # Clean up whitespace
                text = re.sub(r"\s+", " ", text)

                # Limit to reasonable length
                return text[:6000]

            except Exception as e:
                print(f"Failed to scrape {url}: {e}")
                return ""

    async def generate_knowledge_with_llm(
        self, product: Product, scraped_content: List[str]
    ) -> ProductKnowledge:
        """Use Gemini to generate structured knowledge from scraped content."""

        # Combine scraped content
        combined_content = "\n\n".join([c for c in scraped_content if c])[:10000]

        # If no content was scraped, generate basic knowledge from product specs
        if not combined_content.strip():
            return self._generate_fallback_knowledge(product)

        prompt = f"""Analyze the following information about the {product.name} laptop/PC and create a comprehensive summary.

Product Details:
- Name: {product.name}
- Vendor: {product.vendor}
- CPU: {product.cpu}
- GPU: {product.gpu}
- RAM: {product.ram}
- Storage: {product.storage}
- Price: ${product.price}

Web Content:
{combined_content}

Please provide a JSON response with the following structure:
{{
  "summary": "1-2 paragraph summary describing the product, its target audience, and overall value proposition",
  "strengths": ["strength 1", "strength 2", "strength 3", "strength 4"],
  "weaknesses": ["weakness 1", "weakness 2", "weakness 3"],
  "use_cases": ["use case 1", "use case 2", "use case 3", "use case 4"]
}}

Focus on being specific, accurate, and balanced. Include 3-5 items for strengths, weaknesses, and use cases.
Be concise but informative. Base your analysis on the web content provided.
"""

        # Call Gemini API
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-lite:generateContent?key={self.gemini_api_key}"

                response = await client.post(
                    api_url,
                    json={
                        "contents": [{"parts": [{"text": prompt}]}],
                        "generationConfig": {
                            "temperature": 0.3,
                            "maxOutputTokens": 1500,
                        },
                    },
                )

                if response.status_code != 200:
                    print(f"Gemini API error: {response.status_code} - {response.text}")
                    return self._generate_fallback_knowledge(product)

                result = response.json()
                text_response = result["candidates"][0]["content"]["parts"][0]["text"]

                # Extract JSON from response (handle markdown code blocks)
                json_match = re.search(r"```json\s*(\{.*?\})\s*```", text_response, re.DOTALL)
                if not json_match:
                    json_match = re.search(r"\{.*\}", text_response, re.DOTALL)

                if json_match:
                    json_str = json_match.group(1) if json_match.lastindex else json_match.group()
                    knowledge_data = json.loads(json_str)

                    return ProductKnowledge(
                        sku=product.sku,
                        summary=knowledge_data.get("summary", ""),
                        strengths=knowledge_data.get("strengths", []),
                        weaknesses=knowledge_data.get("weaknesses", []),
                        use_cases=knowledge_data.get("use_cases", []),
                        source_urls=[],
                    )

            except Exception as e:
                print(f"LLM generation failed for {product.name}: {e}")

        # Return fallback knowledge if everything fails
        return self._generate_fallback_knowledge(product)

    def _generate_fallback_knowledge(self, product: Product) -> ProductKnowledge:
        """Generate basic knowledge from product specs when scraping/LLM fails."""
        summary = f"{product.name} from {product.vendor} features {product.cpu} processor with {product.gpu} graphics. "
        summary += f"It includes {product.ram} of RAM and {product.storage} storage, priced at ${product.price}."

        strengths = [
            f"{product.cpu} processor for reliable performance",
            f"{product.gpu} graphics capabilities",
            f"{product.ram} RAM for multitasking",
            f"{product.storage} storage capacity",
        ]

        weaknesses = [
            "Limited detailed reviews available",
            "Performance benchmarks pending",
        ]

        use_cases = [
            "General productivity and office work",
            "Web browsing and multimedia",
            "Professional applications",
        ]

        return ProductKnowledge(
            sku=product.sku,
            summary=summary,
            strengths=strengths,
            weaknesses=weaknesses,
            use_cases=use_cases,
            source_urls=[],
        )

    async def build_knowledge_for_product(self, product: Product, force_refresh: bool = False) -> ProductKnowledge:
        """Build complete knowledge base entry for a product."""

        # Check cache first
        if not force_refresh and product.sku in self.knowledge_cache:
            cached = self.knowledge_cache[product.sku]
            # Return cached if less than 30 days old
            age_days = (datetime.utcnow() - cached.last_updated).days
            if age_days < 30:
                print(f"Using cached knowledge for {product.name} (age: {age_days} days)")
                return cached

        print(f"Building knowledge base for {product.name}...")

        # Search for product information
        urls = await self.search_product_info(product)

        # Scrape content from URLs
        scraped_content = []
        for url in urls:
            content = await self.scrape_url_content(url)
            if content:
                scraped_content.append(content)

        # Generate knowledge with LLM
        knowledge = await self.generate_knowledge_with_llm(product, scraped_content)
        knowledge.source_urls = urls

        # Cache the knowledge
        self.knowledge_cache[product.sku] = knowledge
        self._save_cache()

        return knowledge

    async def build_knowledge_base_batch(
        self, products: List[Product], max_concurrent: int = 2, force_refresh: bool = False
    ) -> Dict[str, ProductKnowledge]:
        """Build knowledge base for multiple products concurrently."""

        semaphore = asyncio.Semaphore(max_concurrent)

        async def process_with_semaphore(product: Product):
            async with semaphore:
                try:
                    return await self.build_knowledge_for_product(product, force_refresh)
                except Exception as e:
                    print(f"Error processing {product.name}: {e}")
                    return self._generate_fallback_knowledge(product)

        tasks = [process_with_semaphore(p) for p in products]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        knowledge_base = {}
        for product, result in zip(products, results):
            if isinstance(result, ProductKnowledge):
                knowledge_base[product.sku] = result
            else:
                print(f"Failed to build knowledge for {product.sku}: {result}")
                # Use fallback
                knowledge_base[product.sku] = self._generate_fallback_knowledge(product)

        return knowledge_base
