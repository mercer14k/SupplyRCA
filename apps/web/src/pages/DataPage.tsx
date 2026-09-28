import { useState, useEffect } from "react";
import { ArrowRight, Database } from "lucide-react";
import type { ValidationReport } from "../types";
import { api } from "../api";
import Badge from "../components/Badge";
export default function DataPage({
  datasets,
  active,
  onSelect,
  onRefresh,
  onError,
}: {
  datasets: { id: string; report: ValidationReport }[];
  active: string;
  onSelect: (id: string) => void;
  onRefresh: () => Promise<void>;
  onError: (s: string) => void;
}) {
  const [selected, setSelected] = useState(active),
    [table, setTable] = useState("demand"),
    [query, setQuery] = useState(""),
    [offset, setOffset] = useState(0),
    [rows, setRows] = useState<Record<string, unknown>[]>([]),
    [total, setTotal] = useState(0),
    [uploading, setUploading] = useState(false);
  const report = datasets.find((d) => d.id === selected)?.report;
  useEffect(() => {
    let cancelled = false;
    if (report?.valid)
      api<{ items: Record<string, unknown>[]; total: number }>(
        `/datasets/${selected}/records?table=${table}&q=${encodeURIComponent(query)}&offset=${offset}&limit=25`,
      )
        .then((d) => {
          if (!cancelled) {
            setRows(d.items);
            setTotal(d.total);
          }
        })
        .catch((e) => {
          if (!cancelled) onError(e.message);
        });
    else {
      setRows([]);
      setTotal(0);
    }
    return () => {
      cancelled = true;
    };
  }, [selected, table, query, offset, report?.valid, onError]);
  async function upload(file: File) {
    setUploading(true);
    onError("");
    try {
      if (file.size > 16 * 1024 * 1024)
        throw new Error("File exceeds the 16 MiB upload limit.");
      if (!file.name.toLowerCase().endsWith(".json"))
        throw new Error("Choose an uncompressed JSON dataset bundle.");
      const id = "import-" + crypto.randomUUID();
      try {
        await api(`/datasets/${id}`, {
          method: "PUT",
          headers: { "X-Filename": file.name },
          body: await file.text(),
        });
      } finally {
        await onRefresh();
        setSelected(id);
        setOffset(0);
      }
    } catch (e) {
      onError((e as Error).message);
    } finally {
      setUploading(false);
    }
  }
  return (
    <>
      <section className="panel data-header">
        <div>
          <h2>Source datasets</h2>
          <p>
            Immutable snapshots · stable record IDs · validated inventory
            balances
          </p>
        </div>
        <label className="button primary upload-label">
          {uploading ? "Validating…" : "Import JSON bundle"}
          <input
            type="file"
            accept="application/json,.json"
            disabled={uploading}
            aria-label="Import JSON bundle"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) upload(file);
            }}
          />
        </label>
      </section>
      <div className="data-layout">
        <section className="panel dataset-list">
          {datasets.map((d) => (
            <button
              key={d.id}
              className={selected === d.id ? "dataset selected" : "dataset"}
              onClick={() => {
                setSelected(d.id);
                setOffset(0);
              }}
            >
              <Database size={18} />
              <div>
                <strong>{d.id}</strong>
                <small>{d.report.rows.toLocaleString()} validated rows</small>
              </div>
              <Badge tone={d.report.valid ? "green" : "amber"}>
                {d.report.valid ? "Valid" : "Quarantined"}
              </Badge>
            </button>
          ))}
        </section>
        <section className="panel validation-report">
          <div className="panel-heading">
            <h2>Validation report</h2>
            {report && (
              <Badge tone={report.valid ? "green" : "amber"}>
                {report.valid
                  ? "All checks passed"
                  : `${report.errors.length} issues`}
              </Badge>
            )}
          </div>
          <p>
            Schema, identifiers, foreign keys, daily grain, inventory
            continuity, and cross-table reconciliation.
          </p>
          {report?.errors.map((e, i) => (
            <p className="validation-error" key={i}>
              {e.table} · {e.id ?? `row ${e.row}`} — {e.message}
            </p>
          ))}
          {report?.sha256 && (
            <p className="hash mono">SHA-256 {report.sha256}</p>
          )}
          {report?.valid && (
            <button
              className="button secondary"
              onClick={() => onSelect(selected)}
            >
              Investigate this dataset <ArrowRight size={14} />
            </button>
          )}
        </section>
      </div>
      <section className="panel">
        <div className="panel-heading">
          <h2>
            Raw records <Badge>Source data</Badge>
          </h2>
          <div className="table-controls">
            <select
              aria-label="Source table"
              value={table}
              onChange={(e) => {
                setTable(e.target.value);
                setOffset(0);
              }}
            >
              {[
                "demand",
                "inventory",
                "purchase_orders",
                "shipments",
                "suppliers",
              ].map((t) => (
                <option key={t}>{t}</option>
              ))}
            </select>
            <input
              aria-label="Search raw records"
              placeholder="Search records…"
              value={query}
              onChange={(e) => {
                setQuery(e.target.value);
                setOffset(0);
              }}
            />
          </div>
        </div>
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                {rows[0] &&
                  Object.keys(rows[0])
                    .filter((k) => k !== "lineage")
                    .map((k) => <th key={k}>{k.replaceAll("_", " ")}</th>)}
              </tr>
            </thead>
            <tbody>
              {rows.map((r, i) => (
                <tr key={i}>
                  {Object.entries(r)
                    .filter(([k]) => k !== "lineage")
                    .map(([k, v]) => (
                      <td key={k}>{String(v)}</td>
                    ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {!rows.length && (
          <div className="empty">No valid records match this selection.</div>
        )}
        <div className="pagination">
          <button
            className="button secondary"
            disabled={offset === 0}
            onClick={() => setOffset(Math.max(0, offset - 25))}
          >
            Previous
          </button>
          <span>
            {total === 0 ? 0 : offset + 1}–{Math.min(offset + 25, total)} of{" "}
            {total.toLocaleString()}
          </span>
          <button
            className="button secondary"
            disabled={offset + 25 >= total}
            onClick={() => setOffset(offset + 25)}
          >
            Next
          </button>
        </div>
      </section>
    </>
  );
}
