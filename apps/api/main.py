import json
import os
import re
import secrets
import time
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from sqlalchemy import text
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.trustedhost import TrustedHostMiddleware
from supplyrca.ai.narrative import LocalRuntime
from supplyrca.data.store import Conflict, Store
from supplyrca.data.validation import validate_bundle
from supplyrca.domain.analysis import InsufficientEvidence
from supplyrca.domain.schemas import ErrorResponse, InvestigationOutput, InvestigationRequest, Review
from supplyrca.observability.logging import emit
from supplyrca.services.investigations import InvestigationService, report_markdown

MAX_BODY = 16 * 1024 * 1024


class BodyLimit:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        # Bound the entire body before JSON decoding, including chunked requests.
        chunks = []
        total = 0
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            total += len(message.get("body", b""))
            if total > MAX_BODY:
                response = JSONResponse(
                    {
                        "error": {
                            "code": "body_too_large",
                            "message": "Maximum request size is 16 MiB",
                            "trace_id": str(uuid4()),
                        }
                    },
                    status_code=413,
                )
                return await response(scope, receive, send)
            chunks.append(message.get("body", b""))
            if not message.get("more_body", False):
                break
        delivered = False

        async def replay():
            nonlocal delivered
            if not delivered:
                delivered = True
                return {"type": "http.request", "body": b"".join(chunks), "more_body": False}
            return await receive()

        return await self.app(scope, replay, send)


