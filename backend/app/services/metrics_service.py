"""Metrics and conversation logging service."""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Dict, Iterable, List, Optional

import orjson

from ..config import AppSettings, settings
from ..models import (
    AggregateMetrics,
    ChatMessage,
    ConversationFeedback,
    ConversationSummary,
    SessionMetrics,
)


@dataclass
class MetricsAccumulator:
    """Internal structure to accumulate metrics for a session."""

    session_id: str
    retrieval_latencies: List[float] = field(default_factory=list)
    llm_latencies: List[float] = field(default_factory=list)
    recommended_products: List[str] = field(default_factory=list)
    feedback: Dict[str, str] = field(default_factory=dict)
    started_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    user_messages: int = 0
    assistant_messages: int = 0

    def to_session_metrics(self) -> SessionMetrics:
        retrieval_avg = sum(self.retrieval_latencies) / len(self.retrieval_latencies) if self.retrieval_latencies else 0.0
        llm_avg = sum(self.llm_latencies) / len(self.llm_latencies) if self.llm_latencies else 0.0
        return SessionMetrics(
            session_id=self.session_id,
            turn_count=self.user_messages,
            retrieval_latency_ms=retrieval_avg,
            llm_latency_ms=llm_avg,
            recommended_products=self.recommended_products,
            user_feedback=self.feedback,
            started_at=self.started_at,
            updated_at=self.updated_at,
        )


