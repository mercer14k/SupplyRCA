"""Quarantine whole invalid bundles; retain a report with every rejected row."""

import hashlib
import json
from datetime import datetime, timezone

from pydantic import ValidationError

from supplyrca.domain.schemas import Demand, Inventory, PurchaseOrder, Shipment, Supplier

TABLES = {
    "suppliers": Supplier,
    "demand": Demand,
    "inventory": Inventory,
    "purchase_orders": PurchaseOrder,
    "shipments": Shipment,
}


def _validate_bundle(payload: dict) -> tuple[dict, dict]:
    errors, clean, seen = [], {}, set()
    if not isinstance(payload, dict) or payload.get("schema_version") != "1":
        return {}, {
            "valid": False,
            "rows": 0,
            "errors": [{"table": "bundle", "row": 0, "message": "Expected schema_version 1 and an object"}],
        }
    tables = payload.get("tables", {})
    if not isinstance(tables, dict):
        return {}, {
            "valid": False,
            "rows": 0,
            "errors": [{"table": "bundle", "row": 0, "message": "tables must be an object"}],
        }
    for extra in tables.keys() - TABLES.keys():
        errors.append({"table": extra, "row": 0, "message": "Unknown table"})
    for name, schema in TABLES.items():
        clean[name] = []
        rows = tables.get(name)
        if not isinstance(rows, list) or not rows:
            errors.append({"table": name, "row": 0, "message": "Required nonempty table missing"})
            continue
        natural_keys = set()
        for i, row in enumerate(rows):
            try:
                record = schema.model_validate(row).model_dump(mode="json")
                if record["id"] in seen:
                    raise ValueError("Duplicate stable identifier")
                key = tuple(record.get(k) for k in ("date", "sku", "market"))
                if name != "suppliers" and key in natural_keys:
                    raise ValueError("Duplicate date/SKU/market grain")
                seen.add(record["id"])
                natural_keys.add(key)
                clean[name].append(record)
            except (ValidationError, ValueError) as exc:
                message = (
                    "; ".join(e["msg"] for e in exc.errors())
                    if isinstance(exc, ValidationError)
                    else str(exc)
                )
                errors.append(
                    {
                        "table": name,
                        "row": i + 1,
                        "id": row.get("id") if isinstance(row, dict) else None,
                        "message": message[:500],
                    }
                )
    if not errors:
        suppliers = {x["id"] for x in clean["suppliers"]}
        index = {
            name: {(x["date"], x["sku"], x["market"]): x for x in clean[name]}
            for name in TABLES
            if name != "suppliers"
        }
        for name, rows in index.items():
            if rows.keys() != index["demand"].keys():
                errors.append({"table": name, "row": 0, "message": "Daily grain does not match demand"})
            for key, row in rows.items():
                if row["supplier_id"] not in suppliers:
                    errors.append({"table": name, "id": row["id"], "message": "Unknown supplier"})
                demand = index["demand"].get(key)
                if demand and row["supplier_id"] != demand["supplier_id"]:
                    errors.append({"table": name, "id": row["id"], "message": "Supplier grain mismatch"})
                if name == "inventory" and demand and abs(row["shipped"] - demand["fulfilled"]) > 0.01:
                    errors.append(
                        {"table": name, "id": row["id"], "message": "Shipments do not reconcile demand"}
                    )
                po = index["purchase_orders"].get(key)
                if name == "shipments" and po and row["po_id"] != po["id"]:
                    errors.append({"table": name, "id": row["id"], "message": "Unknown PO reference"})
                if name == "inventory" and po and abs(row["received"] - po["received"]) > 0.01:
                    errors.append({"table": name, "id": row["id"], "message": "Receipts do not reconcile PO"})
        prior = {}
        for row in sorted(clean["inventory"], key=lambda x: (x["sku"], x["market"], x["date"])):
            key = (row["sku"], row["market"])
            if key in prior and abs(prior[key] - row["opening"]) > 0.01:
                errors.append(
                    {"table": "inventory", "id": row["id"], "message": "Opening balance discontinuity"}
                )
            prior[key] = row["closing"]
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    report = {
        "valid": not errors,
        "rows": sum(len(v) for v in clean.values()),
        "errors": errors,
        "error_count": len(errors),
        "sha256": hashlib.sha256(canonical).hexdigest(),
        "validated_at": datetime.now(timezone.utc).isoformat(),
    }
    return clean, report


def validate_bundle(payload: dict) -> tuple[dict, dict]:
    clean, report = _validate_bundle(payload)
    report.setdefault(
        "sha256",
        hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
    )
    report.setdefault("validated_at", datetime.now(timezone.utc).isoformat())
    report.setdefault("error_count", len(report["errors"]))
    return clean, report
