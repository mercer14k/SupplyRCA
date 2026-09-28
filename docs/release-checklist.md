# Release checklist

This checklist records verification, not an assertion that every deployment environment has been tested.

- [x] Repository architecture, strict schemas, provenance and deterministic sample generator.
- [x] Committed 24-month sample with 40 isolated operational failures and separate truth.
- [x] Working deterministic KPI/decomposition/statistical/hypothesis workflow.
- [x] Persistence, validation quarantine, typed API, idempotency and analyst review history.
- [x] React analytical interface with source evidence, archive, report export and responsive layout.
- [x] No-LLM mode; local-runtime abstraction, schema/citation checks and safe fallback tests.
- [x] Actual benchmark JSON/CSV/Markdown committed with hardware/configuration metadata.
- [x] Larger generated performance run measured (233,924 records / 400 incidents).
- [x] Backend lint, frontend lint/type checking/tests/build, browser end-to-end tests.
- [x] Desktop/mobile screenshots from the working app.
- [x] Dependency locks, vulnerability checks, documented licenses and model terms.
- [x] Threat model, contribution guide, code of conduct, security disclosure policy and ADRs.
- [x] PostgreSQL 16.2 native integration: persistence survives reconnect; final API tests pass. Compose PostgreSQL 17 remains a CI gate.
- [ ] Docker Compose build/start verified on a host with an available container daemon.
- [ ] Public GitHub publication — intentionally deferred at the user’s request.
- [ ] GitHub Actions execution — deferred until publication; equivalent native checks have passed.

## Environment limits

The build host has no Docker daemon or Docker CLI. Container files and Compose CI coverage are supplied; native verification does not substitute for an actual container run. Windows development commands are documented but have not been run on Windows. No real local-model inference is claimed unless separately recorded; the example benchmark uses template narratives. A successful local test run must not be reported as a successful GitHub Actions run.

## Public release review

Before tagging a release, ensure the two deployment gates above pass, inspect Git status for accidental local data/secrets, verify README metrics against committed benchmark JSON, enable private vulnerability reporting on GitHub, and pin container images/actions to reviewed digests if required by release policy. Default sample data is synthetic and contains no customer information. Do not include `.env`, database files, generated large datasets, dependency directories or browser session artifacts in a release archive.
