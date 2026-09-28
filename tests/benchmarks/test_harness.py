import json
from pathlib import Path

from supplyrca.evaluation.benchmark import evaluate


def test_harness_reports_real_results_and_hardware(tmp_path):
    result = evaluate(Path("data/sample"), tmp_path)
    assert result["incident_count"] == 40
    assert result["healthy_control_count"] == 16
    assert result["metrics"]["known_cause_top1_recovery"] >= 0.8
    assert result["record_count"] == 23396
    assert result["hardware"]["python"]
    assert result["configuration"]["runtime"] == "none"
    assert result["metrics"]["diagnosis_median_ms"] > 0
    assert json.loads((tmp_path / "benchmark.json").read_text())["dataset_sha256"] == result["dataset_sha256"]
    assert (tmp_path / "episodes.csv").exists() and (tmp_path / "summary.md").exists()
