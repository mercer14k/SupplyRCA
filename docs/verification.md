# Verification record

Build environment: macOS 26.6.2 / arm64, Python 3.12.14, Node 24.19.0. Exact benchmark environment is in each benchmark JSON; tool versions are pinned in lockfiles.

- Backend computational/API suite: run with pytest; coverage and counts in `verification.json`.
- PostgreSQL 16.2 native integration: saved investigations survive database reconnect; the supplied Compose role-initialization SQL was executed; the SELECT-only reader was denied DELETE.
- Frontend: ESLint, TypeScript, Vitest and production Vite build passed.
- Browser workflow: actual local API + UI; investigate, resolve a source PO, accept/annotate, retrieve, export Markdown, search raw records, view architecture; desktop and mobile overflow check passed.
- Source distribution and wheel: successfully built with the standard Python build backend. The default sample path and frontend are repository assets; standalone wheel users must configure SAMPLE_PATH to their own source bundle.
- Security: pip-audit found no known runtime dependency vulnerabilities at verification time; pnpm audit found no high/critical production advisories. This is a point-in-time advisory check, not a guarantee of security.
- Benchmark: both the committed default dataset and a generated 80-SKU performance dataset were actually processed. All figures are stored with machine/configuration metadata.

## Pending external gates

Docker Compose execution and GitHub Actions success are not asserted. The host has no container daemon. GitHub publication is intentionally deferred at the user’s request. Windows and real local-model inference have not been executed here. Refer to the live release checklist rather than interpreting source/configuration presence as verification.
