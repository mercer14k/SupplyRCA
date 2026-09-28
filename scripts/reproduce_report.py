"""Recompute the deterministic hash of an exported investigation against its original dataset."""

import argparse
import gzip
import hashlib
import json
from pathlib import Path

from supplyrca.data.validation import validate_bundle
from supplyrca.domain.analysis import analyze, assemble
from supplyrca.domain.schemas import InvestigationRequest


def reproduce(dataset: Path, report: Path):
    raw = dataset.read_bytes()
    payload = json.loads(gzip.decompress(raw) if dataset.suffix == ".gz" else raw)
    saved = json.loads(report.read_text())
    clean, validation = validate_bundle(payload)
    if not validation["valid"]:
        raise ValueError("Dataset validation failed")
    if validation["sha256"] != saved["dataset_sha256"]:
        raise ValueError("Dataset checksum differs from the investigation source")
    result = analyze(assemble(clean), InvestigationRequest.model_validate(saved["request"]))
    result["dataset_sha256"] = validation["sha256"]
    digest = hashlib.sha256(json.dumps(result, sort_keys=True).encode()).hexdigest()
    if digest != saved["deterministic_sha256"]:
        raise ValueError("Deterministic hash differs; check algorithm/dependency versions")
    return digest


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("dataset", type=Path)
    parser.add_argument("report", type=Path)
    args = parser.parse_args()
    print("Verified deterministic SHA-256:", reproduce(args.dataset, args.report))
