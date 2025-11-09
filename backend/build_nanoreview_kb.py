"""Build knowledge base from nanoreview.net."""
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
    # Load products
    products_path = backend_dir / "app" / "data" / "products.json"

    print("="*60)
    print("Building Knowledge Base from NanoReview.net")
    print("="*60)

    with open(products_path, "r", encoding="utf-8") as f:
        products_data = json.load(f)

    products = [Product(**p) for p in products_data]

    print(f"\nTotal products to process: {len(products)}")

    # Ask how many to build
    choice = input("\n1. Build for ALL products (takes ~15-20 minutes)\n2. Build for first 5 products (demo)\n\nChoice (1 or 2): ").strip()

    if choice == "2":
        products = products[:5]
        print(f"\nBuilding for {len(products)} sample products")
    else:
        print(f"\nBuilding for all {len(products)} products")

    force = input("Force refresh existing entries? (y/N): ").lower() == "y"

    scraper = NanoReviewScraper(
        gemini_api_key=settings.gemini_api_key,
        knowledge_cache_path=backend_dir / "app" / "data" / "product_knowledge.json",
    )

    print(f"\nStarting build process...")
    print("-"*60)

    knowledge_base = await scraper.build_knowledge_base_batch(
        products, max_concurrent=1, force_refresh=force
    )

    print("\n" + "="*60)
    print(f"Knowledge base built successfully!")
    print("="*60)
    print(f"Total entries: {len(knowledge_base)}")

    # Show samples
    print(f"\nSample entries:")
    for i, (sku, kb) in enumerate(list(knowledge_base.items())[:3]):
        product = next((p for p in products if p.sku == sku), None)
        if product:
            print(f"\n{i+1}. {product.name}")
            print(f"   {kb.summary[:150]}...")

    print("\n" + "="*60)
    print("IMPORTANT: Restart the backend server to load the knowledge base!")
    print("="*60)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nBuild cancelled")
        sys.exit(1)
