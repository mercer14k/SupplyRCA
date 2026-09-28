# Measured synthetic benchmark

Generated: 2026-09-27T22:14:02.159580+00:00
Hardware: macOS-26.6.2-arm64-arm-64bit / arm64 / 10 logical CPUs
Configuration: Python 3.12.14, seed 42, runtime none
Dataset: 23,396 records; 40 known incidents; 16 healthy controls.

| Metric | Measured value |
|---|---:|
| known_cause_top1_recovery | 1.000000 |
| known_cause_top3_recovery | 1.000000 |
| false_contributor_rate | 0.000000 |
| healthy_window_false_alert_rate | 0.000000 |
| change_point_recall_within_7_days | 1.000000 |
| change_point_mean_absolute_onset_error_days | 3.525000 |
| narrative_citation_coverage | 1.000000 |
| diagnosis_median_ms | 7.037333 |
| diagnosis_p95_ms | 7.996459 |

Total harness runtime: 0.535 seconds; peak process RSS: 260.3 MiB.

These are synthetic, in-family recovery results, not estimates of production causal accuracy.
The generator and diagnostic mechanisms share domain assumptions. Timing includes warmed-process analysis and narrative, excludes API/network/database overhead.
Change-point accuracy uses the operational incident onset, allowing seven days for inventory buffers to deplete.
Citation coverage validates references, not semantic truthfulness. The default run evaluates deterministic template narratives; it does not benchmark an LLM.
