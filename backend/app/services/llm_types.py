"""Shared LLM data structures and base protocols."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import AsyncIterator, Sequence

from ..models import ChatMessage, RetrievedProduct


@dataclass
class LLMProductRecommendation:
    """Structured product recommendation produced by the LLM."""

    sku: str
    name: str
    rationale: str
    confidence: float | None = None


@dataclass
class LLMResult:
    """Structured response produced by an LLM provider."""

    reply: str
    reasoning: str | None
    recommendations: list[LLMProductRecommendation]


class LLMProvider(ABC):
    """Interface for pluggable LLM providers."""

    @abstractmethod
    async def generate_response(
        self, messages: Sequence[ChatMessage], context_products: Sequence[RetrievedProduct]
    ) -> LLMResult:
        """Return a structured response for the given conversation."""

    @abstractmethod
    async def stream_response(
        self, messages: Sequence[ChatMessage], context_products: Sequence[RetrievedProduct]
    ) -> AsyncIterator[str]:
        """Yield response chunks for streaming endpoints."""

    @abstractmethod
    def parse_response_text(self, text: str, context_products: Sequence[RetrievedProduct]) -> LLMResult:
        """Parse raw provider output into a structured result."""
