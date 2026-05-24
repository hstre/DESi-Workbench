"""Render a review as a deterministic Markdown report."""
from __future__ import annotations

from .models import ReviewResponse

_MAIN_CATEGORIES = ("main_claim", "novelty_claim", "generalization_claim", "result_claim")

_LIMITATIONS = (
    "- This is an epistemic-audit assistant, not a peer reviewer. The only verdict is `REVIEW_ASSISTANCE_ONLY`.",
    "- It never accepts, rejects, or validates a paper, never replaces a reviewer, and never guarantees correctness.",
    "- All findings come from transparent, deterministic heuristics over the submitted text; expect false positives and negatives.",
    "- Absence of a flag is not a sign of quality; presence of a flag is not a sign of a defect. Every item needs human judgement.",
    "- Output is offline and reproducible; it reflects only the provided text and uses no external knowledge.",
)


def render_report(review: ReviewResponse) -> str:
    r = review
    lines: list[str] = []
    add = lines.append

    add("# DESi Workbench Review Report")
    add("")
    add(f"**Title:** {r.title}")
    add(f"**Review ID:** `{r.review_id}`")
    add(f"**Verdict:** `{r.verdict}`")
    add("")

    add("## Scope")
    add("")
    add("This is not peer review. This is an epistemic audit assistant.")
    add("")
    add(f"> {r.replay.audit_framing}")
    add("")
    add(f"- DESi library: `{r.replay.desi_library}` {r.replay.desi_version}")
    add(f"- Protected-core identity: `{r.replay.core_identity}`")
    add(f"- Offline mode: `{str(r.replay.offline_mode).lower()}`")
    add("")

    add("## Main Claims")
    add("")
    mains = [c for c in r.claims if c.category in _MAIN_CATEGORIES]
    if mains:
        for c in mains:
            add(f"- **[{c.id} / {c.category}]** ({c.section}) {c.text}")
    else:
        add("_No main claims detected._")
    add("")

    add("## Overclaim Risks")
    add("")
    if r.overclaims:
        for oc in r.overclaims:
            terms = ", ".join(f"`{t}`" for t in oc.terms)
            add(f"- **[{oc.claim_id}]** ({oc.section}) terms: {terms} — {oc.reason}")
            add(f"  - {oc.text}")
    else:
        add("_No overclaim language detected._")
    add("")

    add("## Evidence Gaps")
    add("")
    if r.evidence_gaps:
        for g in r.evidence_gaps:
            add(f"- **[{g.claim_id}]** ({g.section}) {g.note}")
    else:
        add("_No evidence gaps flagged._")
    add("")

    add("## Reproducibility Risks")
    add("")
    if r.reproducibility_risks:
        for risk in r.reproducibility_risks:
            add(f"- **{risk.risk_type}**: {risk.detail}")
    else:
        add("_No reproducibility risks flagged._")
    add("")

    add("## Claim Graph Summary")
    add("")
    node_types: dict[str, int] = {}
    for n in r.graph.nodes:
        node_types[n.type] = node_types.get(n.type, 0) + 1
    type_summary = ", ".join(f"{k}={node_types[k]}" for k in sorted(node_types))
    add(f"- Nodes: {len(r.graph.nodes)} ({type_summary})")
    add(f"- Edges: {len(r.graph.edges)}")
    add("")

    add("## Reviewer Questions")
    add("")
    for i, q in enumerate(r.reviewer_questions, start=1):
        add(f"{i}. {q}")
    add("")

    add("## Replay Trace")
    add("")
    add(f"- Input hash: `{r.replay.input_hash}`")
    add(f"- Output hash: `{r.replay.output_hash}`")
    add(f"- Pipeline version: `{r.replay.pipeline_version}`")
    add(f"- Offline mode: `{str(r.replay.offline_mode).lower()}`")
    add(f"- Protected-core identity: `{r.replay.core_identity}`")
    hits = ", ".join(f"`{h}`" for h in r.replay.forbidden_term_hits) if r.replay.forbidden_term_hits else "none"
    add(f"- DESi hype/forbidden-term hits: {hits}")
    add("")

    add("## Limitations")
    add("")
    for line in _LIMITATIONS:
        add(line)
    add("")

    return "\n".join(lines)
