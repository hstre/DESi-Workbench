"""Adapters around DESi, Kevin and Doktores.

The host model supplies language. These adapters supply deterministic structure and
explicit provenance. Optional ecosystem packages may be installed, but absence never
silently changes a run: every artifact records whether the native package or the
bounded fallback was used.
"""
from __future__ import annotations

import importlib
import importlib.metadata
import os
import re
from typing import Any

from .. import review_pipeline
from .schemas import STAGE_ORDER


AXES: dict[str, tuple[str, ...]] = {
    "mechanism": ("mechanism", "process", "cause", "derive", "follows"),
    "constraint": ("constraint", "assume", "requires", "only if", "condition"),
    "boundary": ("limit", "critical", "self-dual", "extreme", "r=1", "r = 1", "generic"),
    "actor": ("observer", "source", "author", "agent"),
    "analogy": ("analogy", "similar", "isomorphic", "corresponds"),
    "level": ("local", "global", "asymptotic", "component", "effective"),
    "synthesis": ("combine", "together", "simultaneously", "full group", "completion"),
    "temporal": ("time", "evolution", "late", "early", "decay"),
    "incentive": ("incentive", "reward", "penalty", "motivation"),
    "information": ("evidence", "citation", "known", "unknown", "data"),
    "material": ("field", "brane", "defect", "lattice", "geometry"),
    "inversion": ("opposite", "fails", "cannot", "no-go", "absence"),
}

METHOD_BY_AXIS = {
    "mechanism": "first_principles_reduction",
    "constraint": "constraint_relaxation",
    "boundary": "limit_case_analysis",
    "actor": "source_by_interest",
    "analogy": "distant_analogy_transfer",
    "level": "abstraction_ladder",
    "synthesis": "dimensional_consistency",
    "temporal": "premortem",
    "incentive": "incentive_mapping",
    "information": "claim_splitting",
    "material": "conservation_tracking",
    "inversion": "invert_then_flip",
}


def _package_version(name: str) -> str | None:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None


def _required_ecosystem() -> bool:
    return os.getenv("DESI_REQUIRE_ECOSYSTEM", "0").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _capability(
    *, distribution: str, module_name: str, required_attributes: tuple[str, ...]
) -> dict[str, Any]:
    version = _package_version(distribution)
    try:
        module = importlib.import_module(module_name)
    except ImportError as exc:
        return {
            "available": False,
            "package_version": version,
            "module": module_name,
            "status": "not_installed",
            "detail": f"{type(exc).__name__}: {exc}",
        }
    missing = [name for name in required_attributes if not hasattr(module, name)]
    return {
        "available": not missing,
        "package_version": version,
        "module": module_name,
        "status": "ready" if not missing else "incompatible_api",
        "missing_attributes": missing,
    }


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


def _builtin_blindspots(
    claims: list[dict[str, Any]], *, reason: str | None = None
) -> dict[str, Any]:
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
        "status": "fallback",
        "fallback_reason": reason,
        "coverage_engine": "workbench-token-coverage",
        "covered_axes": covered,
        "blindspot_axes": blind,
        "selected_methods": methods,
        "transition_probe": transition,
        "universe_size": len(AXES),
        "new_region_fraction": round(len(blind) / len(AXES), 6),
        "redundancy": 0.0,
    }


def kevin_blindspots(title: str, claims: list[dict[str, Any]]) -> dict[str, Any]:
    """Use Kevin's real SpacePredictor when importable; otherwise expose the fallback."""
    try:
        base = importlib.import_module("kevin")
        predictor_mod = importlib.import_module("kevin.space_predictor")
        problem = base.Problem(
            statement=f"what important structural question does '{title}' leave unanswered?",
            domain="domain-neutral manuscript review",
            known_approaches=tuple(c["text"] for c in claims),
        )
        prediction = predictor_mod.SpacePredictor().predict(problem)
        blind = list(prediction.blindspots)
        methods = [METHOD_BY_AXIS[a] for a in blind if a in METHOD_BY_AXIS][:6]
        blob = " ".join(c["text"] for c in claims).lower()
        transition = bool(re.search(r"\bgeneric", blob)) and bool(
            re.search(r"self[- ]dual|critical|r\s*=\s*1|enhanc", blob)
        )
        return {
            "engine": "kevin.space_predictor",
            "status": "native",
            "fallback_reason": None,
            "coverage_engine": prediction.engine,
            "covered_axes": list(prediction.covered),
            "blindspot_axes": blind,
            "selected_methods": list(dict.fromkeys(methods)),
            "transition_probe": transition,
            "universe_size": prediction.universe_size,
            "new_region_fraction": prediction.new_region_fraction,
            "redundancy": prediction.redundancy,
        }
    except (ImportError, AttributeError, TypeError, ValueError) as exc:
        if _required_ecosystem():
            raise RuntimeError(
                "Kevin is required but its SpacePredictor integration failed"
            ) from exc
        return _builtin_blindspots(
            claims, reason=f"{type(exc).__name__}: {exc}"
        )


def engine_manifest() -> dict[str, Any]:
    kevin = _capability(
        distribution="kevin",
        module_name="kevin",
        required_attributes=("Kevin", "Problem"),
    )
    doktores = _capability(
        distribution="doktores",
        module_name="doktores",
        required_attributes=("Doktores", "ResearchTask"),
    )
    if _required_ecosystem():
        unavailable = [
            name
            for name, capability in (("kevin", kevin), ("doktores", doktores))
            if not capability["available"]
        ]
        if unavailable:
            raise RuntimeError(
                "Required ecosystem packages unavailable: " + ", ".join(unavailable)
            )
    return {
        "desi": {
            "available": True,
            "adapter": "app.review_pipeline",
            "package_version": _package_version("desi-governance"),
            "execution": "native-claim-audit",
        },
        "kevin": {
            **kevin,
            "adapter": "kevin.space_predictor.SpacePredictor",
            "fallback": "workbench-domain-neutral-fallback",
            "execution": "native-when-available",
        },
        "doktores": {
            **doktores,
            "protocol_roles": list(STAGE_ORDER),
            "execution": "host-mediated-seven-role-protocol",
            "native_run_invoked": False,
            "language_layer": "MCP host model",
            "governance_boundary": "advises-never-decides",
        },
    }
