"""Script to build and update product knowledge base."""

import asyncio
import json
import sys
from pathlib import Path

# Add the backend directory to the path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from app.models import Product
from app.services.scraping_service import ProductScrapingService
from app.config import settings


async def main():
    """Build knowledge base for all products in catalog."""

    # Load products from JSON
    products_path = backend_dir / "products.json"

    if not products_path.exists():
        print(f"Error: products.json not found at {products_path}")
        return

    print(f"Loading products from {products_path}")
    with open(products_path, "r", encoding="utf-8") as f:
        products_data = json.load(f)

    products = [Product(**p) for p in products_data]
    print(f"Loaded {len(products)} products from catalog")

    # Initialize scraping service
    print(f"\nInitializing scraping service with Gemini API...")
    scraper = ProductScrapingService(
        gemini_api_key=settings.gemini_api_key,
        knowledge_cache_path=backend_dir / "app" / "data" / "product_knowledge.json",
    )

    # Build knowledge base
    print(f"\nBuilding knowledge base for {len(products)} products...")
    print("This may take several minutes...\n")

    # Ask user if they want to force refresh
    force_refresh = input("Force refresh all products? (y/N): ").lower() == "y"

    knowledge_base = await scraper.build_knowledge_base_batch(
        products, max_concurrent=2, force_refresh=force_refresh  # Adjust based on rate limits
    )

    print(f"\n{'='*60}")
    print(f"Knowledge base built successfully!")
    print(f"{'='*60}")
    print(f"Total products: {len(knowledge_base)}")
    print(f"Cache location: {scraper.knowledge_cache_path}")

    # Display sample
    print(f"\nSample knowledge base entries:")
    for i, (sku, kb) in enumerate(list(knowledge_base.items())[:3]):
        product = next(p for p in products if p.sku == sku)
        print(f"\n{i+1}. {product.name}")
        print(f"   Summary: {kb.summary[:100]}...")
        print(f"   Strengths: {len(kb.strengths)} items")
        print(f"   Weaknesses: {len(kb.weaknesses)} items")
        print(f"   Use cases: {len(kb.use_cases)} items")

    print(f"\n{'='*60}")
    print("Knowledge base is ready to use!")
    print("Restart the backend server to load the updated knowledge base.")
    print(f"{'='*60}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nBuild cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nError: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
