# Threat model

## Assets and trust boundaries

Assets: imported supply-chain data, analyst notes, investigation integrity, local filesystem/database and optional model resources. Actors: the local analyst, an untrusted upload author, a malicious browser origin and a compromised/misbehaving local model. Boundaries: browser→API, imported JSON→validated snapshot, snapshot→model facts, model response→narrative, and API→PostgreSQL roles.

| Threat | Implemented control | Remaining limitation |
|---|---|---|
| Drive-by browser mutation | Same-origin development proxy; explicit allowed Origin check; required custom mutation header; no permissive CORS | Demo mode trusts local clients and is not authentication |
| Unauthorized access | `APP_MODE=token`, minimum 32-character server token, constant-time bearer comparison on all versioned reads/writes | Shared single-analyst token; no user/tenant roles or SSO |
| Oversized or malformed upload | ASGI 16 MiB bound including chunked bodies, JSON MIME/extension allowlist, filename basename sanitization, strict record schemas | Input is buffered inside the bound; no global byte/storage quota |
| Data loss or poisoned metrics | Whole-bundle quarantine, immutable dataset IDs/hashes, visible row errors, balance and FK checks | Business-plausible but false source data cannot be authenticated by schemas |
| SQL injection | SQLAlchemy parameter binding; no SQL from the model or uploaded content | Production database hardening and backup policy remain operator responsibilities |
| Prompt injection | Model sees a minimal computed-facts projection; data is labeled untrusted; no tools or execution capabilities | Prompt/semantic misinterpretation can still affect optional narrative prose |
| Hallucination | Structured schema, matched citation IDs, numerical-prose rejection, abstention and deterministic fallback | Citation integrity does not prove qualitative statements true |
| Replay/concurrent writes | Unique key plus request hash, transactional inserts, append-only idempotent reviews | Duplicate computation may occur before the unique constraint resolves it |
| XSS | React text rendering, no dangerous HTML insertion, fixed API base, CSP in nginx, nosniff | Compromised frontend dependencies remain a supply-chain risk |
| Privilege escalation | Non-root API/web, dropped container capabilities, internal database network, read-only query credentials | Bootstrap DB superuser exists inside the private Compose network |
| Information leakage | Loopback host bindings, structured errors, generated trace IDs, logs omit auth/payloads | Private imports and notes persist on local disk/volumes; operator must protect backups |

No external cloud AI, paid APIs, analytics beacons or remote fonts are required. Model output never becomes shell, SQL, a URL to fetch, or a tool call. Only typed human-facing investigation/review/import mutations exist. There are no state-changing AI tools to allowlist.

## Deployment boundary

Default Compose is for localhost only. Public database passwords in Compose/init SQL are development defaults and intentionally cannot be considered credentials for any real environment. Before network exposure provision unique secret values through a secret manager, enforce token mode or a stronger identity proxy, require TLS, configure host/origin allowlists, add request rate/storage quotas, backups and tenant policies, and review a deployment-specific threat model. Never commit a real `.env` or imported customer data.

The native SQLite path uses the same in-process connection for reading/writing; it has no separate DB role. PostgreSQL Compose uses `supplyrca` (non-superuser writer) and `supplyrca_reader` (SELECT-only role). Initial schema creation requires writer DDL; managed migrations and a reduced runtime writer role are future work.

Dependency checks use open-source `pip-audit` and pnpm audit in CI; the audit lookups contact public advisory registries. Normal demo runtime does not contact them. See SECURITY.md for vulnerability disclosure. Repository build dependencies are pinned with lockfiles; container image tags are versioned but not digest-pinned, a release-hardening item.
