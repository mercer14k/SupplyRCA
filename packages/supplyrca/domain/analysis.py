"""Deterministic diagnostics: accounting, tests and associations, not causal identification."""

import math
from datetime import timedelta

import numpy as np
import polars as pl
import ruptures as rpt
from scipy import stats

from supplyrca.domain.schemas import InvestigationRequest

ALGORITHM_VERSION = "1.0.0"
PARAMETERS = {
    "min_baseline_days": 14,
    "min_current_days": 7,
    "fdr": 0.05,
    "pelt_penalty": 8,
    "pelt_min_size": 7,
    "seed": 42,
}
CAUSE_LABELS = {
    "supplier_delay": "Supplier receipt shortfall",
    "transport_delay": "Transportation delay",
    "demand_surge": "Unplanned demand increase",
    "forecast_bias": "Forecast under-bias",
    "overforecast": "Forecast-driven overstock",
}


class InsufficientEvidence(ValueError):
    pass


def assemble(tables: dict) -> pl.DataFrame:
    keys = ["date", "sku", "market", "supplier_id"]
    out = pl.DataFrame(tables["demand"]).select(keys + ["id", "demand", "forecast", "fulfilled"])
    out = out.rename({"id": "demand_id"})
    for table, columns, prefix in [
        ("inventory", ["opening", "received", "shipped", "closing"], "inventory"),
        ("purchase_orders", ["ordered", "lead_days", "promised_lead_days"], "po"),
        ("shipments", ["transit_days", "planned_transit_days"], "shipment"),
    ]:
        frame = pl.DataFrame(tables[table]).select(keys + ["id"] + columns).rename({"id": prefix + "_id"})
        out = out.join(frame, on=keys, how="inner", validate="1:1")
    return out.with_columns(pl.col("date").str.to_date()).sort(["date", "sku", "market"])


def metric_parts(frame: pl.DataFrame, kpi: str) -> tuple[float, float]:
    if kpi == "fill_rate":
        return float(frame["fulfilled"].sum()), float(frame["demand"].sum())
    if kpi == "stockout_rate":
        return float(((frame["fulfilled"] < frame["demand"]) & (frame["demand"] > 0)).sum()), float(
            (frame["demand"] > 0).sum()
        )
    if kpi == "lead_time":
        return float(frame["lead_days"].sum()), float(frame.height)
    if kpi == "forecast_accuracy":
        return float((frame["demand"] - (frame["forecast"] - frame["demand"]).abs()).sum()), float(
            frame["demand"].sum()
        )
    return float(frame["closing"].sum()), float(frame["demand"].sum())


def metric(frame: pl.DataFrame, kpi: str) -> float | None:
    numerator, denominator = metric_parts(frame, kpi)
    return numerator / denominator if denominator else None


def change_points(values: list[float | None], dates: list[str]) -> list[str]:
    if len(values) < 21 or any(v is None for v in values):
        return []
    arr = np.array(values, dtype=float)
    scale = float(np.std(arr))
    if scale < 1e-9:
        return []
    indices = (
        rpt.Pelt(model="l2", min_size=7, jump=1)
        .fit(((arr - arr.mean()) / scale).reshape(-1, 1))
        .predict(pen=8)
    )
    return [dates[i] for i in indices if i < len(dates)]


def bh_adjust(pvalues: list[float]) -> list[float]:
    order = np.argsort(pvalues)
    output = [1.0] * len(pvalues)
    running = 1.0
    for rank in range(len(order), 0, -1):
        index = int(order[rank - 1])
        running = min(running, pvalues[index] * len(order) / rank)
        output[index] = running
    return output


def decompose(baseline: pl.DataFrame, current: pl.DataFrame, kpi: str, dimension: str) -> list[dict]:
    """Exact symmetric rate/mix decomposition. Sum equals the aggregate KPI change."""
    total0, total1 = metric_parts(baseline, kpi)[1], metric_parts(current, kpi)[1]
    if not total0 or not total1:
        return []
    output = []
    for key in sorted(set(baseline[dimension].to_list() + current[dimension].to_list())):
        b, c = baseline.filter(pl.col(dimension) == key), current.filter(pl.col(dimension) == key)
        n0, d0 = metric_parts(b, kpi)
        n1, d1 = metric_parts(c, kpi)
        r0, r1 = n0 / d0 if d0 else 0, n1 / d1 if d1 else 0
        w0, w1 = d0 / total0, d1 / total1
        rate, mix = (r1 - r0) * (w1 + w0) / 2, (w1 - w0) * (r1 + r0) / 2
        output.append(
            {
                "dimension": dimension,
                "key": key,
                "baseline": r0,
                "current": r1,
                "rate_effect": rate,
                "mix_effect": mix,
                "contribution": rate + mix,
                "demand": float(c["demand"].sum()),
                "unfilled": float((c["demand"] - c["fulfilled"]).sum()),
            }
        )
    return sorted(output, key=lambda x: abs(x["contribution"]), reverse=True)


