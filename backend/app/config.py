"""Application configuration and settings management."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional

from pydantic import Field, validator
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parent


class AppSettings(BaseSettings):
    """Runtime configuration for the backend services."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    gemini_api_key: Optional[str] = Field(default=None, alias="GEMINI_API_KEY")
    embedding_model: str = Field(default="models/embedding-001", alias="EMBEDDING_MODEL")
    llm_model: str = Field(default="gemini-2.5-pro", alias="LLM_MODEL")
    vector_store_path: Path = Field(
        default=BASE_DIR / "data" / "embeddings.npy", alias="VECTOR_STORE_PATH"
    )
    products_path: Path = Field(
        default=BASE_DIR / "data" / "products.json", alias="PRODUCTS_PATH"
    )
    max_history_messages: int = Field(default=6, alias="MAX_HISTORY_MESSAGES")
    rag_top_k: int = Field(default=5, alias="RAG_TOP_K")
    enable_hybrid_search: bool = Field(default=True, alias="ENABLE_HYBRID_SEARCH")
    metrics_storage_dir: Path = Field(
        default=BASE_DIR / "data" / "metrics", alias="METRICS_STORAGE_DIR"
    )

    @validator("embedding_model", pre=True)
    def _normalise_embedding_model(cls, value: Any) -> str:
        if isinstance(value, str) and not value.startswith(("models/", "tunedModels/")):
            return f"models/{value}"
        return value

    @validator("llm_model", pre=True)
    def _normalise_llm_model(cls, value: Any) -> str:
        if isinstance(value, str):
            return value.replace("models/", "").replace("tunedModels/", "")
        return value

    @validator("vector_store_path", "products_path", "metrics_storage_dir", pre=True)
    def _resolve_path(cls, value: Any) -> Path:
        path = Path(value)
        if not path.is_absolute():
            path = (BASE_DIR / path).resolve()
        return path

    def as_dict(self) -> Dict[str, Any]:
        """Return settings as a serialisable dictionary."""
        return {
            "embedding_model": self.embedding_model,
            "llm_model": self.llm_model,
            "vector_store_path": str(self.vector_store_path),
            "products_path": str(self.products_path),
            "rag_top_k": self.rag_top_k,
            "max_history_messages": self.max_history_messages,
            "enable_hybrid_search": self.enable_hybrid_search,
        }


@lru_cache
def get_settings() -> AppSettings:
    """Return cached application settings."""
    settings = AppSettings()
    settings.metrics_storage_dir.mkdir(parents=True, exist_ok=True)
    return settings


settings = get_settings()
