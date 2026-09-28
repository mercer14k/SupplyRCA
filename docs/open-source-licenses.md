# Open-source and model licenses

SupplyRCA's original code and synthetic data are Apache-2.0 (LICENSE/NOTICE). No customer data, proprietary model weights, paid API SDK, remote analytics, or closed-source AI service is included. Optional models are downloaded separately and their licenses must be reviewed at the selected revision. This is a dependency inventory, not a substitute for preserving upstream notices when redistributing binaries.

## Material application dependencies

| Component | License | Role / upstream |
|---|---|---|
| Python | PSF-2.0 | [Runtime](https://github.com/python/cpython/blob/main/LICENSE) |
| FastAPI, Starlette, Pydantic / pydantic-core, Uvicorn | MIT | Typed HTTP and validation; exact versions in requirements.lock |
| Polars / polars-runtime | MIT | [Columnar computation](https://github.com/pola-rs/polars/blob/main/LICENSE) |
| NumPy | BSD-3-Clause | Numeric arrays; bundled BLAS/runtime notices also apply |
| SciPy | BSD-3-Clause | [Statistical tests](https://github.com/scipy/scipy/blob/main/LICENSE.txt); wheels bundle additional licensed numerical libraries |
| ruptures | BSD-2-Clause | [PELT change-point detection](https://github.com/deepcharles/ruptures/blob/master/LICENSE) |
| SQLAlchemy | MIT | Parameterized persistence |
| Psycopg / psycopg-binary | LGPL-3.0-only | [PostgreSQL driver](https://github.com/psycopg/psycopg/blob/master/LICENSE.txt); preserve LGPL notices and applicable source/relinking rights on redistribution; bundled libpq uses PostgreSQL License |
| PostgreSQL | PostgreSQL License | [Database](https://www.postgresql.org/about/licence/) |
| HTTPX, httpcore, h11, AnyIO | BSD-3-Clause / MIT | Local runtime transport and async primitives; resolved license metadata in inventory |
| certifi | MPL-2.0 | CA certificate bundle; preserve notice for redistributed modifications |
| React / React DOM | MIT | [Interface](https://github.com/facebook/react/blob/main/LICENSE) |
| Apache ECharts / zrender | Apache-2.0 / BSD-3-Clause | [Charts](https://github.com/apache/echarts/blob/master/LICENSE) |
| Lucide React | ISC | [Icons](https://github.com/lucide-icons/lucide/blob/main/LICENSE) |
| nginx | BSD-2-Clause | [Local reverse proxy](https://nginx.org/LICENSE) |
| Docker Engine / Compose | Apache-2.0 | Open-source container engine/orchestration; proprietary Docker Desktop is not required |
| Node.js | MIT and bundled licenses | [Build runtime](https://github.com/nodejs/node/blob/main/LICENSE) |

## Build, testing and security tools

TypeScript and Playwright use Apache-2.0. Vite, Vitest, Rollup, esbuild, ESLint, typescript-eslint, Prettier, pnpm, pytest, Ruff, Testing Library and jsdom use MIT. Coverage.py uses Apache-2.0; pip-audit uses Apache-2.0. GitHub's checkout/setup/upload-artifact actions are MIT. Actions are hosted on GitHub but are not required to run core features locally.

Lockfiles capture exact resolved versions. `docs/dependency-inventory.json` captures installed runtime package license metadata; `requirements.lock`, `requirements-dev.lock` and `apps/web/pnpm-lock.yaml` are the install sources. Transitive binary distributions may include multiple licenses: in particular SciPy/NumPy BLAS/LAPACK and compiler runtime libraries, libpq/OpenSSL, Python, Node, and base container OS packages. Preserve the notices shipped in those distributions. Run the CI audits when changing versions.

A temporary `pgserver` package (Apache-2.0) was used to run an isolated native PostgreSQL validation on the build machine. It is not an application or required development dependency; CI uses the PostgreSQL container instead.

## Optional local AI

| Component | License | Notes |
|---|---|---|
| Ollama | MIT | [Local runtime](https://github.com/ollama/ollama/blob/main/LICENSE) |
| llama.cpp | MIT | [Optional runtime](https://github.com/ggml-org/llama.cpp/blob/master/LICENSE) |
| vLLM | Apache-2.0 | [Optional runtime](https://github.com/vllm-project/vllm/blob/main/LICENSE) |
| Qwen2.5-7B-Instruct | Apache-2.0 | [Model license](https://huggingface.co/Qwen/Qwen2.5-7B-Instruct/blob/main/LICENSE), independently verified for the 7B model. The similarly named 3B/72B variants have different terms. |

Open weights and an open-source runtime are distinct license questions. Do not infer permission for arbitrary models from this table. No model weights are committed or redistributed by this repository; the no-LLM workflow remains the default.
