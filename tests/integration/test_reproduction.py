import json
from pathlib import Path

from scripts.reproduce_report import reproduce


def test_export_is_independently_reproducible(client, request_body, headers, tmp_path):
    result = client.post("/api/v1/investigations", json=request_body, headers=headers).json()
    report = tmp_path / "report.json"
    report.write_text(json.dumps(result))
    assert reproduce(Path("data/sample/dataset.json.gz"), report) == result["deterministic_sha256"]
