"""Chat endpoints for interacting with the recommendation agent."""

from __future__ import annotations

import asyncio
import logging
import re
import time
import uuid
from typing import Any, Dict, List, Optional, Sequence

from fastapi import APIRouter, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.encoders import jsonable_encoder

from ..config import settings
from ..models import (
    ChatMessage,
    ChatRequest,
    ChatResponse,
    ChatResponseMetadata,
    ConversationSummary,
    FeedbackRequest,
    FeedbackSubmitRequest,
    RetrievedProduct,
    SessionHistoryResponse,
)
from ..services.llm_service import LLMResult, LLMService
from ..services.metrics_service import MetricsService
from ..services.rag_service import RAGService

logger = logging.getLogger(__name__)
router = APIRouter()


# --------------------------------------------------------------------------- utils
def _get_rag_service(request: Request) -> RAGService:
    try:
        return request.app.state.rag_service
    except AttributeError as exc:
        raise HTTPException(status_code=500, detail="RAG service not initialised") from exc


def _get_llm_service(request: Request) -> LLMService:
    try:
        return request.app.state.llm_service
    except AttributeError as exc:
        raise HTTPException(status_code=500, detail="LLM service not initialised") from exc


def _get_metrics_service(request: Request) -> MetricsService:
    try:
        return request.app.state.metrics_service
    except AttributeError as exc:
        raise HTTPException(status_code=500, detail="Metrics service not initialised") from exc


def _trim_history(history: Sequence[ChatMessage], limit: int) -> List[ChatMessage]:
    if limit <= 0:
        return list(history)
    return list(history[-limit:])


def _extract_price_from_query(query: str) -> Optional[float]:
    """Extract maximum price constraint from natural language query."""
    # Patterns to match: "under $1500", "max $2000", "below 1400 usd", "under 1,500", etc.
    patterns = [
        r"(?:under|below|max|maximum|up\s+to)\s*\$?\s*([0-9,]+(?:\.[0-9]{2})?)\s*(?:usd|dollars?)?",
        r"\$?\s*([0-9,]+(?:\.[0-9]{2})?)\s*(?:or\s+)?(?:less|under|below|max)",
    ]

    query_lower = query.lower()
    for pattern in patterns:
        match = re.search(pattern, query_lower)
        if match:
            price_str = match.group(1).replace(",", "")
            try:
                return float(price_str)
            except ValueError:
                continue
    return None


