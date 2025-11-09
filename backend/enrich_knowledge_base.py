"""Enrich knowledge base with strengths, weaknesses, and use_cases from summaries."""
import asyncio
import json
import sys
from pathlib import Path

backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

import google.generativeai as genai
from app.models import ProductKnowledge
from app.config import settings


async def extract_attributes(summary: str, product_name: str) -> dict:
    """Extract strengths, weaknesses, and use_cases from summary using LLM."""
    genai.configure(api_key=settings.gemini_api_key)
    model = genai.GenerativeModel(
        "gemini-2.5-flash",
        generation_config={
            "response_mime_type": "application/json",
            "temperature": 0.3,
        }
    )

    prompt = f"""Analyze the following product summary and extract key attributes as JSON.

Product: {product_name}
Summary: {summary}

Extract:
1. strengths: List of 3-5 key strengths (e.g., "High-performance CPU", "Excellent for gaming")
2. weaknesses: List of 2-4 weaknesses or limitations (e.g., "Expensive", "Heavy for portability")
3. use_cases: List of 3-5 ideal use cases (e.g., "Professional video editing", "High-end gaming")

Return JSON format:
{{
  "strengths": ["strength1", "strength2", ...],
  "weaknesses": ["weakness1", "weakness2", ...],
  "use_cases": ["use_case1", "use_case2", ...]
}}

Keep each item concise (under 10 words). Be specific and actionable."""

    try:
        response = model.generate_content(prompt)
        result = json.loads(response.text)
        return result
    except Exception as e:
        print(f"  [ERROR] Failed to extract attributes: {e}")
        return {
            "strengths": [],
            "weaknesses": [],
            "use_cases": []
        }


async def main():
    kb_path = backend_dir / "app" / "data" / "product_knowledge.json"

    print("="*60)
    print("Enriching Knowledge Base")
    print("="*60)

    # Load existing knowledge base
    with open(kb_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    print(f"\nLoaded {len(data)} products from knowledge base")
    print("\nEnriching with strengths, weaknesses, and use_cases...\n")

    enriched_data = {}

    for i, (sku, kb_dict) in enumerate(data.items(), 1):
        # Remove source_urls if present
        if "source_urls" in kb_dict:
            del kb_dict["source_urls"]

        # Create ProductKnowledge object
        kb = ProductKnowledge(**kb_dict)

        # Skip if already enriched
        if kb.strengths or kb.weaknesses or kb.use_cases:
            print(f"[{i}/{len(data)}] {sku}: Already enriched, skipping")
            enriched_data[sku] = kb.model_dump()
            continue

        print(f"[{i}/{len(data)}] {sku}: Extracting attributes...")

        # Extract attributes from summary
        attributes = await extract_attributes(kb.summary, sku)

        # Update knowledge object
        kb.strengths = attributes.get("strengths", [])
        kb.weaknesses = attributes.get("weaknesses", [])
        kb.use_cases = attributes.get("use_cases", [])

        enriched_data[sku] = kb.model_dump()

        print(f"  Strengths: {len(kb.strengths)}")
        print(f"  Weaknesses: {len(kb.weaknesses)}")
        print(f"  Use cases: {len(kb.use_cases)}")

    # Save enriched knowledge base
    print(f"\n{'='*60}")
    print("Saving enriched knowledge base...")
    with open(kb_path, "w", encoding="utf-8") as f:
        json.dump(enriched_data, f, indent=2, default=str)

    print(f"Saved {len(enriched_data)} products to {kb_path}")
    print("="*60)
    print("\nDone! Restart backend to load enriched knowledge base.")


if __name__ == "__main__":
    asyncio.run(main())
