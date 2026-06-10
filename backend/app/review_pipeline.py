"""Deterministic, offline review pipeline.

For the MVP this is a transparent heuristic - no LLM is required. Every
rule below is documented; the guiding principle is "transparently simple
rather than magically wrong". The pipeline uses the real DESi governance
library (via desi_adapter) for the hype-term scan, the protected-core
identity gate, and byte-stable hashing - it never re-implements them.

Heuristics
----------
Claim categories (first matching signal wins, in this order):
  novelty_claim         : "novel", "first", "unprecedented", "for the first time"
  generalization_claim  : "generalize(s)", "any task/domain", "universal", "in general"
  limitation_claim      : "limitation", "however", "cannot", "fails", "future work"
  method_claim          : "we propose/introduce/present/design", "our method/approach"
  result_claim          : "results", "we achieve", "outperform(s)", "accuracy", "N%"
  evidence_claim        : "we show/demonstrate/prove/observe", "results show", "experiments"
  main_claim            : "prove(s)", "solve(s)", "establish", "significant", "robust"

Overclaim terms        : first, novel, significant, robust, generalizes, solves,
                         proves, state of the art
Overclaim risk reasons :
  - "state of the art" / "state-of-the-art"          -> claims SOTA, verify comparison
  - "significant" with no inline statistical support -> stat-free significance claim
  - "novel"/"first" with no inline comparison        -> novelty without comparison
  - otherwise                                        -> strong language, verify support

Evidence gap           : a strong claim (main/result/novelty/generalization, or any
                         overclaim) with no inline support (number, %, citation,
                         table/figure reference).
Reproducibility risks  : missing_code, missing_data, missing_baselines,
                         missing_parameters, unclear_dataset, unsupported_metrics.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from . import PIPELINE_VERSION, VERDICT
from .config import Settings
from . import desi_adapter
from . import graph_builder
from .models import (
    Claim,
    EvidenceGap,
    Overclaim,
    Replay,
    ReproRisk,
    ReviewResponse,
    SplClaim,
)

# Type alias for the injectable, online SPL llm_call (opt-in, live mode only).
from typing import Callable, Optional  # noqa: E402

SplLlmCall = Optional[Callable[[str], str]]

# --- section parsing --------------------------------------------------
_HEADER_RE = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")
_KNOWN_SECTIONS = {
    "abstract", "introduction", "background", "related work", "method",
    "methods", "methodology", "approach", "experimental setup",
    "experiments", "evaluation", "results", "analysis", "discussion",
    "conclusion", "conclusions", "limitations", "future work",
    "references",
}
_ASSERTIVE_SECTIONS = ("abstract", "introduction", "conclusion")

# --- classification ---------------------------------------------------
STRONG_CATEGORIES = {"main_claim", "result_claim", "novelty_claim", "generalization_claim"}

_CATEGORY_SIGNALS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("novelty_claim", (r"\bnovel(?:ty)?\b", r"\bfirst\b", r"\bunprecedented\b",
                       r"\bfor the first time\b")),
    ("generalization_claim", (r"\bgeneraliz", r"\buniversal", r"\bin general\b",
                              r"\bany (?:task|domain|input)\b",
                              r"\bacross (?:all )?(?:tasks|domains)\b")),
    ("limitation_claim", (r"\blimitation", r"\bhowever\b", r"\bcaveat",
                          r"\bdoes not\b", r"\bcannot\b", r"\bfails?\b",
                          r"\bfuture work\b")),
    ("method_claim", (r"\bwe propose\b", r"\bwe introduce\b", r"\bwe present\b",
                      r"\bwe design\b", r"\bour (?:method|approach|model|algorithm)\b",
                      r"\balgorithm\b", r"\bmethod(?:ology)?\b")),
    ("result_claim", (r"\bresults?\b", r"\bwe achieve\b", r"\boutperform",
                      r"\baccuracy\b", r"\bperformance\b", r"\bimprov",
                      r"\d+(?:\.\d+)?\s*%")),
    ("evidence_claim", (r"\bwe show\b", r"\bwe demonstrate\b", r"\bwe prove\b",
                        r"\bwe observe\b", r"\bresults show\b", r"\bexperiments?\b",
                        r"\bevidence\b", r"\bevaluat")),
    ("main_claim", (r"\bprov(?:e|es|ed|ing|en)\b", r"\bsolv(?:e|es|ed|ing)\b",
                    r"\bestablish", r"\bsignificant", r"\brobust\b")),
)
_COMPILED_SIGNALS = tuple(
    (cat, tuple(re.compile(p, re.IGNORECASE) for p in pats))
    for cat, pats in _CATEGORY_SIGNALS
)

OVERCLAIM_TERMS = (
    "first", "novel", "significant", "robust",
    "generalizes", "solves", "proves", "state of the art",
)
_OVERCLAIM_PATTERNS = {
    "first": r"\bfirst\b",
    "novel": r"\bnovel(?:ty)?\b",
    "significant": r"\bsignificant(?:ly)?\b",
    "robust": r"\brobust(?:ness|ly)?\b",
    "generalizes": r"\bgeneraliz(?:e|es|ed|ing|ation|able)\b",
    "solves": r"\bsolv(?:e|es|ed|ing)\b",
    "proves": r"\bprov(?:e|es|ed|ing|en)\b",
    "state of the art": r"state[\s-]of[\s-]the[\s-]art",
}
_OVERCLAIM_RES = {t: re.compile(p, re.IGNORECASE) for t, p in _OVERCLAIM_PATTERNS.items()}

_SUPPORT_RE = re.compile(
    r"\d|\btable\b|\bfigure\b|\bfig\.\b|\[\d+\]|\bp\s*[<=]|"
    r"\bconfidence interval\b|\bappendix\b",
    re.IGNORECASE,
)
_NUMBER_RE = re.compile(r"\d")
_STATS_RE = re.compile(
    r"\bp\s*[<=]|\bp-value\b|\bconfidence interval\b|\bstandard deviation\b|"
    r"\bsignificance test\b|\bstd\b|±",
    re.IGNORECASE,
)
_COMPARISON_RE = re.compile(
    r"\bcompared\b|\bcomparison\b|\bbaseline|\bversus\b|\bvs\.?\b|"
    r"\bthan\b|\brelative to\b|\bprior work\b|\bagainst\b",
    re.IGNORECASE,
)
_MIN_SENTENCE_LEN = 12


@dataclass(frozen=True)
class Section:
    title: str
    text: str


@dataclass
class Analysis:
    title: str
    sections: list[Section]
    claims: list[Claim] = field(default_factory=list)
    overclaims: list[Overclaim] = field(default_factory=list)
    evidence_gaps: list[EvidenceGap] = field(default_factory=list)
    unsupported: list[Claim] = field(default_factory=list)
    reproducibility_risks: list[ReproRisk] = field(default_factory=list)
    reviewer_questions: list[str] = field(default_factory=list)
    forbidden_term_hits: list[str] = field(default_factory=list)


def _split_sections(text: str, fallback_title: str) -> tuple[str, list[Section]]:
    norm = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = norm.split("\n")
    title = fallback_title
    for ln in lines:
        m = _HEADER_RE.match(ln)
        if m and len(m.group(1)) == 1:
            title = m.group(2).strip()
            break
    else:
        for ln in lines:
            if ln.strip():
                title = ln.strip().lstrip("#").strip()
                break

    sections: list[Section] = []
    cur_title: str | None = None
    body: list[str] = []

    def flush() -> None:
        joined = "\n".join(body).strip()
        if cur_title is not None:
            sections.append(Section(cur_title, joined))
        elif joined:
            sections.append(Section("Body", joined))

    for ln in lines:
        m = _HEADER_RE.match(ln)
        heading = None
        if m:
            heading = m.group(2).strip()
        else:
            s = ln.strip().rstrip(":").strip()
            if s and len(s) <= 60 and s.lower() in _KNOWN_SECTIONS:
                heading = s
        if heading is not None:
            flush()
            cur_title = heading
            body = []
        else:
            body.append(ln)
    flush()
    return title, sections


def _split_sentences(text: str) -> list[str]:
    collapsed = re.sub(r"\s+", " ", text).strip()
    if not collapsed:
        return []
    parts = re.split(r"(?<=[.!?])\s+", collapsed)
    return [p.strip() for p in parts if p.strip()]


def _classify(sentence: str) -> str | None:
    for category, patterns in _COMPILED_SIGNALS:
        for pat in patterns:
            if pat.search(sentence):
                return category
    return None


def _overclaim_terms_in(text: str) -> list[str]:
    return [t for t in OVERCLAIM_TERMS if _OVERCLAIM_RES[t].search(text)]


def _overclaim_reason(text: str, terms: list[str]) -> str:
    if "state of the art" in terms:
        return "Claims state-of-the-art; verify against an explicit comparison."
    if "significant" in terms and not _STATS_RE.search(text):
        return "Uses 'significant' without inline statistical support (p-value, CI, etc.)."
    if ("novel" in terms or "first" in terms) and not _COMPARISON_RE.search(text):
        return "Claims novelty/priority without an explicit comparison."
    return "Strong language; verify the wording is supported by the evidence."


def analyze(title: str, text: str) -> Analysis:
    detected_title, sections = _split_sections(text, "Untitled")
    # An explicit title from the request takes precedence over the H1.
    resolved_title = title.strip() if title and title.strip() else detected_title
    an = Analysis(title=resolved_title, sections=sections)

    counter = 0
    oc_counter = 0
    gap_counter = 0
    for sec in sections:
        assertive = any(k in sec.title.lower() for k in _ASSERTIVE_SECTIONS)
        for sentence in _split_sentences(sec.text):
            if len(sentence) < _MIN_SENTENCE_LEN:
                continue
            category = _classify(sentence)
            if category is None:
                if not assertive:
                    continue
                category = "main_claim"
            counter += 1
            claim_id = f"claim_{counter}"
            terms = _overclaim_terms_in(sentence)
            has_numbers = bool(_NUMBER_RE.search(sentence))
            supported = _SUPPORT_RE.search(sentence) is not None
            claim = Claim(
                id=claim_id,
                category=category,
                section=sec.title,
                text=sentence,
                has_numbers=has_numbers,
                overclaim_terms=terms,
                supported=supported,
                method="workbench_heuristic",
                content_hash=desi_adapter.claim_identity(sentence),
            )
            an.claims.append(claim)

            if terms:
                oc_counter += 1
                an.overclaims.append(
                    Overclaim(
                        id=f"overclaim_{oc_counter}",
                        claim_id=claim_id,
                        section=sec.title,
                        text=sentence,
                        terms=terms,
                        reason=_overclaim_reason(sentence, terms),
                    )
                )

            strong = category in STRONG_CATEGORIES or bool(terms)
            if strong and not supported:
                gap_counter += 1
                an.unsupported.append(claim)
                an.evidence_gaps.append(
                    EvidenceGap(
                        id=f"gap_{gap_counter}",
                        claim_id=claim_id,
                        section=sec.title,
                        note="Strong claim with no inline data, citation, or table/figure reference.",
                    )
                )

    an.reproducibility_risks = _detect_reproducibility_risks(text)
    an.forbidden_term_hits = desi_adapter.hype_term_hits(text)
    an.reviewer_questions = _build_reviewer_questions(an)
    return an


def _has_any(low: str, *subs: str) -> bool:
    return any(s in low for s in subs)


def _detect_reproducibility_risks(text: str) -> list[ReproRisk]:
    low = text.lower()
    risks: list[ReproRisk] = []
    n = 0

    def add(risk_type: str, detail: str) -> None:
        nonlocal n
        n += 1
        risks.append(ReproRisk(id=f"repro_{n}", risk_type=risk_type, detail=detail))

    if not _has_any(low, "github", "gitlab", "code is available", "code available",
                    "source code", "open-source", "open source", "code repository",
                    "implementation is available", "zenodo"):
        add("missing_code", "No link or statement that the source code is available.")
    if not _has_any(low, "data is available", "data are available", "data available",
                    "dataset is available", "dataset available", "publicly available",
                    "supplementary data", "data repository", "zenodo"):
        add("missing_data", "No statement that the underlying data are available.")
    if not _has_any(low, "baseline", "compared to", "compared with", "comparison",
                    "state-of-the-art", "state of the art", "prior work", "we compare"):
        add("missing_baselines", "No baseline or comparison against prior work is described.")
    if not _has_any(low, "hyperparameter", "learning rate", "epochs", "batch size",
                    "random seed", "parameter settings", "training details",
                    "we set", "configuration"):
        add("missing_parameters", "No hyperparameters, seeds, or training details reported.")

    mentions_dataset = _has_any(low, "dataset", "data set", "corpus")
    named = _has_any(low, "imagenet", "cifar", "mnist", "glue", "squad", "wikitext",
                     "coco", "penn treebank", "wmt")
    sized = bool(re.search(
        r"\b\d[\d,\.]*\s*(?:samples|examples|images|documents|sentences|instances|rows|records)\b",
        low,
    ))
    if mentions_dataset and not (named or sized):
        add("unclear_dataset", "A dataset is mentioned but not identified by name, size, or construction.")
    elif not mentions_dataset:
        add("unclear_dataset", "No dataset is identified anywhere in the text.")

    has_metric_words = _has_any(low, "accuracy", "f1", "precision", "recall", "auc",
                                "score", "performance", "%", "error rate")
    has_metric_method = _has_any(low, "evaluation protocol", "we measure", "computed as",
                                 "cross-validation", "cross validation", "test set",
                                 "held-out", "held out", "confidence interval",
                                 "standard deviation", "p-value", "p <", "significance test")
    if has_metric_words and not has_metric_method:
        add("unsupported_metrics", "Metrics reported without a measurement protocol or variance/significance.")

    return risks


_RISK_QUESTION = {
    "missing_code": "Can the authors provide a link to the source code to reproduce the results?",
    "missing_data": "Are the underlying data available for independent inspection?",
    "missing_baselines": "Which baselines were used, and how does the method compare to prior work?",
    "missing_parameters": "What exact hyperparameters, seeds, and training settings were used?",
    "unclear_dataset": "Which dataset (name, size, splits) was used, and how was it constructed?",
    "unsupported_metrics": "How were the metrics computed (protocol, test set, variance/significance)?",
}


def _build_reviewer_questions(an: Analysis) -> list[str]:
    questions: list[str] = []
    for oc in an.overclaims:
        questions.append(
            f"Claim {oc.claim_id} ({', '.join(oc.terms)}): {oc.reason} Is the wording justified?"
        )
    for gap in an.evidence_gaps:
        questions.append(
            f"What evidence supports claim {gap.claim_id}? It lacks inline data, a citation, or a table/figure."
        )
    seen: set[str] = set()
    for risk in an.reproducibility_risks:
        if risk.risk_type not in seen:
            questions.append(_RISK_QUESTION[risk.risk_type])
            seen.add(risk.risk_type)
    if not questions:
        questions.append("No automated concerns were flagged; assess the text on its merits.")
    return questions


def run_review(
    title: str | None,
    text: str,
    settings: Settings,
    *,
    spl_llm_call: SplLlmCall = None,
) -> ReviewResponse:
    """Run the full deterministic review and assemble a replay-stable response.

    The deterministic core (claims, gaps, graph, hashes) is always offline.
    If live calls are enabled AND an ``spl_llm_call`` is supplied, the REAL
    DESi SPL semantic projection runs in addition and its canonical claims are
    attached as ``spl_claims`` — deliberately OUTSIDE the replay hash, because
    that path is online and non-deterministic.
    """
    an = analyze(title or "", text)
    graph = graph_builder.build_graph(an)

    input_hash = desi_adapter.stable_hash({"title": title or "", "text": text})

    content = {
        "title": an.title,
        "claims": [c.model_dump() for c in an.claims],
        "unsupported_claims": [c.model_dump() for c in an.unsupported],
        "overclaims": [o.model_dump() for o in an.overclaims],
        "evidence_gaps": [g.model_dump() for g in an.evidence_gaps],
        "reproducibility_risks": [r.model_dump() for r in an.reproducibility_risks],
        "reviewer_questions": an.reviewer_questions,
        "graph": graph.model_dump(),
        "verdict": VERDICT,
    }
    output_hash = desi_adapter.stable_hash(content)

    replay = Replay(
        input_hash=input_hash,
        output_hash=output_hash,
        pipeline_version=PIPELINE_VERSION,
        offline_mode=settings.offline_mode,
        core_identity=desi_adapter.identity(),
        audit_framing=desi_adapter.audit_framing(),
        desi_library=desi_adapter.DESI_LIBRARY,
        desi_version=desi_adapter.DESI_VERSION,
        forbidden_term_hits=an.forbidden_term_hits,
    )

    # Opt-in, online: REAL DESi SPL projection — only when live calls are
    # enabled and a caller-supplied llm_call is present. Outside the hash above.
    spl_claims: list[SplClaim] = []
    if settings.live_calls_enabled and spl_llm_call is not None:
        spl_claims = [SplClaim(**c) for c in desi_adapter.spl_project(text, spl_llm_call)]

    return ReviewResponse(
        review_id=input_hash,
        title=an.title,
        claims=an.claims,
        unsupported_claims=an.unsupported,
        overclaims=an.overclaims,
        evidence_gaps=an.evidence_gaps,
        reproducibility_risks=an.reproducibility_risks,
        reviewer_questions=an.reviewer_questions,
        graph=graph,
        replay=replay,
        verdict=VERDICT,
        spl_claims=spl_claims,
    )