def _enrich_preferences_with_budget(message: str, user_preferences: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Extract budget from query and add to user preferences."""
    preferences = user_preferences.copy() if user_preferences else {}

    # Only extract if not already specified
    if "price_max" not in preferences:
        max_price = _extract_price_from_query(message)
        if max_price:
            preferences["price_max"] = max_price

    return preferences


def _prepare_assistant_message(session_id: str, reply: str) -> ChatMessage:
    return ChatMessage(role="assistant", content=reply, id=f"{session_id}-assistant-{uuid.uuid4()}")


def _prepare_user_message(session_id: str, content: str) -> ChatMessage:
    return ChatMessage(role="user", content=content, id=f"{session_id}-user-{uuid.uuid4()}")


def _record_metrics_for_recommendations(
    metrics_service: MetricsService, session_id: str, llm_result: LLMResult
) -> None:
    recommended_skus = [item.sku for item in llm_result.recommendations]
    metrics_service.record_recommendations(session_id, recommended_skus)


def _assemble_response_products(
    llm_service: LLMService, retrieved_products: Sequence[RetrievedProduct], llm_result: LLMResult
) -> List[RetrievedProduct]:
    return llm_service.merge_recommendations(retrieved_products, llm_result)


def _enrich_products_with_knowledge(
    rag_service: RAGService, products: List[RetrievedProduct]
) -> List[RetrievedProduct]:
    """Attach knowledge base data to each product."""
    for product in products:
        knowledge = rag_service.get_product_knowledge(product.sku)
        if knowledge:
            product.knowledge = knowledge
    return products


# --------------------------------------------------------------------------- routes
@router.post("/message", response_model=ChatResponse)
async def post_message(payload: ChatRequest, request: Request) -> ChatResponse:
    rag_service = _get_rag_service(request)
    llm_service = _get_llm_service(request)
    metrics_service = _get_metrics_service(request)

    session_id = payload.session_id
    if not payload.message.strip():
        raise HTTPException(status_code=400, detail="Message must not be empty.")

    user_message = _prepare_user_message(session_id, payload.message)
    metrics_service.log_message(session_id, user_message)

    history = metrics_service.get_session_history(session_id)
    trimmed_history = _trim_history(history, settings.max_history_messages * 2)

    # Enrich preferences with budget extracted from query
    enriched_preferences = _enrich_preferences_with_budget(payload.message, payload.user_preferences)

    retrieval_result = await asyncio.to_thread(
        rag_service.search,
        payload.message,
        enriched_preferences,
        settings.rag_top_k,
    )
    metrics_service.record_retrieval_latency(session_id, retrieval_result.latency_ms)

    llm_start = time.perf_counter()
    llm_result = await llm_service.generate(trimmed_history, retrieval_result.products)
    llm_latency_ms = (time.perf_counter() - llm_start) * 1000
    metrics_service.record_llm_latency(session_id, llm_latency_ms)
    _record_metrics_for_recommendations(metrics_service, session_id, llm_result)

    products = _assemble_response_products(llm_service, retrieval_result.products, llm_result)
    products = _enrich_products_with_knowledge(rag_service, products)

    assistant_message = _prepare_assistant_message(session_id, llm_result.reply)
    metrics_service.log_message(session_id, assistant_message)

    metadata = ChatResponseMetadata(
        retrieval_latency_ms=retrieval_result.latency_ms,
        llm_latency_ms=llm_latency_ms,
        top_k=settings.rag_top_k,
        applied_filters=retrieval_result.applied_filters,
    )

    # DISABLED: Comparison generation removed for performance
    comparison = None

    return ChatResponse(
        reply=llm_result.reply,
        products_shown=products,
        reasoning=llm_result.reasoning,
        metadata=metadata,
        comparison=comparison,
    )


@router.get("/history/{session_id}", response_model=SessionHistoryResponse)
async def get_history(session_id: str, request: Request) -> SessionHistoryResponse:
    metrics_service = _get_metrics_service(request)
    history = metrics_service.get_session_history(session_id)
    return SessionHistoryResponse(session_id=session_id, messages=history)


@router.post("/feedback")
async def post_feedback(payload: FeedbackRequest, request: Request) -> dict:
    metrics_service = _get_metrics_service(request)
    metrics_service.record_feedback(payload.session_id, payload.message_id, payload.feedback)
    return {"status": "ok"}


@router.post("/feedback/submit")
async def submit_conversation_feedback(payload: FeedbackSubmitRequest, request: Request) -> dict:
    """Submit user feedback for a conversation."""
    metrics_service = _get_metrics_service(request)

    # Validate session exists
    history = metrics_service.get_session_history(payload.session_id)
    if not history:
        raise HTTPException(status_code=404, detail="Session not found")

    metrics_service.record_conversation_feedback(
        payload.session_id, payload.rating, payload.comment
    )

    return {"status": "ok", "message": "Feedback recorded successfully"}


@router.get("/conversations", response_model=List[ConversationSummary])
async def get_all_conversations(request: Request) -> List[ConversationSummary]:
    """Get all past conversations with feedback."""
    metrics_service = _get_metrics_service(request)
    return metrics_service.get_all_conversations()


@router.get("/conversations/{session_id}", response_model=SessionHistoryResponse)
async def get_conversation_detail(session_id: str, request: Request) -> SessionHistoryResponse:
    """Get detailed conversation history."""
    metrics_service = _get_metrics_service(request)
    history = metrics_service.get_session_history(session_id)

    if not history:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return SessionHistoryResponse(session_id=session_id, messages=history)


@router.websocket("/stream")
async def websocket_stream(websocket: WebSocket) -> None:
    session_id = "unknown"
    await websocket.accept()
    try:
        init_payload = await websocket.receive_json()
    except Exception:  # pragma: no cover - defensive
        await websocket.close(code=1003)
        return

    session_id = str(init_payload.get("session_id", "")).strip() or "unknown"
    message = init_payload.get("message")
    user_preferences = init_payload.get("user_preferences")
    if not session_id or not message:
        await websocket.close(code=1008)
        return

    if not str(message).strip():
        await websocket.close(code=1008, reason="Message must not be empty")
        return

    app = websocket.app
    rag_service: RAGService = app.state.rag_service  # type: ignore[attr-defined]
    llm_service: LLMService = app.state.llm_service  # type: ignore[attr-defined]
    metrics_service: MetricsService = app.state.metrics_service  # type: ignore[attr-defined]

    try:
        user_message = _prepare_user_message(session_id, message)
        metrics_service.log_message(session_id, user_message)
        history = metrics_service.get_session_history(session_id)
        trimmed_history = _trim_history(history, settings.max_history_messages * 2)

        enriched_preferences = _enrich_preferences_with_budget(message, user_preferences)
        retrieval_result = await asyncio.to_thread(
            rag_service.search,
            message,
            enriched_preferences,
            settings.rag_top_k,
        )
        metrics_service.record_retrieval_latency(session_id, retrieval_result.latency_ms)

        metadata_payload = jsonable_encoder(
            {
                "retrieval_latency_ms": retrieval_result.latency_ms,
                "filters": retrieval_result.applied_filters,
            },
            by_alias=False,
        )
        await websocket.send_json({"type": "metadata", "data": metadata_payload})

        llm_latency_ms = 0.0
        llm_start = time.perf_counter()
        accumulated_reply = ""
        try:
            async for chunk in llm_service.stream(trimmed_history, retrieval_result.products):
                accumulated_reply += chunk
                await websocket.send_json({"type": "chunk", "data": chunk})
        except WebSocketDisconnect:
            raise
        finally:
            llm_latency_ms = (time.perf_counter() - llm_start) * 1000
            metrics_service.record_llm_latency(session_id, llm_latency_ms)

        logger.info("[TIMING] Streaming complete for session %s", session_id)

        parse_start = time.perf_counter()
        llm_result = llm_service.parse(accumulated_reply, retrieval_result.products)
        parse_ms = (time.perf_counter() - parse_start) * 1000
        logger.info("[TIMING] Parse took %.2fms for session %s", parse_ms, session_id)

        _record_metrics_for_recommendations(metrics_service, session_id, llm_result)

        assemble_start = time.perf_counter()
        products = _assemble_response_products(llm_service, retrieval_result.products, llm_result)
        assemble_ms = (time.perf_counter() - assemble_start) * 1000
        logger.info("[TIMING] Assemble products took %.2fms for session %s", assemble_ms, session_id)

        enrich_start = time.perf_counter()
        products = _enrich_products_with_knowledge(rag_service, products)
        enrich_ms = (time.perf_counter() - enrich_start) * 1000
        logger.info("[TIMING] Enrich knowledge took %.2fms for session %s", enrich_ms, session_id)

        assistant_message = _prepare_assistant_message(session_id, llm_result.reply)
        metrics_service.log_message(session_id, assistant_message)

        comparison = None  # Comparison generation disabled for performance reasons

        response_data = jsonable_encoder(
            {
                "reply": llm_result.reply,
                "reasoning": llm_result.reasoning,
                "llm_latency_ms": llm_latency_ms,
                "products": products,
                "comparison": comparison,
            },
            by_alias=False,
        )

        send_start = time.perf_counter()
        await websocket.send_json({"type": "complete", "data": response_data})
        send_ms = (time.perf_counter() - send_start) * 1000
        logger.info("[TIMING] Send complete message took %.2fms for session %s", send_ms, session_id)

        total_post_stream_ms = (time.perf_counter() - parse_start) * 1000
        logger.info(
            "[TIMING] TOTAL post-streaming processing: %.2fms for session %s",
            total_post_stream_ms,
            session_id,
        )
        await websocket.close()
    except WebSocketDisconnect:
        logger.info("Client disconnected during streaming session %s", session_id)
    except Exception as exc:  # pragma: no cover - defensive
        logger.error("Streaming session failed for %s: %s", session_id, exc, exc_info=True)
        error_payload = jsonable_encoder(
            {"message": "I ran into an issue finalising that recommendation. Please try again."},
            by_alias=False,
        )
        try:
            await websocket.send_json({"type": "error", "data": error_payload})
        except Exception:
            pass
        try:
            await websocket.close(code=1011)
        except Exception:
            pass


