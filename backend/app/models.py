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
    # Provenance + stable identity (SPL content/method discipline).
    # `method` names HOW the claim was derived; `content_hash` is a
    # replay-stable identity over the normalized claim text (DESi replay_hash).
    method: str = "workbench_heuristic"
    content_hash: str = ""


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


class CrossClaimMatch(BaseModel):
    """A claim in THIS review that matches/resembles a claim from a PRIOR review,
    found deterministically in the shared claim ledger (Layer 9).

    ``match_type`` is ``exact`` (same content_hash) or ``lexical`` (Jaccard over
    normalized token sets >= threshold). ``score`` is 1.0 for exact, else Jaccard.
    """
    claim_id: str
    match_type: str
    score: float
    prior_review_id: str
    prior_claim_id: str
    prior_text: str


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
    # Layer 9: claims in THIS review that match/resemble claims from PRIOR
    # reviews in the shared claim ledger. Deterministic (exact + lexical).
    # History-dependent, so kept OUTSIDE the replay hash by design.
    cross_review: list[CrossClaimMatch] = Field(default_factory=list)
