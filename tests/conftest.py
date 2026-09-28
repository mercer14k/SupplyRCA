import gzip
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from supplyrca.domain.analysis import assemble
from supplyrca.domain.schemas import InvestigationRequest

from apps.api.main import create_app

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def bundle():
    return json.loads(gzip.decompress((ROOT / "data/sample/dataset.json.gz").read_bytes()))


@pytest.fixture(scope="session")
def frame(bundle):
    return assemble(bundle["tables"])


@pytest.fixture
def request_body():
    return {
        "dataset_id": "demo-v1",
        "kpi": "fill_rate",
        "start": "2024-04-20",
        "end": "2024-05-10",
        "baseline_days": 28,
        "sku": "SKU-001",
        "market": None,
    }


@pytest.fixture
def investigation_request(request_body):
    return InvestigationRequest(**request_body)


@pytest.fixture
def client(tmp_path):
    app = create_app(f"sqlite:///{tmp_path}/test.db", mode="demo")
    with TestClient(app) as c:
        yield c


@pytest.fixture
def headers():
    return {"X-SupplyRCA-Client": "analyst", "Idempotency-Key": "test-investigation-001"}
