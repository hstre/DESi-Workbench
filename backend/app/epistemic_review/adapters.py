"""Adapters around DESi, Kevin and Doktores.

The host model supplies language. These adapters supply deterministic structure and
explicit provenance. Optional ecosystem packages may be installed, but absence never
silently changes a verdict: the selected engine is returned in every artifact.
"""
from __future__ import annotations

import importlib
import importlib.metadata
import re
from typing import Any

from .. import review_pipeline


AXES: dict[str, tuple[str, ...]] = {
    "mechanism": ("mechanism", "process", "cause", "derive", "follows"),
    "constraint": ("constraint", "assume", "requires", "only if", "condition"),
    "boundary": ("limit", "critical", "self-dual", "extreme", "r=1", "r = 1", "generic"),
    "actor": ("observer", "source", "author", "agent"),
    "level": ("local", "global", "asymptotic", "component", "effective"),
    "synthesis": ("combine", "together", "simultaneously", "full group", "completion"),
    "temporal": ("time", "evolution", "late", "early", "decay"),
    "information": ("evidence", "citation", "known", "unknown", "data"),
    "material": ("field", "brane", "defect", "lattice", "geometry"),
    "inversion": ("opposite", "fails", "cannot", "no-go", "absence"),
}

METHOD_BY_AXIS = {
    "mechanism": "first_principles_reduction",
    "constraint": "constraint_relaxation",
    "boundary": "limit_case_analysis",
    "actor": "source_by_interest",
    "level": "abstraction_ladder",
    "synthesis": "dimensional_consistency",
    "temporal": "premortem",
    "information": "claim_splitting",
    "material": "conservation_tracking",
    "inversion": "invert_then_flip",
}


def _package_version(name: str) -> str | None:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None


def desi_audit(title: str, text: str) -> dict[str, Any]:
    analysis = review_pipeline.analyze(title, text)
    return {
        "title": analysis.title,
        "claims": [c.model_dump(mode="json") for c in analysis.claims],
        "unsupported_claim_ids": [c.id for c in analysis.unsupported],
        "overclaims": [o.model_dump(mode="json") for o in analysis.overclaims],
        "evidence_gaps": [g.model_dump(mode="json") for g in analysis.evidence_gaps],
        "reviewer_questions": list(analysis.reviewer_questions),
        "forbidden_term_hits": list(analysis.forbidden_term_hits),
    }


def _builtin_blindspots(claims: list[dict[str, Any]]) -> dict[str, Any]:
    blob = " ".join(c["text"] for c in claims).lower()
    covered = []
    for axis, signals in AXES.items():
        if any(signal in blob for signal in signals):
            covered.append(axis)
    blind = [axis for axis in AXES if axis not in covered]
    transition = bool(re.search(r"\bgeneric", blob)) and bool(
        re.search(r"self[- ]dual|critical|r\s*=\s*1|enhanc", blob)
    )
    if transition and "boundary" not in blind:
        blind.insert(0, "boundary")
    methods = []
    for axis in blind[:6]:
        method = METHOD_BY_AXIS[axis]
        if method not in methods:
            methods.append(method)
    return {
        "engine": "workbench-domain-neutral-fallback",
        "covered_axes": covered,
        "blindspot_axes": blind,
        "selected_methods": methods,
        "transition_probe": transition,
    }


def kevin_blindspots(title: str, claims: list[dict[str, Any]]) -> dict[str, Any]:
    """Use Kevin when importable; otherwise expose the deterministic fallback."""
    modules = (
        ("kevin", "kevin.space_predictor"),
        ("doktores.kevin", "doktores.kevin.space_predictor"),
    )
    for base_name, predictor_name in modules:
        try:
            base = importlib.import_module(base_name)
            predictor_mod = importlib.import_module(predictor_name)
            problem = base.Problem(
                statement=f"what important structural question does '{title}' leave unanswered?",
                domain="domain-neutral manuscript review",
                known_approaches=tuple(c["text"] for c in claims),
            )
            prediction = predictor_mod.SpacePredictor().predict(problem)
            blind = list(prediction.blindspots)
            methods = [METHOD_BY_AXIS[a] for a in blind if a in METHOD_BY_AXIS][:6]
            return {
                "engine": predictor_name,
                "covered_axes": list(prediction.covered),
                "blindspot_axes": blind,
                "selected_methods": list(dict.fromkeys(methods)),
                "transition_probe": "boundary" in blind,
            }
        except (ImportError, AttributeError, TypeError):
            continue
    return _builtin_blindspots(claims)


def engine_manifest() -> dict[str, Any]:
    return {
        "desi": {
            "adapter": "app.review_pipeline",
            "package_version": _package_version("desi-governance"),
        },
        "kevin": {
            "package_version": _package_version("kevin"),
            "fallback": "workbench-domain-neutral-fallback",
        },
        "doktores": {
            "package_version": _package_version("doktores"),
            "protocol": "theorist -> falsifier -> adversarial_reviewer",
            "language_layer": "MCP host model",
        },
    }
