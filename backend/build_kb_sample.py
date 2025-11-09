"""Build knowledge base for sample products."""
import asyncio
import json
import sys
from pathlib import Path

backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from app.models import Product
from app.services.scraping_service import ProductScrapingService
from app.config import settings


async def main():
    # Load products
    products_path = backend_dir / "app" / "data" / "products.json"
    with open(products_path, "r", encoding="utf-8") as f:
        products_data = json.load(f)

    # Build for first 3 products only
    products = [Product(**p) for p in products_data[:3]]

    print(f"Building knowledge base for {len(products)} sample products:")
    for p in products:
        print(f"  - {p.name}")
    print()

    scraper = ProductScrapingService(
        gemini_api_key=settings.gemini_api_key,
        knowledge_cache_path=backend_dir / "app" / "data" / "product_knowledge.json",
    )

    knowledge_base = await scraper.build_knowledge_base_batch(
        products, max_concurrent=1, force_refresh=True
    )

    print(f"\nBuilt knowledge for {len(knowledge_base)} products")
    for sku, kb in knowledge_base.items():
        product = next(p for p in products if p.sku == sku)
        print(f"\n{product.name}:")
        print(f"  Summary: {kb.summary[:80]}...")
        print(f"  Strengths: {kb.strengths[:2]}")
        print(f"  Use cases: {kb.use_cases[:2]}")

    print("\nKnowledge base ready!")


if __name__ == "__main__":
    asyncio.run(main())
