# Operations runbook

## Start and verify

1. Set `API_KEY` to a strong development value. Check Docker availability and run `docker compose up --build --wait --wait-timeout 300`.
2. Wait for `/health/ready` to succeed. Inspect `docker compose ps` and service logs if it fails. First embedding-model initialization can take longer than a routine restart.
3. Run `./scripts/demo.ps1` or send the documented requests manually. Confirm the returned citation identifies the expected source and version.
4. Run tests and the evaluation fixture before any release. Review CI results and dependency changes.

## Release and rollback

Build and scan an image from a reviewed commit, record its immutable digest, and publish it to a trusted registry. Keep the image digest, embedding model identifier, collection schema, and document versions together in the release record. Validate a candidate in a non-production environment, then monitor error rate, p95 latency, readiness, and resource use after promotion. Rollback restores the previous image and matching configuration. If an embedding-model change alters vector dimensions or scoring behavior, rebuild a separate collection and switch only after reindexing and evaluation; do not mix embeddings in one collection.

Terraform and Helm assets are references. A cloud deployment also needs reviewed credentials, network controls, encrypted persistent storage, backup verification, TLS, secret management, autoscaling tests, and incident ownership. No such rollout is claimed here.

## Triage

| Symptom | Check | Immediate action |
| --- | --- | --- |
| Readiness fails | Qdrant status, service logs, collection creation, connectivity | Keep traffic off the pod; restore dependency before retrying. |
| Ingestion fails | Authentication, payload validation, embedding/model availability, Qdrant writes | Preserve original document and error details; retry only after root cause is known. |
| Search quality drops | Document versions, collection size, embedding model, evaluation cases | Stop promotion, compare with last known-good collection, reindex if model changed. |
| Answers lack citations or invent detail | Retrieved passages, agent trace, abstention path | Disable optional LLM path and serve retrieval evidence while investigating. |
| Latency rises | p95 endpoint latency, vector-store load, model initialization, resource limits | Cap request size/concurrency; scale only after identifying the bottleneck. |

Record onset, affected route, commit/image digest, collection state, hypothesis, mitigation, recovery check, and follow-up in the incident record. Never paste sensitive documents or keys into tickets.

## Backup and recovery

For a real installation, back up source documents and Qdrant state with a documented restore drill. A vector index alone is not authoritative source data. Test restoration into a separate environment, check passage counts and source/version metadata, and run the evaluation cases before redirecting traffic. The local Compose demo can be rebuilt from its synthetic fixtures.
