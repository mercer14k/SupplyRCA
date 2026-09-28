# ADR 001 — Bounded deterministic core and snapshot persistence

Status: accepted for v0.1.0.

Use FastAPI/Pydantic, Polars, SciPy, ruptures, SQLAlchemy and PostgreSQL. Keep the domain engine independent of HTTP, persistence and LLMs. Persist immutable JSON source snapshots and deterministic results, with append-only reviews. Offer SQLite for native development. Use a unified JSON bundle import with all-or-nothing validation and quarantine.

This keeps reproducibility, provenance and first-run setup simple. The tradeoff is whole-snapshot memory use and Python-side record search, unsuitable for a warehouse or multi-tenant production service. The 16 MiB API limit is a deliberate boundary. Large offline evaluations are supported without claiming that the API is a large-data ingestion platform.

The recommended statsmodels and scikit-learn packages are not included because v0.1 needs no fitted predictive ML model or additional time-series model. SciPy supplies tests/correlation; ruptures supplies PELT. Avoiding unused packages reduces maintenance and licensing surface. No model prediction is mislabeled as a computed result; the current product produces deterministic diagnostics, not forecasts.

The generated PO and transport records are daily cohorts with stable identifiers. A future event model should represent order creation, split receipts and physical transport legs before claiming enterprise operational fidelity. Database migrations, async job workers, tenant auth and calibrated causal models are explicitly deferred.
