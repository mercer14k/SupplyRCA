# Evaluation and performance

Run `supplyrca-benchmark --output artifacts/benchmark` from the repository root after installing the Python package. The harness validates the committed dataset, joins source tables, calls the production `analyze` and `narrate` functions, and compares findings with separately loaded truth. No cause label or incident ID enters `analyze`.

Outputs: `benchmark.json` (metadata, aggregate metrics and every episode), `episodes.csv`, and `summary.md`. The committed `docs/benchmarks/example` is a measured run, with its actual OS, CPU architecture/count, Python/dependency versions, generator seed/version, runtime/model configuration and input checksum. `docs/benchmarks/performance` is the same harness against an 80-SKU/400-incident generated dataset.

| Metric | Definition |
|---|---|
| Known-cause top-1/top-3 recovery | Share of seeded episodes with the expected cause in the first one/three ranked hypotheses |
| False contributor rate | Unsupported returned contributors / all returned contributors, including healthy control windows |
| Healthy-window false alert rate | Healthy control windows returning any supported hypothesis / all controls |
| Change-point recall ±7 days | Incidents with at least one detected point within seven days of the operational onset |
| Onset error | Mean minimum absolute distance from a detected point to the operational onset, excluding episodes with no detected point; recall separately captures those misses |
| Narrative citation coverage | Claims with nonempty resolvable evidence references / all claims |
| Time to diagnosis | Wall time of analysis + narrative; median and nearest-rank P95 |

The first benchmark evaluates 40 incidents and 16 control windows using fixed seed 42. Thresholds and generator mechanisms are hand-designed; this is an in-family regression and reproducibility benchmark, not a held-out causal discovery benchmark. The stronger next test is recovery on independently generated/noisy/mixed mechanisms and real operational data with independently adjudicated labels.

Mann–Whitney p-values assume independent observations, whereas daily data has serial dependence. BH correction does not fix autocorrelation or confounding. Correlations use the combined baseline/target time series and are descriptive. Support is an operationally gated normalized shift multiplied by coverage and `(1 − q)`, capped at one. It is **not** a posterior probability, calibrated confidence or estimated effect size. Saturation is common in these intentionally strong synthetic failures.

PELT operates on the standardized KPI series using an L2 cost, minimum segment length seven, penalty eight and one-day resolution. Operational onset can precede a visible KPI break because of inventory buffers. Change-point recall is reported rather than a claim that every predicted point is true. Healthy-window change-point counts are retained in JSON for review.

Timing is warmed-process computation and template generation; excludes data loading, validation, assembly, DB writes, HTTP and browser rendering. Total harness runtime includes loading/scoring/control windows. Peak RSS includes the whole harness and source snapshots. macOS reports bytes and Linux reports KiB; the code normalizes to MiB. On Windows RSS is omitted if unavailable. No inference timing is claimed for the no-LLM runs.

## Larger reproducible run

```sh
supplyrca-benchmark --generate-skus 80 --seed 42 --data data/generated/performance --output artifacts/performance
```

Generated files are ignored by Git. Increasing SKU count increases data size and known incidents, not the variety of causal mechanisms. Large raw bundles deliberately exceed the web import limit and should be exercised offline. The harness reports its dataset size and configuration rather than inventing enterprise scalability claims.
