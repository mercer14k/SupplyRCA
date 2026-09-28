# Architecture

SupplyRCA is a synchronous, single-analyst reference implementation. The bounded local workflow is intentional: API requests never turn into unconstrained agent loops.

## Boundaries

- `domain/schemas.py`: strict record/request/response contracts; generated JSON Schemas live in `data/schemas`.
- `data/generate.py`: fixed-seed two-year simulator and separate ground-truth file.
- `data/validation.py`: record schemas, stable-ID uniqueness, natural grain uniqueness, supplier/PO foreign keys, per-day and across-day inventory reconciliation.
- `data/store.py`: SQLAlchemy tables and parameterized SQL, immutable datasets, transactional investigation inserts, unique idempotency keys, append-only reviews.
- `domain/analysis.py`: no network, database, model, truth-file or UI dependency. Produces serializable deterministic findings.
- `services/investigations.py`: orchestrates retrieval, cached Polars assembly, analysis, narrative and persistence. Only valid snapshots enter the cache.
- `ai/narrative.py`: replaceable local runtime protocol, output validation, citation checking and bounded retry/fallback.
- `apps/api/main.py`: versioned transport, auth, size/origin limits, errors, trace IDs, readiness.
- `apps/web`: typed API client and analytical UI. No KPI or support calculations are delegated to the browser; only formatting and chart presentation occur there.
- `evaluation/benchmark.py`: consumes truth only for scoring, invokes the exact production computational engine.

## Investigation lifecycle

A validated request identifies an immutable dataset, target KPI, dates and optional SKU/market. A matching idempotency key returns the existing investigation. Otherwise the service joins source tables at daily SKU–market–supplier grain, checks temporal coverage, computes findings, hashes the deterministic result, generates a cited narrative and saves the complete snapshot in one transaction.

Concurrent duplicate investigation requests may compute twice, but a database unique constraint preserves one result. A key with a different request hash returns 409. Review events are separately committed and overlaid on read; the deterministic result stored in the database remains unchanged. Annotation is currently a disposition (`annotated`), replacing the displayed accepted/rejected state; the complete history preserves prior decisions.

## Storage and scale

Compose uses PostgreSQL JSON snapshots and read/write role separation. Native development defaults to SQLite. The data model optimizes simple reproducibility over analytical warehouse scale: snapshots are loaded as whole bundles and each service caches at most four assembled frames. Uploads are capped at 16 MiB. SQL JSON snapshots plus Python-side search are unsuitable for large production datasets; use the offline generator/harness for larger tests.

One Uvicorn process handles the demo; blocking diagnostics run in FastAPI's threadpool. The request concurrency limit is 32. There is no durable distributed queue, tenant boundary, cancellation API or rate limiter. Do not use this design as a high-concurrency hosted service without addressing those limitations.

## Failure behavior

Invalid JSON yields 422 without ingestion. Schema/relational failures yield a quarantined immutable bundle and visible row-level report. Insufficient temporal evidence yields a typed 422, not zero-valued metrics. Unavailable AI or invalid structured outputs cannot change deterministic findings and falls back to the template. Readiness depends on the database and validated sample, never a model runtime.
