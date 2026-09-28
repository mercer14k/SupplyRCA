import gzip
import hashlib
import json
import time
from functools import lru_cache
from pathlib import Path

import polars as pl

from supplyrca.ai.narrative import narrate
from supplyrca.data.validation import validate_bundle
from supplyrca.domain.analysis import analyze, assemble, metric


class InvestigationService:
    def __init__(self, store, runtime=None):
        self.store, self.runtime = store, runtime
        self.frame = lru_cache(maxsize=4)(self.frame)
        self.anomalies = lru_cache(maxsize=4)(self.anomalies)

    def seed_demo(self, path):
        try:
            self.store.dataset("demo-v1")
            return
        except KeyError:
            pass
        payload = json.loads(gzip.decompress(Path(path).read_bytes()))
        clean, report = validate_bundle(payload)
        if not report["valid"]:
            raise RuntimeError("Committed sample data failed validation")
        self.store.import_dataset("demo-v1", {"tables": clean, "schema_version": "1"}, report)

    def frame(self, dataset_id):
        data = self.store.dataset(dataset_id)
        if not data["report"]["valid"]:
            raise ValueError("Dataset is quarantined; inspect validation report")
        return assemble(data["payload"]["tables"])

    def run(self, request, key):
        cached = self.store.cached(key, request.model_dump(mode="json"))
        if cached:
            return cached
        start = time.perf_counter()
        dataset = self.store.dataset(request.dataset_id)
        result = analyze(self.frame(request.dataset_id), request)
        result["dataset_sha256"] = dataset["report"]["sha256"]
        result["deterministic_sha256"] = hashlib.sha256(
            json.dumps(result, sort_keys=True).encode()
        ).hexdigest()
        result["narrative"] = narrate(result, self.runtime)
        result["duration_ms"] = round((time.perf_counter() - start) * 1000, 2)
        return self.store.save(result, key)

    def overview(self, dataset_id):
        frame = self.frame(dataset_id)
        latest = frame["date"].max()
        recent = frame.filter(pl.col("date") >= latest - __import__("datetime").timedelta(days=27))
        return {
            "dataset_id": dataset_id,
            "date_start": str(frame["date"].min()),
            "date_end": str(latest),
            "rows": frame.height,
            "skus": sorted(frame["sku"].unique().to_list()),
            "markets": sorted(frame["market"].unique().to_list()),
            "metrics": {
                k: metric(recent, k)
                for k in ["fill_rate", "stockout_rate", "lead_time", "excess_inventory", "forecast_accuracy"]
            },
            "metrics_window": "last 28 dataset days",
            "suppliers": self.store.dataset(dataset_id)["payload"]["tables"]["suppliers"],
        }

    def anomalies(self, dataset_id):
        """Observed alerts from rolling fill rate and cover; never consumes seeded truth."""
        frame = self.frame(dataset_id)
        alerts = []
        for key, group in frame.partition_by(["sku", "market"], as_dict=True).items():
            rows = group.sort("date").to_dicts()
            last = -60
            for i in range(28, len(rows) - 6):
                if i - last < 35:
                    continue
                before, after = rows[i - 28 : i], rows[i : i + 7]

                def ratio(part, n):
                    return sum(r[n] for r in part) / max(sum(r["demand"] for r in part), 1)

                decline = ratio(before, "fulfilled") - ratio(after, "fulfilled")
                cover_delta = ratio(after, "closing") - ratio(before, "closing")
                if decline > 0.07 or cover_delta > 2:
                    kpi = "fill_rate" if decline > 0.07 else "excess_inventory"
                    alerts.append(
                        {
                            "id": f"{key[0]}-{rows[i]['date']}",
                            "sku": key[0],
                            "market": key[1],
                            "start": str(rows[i]["date"]),
                            "end": str(rows[min(i + 20, len(rows) - 1)]["date"]),
                            "kpi": kpi,
                            "change": -decline if kpi == "fill_rate" else cover_delta,
                        }
                    )
                    last = i
        return sorted(alerts, key=lambda a: a["start"], reverse=True)


def report_markdown(result):
    request = result["request"]
    lines = [
        "# SupplyRCA investigation",
        "",
        f"Investigation: {result['id']}",
        f"KPI: {request['kpi']} | {request['start']} through {request['end']}",
        f"Dataset SHA-256: {result['dataset_sha256']}",
        f"Deterministic result SHA-256: {result['deterministic_sha256']}",
        f"Algorithm: {result['algorithm_version']}",
        "",
        "## Computed results",
        "",
        f"Baseline: {result['summary']['baseline']:.6f}",
        f"Current: {result['summary']['current']:.6f}",
        f"Delta: {result['summary']['delta']:.6f}",
        "",
        "## Hypotheses (observational)",
        "",
    ]
    for h in result["hypotheses"]:
        lines += [
            f"- {h['title']} — {h['sku']} / {h['market']}; support {h['support']:.4f}; "
            f"decision {h['decision']}; evidence: {', '.join(h['evidence_ids'])}",
            "  Note: " + h["note"].replace("\n", " "),
        ]
    lines += [
        "",
        f"## Narrative ({result['narrative']['origin']})",
        "",
        result["narrative"]["content"]["summary"],
    ]
    for claim in result["narrative"]["content"]["claims"]:
        lines.append(f"- {claim['explanation']} [{', '.join(claim['evidence_ids'])}]")
    lines += ["", "## Evidence manifest", ""]
    for e in result["evidence"]:
        lines += [f"### {e['id']}", e["method"], "Record IDs: " + ", ".join(e["record_ids"])]
    lines += ["", "## Limitations", ""] + ["- " + x for x in result["limitations"]]
    return "\n".join(lines) + "\n"
