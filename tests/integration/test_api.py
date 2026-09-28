import copy
import json
import os

import pytest
from fastapi.testclient import TestClient

from apps.api.main import create_app


def test_full_workflow(client, request_body, headers):
    assert client.get("/health").json() == {"status": "ok"}
    assert client.get("/ready").status_code == 200
    assert client.get("/api/v1/datasets/demo-v1/validation").json()["valid"]
    response = client.post("/api/v1/investigations", json=request_body, headers=headers)
    assert response.status_code == 201, response.text
    result = response.json()
    h = result["hypotheses"][0]
    assert h["cause"] == "supplier_delay"
    again = client.post("/api/v1/investigations", json=request_body, headers=headers).json()
    assert again["id"] == result["id"]
    reviewed = client.put(
        f"/api/v1/investigations/{result['id']}/hypotheses/{h['id']}/review",
        json={"decision": "accepted", "note": "Supplier receipt history reviewed"},
        headers=headers,
    )
    assert reviewed.status_code == 200
    assert reviewed.json()["hypotheses"][0]["decision"] == "accepted"
    assert reviewed.json()["deterministic_sha256"] == result["deterministic_sha256"]
    assert len(reviewed.json()["reviews"]) == 1
    fetched = client.get(f"/api/v1/investigations/{result['id']}").json()
    assert fetched["hypotheses"][0]["note"] == "Supplier receipt history reviewed"
    assert client.get("/api/v1/investigations").json()["total"] == 1
    exported = client.get(f"/api/v1/investigations/{result['id']}/export").text
    assert "Evidence manifest" in exported and result["dataset_sha256"] in exported
    for evidence in result["evidence"]:
        for record_id in evidence["record_ids"]:
            table = "purchase_orders" if record_id.startswith("P-") else "demand"
            records = client.get(f"/api/v1/datasets/demo-v1/records?table={table}&q={record_id}").json()
            assert records["total"] == 1


def test_conflicting_idempotency(client, request_body, headers):
    client.post("/api/v1/investigations", json=request_body, headers=headers)
    request_body["sku"] = "SKU-002"
    assert client.post("/api/v1/investigations", json=request_body, headers=headers).status_code == 409


def test_malformed_and_missing_inputs(client, headers):
    assert client.post("/api/v1/investigations", content="{bad", headers=headers).status_code == 422
    missing = client.get("/api/v1/investigations/missing")
    assert missing.status_code == 404 and missing.json()["error"]["trace_id"]
    assert client.get("/api/v1/datasets/demo-v1/records?limit=999").status_code == 422
    assert client.get("/api/v1/datasets/demo-v1/records?table=arbitrary_sql").status_code == 422


def test_unauthorized_mutation(client, request_body):
    assert client.post("/api/v1/investigations", json=request_body).status_code == 403
    assert (
        client.post(
            "/api/v1/investigations",
            json=request_body,
            headers={
                "X-SupplyRCA-Client": "analyst",
                "Origin": "https://evil.example",
                "Idempotency-Key": "evil-test",
            },
        ).status_code
        == 403
    )


def test_upload_and_quarantine(client, bundle, headers):
    data = copy.deepcopy(bundle)
    data["tables"]["demand"][0]["demand"] = -1
    response = client.put(
        "/api/v1/datasets/bad-import", json=data, headers={**headers, "X-Filename": "../../evil.json"}
    )
    assert response.status_code == 422
    report = client.get("/api/v1/datasets/bad-import/validation").json()
    assert not report["valid"] and report["filename"] == "evil.json"
    assert client.get("/api/v1/datasets/bad-import/overview").status_code == 422
    valid = client.put("/api/v1/datasets/good-import", json=bundle, headers=headers)
    assert valid.status_code == 201
    assert client.put("/api/v1/datasets/good-import", json=data, headers=headers).status_code == 409
    assert (
        client.put(
            "/api/v1/datasets/wrong-type",
            content=json.dumps(data),
            headers={**headers, "Content-Type": "text/html"},
        ).status_code
        == 415
    )


def test_body_size_limit(client, headers):
    response = client.put("/api/v1/datasets/large", content=b"x" * (16 * 1024 * 1024 + 1), headers=headers)
    assert response.status_code == 413


def test_token_mode_read_write_boundary(tmp_path, request_body, headers):
    app = create_app(f"sqlite:///{tmp_path}/secure.db", mode="token", token="x" * 32)
    with TestClient(app) as client:
        assert client.get("/api/v1/datasets").status_code == 401
        assert client.post("/api/v1/investigations", json=request_body, headers=headers).status_code == 401
        headers = {**headers, "Authorization": "Bearer " + "x" * 32}
        assert client.post("/api/v1/investigations", json=request_body, headers=headers).status_code == 201
        assert client.get("/docs").status_code == 404


def test_readiness_without_model(client):
    assert not client.get("/ready").json()["ai_required"]


def test_observed_alerts_not_ground_truth(client):
    data = client.get("/api/v1/datasets/demo-v1/anomalies").json()
    assert data["total"] >= 30
    assert all("cause" not in row for row in data["items"])


@pytest.mark.skipif(not os.getenv("TEST_DATABASE_URL"), reason="PostgreSQL URL not configured")
def test_postgresql_persistence(request_body, headers):
    from uuid import uuid4

    key = str(uuid4())
    for _ in range(2):
        with TestClient(create_app(os.environ["TEST_DATABASE_URL"], mode="demo")) as client:
            response = client.post(
                "/api/v1/investigations", json=request_body, headers={**headers, "Idempotency-Key": key}
            )
            assert response.status_code == 201
            assert response.json()["hypotheses"][0]["cause"] == "supplier_delay"
