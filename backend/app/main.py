"""FastAPI application entry point with service lifecycle management."""

from __future__ import annotations

import logging
import sys
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .routers import chat, metrics
from .services.llm_service import LLMService
from .services.metrics_service import MetricsService
from .services.rag_service import RAGService


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler("app.log")],
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    logger.info("Starting Automatiq.ai backend services.")
    try:
        rag_service = RAGService(settings)
        logger.info("RAG service initialized.")

        metrics_service = MetricsService(settings)
        logger.info("Metrics service initialized.")

        llm_service = LLMService(settings)
        logger.info("LLM service initialized.")

        app.state.rag_service = rag_service
        app.state.metrics_service = metrics_service
        app.state.llm_service = llm_service

        logger.info("All services initialized successfully.")
        yield
    except Exception as exc:
        logger.error("Failed to initialize services: %s", exc, exc_info=True)
        raise
    finally:
        logger.info("Shutting down services.")


app = FastAPI(title="Automatiq.ai Product Advisor", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(metrics.router, prefix="/api/metrics", tags=["metrics"])
