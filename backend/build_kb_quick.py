"""Quick knowledge base builder for first 3 products."""
import asyncio
import json
import sys
from pathlib import Path

backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from app.models import Product
from app.services.nanoreview_scraper import NanoReviewScraper
from app.config import settings


async def main():
    # Load first 3 products only
    products_path = backend_dir / "app" / "data" / "products.json"
    with open(products_path, "r", encoding="utf-8") as f:
        products_data = json.load(f)[:3]

    products = [Product(**p) for p in products_data]

    print("Building knowledge base for 3 sample products:")
    for p in products:
        print(f"  - {p.name}")

    scraper = NanoReviewScraper(
        gemini_api_key=settings.gemini_api_key,
        knowledge_cache_path=backend_dir / "app" / "data" / "product_knowledge.json",
    )

    kb = await scraper.build_knowledge_base_batch(
        products, max_concurrent=1, force_refresh=True
    )

    print(f"\nBuilt knowledge for {len(kb)} products")
    for sku, knowledge in kb.items():
        product = next((p for p in products if p.sku == sku), None)
        if product:
            print(f"\n{product.name}:")
            print(f"{knowledge.summary}\n")

    print("Knowledge base ready! Restart backend to use it.")


if __name__ == "__main__":
    asyncio.run(main())
