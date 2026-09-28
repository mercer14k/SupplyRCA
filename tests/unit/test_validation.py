import copy

import pytest
from pydantic import ValidationError
from supplyrca.data.validation import validate_bundle
from supplyrca.domain.schemas import Demand, InvestigationRequest


def test_valid_bundle(bundle):
    clean, report = validate_bundle(bundle)
    assert report["valid"] and report["rows"] == 23396 and len(clean) == 5


@pytest.mark.parametrize(
    "mutation,expected",
    [
        (lambda b: b["tables"]["demand"][0].update(demand=-1), "greater than or equal"),
        (lambda b: b["tables"]["demand"][0].update(fulfilled=999999), "exceeds demand"),
        (lambda b: b["tables"]["inventory"][0].update(closing=999999), "balance"),
        (lambda b: b["tables"]["shipments"][0].update(po_id="missing"), "PO reference"),
        (lambda b: b["tables"]["demand"][0].update(supplier_id="missing"), "supplier"),
        (lambda b: b["tables"]["demand"][0].update(demand=float("nan")), "finite"),
        (lambda b: b["tables"]["demand"].append(b["tables"]["demand"][0]), "Duplicate"),
    ],
)
def test_quarantine_never_silently_discards(bundle, mutation, expected):
    data = copy.deepcopy(bundle)
    mutation(data)
    _, report = validate_bundle(data)
    assert not report["valid"]
    assert any(expected.lower() in e["message"].lower() for e in report["errors"])


@pytest.mark.parametrize("payload", [None, [], {}, {"schema_version": "1", "tables": []}])
def test_malformed_bundle(payload):
    _, report = validate_bundle(payload)
    assert not report["valid"] and report["errors"]


def test_continuity_detected(bundle):
    data = copy.deepcopy(bundle)
    data["tables"]["inventory"][1]["opening"] += 1
    data["tables"]["inventory"][1]["closing"] += 1
    _, report = validate_bundle(data)
    assert any("continuity" in e["message"] for e in report["errors"])


def test_extra_fields_rejected(bundle):
    row = {**bundle["tables"]["demand"][0], "execute_sql": "DROP TABLE demand"}
    with pytest.raises(ValidationError):
        Demand.model_validate(row)


def test_window_validation():
    with pytest.raises(ValidationError):
        InvestigationRequest(start="2024-04-20", end="2024-04-10")
