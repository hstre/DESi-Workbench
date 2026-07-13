from __future__ import annotations

import pytest

from app.epistemic_review.orchestrator import EpistemicReviewOrchestrator
from app.epistemic_review.schemas import STAGE_ORDER, StageSubmission, StartReviewInput
from app.epistemic_review.state import RunStore


PAPER = """# Toy paper

## Abstract
We establish that the connected group is generically U(1)^2.

## Critical point
We show that at r = 1 additional root states become massless and enhance the gauge symmetry.
"""


def _orchestrator(tmp_path):
    return EpistemicReviewOrchestrator(RunStore(tmp_path / "runs.sqlite3"))


def _theorist():
    return {
        "hypotheses": [{
            "id": "H1",
            "claim_ids": ["claim_1", "claim_2"],
            "statement": "The generic connected group description changes at the critical point.",
            "assumptions": ["Both claims refer to the same connected gauge structure."],
            "testable_consequence": "Compare root and character lattices on both sides of r=1.",
        }],
        "unresolved_terms": [],
    }


def _literature():
    return {
        "related_work": [],
        "competing_explanations": [
            "The two statements may describe different strata rather than a contradiction."
        ],
        "known_counterexamples": [],
        "datasets": [],
        "evidence": [{
            "target_hypothesis_ids": ["H1"],
            "stance": "context",
            "statement": "The manuscript itself separates a generic regime from the critical point.",
            "reference": "claim_1; claim_2",
            "source_type": "manuscript",
        }],
        "search_limitations": ["No external literature search was performed."],
    }


def _falsifier():
    return {
        "attacks": [{
            "hypothesis_id": "H1",
            "target_claim_ids": ["claim_1", "claim_2"],
            "attack_type": "boundary_change",
            "argument": "A generic abelian description need not survive gauge enhancement at r=1.",
            "fatal": False,
        }],
        "surviving_hypothesis_ids": ["H1"],
        "weakest_assumption": "The manuscript intends one group statement to cover every radius.",
    }


def _designer():
    return {
        "experiments": [{
            "id": "EX1",
            "target_hypothesis_ids": ["H1"],
            "design": "Compute root and character lattices for a generic radius and exactly at r=1.",
            "baselines": ["Generic-radius U(1)^2 lattice"],
            "metrics": ["rank", "root multiplicity", "connected group dimension"],
            "stop_criteria": "Stop when both regimes have independently reproducible lattice data.",
            "reproducibility_requirements": [
                "Publish the lattice generators and the symbolic calculation."
            ],
        }],
        "unresolved_constraints": [],
        "blocked_reason": None,
    }


def _method_review():
    return {
        "assessments": [{
            "experiment_id": "EX1",
            "verdict": "repairable",
            "concerns": ["The critical-point calculation needs an independent implementation."],
            "required_controls": ["Repeat with a second lattice construction."],
            "measurement_risks": ["Conflating Lie algebra rank with global group structure."],
        }],
        "cross_cutting_limitations": ["The exact enhanced global group remains domain-specific."],
        "blocked_reason": None,
    }


def _paper_builder():
    return {
        "publication_kind": "report",
        "title": "Generic and critical connected gauge groups",
        "markdown": (
            "# Generic and critical connected gauge groups\n\n"
            "The manuscript should state the generic and critical regimes separately. "
            "Hypothesis H1 survives the structural falsification step, while experiment EX1 "
            "requires an independent lattice construction before any stronger conclusion."
        ),
        "included_hypothesis_ids": ["H1"],
        "included_experiment_ids": ["EX1"],
        "limitations": ["No external calculation has yet been executed."],
        "open_questions": ["What is the exact global form at r=1?"],
    }


