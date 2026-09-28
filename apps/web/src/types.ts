export type KPI =
  | "fill_rate"
  | "stockout_rate"
  | "lead_time"
  | "excess_inventory"
  | "forecast_accuracy";
export type InvestigationRequest = {
  dataset_id: string;
  kpi: KPI;
  start: string;
  end: string;
  baseline_days: number;
  sku: string | null;
  market: string | null;
};
export type Hypothesis = {
  id: string;
  cause: string;
  title: string;
  sku: string;
  market: string;
  supplier_id: string;
  support: number;
  evidence_level: string;
  q_value: number;
  correlation: number | null;
  evidence_ids: string[];
  decision: string;
  note: string;
  caveat: string;
};
export type Evidence = {
  id: string;
  kind: string;
  label: string;
  baseline: number;
  current: number;
  p_value?: number;
  q_value?: number;
  spearman_rho?: number | null;
  record_ids: string[];
  method: string;
};
export type Decomposition = {
  dimension: string;
  key: string;
  baseline: number;
  current: number;
  rate_effect: number;
  mix_effect: number;
  contribution: number;
  demand: number;
  unfilled: number;
};
export type Investigation = {
  id: string;
  created_at: string;
  request: InvestigationRequest;
  summary: {
    baseline: number;
    current: number;
    delta: number;
    unfilled_units: number;
    coverage: number;
    baseline_rows: number;
    current_rows: number;
  };
  timeline: {
    date: string;
    value: number | null;
    demand: number;
    unfilled: number;
  }[];
  change_points: string[];
  decomposition: Record<string, Decomposition[]>;
  hypotheses: Hypothesis[];
  evidence: Evidence[];
  duration_ms: number;
  algorithm_version: string;
  dataset_sha256: string;
  deterministic_sha256: string;
  tests_performed: number;
  limitations: string[];
  graph: {
    nodes: { id: string; label: string; kind: string }[];
    edges: {
      source: string;
      target: string;
      type: string;
      evidence_ids: string[];
    }[];
  };
  narrative: {
    origin: string;
    content: {
      summary: string;
      claims: {
        finding_id: string;
        evidence_ids: string[];
        explanation: string;
      }[];
      abstained: boolean;
      limitations: string[];
    };
    telemetry: {
      runtime: string;
      model: string | null;
      latency_ms: number;
      validation_failures: string[];
    };
  };
};
export type Overview = {
  dataset_id: string;
  date_start: string;
  date_end: string;
  rows: number;
  skus: string[];
  markets: string[];
  metrics: Record<KPI, number | null>;
  metrics_window: string;
  suppliers: { id: string; name: string }[];
};
export type Alert = {
  id: string;
  sku: string;
  market: string;
  start: string;
  end: string;
  kpi: KPI;
  change: number;
};
export type ValidationReport = {
  valid: boolean;
  rows: number;
  error_count?: number;
  sha256?: string;
  errors: { table: string; row?: number; id?: string; message: string }[];
  filename?: string;
};
export const kpiLabels: Record<KPI, string> = {
  fill_rate: "Fill rate",
  stockout_rate: "Stockout rate",
  lead_time: "Lead time",
  excess_inventory: "Inventory cover",
  forecast_accuracy: "Forecast accuracy",
};
export function formatKpi(value: number | null, kpi: KPI): string {
  return value === null
    ? "Undefined"
    : kpi === "lead_time" || kpi === "excess_inventory"
      ? `${value.toFixed(2)} days`
      : `${(value * 100).toFixed(1)}%`;
}
