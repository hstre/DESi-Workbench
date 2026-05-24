"""API models for the DESi Workbench backend."""
from __future__ import annotations

from pydantic import BaseModel, Field

CLAIM_CATEGORIES = (
    "main_claim",
    "method_claim",
    "evidence_claim",
    "result_claim",
    "limitation_claim",
    "novelty_claim",
    "generalization_claim",
)

REPRO_RISK_TYPES = (
    "missing_data",
    "missing_code",
    "missing_baselines",
    "missing_parameters",
    "unclear_dataset",
    "unsupported_metrics",
)


class ReviewRequest(BaseModel):
    title: str | None = Field(default=None)
    text: str
    mode: str = Field(default="offline")


class Claim(BaseModel):
    id: str
    category: str
    section: str
    text: str
    has_numbers: bool = False
    overclaim_terms: list[str] = Field(default_factory=list)
    supported: bool = True


class Overclaim(BaseModel):
    id: str
    claim_id: str
    section: str
    text: str
    terms: list[str]
    reason: str


class EvidenceGap(BaseModel):
    id: str
    claim_id: str
    section: str
    note: str
    missing: str = "inline_support"


class ReproRisk(BaseModel):
    id: str
    risk_type: str
    detail: str


class GraphNode(BaseModel):
    id: str
    type: str
    label: str


class GraphEdge(BaseModel):
    source: str
    target: str
    type: str


class Graph(BaseModel):
    nodes: list[GraphNode] = Field(default_factory=list)
    edges: list[GraphEdge] = Field(default_factory=list)


class Replay(BaseModel):
    input_hash: str
    output_hash: str
    pipeline_version: str
    offline_mode: bool
    core_identity: float
    audit_framing: str
    desi_library: str
    desi_version: str
    forbidden_term_hits: list[str] = Field(default_factory=list)


class ReviewResponse(BaseModel):
    review_id: str
    title: str
    claims: list[Claim] = Field(default_factory=list)
    unsupported_claims: list[Claim] = Field(default_factory=list)
    overclaims: list[Overclaim] = Field(default_factory=list)
    evidence_gaps: list[EvidenceGap] = Field(default_factory=list)
    reproducibility_risks: list[ReproRisk] = Field(default_factory=list)
    reviewer_questions: list[str] = Field(default_factory=list)
    graph: Graph = Field(default_factory=Graph)
    replay: Replay
    verdict: str
