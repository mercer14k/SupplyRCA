# SupplyRCA contributor instructions

Use Python domain/services for business logic and React for presentation. The LLM must never calculate KPIs, invent evidence, execute SQL/shell, or mutate investigation state. Keep core operation model-free and local; do not add required cloud APIs.

Use the committed schemas and immutable datasets. Invalid records must produce visible validation errors and whole-bundle quarantine. Preserve append-only analyst reviews and idempotency checks.

Verification from repository root: `ruff check .`, `ruff format --check .`, `pytest`, `supplyrca-benchmark`. Frontend from `apps/web`: `pnpm lint`, `pnpm typecheck`, `pnpm test`, `pnpm build`; use `pnpm test:e2e` with the servers running for workflow changes. Docker verification: `docker compose up --build --wait` followed by `python scripts/smoke.py`.

Never fabricate benchmark results, deployment status, causal confidence, integration claims, or model evaluation success. Ground truth belongs only in the evaluation harness. Report container/CI checks as unverified when they have not run. Update dependency licenses and ADRs for material dependency or architecture changes. Synthetic data and no credentials only in Git.
