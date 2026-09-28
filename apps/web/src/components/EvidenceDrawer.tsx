import { useState, useEffect } from "react";
import { X, Database, ChevronRight } from "lucide-react";
import type { Evidence } from "../types";
import { api } from "../api";
import Badge from "./Badge";
export default function EvidenceDrawer({
  evidence: e,
  datasetId,
  close,
}: {
  evidence: Evidence;
  datasetId: string;
  close: () => void;
}) {
  const [record, setRecord] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    const prior = document.activeElement as HTMLElement;
    document.getElementById("close-evidence")?.focus();
    return () => prior?.focus();
  }, []);
  async function loadRecord(id: string) {
    setRecord(null);
    setError("");
    const table = id.startsWith("P-")
      ? "purchase_orders"
      : id.startsWith("T-")
        ? "shipments"
        : id.startsWith("I-")
          ? "inventory"
          : "demand";
    try {
      const d = await api<{ items: Record<string, unknown>[] }>(
        `/datasets/${datasetId}/records?table=${table}&q=${encodeURIComponent(id)}`,
      );
      setRecord(d.items.find((r) => r.id === id) ?? null);
    } catch (err) {
      setError((err as Error).message);
    }
  }
  return (
    <div className="drawer-backdrop" onClick={close}>
      <section
        className="drawer"
        role="dialog"
        aria-modal="true"
        aria-labelledby="evidence-title"
        onClick={(e) => e.stopPropagation()}
        onKeyDown={(event) => {
          if (event.key === "Escape") close();
          if (event.key === "Tab") {
            const elements = event.currentTarget.querySelectorAll<HTMLElement>(
              'button,[href],input,select,textarea,[tabindex="0"]',
            );
            const first = elements[0],
              last = elements[elements.length - 1];
            if (event.shiftKey && document.activeElement === first) {
              last.focus();
              event.preventDefault();
            } else if (!event.shiftKey && document.activeElement === last) {
              first.focus();
              event.preventDefault();
            }
          }
        }}
      >
        <div className="drawer-heading">
          <Badge tone="green">Evidence record</Badge>
          <button
            id="close-evidence"
            aria-label="Close evidence"
            className="icon-button"
            onClick={close}
          >
            <X />
          </button>
        </div>
        <h2 id="evidence-title">{e.label}</h2>
        <p>{e.method}</p>
        <div className="evidence-values">
          <div>
            Baseline<strong>{e.baseline.toFixed(4)}</strong>
          </div>
          <div>
            Current<strong>{e.current.toFixed(4)}</strong>
          </div>
        </div>
        <p className="mono">{e.id}</p>
        <h3>Linked source records</h3>
        <p className="muted-text">
          Representative baseline and current records. The calculation uses the
          full investigation window.
        </p>
        <div className="record-links">
          {e.record_ids.map((id) => (
            <button key={id} onClick={() => loadRecord(id)}>
              <Database size={14} />
              <span>{id}</span>
              <ChevronRight size={14} />
            </button>
          ))}
        </div>
        {error && <p role="alert">{error}</p>}
        {record && (
          <>
            <h3>Raw source record</h3>
            <pre>{JSON.stringify(record, null, 2)}</pre>
          </>
        )}
      </section>
    </div>
  );
}
