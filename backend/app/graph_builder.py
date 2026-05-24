"""Build a simple claim graph as JSON (no Neo4j in the MVP).

Node types: paper, claim, evidence_gap, overclaim_risk, reproducibility_risk.
Edge types: contains (paper->claim), has_gap (claim->gap),
has_overclaim_risk (claim->overclaim), has_reproducibility_risk (paper->risk).
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from .models import Graph, GraphEdge, GraphNode

if TYPE_CHECKING:  # avoid a runtime import cycle with review_pipeline
    from .review_pipeline import Analysis

_LABEL_MAX = 80


def _label(text: str) -> str:
    text = " ".join(text.split())
    if len(text) <= _LABEL_MAX:
        return text
    return text[: _LABEL_MAX - 1].rstrip() + "…"


def build_graph(an: "Analysis") -> Graph:
    nodes: list[GraphNode] = []
    edges: list[GraphEdge] = []

    paper_id = "paper"
    nodes.append(GraphNode(id=paper_id, type="paper", label=_label(an.title or "Paper")))

    for claim in an.claims:
        nodes.append(GraphNode(
            id=claim.id, type="claim",
            label=f"[{claim.category}] {_label(claim.text)}",
        ))
        edges.append(GraphEdge(source=paper_id, target=claim.id, type="contains"))

    for oc in an.overclaims:
        nodes.append(GraphNode(id=oc.id, type="overclaim_risk", label=_label(", ".join(oc.terms))))
        edges.append(GraphEdge(source=oc.claim_id, target=oc.id, type="has_overclaim_risk"))

    for gap in an.evidence_gaps:
        nodes.append(GraphNode(id=gap.id, type="evidence_gap", label="evidence gap"))
        edges.append(GraphEdge(source=gap.claim_id, target=gap.id, type="has_gap"))

    for risk in an.reproducibility_risks:
        nodes.append(GraphNode(id=risk.id, type="reproducibility_risk", label=risk.risk_type))
        edges.append(GraphEdge(source=paper_id, target=risk.id, type="has_reproducibility_risk"))

    return Graph(nodes=nodes, edges=edges)
