from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Nonnegative = Annotated[float, Field(ge=0, allow_inf_nan=False)]
Identifier = Annotated[str, Field(min_length=1, max_length=100, pattern=r"^[a-zA-Z0-9_.:-]+$")]
KPI = Literal["fill_rate", "stockout_rate", "lead_time", "excess_inventory", "forecast_accuracy"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class Provenance(StrictModel):
    id: Identifier
    source_id: Identifier
    ingested_at: datetime
    validation_status: Literal["valid"] = "valid"
    lineage: dict[str, str] = Field(default_factory=dict)


class Supplier(Provenance):
    name: str = Field(max_length=120)
    country: str = Field(max_length=80)


class DailyRecord(Provenance):
    date: date
    sku: Identifier
    market: Identifier
    supplier_id: Identifier


class Demand(DailyRecord):
    demand: Nonnegative
    forecast: Nonnegative
    fulfilled: Nonnegative

    @model_validator(mode="after")
    def balance(self):
        if self.fulfilled > self.demand:
            raise ValueError("fulfilled exceeds demand")
        return self


class Inventory(DailyRecord):
    opening: Nonnegative
    received: Nonnegative
    shipped: Nonnegative
    closing: Nonnegative

    @model_validator(mode="after")
    def balance(self):
        if abs(self.opening + self.received - self.shipped - self.closing) > 0.011:
            raise ValueError("inventory balance does not reconcile")
        return self


class PurchaseOrder(DailyRecord):
    ordered: Nonnegative
    received: Nonnegative
    lead_days: Nonnegative
    promised_lead_days: Nonnegative


class Shipment(DailyRecord):
    transit_days: Nonnegative
    planned_transit_days: Nonnegative
    po_id: Identifier


class InvestigationRequest(StrictModel):
    dataset_id: Identifier = "demo-v1"
    kpi: KPI = "fill_rate"
    start: date
    end: date
    baseline_days: int = Field(default=28, ge=14, le=90)
    sku: Identifier | None = None
    market: Identifier | None = None

    @model_validator(mode="after")
    def dates(self):
        if self.end < self.start or (self.end - self.start).days > 90:
            raise ValueError("investigation window must be between 1 and 91 days")
        return self


class Review(StrictModel):
    decision: Literal["accepted", "rejected", "annotated"]
    note: str = Field(default="", max_length=2000)


class Citation(StrictModel):
    finding_id: str
    evidence_ids: list[str] = Field(min_length=1, max_length=12)
    explanation: str = Field(min_length=1, max_length=800)


class Narrative(StrictModel):
    summary: str = Field(max_length=1200)
    claims: list[Citation] = Field(max_length=8)
    abstained: bool
    limitations: list[str] = Field(max_length=8)


class ErrorDetail(StrictModel):
    code: str
    message: str
    trace_id: str


class ErrorResponse(StrictModel):
    error: ErrorDetail


class KPISummary(StrictModel):
    baseline: float
    current: float
    delta: float
    unfilled_units: Nonnegative
    coverage: float = Field(ge=0, le=1)
    baseline_rows: int
    current_rows: int


class Evidence(StrictModel):
    id: str
    kind: Literal["accounting", "operational_association"]
    label: str
    baseline: float
    current: float
    record_ids: list[str]
    method: str
    p_value: float | None = None
    q_value: float | None = None
    spearman_rho: float | None = None


class Hypothesis(StrictModel):
    id: str
    cause: str
    title: str
    sku: str
    market: str
    supplier_id: str
    support: float = Field(ge=0, le=1)
    evidence_level: Literal["observational"]
    q_value: float = Field(ge=0, le=1)
    correlation: float | None
    evidence_ids: list[str]
    decision: Literal["unreviewed", "accepted", "rejected", "annotated"]
    note: str
    caveat: str


class Decomposition(StrictModel):
    dimension: str
    key: str
    baseline: float
    current: float
    rate_effect: float
    mix_effect: float
    contribution: float
    demand: float
    unfilled: float


class TimelinePoint(StrictModel):
    date: date
    value: float | None
    demand: float
    unfilled: float


class GraphNode(StrictModel):
    id: str
    label: str
    kind: Literal["computed", "hypothesis"]


class GraphEdge(StrictModel):
    source: str
    target: str
    type: Literal["supported_association"]
    evidence_ids: list[str]


class Graph(StrictModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]


class NarrativeResult(StrictModel):
    origin: Literal["deterministic_template", "local_llm"]
    content: Narrative
    telemetry: dict


class ReviewEvent(StrictModel):
    id: str
    investigation_id: str
    hypothesis_id: str
    payload: Review
    created_at: datetime


class InvestigationOutput(StrictModel):
    id: str
    created_at: datetime
    algorithm_version: str
    parameters: dict
    request: InvestigationRequest
    summary: KPISummary
    timeline: list[TimelinePoint]
    change_points: list[str]
    decomposition: dict[str, list[Decomposition]]
    hypotheses: list[Hypothesis]
    evidence: list[Evidence]
    graph: Graph
    tests_performed: int
    limitations: list[str]
    dataset_sha256: str
    deterministic_sha256: str
    narrative: NarrativeResult
    duration_ms: float
    reviews: list[ReviewEvent] = Field(default_factory=list)
