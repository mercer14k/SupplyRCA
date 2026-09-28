import { useState } from "react";
import { Check, X, FileText, ChevronRight } from "lucide-react";
import type { Hypothesis } from "../types";
import Badge from "./Badge";
export default function HypothesisCard({
  hypothesis: h,
  index,
  onEvidence,
  onReview,
  busy,
}: {
  hypothesis: Hypothesis;
  index: number;
  onEvidence: (id: string) => void;
  onReview: (h: Hypothesis, d: string, n: string) => Promise<void>;
  busy: boolean;
}) {
  const [note, setNote] = useState(h.note);
  return (
    <article className="hypothesis">
      <div className="hypothesis-top">
        <span className="rank">{String(index + 1).padStart(2, "0")}</span>
        <div className="hypothesis-title">
          <h3>
            {h.title}
            <Badge
              tone={
                h.decision === "accepted"
                  ? "green"
                  : h.decision === "rejected"
                    ? "amber"
                    : "neutral"
              }
            >
              {h.decision}
            </Badge>
          </h3>
          <p>
            {h.sku} <span>·</span> {h.supplier_id} <span>·</span> {h.market}
          </p>
        </div>
        <div className="support">
          <strong>
            {(h.support * 100).toFixed(0)}
            <small>/100</small>
          </strong>
          <span>Measured support</span>
        </div>
      </div>
      <div className="hypothesis-body">
        <div className="signal-stats">
          <Badge tone="amber">Observational evidence</Badge>
          <span>FDR q = {h.q_value.toExponential(2)}</span>
          <span>
            Spearman ρ{" "}
            {h.correlation === null ? "unavailable" : h.correlation.toFixed(2)}
          </span>
        </div>
        <p>{h.caveat}</p>
        <div className="hypothesis-actions">
          <div>
            {h.evidence_ids.map((id) => (
              <button
                key={id}
                className="evidence-link"
                onClick={() => onEvidence(id)}
              >
                <FileText size={14} />
                {id === "ev-kpi" ? "KPI evidence" : "Source evidence"}
                <ChevronRight size={12} />
              </button>
            ))}
          </div>
          <div className="review-buttons">
            <button
              disabled={busy}
              className="button compact"
              onClick={() => onReview(h, "accepted", note)}
            >
              <Check size={14} />
              Accept
            </button>
            <button
              disabled={busy}
              className="button compact"
              onClick={() => onReview(h, "rejected", note)}
            >
              <X size={14} />
              Reject
            </button>
          </div>
        </div>
        <details>
          <summary>Analyst notes</summary>
          <label className="note-label">
            Investigation note
            <textarea
              value={note}
              onChange={(e) => setNote(e.target.value)}
              maxLength={2000}
              placeholder="Record supporting context, a counterargument, or the next verification step."
            />
          </label>
          <button
            disabled={busy}
            className="button secondary compact"
            onClick={() => onReview(h, "annotated", note)}
          >
            Save annotation
          </button>
        </details>
      </div>
    </article>
  );
}