def _reviewer():
    return {
        "findings": [{
            "target": "H1",
            "verdict": "present",
            "reason": "The manuscript must distinguish the generic and critical connected groups.",
            "required_revision": "State the connected group separately at r=1.",
            "deterministic_check": "character lattice and root lattice",
        }, {
            "target": "EX1",
            "verdict": "borderline",
            "reason": "The design is relevant but needs an independent lattice implementation.",
            "required_revision": "Add a second implementation and publish generators.",
            "deterministic_check": "method review coverage",
        }, {
            "target": "publication",
            "verdict": "present",
            "reason": "The report preserves the unresolved global-group limitation explicitly.",
            "required_revision": None,
            "deterministic_check": "publication traceability",
        }],
        "overall": "revise",
        "blocking_issues": [],
        "limitations": ["The exact enhanced group still needs a domain calculation."],
    }


def _complete_run(o: EpistemicReviewOrchestrator, run_id: str) -> None:
    results = (
        _theorist(),
        _literature(),
        _falsifier(),
        _designer(),
        _method_review(),
        _paper_builder(),
        _reviewer(),
    )
    for ordinal, result in enumerate(results, start=1):
        o.next_stage(run_id)
        o.submit(
            StageSubmission(
                run_id=run_id,
                stage_id=f"S{ordinal:02d}",
                result=result,
            )
        )


def test_start_is_replay_stable_and_builds_seven_role_plan(tmp_path):
    o = _orchestrator(tmp_path)
    request = StartReviewInput(text=PAPER)
    a = o.start(request, PAPER)
    b = o.start(request, PAPER)
    assert a["run_id"] == b["run_id"]
    assert a["document_hash"] == b["document_hash"]
    assert a["protocol_version"] == "epistemic-review-v1"
    assert [stage["role"] for stage in a["stages"]] == list(STAGE_ORDER)
    assert a["blindspots"]["transition_probe"] is True
    assert "limit_case_analysis" in a["blindspots"]["selected_methods"]


def test_roles_cannot_be_skipped_and_packets_are_role_bounded(tmp_path):
    o = _orchestrator(tmp_path)
    rid = o.start(StartReviewInput(text=PAPER), PAPER)["run_id"]
    first = o.next_stage(rid)
    assert first["role"] == "theorist"
    assert first["packet"]["prior_stage_results"] == {}

    with pytest.raises(ValueError, match="in order"):
        o.submit(
            StageSubmission(
                run_id=rid,
                stage_id="S03",
                result=_falsifier(),
            )
        )

    done = o.submit(
        StageSubmission(run_id=rid, stage_id="S01", result=_theorist())
    )
    assert done["next"]["role"] == "literature_scout"
    assert set(done["next"]["packet"]["prior_stage_results"]) == {"theorist"}


def test_literature_sources_cannot_claim_verifiability_without_reference(tmp_path):
    o = _orchestrator(tmp_path)
    rid = o.start(StartReviewInput(text=PAPER), PAPER)["run_id"]
    o.next_stage(rid)
    o.submit(StageSubmission(run_id=rid, stage_id="S01", result=_theorist()))
    bad = _literature()
    bad["evidence"][0]["source_type"] = "citation"
    bad["evidence"][0]["reference"] = None
    with pytest.raises(ValueError, match="requires a reference"):
        o.submit(StageSubmission(run_id=rid, stage_id="S02", result=bad))


def test_full_seven_role_run_requires_boundary_attack_and_finalizes(tmp_path):
    o = _orchestrator(tmp_path)
    rid = o.start(StartReviewInput(text=PAPER), PAPER)["run_id"]
    _complete_run(o, rid)
    out = o.finalize(rid)
    checks = {check["check"]: check["passed"] for check in out["report"]["deterministic_checks"]}
    assert checks["claim_reference_integrity"]
    assert checks["seven_role_separation"]
    assert checks["critical_boundary_probe"]
    assert checks["experiment_traceability"]
    assert checks["method_review_coverage"]
    assert checks["publication_traceability"]
    assert checks["ecosystem_provenance"]
    assert "full seven-role Doktores protocol" in out["markdown"]
    assert out["report"]["verdict"] == "REVIEW_ASSISTANCE_ONLY"
    assert len(out["report"]["audit_chain"]) == 7