def series(frame: pl.DataFrame, kpi: str) -> list[dict]:
    return [
        {
            "date": str(key[0]),
            "value": metric(group, kpi),
            "demand": float(group["demand"].sum()),
            "unfilled": float((group["demand"] - group["fulfilled"]).sum()),
        }
        for key, group in frame.partition_by("date", as_dict=True, maintain_order=True).items()
    ]


def analyze(frame: pl.DataFrame, request: InvestigationRequest) -> dict:
    selected = frame
    if request.sku:
        selected = selected.filter(pl.col("sku") == request.sku)
    if request.market:
        selected = selected.filter(pl.col("market") == request.market)
    baseline_start = request.start - timedelta(days=request.baseline_days)
    b = selected.filter((pl.col("date") >= baseline_start) & (pl.col("date") < request.start))
    c = selected.filter((pl.col("date") >= request.start) & (pl.col("date") <= request.end))
    if b["date"].n_unique() < 14 or c["date"].n_unique() < 7:
        raise InsufficientEvidence("At least 14 baseline days and 7 investigation days are required.")
    entities = selected.select(["sku", "market"]).unique().height
    expected = entities * (request.baseline_days + (request.end - request.start).days + 1)
    coverage = min(1.0, (b.height + c.height) / expected) if expected else 0
    if coverage < 0.9:
        raise InsufficientEvidence("Less than 90% daily grain coverage; inspect the validation report.")
    before, after = metric(b, request.kpi), metric(c, request.kpi)
    if before is None or after is None:
        raise InsufficientEvidence("Zero denominator: the requested KPI is undefined.")
    deterioration = before - after if request.kpi in ("fill_rate", "forecast_accuracy") else after - before
    combined = pl.concat([b, c]).sort(["date", "sku", "market"])
    timeline = series(combined, request.kpi)
    evidence = [
        {
            "id": "ev-kpi",
            "kind": "accounting",
            "label": "Reconciled KPI comparison",
            "baseline": before,
            "current": after,
            "record_ids": c["demand_id"].head(12).to_list(),
            "method": "Ratio of summed numerators and denominators; no averaging of percentages",
        }
    ]
    candidates = []
    for key, cg in c.partition_by(["sku", "market"], as_dict=True).items():
        sku, market = key
        bg = b.filter((pl.col("sku") == sku) & (pl.col("market") == market))
        if bg.height < 14 or cg.height < 7:
            continue
        actual_ratio = float(cg["demand"].mean()) / max(float(bg["demand"].mean()), 1)
        forecast_ratio_b = bg["forecast"].to_numpy() / np.maximum(bg["demand"].to_numpy(), 1)
        forecast_ratio_c = cg["forecast"].to_numpy() / np.maximum(cg["demand"].to_numpy(), 1)
        shortfall = 1 - float(cg["received"].sum()) / max(float(cg["ordered"].sum()), 1)
        specifications = [
            (
                "supplier_delay",
                (bg["lead_days"] - bg["transit_days"]).to_numpy(),
                (cg["lead_days"] - cg["transit_days"]).to_numpy(),
                5.0,
                shortfall > 0.2,
                "po_id",
            ),
            (
                "transport_delay",
                bg["transit_days"].to_numpy(),
                cg["transit_days"].to_numpy(),
                4.0,
                shortfall > 0.2,
                "shipment_id",
            ),
            (
                "demand_surge",
                bg["demand"].to_numpy(),
                cg["demand"].to_numpy(),
                max(float(bg["demand"].mean()) * 0.5, 1),
                actual_ratio > 1.25,
                "demand_id",
            ),
            (
                "forecast_bias",
                -forecast_ratio_b,
                -forecast_ratio_c,
                0.35,
                0.8 < actual_ratio < 1.2,
                "demand_id",
            ),
            ("overforecast", forecast_ratio_b, forecast_ratio_c, 0.6, actual_ratio < 1.25, "demand_id"),
        ]
        for cause, x, y, threshold, gate, column in specifications:
            delta = float(np.mean(y) - np.mean(x))
            p = float(stats.mannwhitneyu(y, x, alternative="greater", method="asymptotic").pvalue)
            if not math.isfinite(p):
                p = 1.0
            joined = pl.concat([bg, cg]).sort("date")
            impact = np.array([metric(g, request.kpi) for g in joined.partition_by("date")], dtype=float)
            if request.kpi in ("fill_rate", "forecast_accuracy"):
                impact = -impact
            signal = np.concatenate([x, y])
            correlation = None
            if np.std(signal) > 1e-9 and np.nanstd(impact) > 1e-9 and np.all(np.isfinite(impact)):
                value = float(stats.spearmanr(signal, impact).statistic)
                correlation = value if math.isfinite(value) else None
            eligible = gate and delta > threshold * 0.25 and deterioration > 1e-5
            if request.kpi == "lead_time" and cause not in ("supplier_delay", "transport_delay"):
                eligible = False
            if request.kpi == "excess_inventory" and cause != "overforecast":
                eligible = False
            candidates.append(
                {
                    "cause": cause,
                    "sku": sku,
                    "market": market,
                    "supplier_id": cg["supplier_id"][0],
                    "delta": delta,
                    "p_value": p,
                    "correlation": correlation,
                    "eligible": eligible,
                    "threshold": threshold,
                    "signal_baseline": float(np.mean(x)),
                    "signal_current": float(np.mean(y)),
                    "column": column,
                    "record_ids": bg[column].head(3).to_list() + cg[column].head(9).to_list(),
                }
            )
    qs = bh_adjust([h["p_value"] for h in candidates])
    hypotheses = []
    for h, q in zip(candidates, qs, strict=True):
        if not h["eligible"] or q > 0.05:
            continue
        score = min(1, h["delta"] / h["threshold"]) * (1 - q) * coverage
        identifier = f"{h['cause']}:{h['sku']}:{h['market']}"
        eid = f"ev-{identifier}"
        evidence.append(
            {
                "id": eid,
                "kind": "operational_association",
                "label": CAUSE_LABELS[h["cause"]],
                "baseline": h["signal_baseline"],
                "current": h["signal_current"],
                "p_value": h["p_value"],
                "q_value": q,
                "spearman_rho": h["correlation"],
                "record_ids": h["record_ids"],
                "method": "One-sided Mann–Whitney U; Benjamini–Hochberg correction over every tested candidate",
            }
        )
        hypotheses.append(
            {
                "id": identifier,
                "cause": h["cause"],
                "title": CAUSE_LABELS[h["cause"]],
                "sku": h["sku"],
                "market": h["market"],
                "supplier_id": h["supplier_id"],
                "support": round(score, 6),
                "evidence_level": "observational",
                "q_value": q,
                "correlation": h["correlation"],
                "evidence_ids": ["ev-kpi", eid],
                "decision": "unreviewed",
                "note": "",
                "caveat": "Temporal association and process consistency; not an identified causal effect.",
            }
        )
    hypotheses.sort(key=lambda h: (-h["support"], h["id"]))
    nodes = [{"id": "kpi", "label": request.kpi, "kind": "computed"}]
    edges = []
    for h in hypotheses:
        nodes.append({"id": h["id"], "label": h["title"], "kind": "hypothesis"})
        edges.append(
            {
                "source": h["id"],
                "target": "kpi",
                "type": "supported_association",
                "evidence_ids": h["evidence_ids"],
            }
        )
    return {
        "algorithm_version": ALGORITHM_VERSION,
        "parameters": PARAMETERS,
        "request": request.model_dump(mode="json"),
        "summary": {
            "baseline": before,
            "current": after,
            "delta": after - before,
            "unfilled_units": float((c["demand"] - c["fulfilled"]).sum()),
            "coverage": coverage,
            "baseline_rows": b.height,
            "current_rows": c.height,
        },
        "timeline": timeline,
        "change_points": change_points([x["value"] for x in timeline], [x["date"] for x in timeline]),
        "decomposition": {d: decompose(b, c, request.kpi, d) for d in ["sku", "supplier_id", "market"]},
        "hypotheses": hypotheses,
        "evidence": evidence,
        "graph": {"nodes": nodes, "edges": edges},
        "tests_performed": len(candidates),
        "limitations": [
            "Observational diagnostics cannot establish causation or estimate intervention effects.",
            "Daily observations are autocorrelated; test p-values are exploratory, not confirmatory.",
            "Hypothesis coverage is limited to five operational mechanisms; omitted causes remain possible.",
        ],
    }
