import argparse
import csv
import gzip
import importlib.metadata
import json
import os
import platform
import statistics
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

try:
    import resource
except ImportError:  # Windows has no standard resource module.
    resource = None

from supplyrca.ai.narrative import LocalRuntime, narrate
from supplyrca.data.generate import write_bundle
from supplyrca.data.validation import validate_bundle
from supplyrca.domain.analysis import analyze, assemble
from supplyrca.domain.schemas import InvestigationRequest


def hardware():
    return {
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "logical_cpus": os.cpu_count(),
        "python": platform.python_version(),
        "dependencies": {
            p: importlib.metadata.version(p) for p in ["polars", "scipy", "ruptures", "pydantic"]
        },
    }


def evaluate(directory: Path, output: Path, runtime=None):
    started = time.perf_counter()
    payload = json.loads(gzip.decompress((directory / "dataset.json.gz").read_bytes()))
    clean, report = validate_bundle(payload)
    if not report["valid"]:
        raise ValueError("Benchmark input failed validation")
    frame = assemble(clean)
    truth = json.loads((directory / "ground_truth.json").read_text())
    # Ground truth is passed only to the scorer; analyze never receives cause or incident ID.
    episodes = []
    for incident in truth:
        req = InvestigationRequest(
            start=incident["start"], end=incident["end"], sku=incident["sku"], kpi=incident["kpi"]
        )
        t = time.perf_counter()
        result = analyze(frame, req)
        narrative = narrate(result, runtime)
        elapsed = (time.perf_counter() - t) * 1000
        causes = [h["cause"] for h in result["hypotheses"]]
        detected = result["change_points"]
        distances = [abs((date.fromisoformat(d) - req.start).days) for d in detected]
        linked = {e["id"] for e in result["evidence"]}
        claims = narrative["content"]["claims"]
        episodes.append(
            {
                "incident_id": incident["id"],
                "expected": incident["cause"],
                "predicted": causes,
                "top1_correct": bool(causes and causes[0] == incident["cause"]),
                "top3_correct": incident["cause"] in causes[:3],
                "false_contributors": sum(c != incident["cause"] for c in causes),
                "contributors": len(causes),
                "change_points": detected,
                "change_point_within_7_days": bool(distances and min(distances) <= 7),
                "onset_error_days": min(distances) if distances else None,
                "cited_claims": sum(
                    bool(c["evidence_ids"]) and set(c["evidence_ids"]) <= linked for c in claims
                ),
                "claims": len(claims),
                "narrative_origin": narrative["origin"],
                "latency_ms": elapsed,
            }
        )
    controls = []
    for sku in sorted(frame["sku"].unique().to_list()):
        for start in ["2024-02-15", "2025-10-01"]:
            day = date.fromisoformat(start)
            r = analyze(frame, InvestigationRequest(start=day, end=day + timedelta(days=20), sku=sku))
            controls.append(
                {
                    "sku": sku,
                    "start": start,
                    "hypotheses": len(r["hypotheses"]),
                    "change_points": len(r["change_points"]),
                }
            )
    latencies = sorted(e["latency_ms"] for e in episodes)
    total_h = sum(e["contributors"] for e in episodes) + sum(c["hypotheses"] for c in controls)
    total_claims = sum(e["claims"] for e in episodes)
    metrics = {
        "known_cause_top1_recovery": statistics.mean(e["top1_correct"] for e in episodes),
        "known_cause_top3_recovery": statistics.mean(e["top3_correct"] for e in episodes),
        "false_contributor_rate": (
            sum(e["false_contributors"] for e in episodes) + sum(c["hypotheses"] for c in controls)
        )
        / max(total_h, 1),
        "healthy_window_false_alert_rate": statistics.mean(c["hypotheses"] > 0 for c in controls),
        "change_point_recall_within_7_days": statistics.mean(
            e["change_point_within_7_days"] for e in episodes
        ),
        "change_point_mean_absolute_onset_error_days": statistics.mean(
            e["onset_error_days"] for e in episodes if e["onset_error_days"] is not None
        ),
        "narrative_citation_coverage": sum(e["cited_claims"] for e in episodes) / max(total_claims, 1),
        "diagnosis_median_ms": statistics.median(latencies),
        "diagnosis_p95_ms": latencies[min(len(latencies) - 1, int(0.95 * len(latencies)))],
    }
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss if resource else None
    report_out = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "hardware": hardware(),
        "configuration": {
            "seed": payload["seed"],
            "generator_version": payload["generator_version"],
            "algorithm_version": "1.0.0",
            "runtime": runtime.name if runtime else "none",
            "model": runtime.model if runtime else None,
            "temperature": 0,
            "prompt_version": "evidence-only-v1",
            "timing_scope": "analyze + narrate; excludes loading/validation/database",
        },
        "dataset_sha256": report["sha256"],
        "record_count": report["rows"],
        "incident_count": len(episodes),
        "healthy_control_count": len(controls),
        "metrics": metrics,
        "episodes": episodes,
        "healthy_controls": controls,
        "total_runtime_seconds": time.perf_counter() - started,
        "peak_rss_mib": rss / (1024 * 1024 if platform.system() == "Darwin" else 1024)
        if rss is not None
        else None,
    }
    output.mkdir(parents=True, exist_ok=True)
    (output / "benchmark.json").write_text(json.dumps(report_out, indent=2) + "\n")
    with (output / "episodes.csv").open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=episodes[0].keys(), lineterminator="\n")
        writer.writeheader()
        writer.writerows(episodes)
    lines = [
        "# Measured synthetic benchmark",
        "",
        f"Generated: {report_out['generated_at']}",
        f"Hardware: {report_out['hardware']['platform']} / {report_out['hardware']['machine']} / {os.cpu_count()} logical CPUs",
        f"Configuration: Python {platform.python_version()}, seed {payload['seed']}, runtime {report_out['configuration']['runtime']}",
        f"Dataset: {report_out['record_count']:,} records; {len(episodes)} known incidents; {len(controls)} healthy controls.",
        "",
        "| Metric | Measured value |",
        "|---|---:|",
    ]
    for k, v in metrics.items():
        lines.append(f"| {k} | {v:.6f} |")
    lines += [
        "",
        f"Total harness runtime: {report_out['total_runtime_seconds']:.3f} seconds; peak process RSS: {report_out['peak_rss_mib']} MiB.",
        "",
        "These are synthetic, in-family recovery results, not estimates of production causal accuracy. ",
        "The generator and diagnostic mechanisms share domain assumptions. Timing includes warmed-process analysis and narrative, excludes API/network/database overhead.",
        "Change-point accuracy uses the operational incident onset, allowing seven days for inventory buffers to deplete. ",
        "Citation coverage validates references, not semantic truthfulness. The default run evaluates deterministic template narratives; it does not benchmark an LLM.",
    ]
    (output / "summary.md").write_text("\n".join(lines) + "\n")
    return report_out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, default=Path("data/sample"))
    parser.add_argument("--output", type=Path, default=Path("artifacts/benchmark"))
    parser.add_argument("--generate-skus", type=int)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--runtime", choices=["none", "ollama", "llamacpp", "vllm"], default="none")
    parser.add_argument("--model", default="qwen2.5:7b")
    parser.add_argument("--base-url", default="http://localhost:11434")
    args = parser.parse_args()
    if args.generate_skus:
        if not 1 <= args.generate_skus <= 1000:
            parser.error("generate-skus must be between 1 and 1000")
        write_bundle(args.data, args.seed, args.generate_skus)
    runtime = None if args.runtime == "none" else LocalRuntime(args.base_url, args.model, args.runtime)
    result = evaluate(args.data, args.output, runtime)
    print(
        json.dumps(
            {
                k: result[k]
                for k in [
                    "record_count",
                    "incident_count",
                    "metrics",
                    "total_runtime_seconds",
                    "peak_rss_mib",
                ]
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
