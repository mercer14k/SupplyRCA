# ADR 002 — Observable evidence, optional local prose

Status: accepted for v0.1.0.

Use deterministic mechanism gates and multiple-test-adjusted support instead of asking a model to select causes. Name graph edges `supported_association` and record the observational caveat on every hypothesis. Exact accounting attribution is separate from evidence support and is not interpreted as a causal effect.

Use a minimal local runtime protocol with Ollama and local OpenAI-compatible llama.cpp/vLLM endpoints. The compatibility protocol is open and does not imply use of OpenAI's proprietary service. Qwen2.5-7B-Instruct is the documented optional Apache-2.0 model; its weights are separate downloads. The default template path is fully usable without AI.

Structured schema and citation validation reject malformed/unmatched outputs. A deterministic fallback means model outages do not block the computational workflow. The tradeoff is constrained narratives and potential abstention even when a model might produce helpful unconstrained prose. Semantic entailment is not guaranteed by citation validation, so analyst review and adversarial evaluation remain required.
