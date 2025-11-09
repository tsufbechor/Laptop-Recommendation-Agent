"""Metrics and analytics endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse

from ..models import AggregateMetrics, SessionMetrics
from ..services.metrics_service import MetricsService

router = APIRouter()


def _get_metrics_service(request: Request) -> MetricsService:
    try:
        return request.app.state.metrics_service
    except AttributeError as exc:
        raise HTTPException(status_code=500, detail="Metrics service not initialised") from exc


@router.get("/sessions")
async def list_sessions(request: Request) -> dict:
    metrics_service = _get_metrics_service(request)
    sessions = metrics_service.list_sessions()
    return {"sessions": sessions}


@router.get("/session/{session_id}", response_model=SessionMetrics)
async def get_session_metrics(session_id: str, request: Request) -> SessionMetrics:
    metrics_service = _get_metrics_service(request)
    metrics = metrics_service.get_session_metrics(session_id)
    if not metrics:
        raise HTTPException(status_code=404, detail="Session not found")
    return metrics


@router.get("/aggregate", response_model=AggregateMetrics)
async def get_aggregate(request: Request) -> AggregateMetrics:
    metrics_service = _get_metrics_service(request)
    return metrics_service.get_aggregate_metrics()


@router.get("/export")
async def export_metrics(request: Request) -> FileResponse:
    metrics_service = _get_metrics_service(request)
    csv_path = metrics_service.export_csv()
    return FileResponse(csv_path, media_type="text/csv", filename="metrics.csv")
