# API v1

OpenAPI: `/openapi.json`; interactive docs: `/docs` in demo mode. Token mode disables public docs. Liveness: `/health`. Readiness: `/ready` (database plus seeded dataset; no LLM dependency).

| Method | Route (under `/api/v1`) | Behavior |
|---|---|---|
| GET | `/config` | Execution mode and provider |
| GET | `/datasets` | Snapshot identifiers and validation reports |
| GET | `/datasets/{id}/validation` | Row/relational quality report |
| GET | `/datasets/{id}/overview` | Date coverage, dimensions and latest 28-day KPIs |
| GET | `/datasets/{id}/anomalies?offset=0&limit=50` | Rolling alerts from observations, never truth labels |
| GET | `/datasets/{id}/records?table=demand&q=SKU-001&offset=0&limit=50` | Searchable paginated raw records |
| PUT | `/datasets/{id}` | Import immutable JSON bundle; X-Filename for sanitized display name |
| POST | `/investigations` | Typed target KPI request; computes and persists investigation |
| GET | `/investigations?offset=0&limit=20` | Paginated archive |
| GET | `/investigations/{id}` | Frozen findings with current review projection and full history |
| PUT | `/investigations/{id}/hypotheses/{hypothesis_id}/review` | Accepted/rejected/annotated disposition and bounded note |
| GET | `/investigations/{id}/export?format=markdown` | Reproducible report; `json` also supported |

All versioned routes enforce bearer auth in token mode. Mutations additionally require `X-SupplyRCA-Client: analyst`; Origin, when present, must be configured. Investigation/review writes require `Idempotency-Key` (8–100 safe identifier characters). Dataset PUT is idempotent on snapshot ID and original-content hash; changing a snapshot returns 409. Pagination bounds are enforced; record page size ≤200, archive/alerts ≤100. Dataset listing is bounded only by the local store and is intended for small demo catalogs.

Request windows are 1–91 calendar days, but at least seven observed current days and fourteen baseline days are needed for inference. Baseline configuration is 14–90 days. Required grain coverage is ≥90%. Undefined KPI denominators and missing evidence return 422 with `insufficient_evidence`.

Error shape: `{"error":{"code":"...","message":"...","trace_id":"..."}}`. Each request has `X-Trace-ID`. Semantically invalid JSON imports return 422 containing `{dataset_id, validation}` because the quarantine report is the primary result. Syntactically malformed JSON returns a normal error and is not persisted. Raw uploads are never interpreted as filesystem paths or executable code.

The import format is a unified operational bundle, not a generic CSV chat upload. Transform ERP exports to the documented daily schema outside the API. No built-in enterprise connector is claimed.
