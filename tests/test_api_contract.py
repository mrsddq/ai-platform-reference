"""API contract checks that run without a model download or external Qdrant."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from qdrant_client import QdrantClient

from platform_app.api import create_app
from platform_app.config import Settings

DATA = Path(__file__).resolve().parents[1] / "sample_data"
KEY = {"X-API-Key": "test-secret"}


class FakeEmbedder:
    dimension = 4

    def embed(self, texts: list[str]) -> list[list[float]]:
        groups = (
            ("canary", "training", "artifact", "release"),
            ("retrieval", "provenance", "passage", "document"),
            ("incident", "alert", "latency", "on-call"),
        )
        result = []
        for text in texts:
            lower = text.lower()
            vector = [float(sum(word in lower for word in group)) for group in groups]
            vector.append(float(not any(vector)))
            result.append(vector)
        return result


@pytest.fixture
def api():
    settings = Settings(
        qdrant_url=":memory:",
        qdrant_api_key=None,
        api_key="test-secret",
        collection="api_contract",
        embedding_model="unused-in-tests",
        ollama_url="http://127.0.0.1:11434",
        ollama_model="unused-in-tests",
        min_score=0.25,
        max_document_chars=1200,
    )
    qdrant = QdrantClient(":memory:")
    with TestClient(create_app(settings, qdrant=qdrant, embedder=FakeEmbedder())) as client:
        yield client, qdrant


def test_auth_and_document_limit(api):
    client, _ = api
    document = {"source_id": "release", "version": "v1", "text": "Canary release artifact."}
    for endpoint, payload in (
        ("/documents", document),
        ("/search", {"query": "canary"}),
        ("/answer", {"query": "canary"}),
    ):
        assert client.post(endpoint, json=payload).status_code == 401

    too_large = dict(document, text="Canary " * 200)
    assert client.post("/documents", json=too_large, headers=KEY).status_code in (413, 422)
    search = client.post("/search", json={"query": "canary"}, headers=KEY)
    assert search.status_code == 200
    assert search.json()["hits"] == []


def test_ingestion_is_idempotent_and_citations_are_versioned(api):
    client, _ = api
    document = {
        "source_id": "synthetic-oncology-release",
        "version": "v1",
        "text": (DATA / "oncology_model_release.txt").read_text(encoding="utf-8"),
    }
    first = client.post("/documents", json=document, headers=KEY)
    second = client.post("/documents", json=document, headers=KEY)
    assert first.status_code == second.status_code == 200
    assert first.json()["sha256"] == second.json()["sha256"]
    assert first.json()["point_ids"] == second.json()["point_ids"]
    assert first.json()["chunks"] == second.json()["chunks"]

    search = client.post(
        "/search", json={"query": "canary release artifact", "limit": 10}, headers=KEY
    )
    assert search.status_code == 200
    hits = search.json()["hits"]
    assert hits
    assert all(hit["source_id"] == document["source_id"] for hit in hits)
    assert all(hit["version"] == "v1" and hit["citation"] for hit in hits)
    assert all(hit["sha256"] == first.json()["sha256"] for hit in hits)
    assert len({hit["point_id"] for hit in hits}) == len(hits)


def test_versions_keep_distinct_provenance_and_conflicts_fail(api):
    client, _ = api
    base = {"source_id": "synthetic-release", "text": "Canary release artifact alpha."}
    v1 = client.post("/documents", json=dict(base, version="v1"), headers=KEY)
    v2 = client.post(
        "/documents",
        json=dict(base, version="v2", text="Canary release artifact beta."),
        headers=KEY,
    )
    conflict = client.post(
        "/documents",
        json=dict(base, version="v1", text="Canary release artifact changed."),
        headers=KEY,
    )
    assert v1.status_code == v2.status_code == 200
    assert conflict.status_code == 409
    assert v1.json()["sha256"] != v2.json()["sha256"]

    search = client.post(
        "/search", json={"query": "canary release artifact", "limit": 10}, headers=KEY
    )
    assert search.status_code == 200
    hits = search.json()["hits"]
    assert {hit["version"] for hit in hits} == {"v1", "v2"}
    for hit in hits:
        assert hit["citation"] == f"[synthetic-release@{hit['version']}#chunk-{hit['chunk_index']}]"
        assert hit["sha256"] == (v1 if hit["version"] == "v1" else v2).json()["sha256"]


def test_synthetic_documents_retrieve_their_own_topics(api):
    client, _ = api
    cases = (
        ("oncology_model_release.txt", "canary training artifact"),
        ("oncology_retrieval_policy.txt", "retrieval provenance passage"),
        ("oncology_platform_incident.txt", "incident alert latency"),
    )
    for filename, _ in cases:
        response = client.post(
            "/documents",
            json={
                "source_id": filename,
                "version": "v1",
                "text": (DATA / filename).read_text(encoding="utf-8"),
            },
            headers=KEY,
        )
        assert response.status_code == 200
    for filename, query in cases:
        response = client.post("/search", json={"query": query, "limit": 1}, headers=KEY)
        assert response.status_code == 200
        assert response.json()["hits"][0]["source_id"] == filename


def test_no_hits_abstains_without_an_llm_call(api):
    client, _ = api
    assert client.post(
        "/documents",
        json={"source_id": "release", "version": "v1", "text": "Canary release artifact."},
        headers=KEY,
    ).status_code == 200
    response = client.post("/answer", json={"query": "planetary zebras"}, headers=KEY)
    assert response.status_code == 200
    assert response.json()["answer"] is None
    assert response.json()["citations"] == []
    assert response.json()["mode"] == "abstain"


def test_metrics_do_not_expose_document_text(api):
    client, _ = api
    marker = "SyntheticPrivateMarker739"
    assert client.post(
        "/documents",
        json={"source_id": "metrics-doc", "version": "v1", "text": f"Canary release {marker}."},
        headers=KEY,
    ).status_code == 200
    metrics = client.get("/metrics")
    assert metrics.status_code == 200
    assert marker not in metrics.text


def test_readiness_fails_when_vector_store_is_unavailable(api, monkeypatch):
    client, qdrant = api
    assert client.get("/health/live").status_code == 200
    assert client.get("/health/ready").status_code == 200

    def unavailable():
        raise ConnectionError("synthetic outage")

    monkeypatch.setattr(qdrant, "get_collections", unavailable)
    assert client.get("/health/live").status_code == 200
    assert client.get("/health/ready").status_code == 503
