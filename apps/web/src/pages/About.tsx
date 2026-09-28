import { useState } from "react";
import Badge from "../components/Badge";
export default function About() {
  const [token, setToken] = useState("");
  return (
    <div className="about">
      <section className="panel about-intro">
        <Badge tone="green">OPEN SOURCE / LOCAL FIRST</Badge>
        <h2>
          An investigation engine,
          <br />
          with the evidence in the foreground.
        </h2>
        <p>
          SupplyRCA connects service deterioration to operational records.
          Deterministic code computes every KPI, statistical test, ranking and
          graph edge. A local model can summarize validated findings; it never
          controls the calculation or workflow.
        </p>
      </section>
      <div className="architecture-flow">
        {[
          ["01", "Validate", "Schema, provenance and balances"],
          ["02", "Diagnose", "Rate/mix, change points, tests"],
          ["03", "Explain", "Cited template or local model"],
          ["04", "Review", "Analyst disposition and export"],
        ].map(([n, t, d]) => (
          <section className="panel" key={n}>
            <span>{n}</span>
            <h3>{t}</h3>
            <p>{d}</p>
          </section>
        ))}
      </div>
      <div className="about-grid">
        <section className="panel">
          <h2>What the signals mean</h2>
          <p>
            <strong>Accounting decomposition</strong> attributes a KPI change to
            rate and mix effects. It reconciles exactly, but is not a causal
            estimate.
          </p>
          <p>
            <strong>Statistical support</strong> combines operational
            thresholds, coverage and false-discovery-adjusted tests. A support
            score is not a probability of causation.
          </p>
          <p>
            <strong>Hypothesis edges</strong> encode observational associations.
            Confounders, autocorrelation and unknown mechanisms remain
            limitations.
          </p>
        </section>
        <section className="panel">
          <h2>Built to be reproducible</h2>
          <p>
            Polars · SciPy · ruptures · FastAPI · SQLAlchemy · PostgreSQL ·
            React · Apache ECharts
          </p>
          <p>
            Model adapters: Ollama, llama.cpp and vLLM through local endpoints.
            No-LLM mode is the default. No model tools, arbitrary SQL or shell
            execution.
          </p>
          <p>
            Reports preserve dataset and deterministic-result hashes, algorithm
            parameters, citations and analyst review history.
          </p>
          <details>
            <summary>Access settings for token mode</summary>
            <label>
              API bearer token
              <input
                type="password"
                autoComplete="off"
                value={token}
                onChange={(e) => setToken(e.target.value)}
              />
            </label>
            <button
              className="button secondary"
              onClick={() => {
                sessionStorage.setItem("supplyrca-token", token);
                location.reload();
              }}
            >
              Use for this browser session
            </button>
          </details>
        </section>
      </div>
      <section className="panel">
        <h2>Known boundaries</h2>
        <p>
          The demo models five operational mechanisms using a daily SKU–market
          grain and a simplified lost-sales replenishment policy. It does not
          claim production ERP integration, causal identification, multi-tenant
          isolation, or enterprise SSO. The benchmark measures recovery on
          synthetic incidents, not real-world accuracy.
        </p>
      </section>
    </div>
  );
}
