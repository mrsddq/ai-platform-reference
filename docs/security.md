# Security and data handling

The included documents are synthetic operations notes. Do not ingest patient data, personal records, secrets, or proprietary documents into the public demo.

## Local controls

- The write, search, and answer routes require `X-API-Key`; keep `API_KEY` out of source control and terminal transcripts.
- Compose keeps Qdrant off the public host interface. Expose the API only on a trusted local interface during the demo.
- Each indexed passage includes source/version/digest provenance so a reviewer can identify the source of a result.
- Retrieved passages are untrusted content. The service must not let a passage authorize external actions or override the platform instructions.
- Dependency readiness is separate from liveness; a failed vector store should not appear healthy for traffic.

The Ollama system prompt asks for citations and refusal of medical advice, but a prompt is not a validated safety control. Review generated content and add independent output checks before any sensitive use.

These controls are suitable for a local exercise. A production deployment needs a real identity provider, separate ingestion/read permissions, tenant isolation, TLS, network policies, egress restrictions, secret rotation, audit retention, encrypted backups, vulnerability scanning, a reviewed model supply chain, prompt-injection tests, and privacy review. Kubernetes Secrets alone are not a substitute for an external secret manager.

## Logging and observability

Log request identifiers, operation, status, latency, and source IDs where necessary. Avoid raw document text, API keys, prompts, and generated answers in routine logs or metrics. Metrics should aggregate counts and durations without sensitive labels. Incident traces and evaluation samples need a defined retention policy before production use.

## Clinical boundary

The sample oncology setting is only a synthetic operations scenario. The platform is not evaluated for diagnosis, triage, treatment, or patient outcomes. Clinical use would require validated datasets, risk management, clinical review, regulatory assessment, security review, and controlled release evidence outside this repository.
