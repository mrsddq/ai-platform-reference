"""Runtime configuration; credentials come only from environment variables."""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str | None = None
    api_key: str = ""
    collection: str = "platform_documents_v1"
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    ollama_url: str | None = None
    ollama_model: str = "qwen2.5:3b"
    min_score: float = 0.35
    max_document_chars: int = 20_000

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            qdrant_url=os.getenv("QDRANT_URL", cls.qdrant_url),
            qdrant_api_key=os.getenv("QDRANT_API_KEY") or None,
            api_key=os.getenv("API_KEY", ""),
            collection=os.getenv("COLLECTION", cls.collection),
            embedding_model=os.getenv("EMBEDDING_MODEL", cls.embedding_model),
            ollama_url=os.getenv("OLLAMA_URL") or None,
            ollama_model=os.getenv("OLLAMA_MODEL", cls.ollama_model),
            min_score=float(os.getenv("MIN_SCORE", "0.35")),
            max_document_chars=int(os.getenv("MAX_DOCUMENT_CHARS", "20000")),
        )
