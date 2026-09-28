"""Synthetic operational simulator. Ground truth is a separate evaluation-only file."""

import argparse
import gzip
import json
import random
from datetime import date, timedelta
from pathlib import Path

GENERATOR_VERSION = "1.0.0"
CAUSES = ["supplier_delay", "transport_delay", "demand_surge", "forecast_bias", "overforecast"]


def generate(seed: int = 42, skus: int = 8) -> tuple[dict, list[dict]]:
    rng = random.Random(seed)
    start = date(2024, 1, 1)
    days = (date(2026, 1, 1) - start).days
    dataset = f"synthetic-{seed}-{skus}"
    stamp = "2026-01-01T00:00:00Z"  # logical ingestion time, deliberately reproducible
    tables = {name: [] for name in ["suppliers", "demand", "inventory", "purchase_orders", "shipments"]}
    truth = []

    def provenance(identifier):
        return {
            "id": identifier,
            "source_id": dataset,
            "ingested_at": stamp,
            "validation_status": "valid",
            "lineage": {"generator": GENERATOR_VERSION},
        }

    for s in range(4):
        tables["suppliers"].append(
            {
                **provenance(f"SUP-{s + 1:02d}"),
                "name": ["Atlas Components", "Meridian Supply", "Northstar Industrial", "Pacific Assemblies"][
                    s
                ],
                "country": ["US", "MX", "DE", "VN"][s],
            }
        )
    for s in range(skus):
        sku = f"SKU-{s + 1:03d}"
        market = ["North-America", "Europe", "APAC"][s % 3]
        supplier = f"SUP-{s % 4 + 1:02d}"
        base = 80 + s % 8 * 14
        closing = float(base * 2)
        incidents = []
        for j, cause in enumerate(CAUSES):
            onset = 110 + j * 110 + s % 8 * 3
            incident = {
                "id": f"INC-{s + 1:03d}-{j + 1}",
                "sku": sku,
                "market": market,
                "supplier_id": supplier,
                "cause": cause,
                "start": str(start + timedelta(days=onset)),
                "end": str(start + timedelta(days=onset + 20)),
                "kpi": "excess_inventory" if cause == "overforecast" else "fill_rate",
            }
            truth.append(incident)
            incidents.append((onset, onset + 20, cause))
        for d in range(days):
            day = start + timedelta(days=d)
            cause = next((c for a, b, c in incidents if a <= d <= b), None)
            demand = round(base * (1.08 if day.weekday() < 5 else 0.80) * rng.uniform(0.94, 1.06))
            forecast = round(base * (1.08 if day.weekday() < 5 else 0.80))
            lead = 7 + rng.choice([0, 0, 0, 1, -1])
            transit = 2 + rng.uniform(-0.25, 0.25)
            if cause == "demand_surge":
                demand = round(demand * 1.85)
            elif cause == "forecast_bias":
                forecast = round(forecast * 0.52)
            elif cause == "overforecast":
                forecast = round(forecast * 1.9)
            # A bounded periodic base-stock replenishment policy with lost sales.
            target = forecast * (5 if cause == "overforecast" else 2)
            ordered = max(0, round(forecast + 0.35 * (target - closing)))
            received = float(ordered)
            if cause == "supplier_delay":
                received = round(ordered * 0.34)
                lead += 8
            elif cause == "transport_delay":
                received = round(ordered * 0.38)
                lead += 6
                transit += 6
            opening = closing
            shipped = min(float(demand), opening + received)
            closing = round(opening + received - shipped, 2)
            common = {"date": str(day), "sku": sku, "market": market, "supplier_id": supplier}
            key = f"{sku}-{day}"
            tables["demand"].append(
                {
                    **provenance(f"D-{key}"),
                    **common,
                    "demand": demand,
                    "forecast": forecast,
                    "fulfilled": shipped,
                }
            )
            tables["inventory"].append(
                {
                    **provenance(f"I-{key}"),
                    **common,
                    "opening": opening,
                    "received": received,
                    "shipped": shipped,
                    "closing": closing,
                }
            )
            tables["purchase_orders"].append(
                {
                    **provenance(f"P-{key}"),
                    **common,
                    "ordered": ordered,
                    "received": received,
                    "lead_days": lead,
                    "promised_lead_days": 7,
                }
            )
            tables["shipments"].append(
                {
                    **provenance(f"T-{key}"),
                    **common,
                    "transit_days": round(transit, 2),
                    "planned_transit_days": 2,
                    "po_id": f"P-{key}",
                }
            )
    return {
        "schema_version": "1",
        "generator_version": GENERATOR_VERSION,
        "seed": seed,
        "tables": tables,
    }, truth


def write_bundle(directory: Path, seed=42, skus=8):
    directory.mkdir(parents=True, exist_ok=True)
    data, truth = generate(seed, skus)
    raw = json.dumps(data, separators=(",", ":"), sort_keys=True).encode()
    (directory / "dataset.json.gz").write_bytes(gzip.compress(raw, mtime=0))
    (directory / "ground_truth.json").write_text(json.dumps(truth, indent=2) + "\n")
    return data, truth


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--output", type=Path, default=Path("data/generated"))
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--skus", type=int, default=8)
    args = p.parse_args()
    if not 1 <= args.skus <= 1000:
        p.error("skus must be between 1 and 1000")
    data, truth = write_bundle(args.output, args.seed, args.skus)
    print(
        json.dumps(
            {
                "rows": sum(map(len, data["tables"].values())),
                "incidents": len(truth),
                "seed": args.seed,
                "output": str(args.output),
            }
        )
    )


if __name__ == "__main__":
    main()
