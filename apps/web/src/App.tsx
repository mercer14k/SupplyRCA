import About from "./pages/About";
import DataPage from "./pages/DataPage";
import EvidenceDrawer from "./components/EvidenceDrawer";
import HypothesisCard from "./components/HypothesisCard";
import Metric from "./components/Metric";
import Badge from "./components/Badge";
import { useCallback, useEffect, useState } from "react";
import {
  Activity,
  ArrowDownRight,
  ArrowRight,
  Box,
  Check,
  ChevronRight,
  Database,
  Download,
  FileText,
  FlaskConical,
  GitBranch,
  Layers,
  LayoutDashboard,
  LoaderCircle,
  Play,
  Search,
  ShieldCheck,
  SlidersHorizontal,
  X,
} from "lucide-react";
import Chart from "./Chart";
import { api, download } from "./api";
import { formatKpi, kpiLabels } from "./types";
import type {
  Alert,
  Evidence,
  Hypothesis,
  Investigation,
  InvestigationRequest,
  KPI,
  Overview,
  ValidationReport,
} from "./types";

const initial: InvestigationRequest = {
  dataset_id: "demo-v1",
  kpi: "fill_rate",
  start: "2024-04-20",
  end: "2024-05-10",
  baseline_days: 28,
  sku: "SKU-001",
  market: null,
};
const titles = {
  workspace: "Investigation workspace",
  history: "Investigation archive",
  data: "Data & validation",
  about: "Architecture & methods",
};
type Page = keyof typeof titles;
export default function App() {
  const [page, setPage] = useState<Page>("workspace");
  const [request, setRequest] = useState(initial);
  const [overview, setOverview] = useState<Overview | null>(null);
  const [result, setResult] = useState<Investigation | null>(null);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [history, setHistory] = useState<Investigation[]>([]);
  const [historyTotal, setHistoryTotal] = useState(0);
  const [historyOffset, setHistoryOffset] = useState(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [evidence, setEvidence] = useState<Evidence | null>(null);
  const [dimension, setDimension] = useState("sku");
  const [tab, setTab] = useState<"contributors" | "graph" | "narrative">(
    "contributors",
  );
  const [filter, setFilter] = useState("");
  const [datasets, setDatasets] = useState<
    { id: string; report: ValidationReport }[]
  >([]);
  const refreshDatasets = useCallback(async () => {
    const d = await api<{ items: { id: string; report: ValidationReport }[] }>(
      "/datasets",
    );
    setDatasets(d.items);
  }, []);
  const run = useCallback(
    async (r: InvestigationRequest, key: string = crypto.randomUUID()) => {
      setBusy(true);
      setError("");
      setNotice("");
      setEvidence(null);
      try {
        const next = await api<Investigation>("/investigations", {
          method: "POST",
          headers: { "Idempotency-Key": key },
          body: JSON.stringify(r),
        });
        setResult(next);
        setRequest(r);
        setPage("workspace");
      } catch (e) {
        setError((e as Error).message);
      } finally {
        setBusy(false);
      }
    },
    [],
  );
  useEffect(() => {
    let cancelled = false;
    Promise.all([
      api<Overview>(`/datasets/${request.dataset_id}/overview`),
      api<{ items: Alert[] }>(`/datasets/${request.dataset_id}/anomalies`),
    ])
      .then(([o, a]) => {
        if (!cancelled) {
          setOverview(o);
          setAlerts(a.items);
        }
      })
      .catch((e) => {
        if (!cancelled) setError(e.message);
      });
    return () => {
      cancelled = true;
    };
  }, [request.dataset_id]);
  useEffect(() => {
    refreshDatasets().catch((e) => setError(e.message));
    run(initial, "demo-v1-initial-investigation").catch((e) =>
      setError(e.message),
    );
  }, [run, refreshDatasets]);
  useEffect(() => {
    if (page === "history")
      api<{ items: Investigation[]; total: number }>(
        `/investigations?offset=${historyOffset}`,
      )
        .then((d) => {
          setHistory(d.items);
          setHistoryTotal(d.total);
        })
        .catch((e) => setError(e.message));
  }, [page, result, historyOffset]);
  async function review(h: Hypothesis, decision: string, note: string) {
    if (!result) return;
    setBusy(true);
    setError("");
    try {
      const updated = await api<Investigation>(
        `/investigations/${result.id}/hypotheses/${encodeURIComponent(h.id)}/review`,
        {
          method: "PUT",
          headers: { "Idempotency-Key": crypto.randomUUID() },
          body: JSON.stringify({ decision, note }),
        },
      );
      setResult(updated);
      setNotice("Analyst review saved to the audit history.");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function open(id: string) {
    setBusy(true);
    setError("");
    try {
      const r = await api<Investigation>(`/investigations/${id}`);
      setResult(r);
      setRequest(r.request);
      setPage("workspace");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  const selectEvidence = (id: string) =>
    setEvidence(result?.evidence.find((e) => e.id === id) ?? null);
  const nav = [
    ["workspace", LayoutDashboard, "Investigate"],
    ["history", FileText, "Investigations"],
    ["data", Database, "Data & validation"],
    ["about", Layers, "Architecture"],
  ] as const;
  return (
    <div className="shell">
      <a className="skip" href="#main">
        Skip to content
      </a>
      <aside className="sidebar">
        <a className="brand" href="#" onClick={() => setPage("workspace")}>
          <span className="brand-mark">
            <GitBranch size={23} />
          </span>
          SupplyRCA<span className="brand-dot">.</span>
        </a>
        <div className="workspace-label">ANALYST WORKSPACE</div>
        <nav aria-label="Main navigation">
          {nav.map(([id, Icon, label]) => (
            <button
              key={id}
              className={page === id ? "nav-item active" : "nav-item"}
              onClick={() => {
                setPage(id);
                setError("");
              }}
            >
              <Icon size={18} />
              {label}
              {id === page && <ChevronRight size={14} />}
            </button>
          ))}
        </nav>
        <div className="sidebar-note">
          <ShieldCheck size={18} />
          <div>
            Local by design<span>Open source · No paid APIs</span>
          </div>
        </div>
        <div className="sidebar-bottom">
          <span className="avatar">SC</span>
          <div>
            Supply chain lab<small>Synthetic demo environment</small>
          </div>
        </div>
      </aside>
      <div className="content">
        <header className="topbar">
          <div>
            Workspace <ChevronRight size={14} /> <span>{titles[page]}</span>
          </div>
          <Badge tone="green">
            <span className="status-dot" /> Local-first analysis
          </Badge>
        </header>
        <main id="main">
          <div className="page-heading">
            <div>
              <div className="eyebrow">SUPPLY CHAIN INTELLIGENCE</div>
              <h1>{titles[page]}</h1>
              <p>
                {page === "workspace"
                  ? "Follow the evidence. Understand what changed."
                  : page === "history"
                    ? "Revisit findings, evidence, and analyst decisions."
                    : page === "data"
                      ? "Inspect source records and the quality checks behind every result."
                      : "Deterministic diagnostics. Grounded explanations. Explicit uncertainty."}
              </p>
            </div>
            {result && page === "workspace" && (
              <button
                className="button secondary"
                onClick={() =>
                  download(result.id, "markdown").catch((e) =>
                    setError(e.message),
                  )
                }
              >
                <Download size={16} />
                Export report
              </button>
            )}
          </div>
          {error && (
            <div role="alert" className="alert error">
              <X size={18} />
              {error}
              <button onClick={() => setError("")} aria-label="Dismiss error">
                <X size={16} />
              </button>
            </div>
          )}
          {notice && (
            <div role="status" className="alert success">
              <Check size={18} />
              {notice}
            </div>
          )}
          {page === "workspace" && (
            <>
              <section className="scope panel" aria-label="Investigation scope">
                <div className="scope-heading">
                  <SlidersHorizontal size={16} />
                  <strong>Investigation scope</strong>
                  <Badge>Synthetic data</Badge>
                </div>
                <form
                  onSubmit={(e) => {
                    e.preventDefault();
                    run(request);
                  }}
                >
                  <label>
                    Target KPI
                    <select
                      value={request.kpi}
                      onChange={(e) =>
                        setRequest({ ...request, kpi: e.target.value as KPI })
                      }
                    >
                      {Object.entries(kpiLabels).map(([k, v]) => (
                        <option key={k} value={k}>
                          {v}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label>
                    SKU
                    <select
                      value={request.sku ?? ""}
                      onChange={(e) =>
                        setRequest({ ...request, sku: e.target.value || null })
                      }
                    >
                      <option value="">All SKUs</option>
                      {overview?.skus.map((s) => (
                        <option key={s}>{s}</option>
                      ))}
                    </select>
                  </label>
                  <label>
                    Market
                    <select
                      value={request.market ?? ""}
                      onChange={(e) =>
                        setRequest({
                          ...request,
                          market: e.target.value || null,
                        })
                      }
                    >
                      <option value="">All markets</option>
                      {overview?.markets.map((m) => (
                        <option key={m}>{m}</option>
                      ))}
                    </select>
                  </label>
                  <label>
                    From
                    <input
                      type="date"
                      value={request.start}
                      onChange={(e) =>
                        setRequest({ ...request, start: e.target.value })
                      }
                      required
                    />
                  </label>
                  <label>
                    Through
                    <input
                      type="date"
                      value={request.end}
                      onChange={(e) =>
                        setRequest({ ...request, end: e.target.value })
                      }
                      required
                    />
                  </label>
                  <button
                    className="button primary"
                    disabled={busy}
                    type="submit"
                  >
                    {busy ? (
                      <LoaderCircle className="spin" size={16} />
                    ) : (
                      <Play size={16} />
                    )}{" "}
                    {busy ? "Investigating…" : "Run investigation"}
                  </button>
                </form>
                <div className="scope-foot">
                  <span>
                    <Database size={13} />
                    {request.dataset_id} · {overview?.date_start} to{" "}
                    {overview?.date_end}
                  </span>
                  <label className="inline-label">
                    Baseline
                    <select
                      aria-label="Baseline days"
                      value={request.baseline_days}
                      onChange={(e) =>
                        setRequest({
                          ...request,
                          baseline_days: Number(e.target.value),
                        })
                      }
                    >
                      <option value={14}>14 days</option>
                      <option value={28}>28 days</option>
                      <option value={56}>56 days</option>
                    </select>
                  </label>
                </div>
              </section>
              {busy && (
                <div className="loading" role="status">
                  <LoaderCircle className="spin" size={18} />
                  Assembling records and calculating statistical support…
                </div>
              )}
              {result && (
                <div className={busy ? "results muted" : "results"}>
                  <div className="result-meta">
                    <span>
                      <span className="status-dot" /> Investigation saved{" "}
                      <span className="mono">{result.id.slice(0, 8)}</span>
                    </span>
                    <span>
                      {result.request.start} — {result.request.end} ·{" "}
                      {result.duration_ms.toFixed(0)} ms · algorithm{" "}
                      {result.algorithm_version}
                    </span>
                  </div>
                  <div className="metrics">
                    <Metric
                      label={kpiLabels[result.request.kpi]}
                      value={formatKpi(
                        result.summary.current,
                        result.request.kpi,
                      )}
                      detail={`Baseline ${formatKpi(result.summary.baseline, result.request.kpi)}`}
                      icon={<Activity />}
                      accent
                    />
                    <Metric
                      label="Change from baseline"
                      value={
                        result.request.kpi === "lead_time" ||
                        result.request.kpi === "excess_inventory"
                          ? `${result.summary.delta.toFixed(2)} days`
                          : `${(result.summary.delta * 100).toFixed(1)} pp`
                      }
                      detail="Computed over selected scope"
                      icon={<ArrowDownRight />}
                    />
                    <Metric
                      label="Unfilled demand"
                      value={result.summary.unfilled_units.toLocaleString()}
                      detail="Units · reconciled against inventory"
                      icon={<Box />}
                    />
                    <Metric
                      label="Supported hypotheses"
                      value={String(result.hypotheses.length)}
                      detail={`${result.tests_performed} tests · ${(result.summary.coverage * 100).toFixed(0)}% data coverage`}
                      icon={<GitBranch />}
                    />
                  </div>
                  <div className="analysis-grid">
                    <section className="panel trajectory">
                      <div className="panel-heading">
                        <div>
                          <h2>Performance trajectory</h2>
                          <p>
                            {kpiLabels[result.request.kpi]} · daily observations
                          </p>
                        </div>
                        <Badge tone="green">Computed</Badge>
                      </div>
                      <Chart
                        label={`Daily ${kpiLabels[result.request.kpi]} with detected change points. Baseline ${formatKpi(result.summary.baseline, result.request.kpi)}, current ${formatKpi(result.summary.current, result.request.kpi)}.`}
                        option={{
                          animation: false,
                          grid: { left: 53, right: 25, top: 30, bottom: 34 },
                          tooltip: {
                            trigger: "axis",
                            backgroundColor: "#17212c",
                            borderColor: "#33424f",
                            textStyle: { color: "#edf4fa" },
                          },
                          xAxis: {
                            type: "category",
                            boundaryGap: false,
                            data: result.timeline.map((x) => x.date),
                            axisLabel: {
                              color: "#94a2af",
                              formatter: (s: string) => s.slice(5),
                            },
                            axisLine: { lineStyle: { color: "#2a3541" } },
                          },
                          yAxis: {
                            type: "value",
                            axisLabel: {
                              color: "#94a2af",
                              formatter: (v: number) =>
                                result.request.kpi === "lead_time" ||
                                result.request.kpi === "excess_inventory"
                                  ? v.toFixed(1)
                                  : `${Math.round(v * 100)}%`,
                            },
                            splitLine: {
                              lineStyle: { color: "#202a35", type: "dashed" },
                            },
                          },
                          series: [
                            {
                              type: "line",
                              data: result.timeline.map((x) => x.value),
                              showSymbol: false,
                              lineStyle: { color: "#a4ebc4", width: 2.5 },
                              areaStyle: { color: "#a4ebc4", opacity: 0.045 },
                              markArea: {
                                silent: true,
                                itemStyle: { color: "rgba(245,184,103,.05)" },
                                data: [
                                  [
                                    { xAxis: result.request.start },
                                    { xAxis: result.request.end },
                                  ],
                                ],
                              },
                              markLine: {
                                symbol: "none",
                                label: { show: false },
                                lineStyle: { color: "#e9ad71", type: "dashed" },
                                data: result.change_points.map((d) => ({
                                  xAxis: d,
                                })),
                              },
                            },
                          ],
                        }}
                      />
                      <div className="chart-legend">
                        <span>
                          <i className="legend-line" />
                          Observed KPI
                        </span>
                        <span>
                          <i className="legend-line amber" />
                          Detected change point
                        </span>
                        <span className="right">
                          {result.change_points.length} changes detected
                        </span>
                      </div>
                      <details className="data-alternative">
                        <summary>View chart data as table</summary>
                        <div className="table-scroll">
                          <table>
                            <thead>
                              <tr>
                                <th>Date</th>
                                <th>KPI</th>
                                <th>Unfilled</th>
                              </tr>
                            </thead>
                            <tbody>
                              {result.timeline.map((x) => (
                                <tr key={x.date}>
                                  <td>{x.date}</td>
                                  <td>
                                    {formatKpi(x.value, result.request.kpi)}
                                  </td>
                                  <td>{x.unfilled}</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </details>
                    </section>
                    <section className="panel decomposition">
                      <div className="panel-heading">
                        <div>
                          <h2>Where it changed</h2>
                          <p>Exact rate + mix decomposition</p>
                        </div>
                        <select
                          aria-label="Decomposition dimension"
                          value={dimension}
                          onChange={(e) => setDimension(e.target.value)}
                        >
                          <option value="sku">By SKU</option>
                          <option value="supplier_id">By supplier</option>
                          <option value="market">By market</option>
                        </select>
                      </div>
                      <div className="decomp-list">
                        {result.decomposition[dimension]
                          .slice(0, 6)
                          .map((d, i) => (
                            <button
                              key={d.key}
                              className="decomp-row"
                              onClick={() => {
                                setFilter(d.key);
                                setTab("contributors");
                              }}
                            >
                              <div>
                                <span className="row-number">
                                  {String(i + 1).padStart(2, "0")}
                                </span>
                                <strong>{d.key}</strong>
                                <span>
                                  {(
                                    d.contribution *
                                    (result.request.kpi === "lead_time" ||
                                    result.request.kpi === "excess_inventory"
                                      ? 1
                                      : 100)
                                  ).toFixed(2)}{" "}
                                  {result.request.kpi === "lead_time" ||
                                  result.request.kpi === "excess_inventory"
                                    ? "days"
                                    : "pp"}
                                </span>
                              </div>
                              <div className="bar-track">
                                <div
                                  style={{
                                    width: `${Math.max(2, Math.min(100, (Math.abs(d.contribution) / Math.max(Math.abs(result.summary.delta), 0.0001)) * 100))}%`,
                                  }}
                                />
                              </div>
                              <small>
                                {d.unfilled.toLocaleString()} unfilled units
                              </small>
                            </button>
                          ))}
                      </div>
                      <p className="panel-note">
                        Contributions sum to the overall change within each
                        dimension. They are accounting effects, not causal
                        effects.
                      </p>
                    </section>
                  </div>
                  <section className="panel findings">
                    <div
                      className="tabs"
                      role="tablist"
                      aria-label="Investigation findings"
                    >
                      {(
                        [
                          ["contributors", "Contributing factors"],
                          ["graph", "Hypothesis graph"],
                          ["narrative", "Investigation narrative"],
                        ] as const
                      ).map(([id, label]) => (
                        <button
                          key={id}
                          role="tab"
                          id={`tab-${id}`}
                          aria-controls={`panel-${id}`}
                          aria-selected={tab === id}
                          className={tab === id ? "selected" : ""}
                          onClick={() => setTab(id)}
                        >
                          {label}
                          {id === "contributors" && (
                            <span>{result.hypotheses.length}</span>
                          )}
                        </button>
                      ))}
                      <Badge>Evidence first</Badge>
                    </div>
                    {tab === "contributors" && (
                      <div
                        role="tabpanel"
                        id="panel-contributors"
                        aria-labelledby="tab-contributors"
                      >
                        <div className="findings-toolbar">
                          <p>
                            Ranked by measured support. Analyst review
                            determines the disposition.
                          </p>
                          <label className="search">
                            <Search size={16} />
                            <input
                              aria-label="Search contributing factors"
                              placeholder="Filter SKU, supplier, market…"
                              value={filter}
                              onChange={(e) => setFilter(e.target.value)}
                            />
                          </label>
                        </div>
                        {result.hypotheses
                          .filter((h) =>
                            `${h.title} ${h.sku} ${h.supplier_id} ${h.market}`
                              .toLowerCase()
                              .includes(filter.toLowerCase()),
                          )
                          .map((h, i) => (
                            <HypothesisCard
                              key={h.id}
                              hypothesis={h}
                              index={i}
                              onEvidence={selectEvidence}
                              onReview={review}
                              busy={busy}
                            />
                          ))}
                        {!result.hypotheses.length && (
                          <div className="empty">
                            <FlaskConical />
                            <h3>No supported hypothesis</h3>
                            <p>
                              The engine abstained. Inspect source coverage or
                              expand the investigation window.
                            </p>
                          </div>
                        )}
                        {result.hypotheses.length > 0 &&
                          !result.hypotheses.some((h) =>
                            `${h.title} ${h.sku} ${h.supplier_id} ${h.market}`
                              .toLowerCase()
                              .includes(filter.toLowerCase()),
                          ) && (
                            <div className="empty">
                              No contributors match this filter.
                            </div>
                          )}
                      </div>
                    )}
                    {tab === "graph" && (
                      <div
                        className="graph-panel"
                        role="tabpanel"
                        id="panel-graph"
                        aria-labelledby="tab-graph"
                      >
                        <p>
                          Every edge represents a supported association. No edge
                          asserts proven causation.
                        </p>
                        <Chart
                          height={300}
                          label="Hypotheses connect to the target KPI through observational evidence."
                          option={{
                            animation: false,
                            tooltip: {},
                            series: [
                              {
                                type: "graph",
                                layout: "circular",
                                roam: false,
                                symbolSize: 65,
                                label: {
                                  show: true,
                                  color: "#e3eaf0",
                                  position: "bottom",
                                  fontSize: 12,
                                },
                                edgeSymbol: ["none", "arrow"],
                                lineStyle: {
                                  color: "#7a9c8b",
                                  curveness: 0.15,
                                },
                                data: result.graph.nodes.map((n) => ({
                                  id: n.id,
                                  name:
                                    n.id === "kpi"
                                      ? kpiLabels[result.request.kpi]
                                      : n.label,
                                  itemStyle: {
                                    color:
                                      n.kind === "computed"
                                        ? "#a4ebc4"
                                        : "#364c43",
                                  },
                                })),
                                links: result.graph.edges,
                              },
                            ],
                          }}
                        />
                        <ul className="graph-edges">
                          {result.graph.edges.map((edge) => (
                            <li key={edge.source}>
                              {edge.source} → {kpiLabels[result.request.kpi]}{" "}
                              <button
                                className="text-button"
                                onClick={() =>
                                  selectEvidence(edge.evidence_ids[1])
                                }
                              >
                                View association evidence
                              </button>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                    {tab === "narrative" && (
                      <div
                        className="narrative"
                        role="tabpanel"
                        id="panel-narrative"
                        aria-labelledby="tab-narrative"
                      >
                        <Badge tone="green">
                          {result.narrative.origin === "local_llm"
                            ? "AI-generated · local model"
                            : "Deterministic narrative · AI disabled or unavailable"}
                        </Badge>
                        <h3>{result.narrative.content.summary}</h3>
                        {result.narrative.content.claims.map((c) => (
                          <div className="narrative-claim" key={c.finding_id}>
                            <p>{c.explanation}</p>
                            <div>
                              {c.evidence_ids.map((id) => (
                                <button
                                  className="evidence-link"
                                  key={id}
                                  onClick={() => selectEvidence(id)}
                                >
                                  <FileText size={14} />
                                  {id === "ev-kpi"
                                    ? "KPI reconciliation"
                                    : "Operational evidence"}
                                </button>
                              ))}
                            </div>
                          </div>
                        ))}
                        <h4>Investigation limitations</h4>
                        <ul>
                          {result.narrative.content.limitations.map((l) => (
                            <li key={l}>{l}</li>
                          ))}
                        </ul>
                        <p className="mono">
                          Runtime: {result.narrative.telemetry.runtime} · Model:{" "}
                          {result.narrative.telemetry.model ?? "none"} ·
                          Fallback events:{" "}
                          {
                            result.narrative.telemetry.validation_failures
                              .length
                          }
                        </p>
                      </div>
                    )}
                  </section>
                  <div className="method-foot">
                    <ShieldCheck size={15} />
                    Calculated from source records. Hypotheses remain
                    observational until independently verified.
                    <button
                      className="text-button"
                      onClick={() =>
                        download(result.id, "json").catch((e) =>
                          setError(e.message),
                        )
                      }
                    >
                      Export reproducibility bundle <ArrowRight size={13} />
                    </button>
                  </div>
                </div>
              )}
              {!result && !busy && (
                <div className="empty panel">
                  <Activity />
                  <h3>Start an investigation</h3>
                  <p>
                    Select a KPI and date window, then run the deterministic
                    analysis.
                  </p>
                </div>
              )}
              <section className="detected">
                <div className="section-title">
                  <h2>Detected in this dataset</h2>
                  <Badge>{alerts.length} displayed alerts</Badge>
                </div>
                <p>
                  Rolling observations from operational data · select an alert
                  to investigate
                </p>
                <div className="alert-cards">
                  {alerts.slice(0, 6).map((a) => (
                    <button
                      key={a.id}
                      onClick={() =>
                        run({
                          ...request,
                          kpi: a.kpi,
                          sku: a.sku,
                          market: a.market,
                          start: a.start,
                          end: a.end,
                          baseline_days: 28,
                        })
                      }
                      className="alert-card"
                      disabled={busy}
                    >
                      <span>
                        <Badge tone={a.kpi === "fill_rate" ? "amber" : "blue"}>
                          {kpiLabels[a.kpi]}
                        </Badge>
                        <ArrowRight size={16} />
                      </span>
                      <strong>{a.sku}</strong>
                      <small>
                        {a.market} · {a.start}
                      </small>
                    </button>
                  ))}
                </div>
              </section>
            </>
          )}
          {page === "history" && (
            <section className="panel archive">
              <div className="panel-heading">
                <h2>Saved investigations</h2>
                <Badge>{historyTotal} total</Badge>
              </div>
              {history.length === 0 ? (
                <div className="empty">
                  No investigations yet. Run one in the workspace.
                </div>
              ) : (
                <div className="table-scroll">
                  <table>
                    <thead>
                      <tr>
                        <th>Investigation</th>
                        <th>KPI & scope</th>
                        <th>Window</th>
                        <th>Computed result</th>
                        <th />
                      </tr>
                    </thead>
                    <tbody>
                      {history.map((r) => (
                        <tr key={r.id}>
                          <td>
                            <span className="mono">{r.id.slice(0, 8)}</span>
                            <small>
                              {new Date(r.created_at).toLocaleString()}
                            </small>
                          </td>
                          <td>
                            {kpiLabels[r.request.kpi]}
                            <small>
                              {r.request.sku ?? "All SKUs"} ·{" "}
                              {r.request.dataset_id}
                            </small>
                          </td>
                          <td>
                            {r.request.start}
                            <small>through {r.request.end}</small>
                          </td>
                          <td>{formatKpi(r.summary.current, r.request.kpi)}</td>
                          <td>
                            <button
                              className="button secondary"
                              onClick={() => open(r.id)}
                            >
                              Open <ArrowRight size={14} />
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
              <div className="pagination">
                <button
                  className="button secondary"
                  disabled={historyOffset === 0}
                  onClick={() =>
                    setHistoryOffset(Math.max(0, historyOffset - 20))
                  }
                >
                  Previous
                </button>
                <span>
                  {historyOffset + 1}–
                  {Math.min(historyOffset + 20, historyTotal)} of {historyTotal}
                </span>
                <button
                  className="button secondary"
                  disabled={historyOffset + 20 >= historyTotal}
                  onClick={() => setHistoryOffset(historyOffset + 20)}
                >
                  Next
                </button>
              </div>
            </section>
          )}
          {page === "data" && (
            <DataPage
              datasets={datasets}
              active={request.dataset_id}
              onSelect={(id) => {
                setRequest({ ...initial, dataset_id: id });
                setResult(null);
                setPage("workspace");
              }}
              onRefresh={refreshDatasets}
              onError={setError}
            />
          )}
          {page === "about" && <About />}
          <footer>
            SupplyRCA{" "}
            <span>v0.1.0 · Evidence-grounded investigations · Apache 2.0</span>
          </footer>
        </main>
      </div>
      {evidence && result && (
        <EvidenceDrawer
          evidence={evidence}
          datasetId={result.request.dataset_id}
          close={() => setEvidence(null)}
        />
      )}
    </div>
  );
}
