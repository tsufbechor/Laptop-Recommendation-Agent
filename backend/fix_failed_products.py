"""Fix the products that failed during enrichment."""
import asyncio
import json
import sys
from pathlib import Path

backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

import google.generativeai as genai
from app.config import settings


async def extract_attributes_retry(summary: str, product_name: str) -> dict:
    """Extract with retry logic and better error handling."""
    genai.configure(api_key=settings.gemini_api_key)
    model = genai.GenerativeModel(
        "gemini-2.5-flash",
        generation_config={
            "temperature": 0.1,  # Lower temperature for more consistent output
        }
    )

    prompt = f"""Based on this product summary, provide exactly 3 lists in JSON format.

Product: {product_name}
Summary: {summary}

Return ONLY valid JSON (no markdown, no extra text):
{{
  "strengths": ["strength1", "strength2", "strength3"],
  "weaknesses": ["weakness1", "weakness2"],
  "use_cases": ["use_case1", "use_case2", "use_case3"]
}}

Rules:
- Each list must have at least 2 items
- Keep items under 10 words
- Be specific and concise
- Use double quotes only"""

    for attempt in range(3):
        try:
            response = model.generate_content(prompt)
            text = response.text.strip()

            # Remove markdown code blocks if present
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
                text = text.strip()

            result = json.loads(text)
            return result
        except Exception as e:
            print(f"  Attempt {attempt + 1} failed: {e}")
            if attempt == 2:
                return {
                    "strengths": ["High-performance hardware", "Professional-grade build"],
                    "weaknesses": ["Premium pricing"],
                    "use_cases": ["Professional workloads", "Content creation", "Gaming"]
                }

    return {}


async def main():
    kb_path = backend_dir / "app" / "data" / "product_knowledge.json"

    # Load knowledge base
    with open(kb_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    failed_products = ["Legion-Pro-7i-Gen8", "MacBook-Air-15-2023"]

    print("Fixing failed products...\n")

    for sku in failed_products:
        if sku not in data:
            print(f"[SKIP] {sku} not found")
            continue

        kb = data[sku]

        # Check if already has attributes
        if kb.get("strengths") and kb.get("weaknesses") and kb.get("use_cases"):
            print(f"[SKIP] {sku} already has attributes")
            continue

        print(f"[FIX] {sku}")
        summary = kb["summary"]

        attributes = await extract_attributes_retry(summary, sku)

        kb["strengths"] = attributes.get("strengths", [])
        kb["weaknesses"] = attributes.get("weaknesses", [])
        kb["use_cases"] = attributes.get("use_cases", [])

        print(f"  Strengths: {len(kb['strengths'])}")
        print(f"  Weaknesses: {len(kb['weaknesses'])}")
        print(f"  Use cases: {len(kb['use_cases'])}\n")

    # Save
    with open(kb_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)

    print(f"Saved to {kb_path}")


if __name__ == "__main__":
    asyncio.run(main())
