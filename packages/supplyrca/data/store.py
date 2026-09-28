"""Transactional SQL persistence with immutable datasets and append-only review history."""

import hashlib
import json
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    ForeignKey,
    MetaData,
    String,
    Table,
    create_engine,
    func,
    select,
)
from sqlalchemy.exc import IntegrityError

metadata = MetaData()
datasets = Table(
    "datasets",
    metadata,
    Column("id", String(100), primary_key=True),
    Column("payload", JSON, nullable=False),
    Column("report", JSON, nullable=False),
)
investigations = Table(
    "investigations",
    metadata,
    Column("id", String(40), primary_key=True),
    Column("dataset_id", String(100), ForeignKey("datasets.id"), nullable=False),
    Column("idempotency_key", String(100), unique=True, nullable=False),
    Column("request_hash", String(64), nullable=False),
    Column("result", JSON, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
)
reviews = Table(
    "reviews",
    metadata,
    Column("id", String(40), primary_key=True),
    Column("investigation_id", String(40), ForeignKey("investigations.id"), nullable=False),
    Column("hypothesis_id", String(200), nullable=False),
    Column("payload", JSON, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
)


class Conflict(ValueError):
    pass


class Store:
    def __init__(self, url: str, read_url: str | None = None):
        options = {"connect_args": {"check_same_thread": False}} if url.startswith("sqlite") else {}
        self.engine = create_engine(url, **options)
        self.read_engine = create_engine(read_url) if read_url else self.engine
        metadata.create_all(self.engine)

    def dataset(self, identifier):
        with self.read_engine.connect() as conn:
            row = conn.execute(select(datasets).where(datasets.c.id == identifier)).mappings().first()
        if row is None:
            raise KeyError(identifier)
        return dict(row)

    def import_dataset(self, identifier, payload, report):
        try:
            with self.engine.begin() as conn:
                conn.execute(datasets.insert().values(id=identifier, payload=payload, report=report))
        except IntegrityError:
            existing = self.dataset(identifier)
            if existing["report"].get("sha256") != report.get("sha256"):
                raise Conflict("Dataset IDs are immutable; choose a new ID") from None
        return self.dataset(identifier)

    def list_datasets(self):
        with self.read_engine.connect() as conn:
            return [dict(row) for row in conn.execute(select(datasets.c.id, datasets.c.report)).mappings()]

    @staticmethod
    def request_hash(request):
        return hashlib.sha256(json.dumps(request, sort_keys=True).encode()).hexdigest()

    def cached(self, key, request):
        with self.read_engine.connect() as conn:
            row = (
                conn.execute(select(investigations).where(investigations.c.idempotency_key == key))
                .mappings()
                .first()
            )
        if row:
            if row["request_hash"] != self.request_hash(request):
                raise Conflict("Idempotency key was already used with another request")
            return self.get(row["id"])
        return None

    def save(self, result, key):
        identifier = str(uuid4())
        result = {**result, "id": identifier, "created_at": datetime.now(timezone.utc).isoformat()}
        try:
            with self.engine.begin() as conn:
                conn.execute(
                    investigations.insert().values(
                        id=identifier,
                        dataset_id=result["request"]["dataset_id"],
                        idempotency_key=key,
                        request_hash=self.request_hash(result["request"]),
                        result=result,
                        created_at=datetime.now(timezone.utc),
                    )
                )
        except IntegrityError:
            cached = self.cached(key, result["request"])
            if cached:
                return cached
            raise
        return result

    def get(self, identifier):
        with self.read_engine.connect() as conn:
            row = conn.execute(
                select(investigations.c.result).where(investigations.c.id == identifier)
            ).first()
            if row is None:
                raise KeyError(identifier)
            result = row[0]
            history = [
                dict(r)
                for r in conn.execute(
                    select(reviews)
                    .where(reviews.c.investigation_id == identifier)
                    .order_by(reviews.c.created_at, reviews.c.id)
                ).mappings()
            ]
        result["reviews"] = [{**r, "created_at": r["created_at"].isoformat()} for r in history]
        for review in history:
            for hypothesis in result["hypotheses"]:
                if hypothesis["id"] == review["hypothesis_id"]:
                    hypothesis.update(review["payload"])
        return result

    def review(self, identifier, hypothesis_id, payload, key):
        result = self.get(identifier)
        if hypothesis_id not in {h["id"] for h in result["hypotheses"]}:
            raise KeyError(hypothesis_id)
        rid = hashlib.sha256((identifier + ":" + key).encode()).hexdigest()[:40]
        try:
            with self.engine.begin() as conn:
                conn.execute(
                    reviews.insert().values(
                        id=rid,
                        investigation_id=identifier,
                        hypothesis_id=hypothesis_id,
                        payload=payload,
                        created_at=datetime.now(timezone.utc),
                    )
                )
        except IntegrityError:
            with self.read_engine.connect() as conn:
                old = conn.execute(select(reviews).where(reviews.c.id == rid)).mappings().one()
                if old["payload"] != payload or old["hypothesis_id"] != hypothesis_id:
                    raise Conflict("Review idempotency key reused with another payload") from None
        return self.get(identifier)

    def list(self, offset=0, limit=20):
        with self.read_engine.connect() as conn:
            total = conn.execute(select(func.count()).select_from(investigations)).scalar_one()
            rows = (
                conn.execute(
                    select(investigations.c.result)
                    .order_by(investigations.c.created_at.desc())
                    .offset(offset)
                    .limit(limit)
                )
                .scalars()
                .all()
            )
        return {
            "items": [{k: r[k] for k in ["id", "created_at", "request", "summary"]} for r in rows],
            "total": total,
            "offset": offset,
            "limit": limit,
        }
