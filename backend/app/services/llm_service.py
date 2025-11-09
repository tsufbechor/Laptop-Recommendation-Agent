"""LLM orchestration service."""

from __future__ import annotations

from typing import AsyncIterator, Dict, List, Optional, Sequence

from ..config import AppSettings, settings
from ..models import (
    ChatMessage,
    ComparedProduct,
    ComparisonResponse,
    ProductComparison,
    RetrievedProduct,
)
from .llm_types import LLMProductRecommendation, LLMProvider, LLMResult


class LLMService:
    """High-level orchestrator around the LLM provider."""

    def __init__(self, app_settings: Optional[AppSettings] = None, provider: Optional[LLMProvider] = None) -> None:
        self.settings = app_settings or settings
        self.provider = provider or self._default_provider()

    def _default_provider(self) -> LLMProvider:
        from .gemini_provider import GeminiProvider  # Local import to avoid circular dependency

        return GeminiProvider(self.settings)

    async def generate(
        self, messages: Sequence[ChatMessage], context_products: Sequence[RetrievedProduct]
    ) -> LLMResult:
        return await self.provider.generate_response(messages, context_products)

    async def stream(
        self, messages: Sequence[ChatMessage], context_products: Sequence[RetrievedProduct]
    ) -> AsyncIterator[str]:
        async for chunk in self.provider.stream_response(messages, context_products):
            yield chunk

    def parse(self, text: str, context_products: Sequence[RetrievedProduct]) -> LLMResult:
        return self.provider.parse_response_text(text, context_products)

    @staticmethod
    def merge_recommendations(
        retrieved_products: Sequence[RetrievedProduct], llm_result: LLMResult
    ) -> List[RetrievedProduct]:
        """Attach LLM rationale to retrieved products."""

        # If no recommendations, return empty list (agent is asking questions)
        if not llm_result.recommendations:
            return []

        retrieved_by_sku: Dict[str, RetrievedProduct] = {product.sku: product for product in retrieved_products}
        enriched: List[RetrievedProduct] = []

        for recommendation in llm_result.recommendations:
            product = retrieved_by_sku.get(recommendation.sku)
            if not product:
                # LLM recommended a product we did not retrieve; skip or attach placeholder
                continue
            product.explanation = recommendation.rationale
            enriched.append(product)

        return enriched

    # REMOVED: generate_comparison() method - was causing 2-5 second delay after streaming
    # The frontend ProductComparison component now handles comparison display using product data