def create_app(database_url=None, sample_path=None, mode=None, token=None, runtime=None):
    mode = mode or os.getenv("APP_MODE", "demo")
    token = token if token is not None else os.getenv("API_TOKEN", "")
    if mode not in {"demo", "token"} or (mode == "token" and len(token) < 32):
        raise RuntimeError("APP_MODE must be demo or token; token mode requires a 32-character API_TOKEN")
    store = Store(
        database_url or os.getenv("DATABASE_URL", "sqlite:///./supplyrca.db"),
        os.getenv("READ_DATABASE_URL") or None,
    )
    provider = os.getenv("AI_PROVIDER", "none")
    if runtime is None and provider != "none":
        if provider not in {"ollama", "llamacpp", "vllm"}:
            raise RuntimeError("Only local AI runtimes are supported")
        runtime = LocalRuntime(
            os.getenv("AI_BASE_URL", "http://localhost:11434"), os.getenv("AI_MODEL", "qwen2.5:7b"), provider
        )
    service = InvestigationService(store, runtime)
    sample = sample_path or os.getenv(
        "SAMPLE_PATH", str(Path(__file__).resolve().parents[2] / "data/sample/dataset.json.gz")
    )

    @asynccontextmanager
    async def lifespan(app):
        service.seed_demo(sample)
        yield
        store.engine.dispose()
        if store.read_engine is not store.engine:
            store.read_engine.dispose()

    app = FastAPI(
        title="SupplyRCA",
        version="0.1.0",
        responses={code: {"model": ErrorResponse} for code in [401, 403, 404, 409, 413, 415, 422, 500]},
        lifespan=lifespan,
        docs_url="/docs" if mode == "demo" else None,
        redoc_url=None,
        openapi_url="/openapi.json" if mode == "demo" else None,
    )
    app.state.service, app.state.store = service, store
    app.add_middleware(BodyLimit)
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1,testserver,api").split(","),
    )

    @app.middleware("http")
    async def observe(request, call_next):
        request.state.trace_id = str(uuid4())
        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception as exc:
            emit("request_failed", trace_id=request.state.trace_id, error_type=type(exc).__name__)
            response = JSONResponse(
                {
                    "error": {
                        "code": "internal_error",
                        "message": "Unexpected error; use trace ID for diagnosis",
                        "trace_id": request.state.trace_id,
                    }
                },
                status_code=500,
            )
        response.headers["X-Trace-ID"] = request.state.trace_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Cache-Control"] = "no-store"
        emit(
            "request",
            trace_id=request.state.trace_id,
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            latency_ms=round((time.perf_counter() - started) * 1000, 2),
        )
        return response

    def error(request, status, code, message):
        return JSONResponse(
            {"error": {"code": code, "message": message, "trace_id": request.state.trace_id}},
            status_code=status,
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_error(request, exc):
        return error(request, exc.status_code, "http_error", str(exc.detail))

    @app.exception_handler(RequestValidationError)
    async def schema_error(request, exc):
        return error(request, 422, "schema_validation", "; ".join(e["msg"] for e in exc.errors())[:1000])

    @app.exception_handler(KeyError)
    async def missing(request, exc):
        return error(request, 404, "not_found", "Requested resource was not found")

    @app.exception_handler(Conflict)
    async def conflict(request, exc):
        return error(request, 409, "conflict", str(exc))

    @app.exception_handler(InsufficientEvidence)
    async def insufficient(request, exc):
        return error(request, 422, "insufficient_evidence", str(exc))

    @app.exception_handler(ValueError)
    async def invalid(request, exc):
        return error(request, 422, "invalid_data", str(exc)[:500])

    def authorize(authorization: str | None = Header(default=None)):
        if mode == "token" and not secrets.compare_digest(authorization or "", "Bearer " + token):
            raise HTTPException(401, "Valid bearer token required")

    def mutate(request: Request, x_supplyrca_client: str | None = Header(default=None)):
        if x_supplyrca_client != "analyst":
            raise HTTPException(403, "X-SupplyRCA-Client: analyst required")
        origin = request.headers.get("origin")
        if origin and origin not in os.getenv(
            "ALLOWED_ORIGINS",
            "http://localhost:8080,http://127.0.0.1:8080,http://localhost:5173,http://127.0.0.1:5173",
        ).split(","):
            raise HTTPException(403, "Origin is not allowed")

    def key(idempotency_key: str = Header(min_length=8, max_length=100)):
        if not re.fullmatch(r"[a-zA-Z0-9_.:-]+", idempotency_key):
            raise HTTPException(422, "Invalid idempotency key")
        return idempotency_key

    read = APIRouter(prefix="/api/v1", dependencies=[Depends(authorize)])
    write = APIRouter(prefix="/api/v1", dependencies=[Depends(authorize), Depends(mutate)])

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.get("/ready")
    def ready():
        try:
            with store.read_engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            store.dataset("demo-v1")
        except Exception:
            raise HTTPException(503, "Database or sample dataset unavailable") from None
        return {"status": "ready", "ai_required": False}

    @read.get("/config")
    def config():
        return {"mode": mode, "ai_provider": provider, "version": "0.1.0"}

    @read.get("/datasets")
    def datasets():
        return {"items": store.list_datasets()}

    @read.get("/datasets/{dataset_id}/validation")
    def validation(dataset_id: str):
        return store.dataset(dataset_id)["report"]

    @read.get("/datasets/{dataset_id}/overview")
    def overview(dataset_id: str):
        return service.overview(dataset_id)

    @read.get("/datasets/{dataset_id}/anomalies")
    def anomalies(dataset_id: str, offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100)):
        rows = service.anomalies(dataset_id)
        return {"items": rows[offset : offset + limit], "total": len(rows), "offset": offset, "limit": limit}

    @read.get("/datasets/{dataset_id}/records")
    def records(
        dataset_id: str,
        table: str = "demand",
        q: str = Query("", max_length=100),
        offset: int = Query(0, ge=0),
        limit: int = Query(50, ge=1, le=200),
    ):
        data = store.dataset(dataset_id)
        if not data["report"]["valid"]:
            raise ValueError("Dataset is quarantined")
        if table not in data["payload"]["tables"]:
            raise HTTPException(422, "Unknown table")
        rows = data["payload"]["tables"][table]
        if q:
            rows = [r for r in rows if q.casefold() in json.dumps(r).casefold()]
        return {"items": rows[offset : offset + limit], "total": len(rows), "offset": offset, "limit": limit}

    @write.put("/datasets/{dataset_id}")
    async def upload(dataset_id: str, request: Request, x_filename: str = Header(default="dataset.json")):
        if not re.fullmatch(r"[a-zA-Z0-9_.:-]{1,100}", dataset_id):
            raise HTTPException(422, "Invalid dataset ID")
        filename = Path(x_filename.replace("\\", "/")).name
        if (
            not filename.lower().endswith(".json")
            or request.headers.get("content-type", "").split(";")[0] != "application/json"
        ):
            raise HTTPException(415, "Upload a JSON bundle using application/json")
        raw = await request.body()
        try:
            payload = json.loads(raw)
        except (ValueError, UnicodeDecodeError):
            raise HTTPException(422, "Malformed JSON; nothing was imported") from None
        clean, report = validate_bundle(payload)
        report["filename"] = filename
        # Whole-bundle quarantine preserves rejected input and its validation report.
        stored = (
            {"schema_version": "1", "tables": clean} if report["valid"] else {"quarantined_input": payload}
        )
        store.import_dataset(dataset_id, stored, report)
        return JSONResponse(
            {"dataset_id": dataset_id, "validation": report}, status_code=201 if report["valid"] else 422
        )

    @read.get("/investigations")
    def list_investigations(offset: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=100)):
        return store.list(offset, limit)

    @write.post("/investigations", status_code=201, response_model=InvestigationOutput)
    def investigate(body: InvestigationRequest, request: Request, idempotency: str = Depends(key)):
        result = service.run(body, idempotency)
        emit(
            "investigation",
            trace_id=request.state.trace_id,
            episode_id=result["id"],
            data_version=result["dataset_sha256"],
            algorithm_version=result["algorithm_version"],
            parameters=result["parameters"],
            **result["narrative"]["telemetry"],
        )
        return result

    @read.get("/investigations/{identifier}", response_model=InvestigationOutput)
    def investigation(identifier: str):
        return store.get(identifier)

    @write.put(
        "/investigations/{identifier}/hypotheses/{hypothesis_id}/review", response_model=InvestigationOutput
    )
    def review(identifier: str, hypothesis_id: str, body: Review, idempotency: str = Depends(key)):
        return store.review(identifier, hypothesis_id, body.model_dump(), idempotency)

    @read.get("/investigations/{identifier}/export")
    def export(identifier: str, format: str = Query("markdown", pattern="^(markdown|json)$")):
        result = store.get(identifier)
        raw = json.dumps(result, indent=2) if format == "json" else report_markdown(result)
        extension = "json" if format == "json" else "md"
        return Response(
            raw,
            media_type="application/json" if format == "json" else "text/markdown",
            headers={"Content-Disposition": f'attachment; filename="supplyrca-{result["id"]}.{extension}"'},
        )

    app.include_router(read)
    app.include_router(write)
    return app
