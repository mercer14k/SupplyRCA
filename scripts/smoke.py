"""End-to-end Compose/API smoke, no credentials required in localhost demo mode."""

import json
import os
from urllib.request import Request, urlopen
from uuid import uuid4

base = os.environ.get("API_URL", "http://localhost:8000")
headers = {
    "Content-Type": "application/json",
    "X-SupplyRCA-Client": "analyst",
    "Idempotency-Key": str(uuid4()),
}
request = {
    "dataset_id": "demo-v1",
    "kpi": "fill_rate",
    "start": "2024-04-20",
    "end": "2024-05-10",
    "sku": "SKU-001",
}
with urlopen(base + "/ready", timeout=10) as response:
    assert json.load(response)["status"] == "ready"
with urlopen(
    Request(base + "/api/v1/investigations", data=json.dumps(request).encode(), headers=headers), timeout=90
) as response:
    result = json.load(response)
assert result["hypotheses"][0]["cause"] == "supplier_delay"
assert result["summary"]["current"] < 0.7
with urlopen(base + "/api/v1/investigations/" + result["id"] + "/export", timeout=10) as response:
    assert b"Evidence manifest" in response.read()
print("PASS: readiness → deterministic investigation → persisted evidence report")
