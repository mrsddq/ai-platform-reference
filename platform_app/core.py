"""Versioned document ingestion and vector retrieval."""

import hashlib
import re
import textwrap
import uuid
from typing import Protocol

from qdrant_client import QdrantClient, models

from platform_app.config import Settings


class Embedder(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]: ...


class FastEmbedder:
    def __init__(self, model_name: str):
        from fastembed import TextEmbedding

        self.model = TextEmbedding(model_name=model_name)

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [vector.tolist() for vector in self.model.embed(texts)]


def split_text(text: str) -> list[str]:
    normalized = re.sub(r"\s+", " ", text).strip()
    return textwrap.wrap(normalized, 700, break_long_words=False, break_on_hyphens=False)


class Platform:
    def __init__(
        self,
        settings: Settings,
        *,
        qdrant: QdrantClient | None = None,
        embedder: Embedder | None = None,
    ):
        self.settings = settings
        self.qdrant = qdrant or QdrantClient(
            url=settings.qdrant_url, api_key=settings.qdrant_api_key, timeout=5
        )
        self.embedder = embedder or FastEmbedder(settings.embedding_model)

    def ready(self) -> bool:
        self.qdrant.get_collections()
        return True

    def _create_collection(self, dimension: int) -> None:
        if not self.qdrant.collection_exists(self.settings.collection):
            self.qdrant.create_collection(
                collection_name=self.settings.collection,
                vectors_config=models.VectorParams(size=dimension, distance=models.Distance.COSINE),
            )

    def ingest(self, source_id: str, version: str, text: str) -> dict:
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        chunks = split_text(text)
        vectors = self.embedder.embed(chunks)
        self._create_collection(len(vectors[0]))

        old, _ = self.qdrant.scroll(
            collection_name=self.settings.collection,
            scroll_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="source_id", match=models.MatchValue(value=source_id)
                    ),
                    models.FieldCondition(key="version", match=models.MatchValue(value=version)),
                ]
            ),
            limit=1,
            with_payload=True,
        )
        if old and old[0].payload["sha256"] != digest:
            raise ValueError("Source version already exists with different content")

        point_ids: list[str] = []
        points = []
        for index, (chunk, vector) in enumerate(zip(chunks, vectors, strict=True), start=1):
            point_id = str(
                uuid.uuid5(uuid.NAMESPACE_URL, f"{source_id}/{version}/{digest}/{index}")
            )
            point_ids.append(point_id)
            points.append(
                models.PointStruct(
                    id=point_id,
                    vector=vector,
                    payload={
                        "source_id": source_id,
                        "version": version,
                        "sha256": digest,
                        "chunk_index": index,
                        "text": chunk,
                        "embedding_model": self.settings.embedding_model,
                    },
                )
            )
        self.qdrant.upsert(collection_name=self.settings.collection, points=points, wait=True)
        return {
            "source_id": source_id,
            "version": version,
            "sha256": digest,
            "chunks": len(chunks),
            "point_ids": point_ids,
        }

    def search(self, query: str, limit: int = 5) -> list[dict]:
        if not self.qdrant.collection_exists(self.settings.collection):
            return []
        vector = self.embedder.embed([query])[0]
        points = self.qdrant.query_points(
            collection_name=self.settings.collection,
            query=vector,
            limit=limit,
            score_threshold=self.settings.min_score,
            with_payload=True,
        ).points
        return [
            {
                "point_id": str(point.id),
                "score": round(point.score, 4),
                "source_id": point.payload["source_id"],
                "version": point.payload["version"],
                "sha256": point.payload["sha256"],
                "chunk_index": point.payload["chunk_index"],
                "text": point.payload["text"],
                "citation": (
                    f"[{point.payload['source_id']}@{point.payload['version']}"
                    f"#chunk-{point.payload['chunk_index']}]"
                ),
            }
            for point in points
        ]
