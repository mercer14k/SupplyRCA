import copy
from datetime import date, timedelta

import numpy as np
import polars as pl
import pytest
from supplyrca.data.generate import generate
from supplyrca.domain.analysis import (
    InsufficientEvidence,
    analyze,
    bh_adjust,
    change_points,
    decompose,
    metric,
)
from supplyrca.domain.schemas import InvestigationRequest


@pytest.mark.parametrize(
    "kpi", ["fill_rate", "stockout_rate", "lead_time", "excess_inventory", "forecast_accuracy"]
)
def test_metric_decomposition_reconciles(frame, kpi):
    b = frame.filter((pl.col("date") >= date(2024, 3, 23)) & (pl.col("date") < date(2024, 4, 20)))
    c = frame.filter((pl.col("date") >= date(2024, 4, 20)) & (pl.col("date") <= date(2024, 5, 10)))
    for dimension in ["sku", "market", "supplier_id"]:
        parts = decompose(b, c, kpi, dimension)
        assert sum(p["contribution"] for p in parts) == pytest.approx(
            metric(c, kpi) - metric(b, kpi), abs=1e-10
        )


@pytest.mark.parametrize(
    "start,cause,kpi",
    [
        ("2024-04-20", "supplier_delay", "fill_rate"),
        ("2024-08-08", "transport_delay", "fill_rate"),
        ("2024-11-26", "demand_surge", "fill_rate"),
        ("2025-03-16", "forecast_bias", "fill_rate"),
        ("2025-07-04", "overforecast", "excess_inventory"),
    ],
)
def test_known_cause_recovery(frame, start, cause, kpi):
    day = date.fromisoformat(start)
    result = analyze(
        frame, InvestigationRequest(start=day, end=day + timedelta(days=20), sku="SKU-001", kpi=kpi)
    )
    assert result["hypotheses"][0]["cause"] == cause
    assert all(h["q_value"] <= 0.05 for h in result["hypotheses"])
    assert all(e["type"] == "supported_association" for e in result["graph"]["edges"])


def test_no_event_abstains(frame):
    result = analyze(frame, InvestigationRequest(start="2024-03-01", end="2024-03-21", sku="SKU-001"))
    assert result["hypotheses"] == []
    assert result["summary"]["current"] == 1


def test_missing_evidence(frame, investigation_request):
    with pytest.raises(InsufficientEvidence):
        analyze(frame.head(10), investigation_request)
    missing = frame.filter(pl.col("date").dt.day() % 2 == 0)
    with pytest.raises(InsufficientEvidence):
        analyze(missing, investigation_request)


def test_zero_denominator(frame, investigation_request):
    zeros = frame.with_columns(pl.lit(0.0).alias("demand"), pl.lit(0.0).alias("fulfilled"))
    assert metric(zeros, "fill_rate") is None
    with pytest.raises(InsufficientEvidence):
        analyze(zeros, investigation_request)


def test_accounting_not_average_percentages():
    frame = pl.DataFrame({"demand": [1.0, 99.0], "fulfilled": [0.0, 99.0]})
    assert metric(frame, "fill_rate") == 0.99


def test_pelt_known_step():
    dates = [str(date(2024, 1, 1) + timedelta(days=i)) for i in range(60)]
    assert change_points([1.0] * 30 + [0.6] * 30, dates) == [dates[30]]
    assert change_points([1.0] * 60, dates) == []
    assert change_points([None] * 60, dates) == []


def test_bh_multiple_test_correction():
    assert bh_adjust([0.001, 0.02, 0.2]) == pytest.approx([0.003, 0.03, 0.2])
    assert bh_adjust([]) == []


def test_seed_determinism():
    a, ta = generate(42, 1)
    b, tb = generate(42, 1)
    c, _ = generate(43, 1)
    assert a == b and ta == tb and a != c
    assert len(a["tables"]["demand"]) == 731


def test_analysis_does_not_mutate(frame, investigation_request):
    before = copy.deepcopy(investigation_request.model_dump())
    a = analyze(frame, investigation_request)
    b = analyze(frame, investigation_request)
    assert a == b
    assert before == investigation_request.model_dump()
    assert np.isfinite(a["summary"]["delta"])
