# AI design

Statistical diagnostics lead; a model is an optional evidence-grounded prose assistant. The default `AI_PROVIDER=none` requires no AI runtime, model, paid account or outbound service.

## Runtime abstraction

`Runtime.generate(facts)` returns a JSON object and observable usage metadata. `LocalRuntime` supports Ollama `/api/chat` with JSON schema output, or local llama.cpp/vLLM `/v1/chat/completions` with a JSON schema response format. No cloud client SDK, model-generated tools, SQL, shell, or free-form workflow state is accepted. The local endpoint is server configuration, never provided by imported records or requests.

Recommended optional model: `qwen2.5:7b`, corresponding to Apache-2.0 Qwen2.5-7B-Instruct. The similarly named 3B model has different licensing; do not assume a family-wide license. Weights are downloaded separately. Optional runtimes' protocol behavior must be checked against the installed version; unsupported structured output falls back safely.

## Generation and validation

The prompt labels findings as untrusted data and provides only computed finding IDs, titles, support and permitted evidence IDs. It excludes analyst notes, supplier prose and raw uploaded strings. Temperature is zero; seed is 42; output generation is capped at 1,400 tokens. Requests have a 35-second timeout and at most one retry.

Pydantic requires a summary, bounded claims with finding/evidence references, abstention and limitations. Every cited finding and evidence must exist and match. Mechanism claims must cite specific evidence, not only the aggregate KPI. Duplicate findings, prose digits, and selected definitive causal terms are rejected. Unknown/missing evidence forces abstention. Numbers and inventory calculations are displayed from deterministic fields, not model prose.

These checks ensure reference integrity, not semantic truthfulness. A model can still produce an unsupported qualitative interpretation with a valid citation. Treat local-model narrative as generated commentary and review its sources. No hidden chain-of-thought is requested, retained or exposed.

## Telemetry and failure isolation

Each investigation stores runtime, requested/reported model, template version, input evidence IDs, temperature/seed, latency, retry count, output validation failure types, optional tokens/usage, and an empty tool-call list because no model tools are permitted. Request logs add trace/episode ID, dataset hash and algorithm parameters. Raw prompts, private notes, auth headers and database URLs are not logged.

The computational snapshot is hashed before the model is called. Model facts are copied. Exceptions/invalid outputs trigger the deterministic narrative; saved numerical findings remain identical. Tests exercise offline runtimes, forged citations, numerical hallucinations, missing evidence, and valid schema output. The committed benchmark runs without a model and must not be described as LLM performance.

## Compare local models

```sh
supplyrca-benchmark --runtime ollama --model qwen2.5:7b --base-url http://localhost:11434 --output artifacts/ollama-qwen
supplyrca-benchmark --runtime llamacpp --model local-model --base-url http://localhost:8081 --output artifacts/llamacpp
```

Run one model at a time on the same dataset/hardware. Inspect `narrative_origin` per episode: fallback results are reported as templates, not successful generations. Citation coverage alone is insufficient; inspect qualitative correctness and abstention on adversarial/unknown-mechanism inputs before deployment. Model digest/quantization metadata needs to be captured by the operator when the runtime does not expose it in the response.
