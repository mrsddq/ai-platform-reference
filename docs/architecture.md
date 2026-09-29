# Architecture and data flow

This reference combines one FastAPI service, one vector store, a local embedding model, and an optional Ollama answer path. The selected vertical slice is document-grounded operations Q&A; it does not implement model training, registry promotion, or clinical inference.

## Ingestion

The caller sends a `source_id`, `version`, and text to `POST /documents` with an API key. The service validates input, computes a SHA-256 digest, splits text into passages, embeds them, and writes points to Qdrant. Stored payloads carry source ID, version, digest, passage number, and text. A response includes the digest, chunk count, and point IDs. This is the trace from an answer citation back to the supplied document version.

For real operations use, source IDs and versions must come from an approved document registry. A production workflow would authenticate the uploader independently of readers, record approvals, and keep the original immutable document alongside the index. This reference does not provide those workflow controls.

## Retrieval and answer

`POST /search` embeds the question and requests the highest-ranking passages from Qdrant. It returns scores and citation metadata; a similarity score is a ranking signal, not proof of factual relevance. `POST /answer` retrieves before any optional LLM call. An empty result yields an abstention. When Ollama is configured, retrieved passages are untrusted input: they can supply facts but cannot authorize tools or change system behavior. The tool path restricts source lookup to retrieved point IDs, but generated statements and citation use are not independently verified by the service.

Only the local synthetic fixtures are supported as demonstration content. They cover model release metadata, a vector-search incident drill, and retrieval policy. The service is an engineering exercise; it does not answer patient-specific questions.

## Operating boundaries

The FastAPI service and Qdrant are separate containers locally. Qdrant is internal to the Compose network. `GET /health/live` confirms the process is responsive; `GET /health/ready` checks dependent readiness. Metrics expose service activity to a monitoring system. The application API key is an elementary local gate, not a complete multi-tenant identity or authorization system.

The infrastructure manifests show how a cluster or cloud environment could host the same service. Apply them only after reviewing network access, image immutability, resource requests, secret delivery, vector-store persistence and backups, model-cache behavior, ingress TLS, and cost limits. The repository does not contain evidence of a real cluster deployment.

## Failure cases to test

1. Reject a missing or invalid API key and malformed/oversized documents.
2. Preserve source/version/digest across ingestion, search, and answer citations.
3. Abstain when evidence is absent; do not fill gaps with model priors.
4. Treat retrieved instructions as data, never authority for tool execution.
5. Show not-ready when Qdrant is unavailable; distinguish dependency failure from an empty collection.
6. Re-ingest and rollback a document version with predictable point identity and audit records.

The automated tests cover implemented behavior; the remaining items are production acceptance criteria where the implementation does not yet provide a control.