class MetricsService:
    """Manage session histories and analytics."""

    def __init__(self, app_settings: Optional[AppSettings] = None) -> None:
        self.settings = app_settings or settings
        self.storage_dir: Path = self.settings.metrics_storage_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._sessions: Dict[str, List[ChatMessage]] = {}
        self._metrics: Dict[str, MetricsAccumulator] = {}
        self._conversation_feedback: Dict[str, ConversationFeedback] = {}
        self._lock = Lock()

    # ----------------------------------------------------------------- sessions
    def log_message(self, session_id: str, message: ChatMessage) -> None:
        with self._lock:
            history = self._sessions.setdefault(session_id, [])
            history.append(message)
            metrics = self._metrics.setdefault(session_id, MetricsAccumulator(session_id=session_id))
            if message.role == "user":
                metrics.user_messages += 1
            elif message.role == "assistant":
                metrics.assistant_messages += 1
            metrics.updated_at = datetime.utcnow()
            self._persist_session(session_id)

    def get_session_history(self, session_id: str) -> List[ChatMessage]:
        with self._lock:
            return list(self._sessions.get(session_id, []))

    def list_sessions(self) -> List[str]:
        with self._lock:
            return sorted(self._sessions.keys())

    # ------------------------------------------------------------------- metrics
    def record_retrieval_latency(self, session_id: str, latency_ms: float) -> None:
        with self._lock:
            metrics = self._metrics.setdefault(session_id, MetricsAccumulator(session_id=session_id))
            metrics.retrieval_latencies.append(latency_ms)
            metrics.updated_at = datetime.utcnow()
            self._persist_session(session_id)

    def record_llm_latency(self, session_id: str, latency_ms: float) -> None:
        with self._lock:
            metrics = self._metrics.setdefault(session_id, MetricsAccumulator(session_id=session_id))
            metrics.llm_latencies.append(latency_ms)
            metrics.updated_at = datetime.utcnow()
            self._persist_session(session_id)

    def record_recommendations(self, session_id: str, products: Iterable[str]) -> None:
        with self._lock:
            metrics = self._metrics.setdefault(session_id, MetricsAccumulator(session_id=session_id))
            metrics.recommended_products.extend(products)
            metrics.updated_at = datetime.utcnow()
            self._persist_session(session_id)

    def record_feedback(self, session_id: str, message_id: str, feedback: str) -> None:
        with self._lock:
            metrics = self._metrics.setdefault(session_id, MetricsAccumulator(session_id=session_id))
            metrics.feedback[message_id] = feedback
            metrics.updated_at = datetime.utcnow()
            self._persist_session(session_id)

    def record_conversation_feedback(
        self, session_id: str, rating: int, comment: Optional[str] = None
    ) -> None:
        """Record user feedback for a complete conversation."""
        with self._lock:
            # Get products recommended in this session
            products = self._get_session_products(session_id)

            feedback = ConversationFeedback(
                session_id=session_id,
                rating=rating,
                comment=comment,
                products_recommended=products,
            )

            self._conversation_feedback[session_id] = feedback
            self._persist_session(session_id)

    def get_conversation_feedback(self, session_id: str) -> Optional[ConversationFeedback]:
        """Retrieve feedback for a specific conversation."""
        with self._lock:
            return self._conversation_feedback.get(session_id)

    def get_all_conversations(self) -> List[ConversationSummary]:
        """Get summaries of all conversations with feedback status."""
        with self._lock:
            conversations = []
            for session_id, metrics in self._metrics.items():
                history = self._sessions.get(session_id, [])
                first_user_msg = next(
                    (msg.content for msg in history if msg.role == "user"), None
                )

                conversations.append(
                    ConversationSummary(
                        session_id=session_id,
                        started_at=metrics.started_at,
                        updated_at=metrics.updated_at,
                        message_count=len(history),
                        products_recommended=metrics.recommended_products,
                        feedback=self._conversation_feedback.get(session_id),
                        first_user_message=first_user_msg,
                    )
                )

            # Sort by most recent first
            conversations.sort(key=lambda x: x.updated_at, reverse=True)
            return conversations

    def _get_session_products(self, session_id: str) -> List[str]:
        """Get list of products recommended in a session."""
        metrics = self._metrics.get(session_id)
        if metrics:
            return metrics.recommended_products
        return []

    def get_session_metrics(self, session_id: str) -> Optional[SessionMetrics]:
        with self._lock:
            accumulator = self._metrics.get(session_id)
            if not accumulator:
                return None
            return accumulator.to_session_metrics()

    def get_aggregate_metrics(self) -> AggregateMetrics:
        with self._lock:
            total_sessions = len(self._metrics)
            if total_sessions == 0:
                return AggregateMetrics(
                    total_sessions=0,
                    average_turns=0.0,
                    average_retrieval_latency_ms=0.0,
                    average_llm_latency_ms=0.0,
                    most_recommended_products=[],
                    positive_feedback_ratio=None,
                )

            total_turns = 0
            total_retrieval = 0.0
            total_llm = 0.0
            product_frequency: Dict[str, int] = {}
            total_feedback = 0
            positive_feedback = 0

            for metrics in self._metrics.values():
                total_turns += metrics.user_messages
                if metrics.retrieval_latencies:
                    total_retrieval += sum(metrics.retrieval_latencies) / len(metrics.retrieval_latencies)
                if metrics.llm_latencies:
                    total_llm += sum(metrics.llm_latencies) / len(metrics.llm_latencies)
                for sku in metrics.recommended_products:
                    product_frequency[sku] = product_frequency.get(sku, 0) + 1
                for sentiment in metrics.feedback.values():
                    total_feedback += 1
                    if sentiment == "positive":
                        positive_feedback += 1

            most_recommended = sorted(product_frequency.items(), key=lambda item: item[1], reverse=True)[:5]
            most_recommended_products = [sku for sku, _ in most_recommended]
            positive_ratio = (positive_feedback / total_feedback) if total_feedback else None

            return AggregateMetrics(
                total_sessions=total_sessions,
                average_turns=total_turns / total_sessions if total_sessions else 0.0,
                average_retrieval_latency_ms=total_retrieval / total_sessions if total_sessions else 0.0,
                average_llm_latency_ms=total_llm / total_sessions if total_sessions else 0.0,
                most_recommended_products=most_recommended_products,
                positive_feedback_ratio=positive_ratio,
            )

    # --------------------------------------------------------------------- export
    def export_csv(self) -> Path:
        export_path = self.storage_dir / "metrics_export.csv"
        with self._lock, export_path.open("w", newline="", encoding="utf-8") as handle:
            fieldnames = [
                "session_id",
                "turn_count",
                "avg_retrieval_latency_ms",
                "avg_llm_latency_ms",
                "recommended_products",
                "positive_feedback",
                "negative_feedback",
                "started_at",
                "updated_at",
            ]
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            for metrics in self._metrics.values():
                positive = sum(1 for sentiment in metrics.feedback.values() if sentiment == "positive")
                negative = sum(1 for sentiment in metrics.feedback.values() if sentiment == "negative")
                writer.writerow(
                    {
                        "session_id": metrics.session_id,
                        "turn_count": metrics.user_messages,
                        "avg_retrieval_latency_ms": self._safe_average(metrics.retrieval_latencies),
                        "avg_llm_latency_ms": self._safe_average(metrics.llm_latencies),
                        "recommended_products": ";".join(metrics.recommended_products),
                        "positive_feedback": positive,
                        "negative_feedback": negative,
                        "started_at": metrics.started_at.isoformat(),
                        "updated_at": metrics.updated_at.isoformat(),
                    }
                )
        return export_path

    # ------------------------------------------------------------------- internal
    def _persist_session(self, session_id: str) -> None:
        history = self._sessions.get(session_id)
        metrics = self._metrics.get(session_id)
        if not history or not metrics:
            return

        metrics_payload = {
            "session_id": metrics.session_id,
            "retrieval_latencies": metrics.retrieval_latencies,
            "llm_latencies": metrics.llm_latencies,
            "recommended_products": metrics.recommended_products,
            "feedback": metrics.feedback,
            "started_at": metrics.started_at.isoformat(),
            "updated_at": metrics.updated_at.isoformat(),
            "user_messages": metrics.user_messages,
            "assistant_messages": metrics.assistant_messages,
        }

        # Include conversation feedback if exists
        conversation_feedback = self._conversation_feedback.get(session_id)
        conversation_feedback_payload = (
            conversation_feedback.model_dump() if conversation_feedback else None
        )

        payload = {
            "session": [message.model_dump() for message in history],
            "metrics": metrics_payload,
            "conversation_feedback": conversation_feedback_payload,
        }
        path = self.storage_dir / f"{session_id}.json"
        with path.open("wb") as handle:
            handle.write(orjson.dumps(payload, option=orjson.OPT_INDENT_2))

    @staticmethod
    def _safe_average(values: Iterable[float]) -> float:
        values = list(values)
        if not values:
            return 0.0
        return sum(values) / len(values)
