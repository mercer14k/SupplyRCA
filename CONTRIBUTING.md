# Contributing

SupplyRCA welcomes reproducible bug reports, domain corrections, tests and documentation. Use synthetic/redacted data only. Explain the operational decision affected, the expected behavior, a small reproducible input and the observed output. Do not include credentials, customer records or private supplier performance in public issues.

Install the native development environment described in README. Work on a branch. Domain changes belong in `packages/supplyrca`, not route handlers or UI components. Add regression tests for behavioral changes; preserve no-LLM operation and explicit evidence provenance. Update schema files and docs when contracts change. Do not silently replace the committed sample or benchmark results; document generator/config changes and regenerate outputs.

Before proposing a change:

```sh
ruff check .
ruff format --check .
pytest
supplyrca-benchmark
cd apps/web
pnpm lint && pnpm typecheck && pnpm test && pnpm build
```

Run browser tests for workflow changes and Compose smoke for deployment changes. Include exact commands, measured results, environment and any unverified limitations in your PR. New material dependencies require a license entry; architectural substitutions require an ADR. Model adapters may only extend optional local runtimes without changing domain calculations.

By contributing, you license your contribution under Apache-2.0. Follow CODE_OF_CONDUCT.md. Security issues should follow SECURITY.md rather than public disclosure of an exploit or private data.
