from __future__ import annotations

from app.epistemic_review.orchestrator import EpistemicReviewOrchestrator
from app.epistemic_review.schemas import StageSubmission, StartReviewInput
from app.epistemic_review.state import RunStore


PAPER = """# Toy paper

## Abstract
We establish that the connected group is generically U(1)^2.

## Critical point
We show that at r = 1 additional root states become massless and enhance the gauge symmetry.
"""


def _orchestrator(tmp_path):
    return EpistemicReviewOrchestrator(RunStore(tmp_path / "runs.sqlite3"))


def test_start_is_replay_stable_and_detects_boundary_probe(tmp_path):
    o = _orchestrator(tmp_path)
    request = StartReviewInput(text=PAPER)
    a = o.start(request, PAPER)
    b = o.start(request, PAPER)
    assert a["run_id"] == b["run_id"]
    assert a["document_hash"] == b["document_hash"]
    assert a["blindspots"]["transition_probe"] is True
    assert "limit_case_analysis" in a["blindspots"]["selected_methods"]


def test_roles_cannot_be_skipped_and_chain_advances(tmp_path):
    o = _orchestrator(tmp_path)
    run = o.start(StartReviewInput(text=PAPER), PAPER)
    rid = run["run_id"]
    first = o.next_stage(rid)
    assert first["role"] == "theorist"

    try:
        o.submit(
            StageSubmission(
                run_id=rid,
                stage_id="S02",
                result={
                    "attacks": [{
                        "hypothesis_id": "H1",
                        "target_claim_ids": ["claim_1"],
                        "attack_type": "boundary_change",
                        "argument": "x" * 25,
                        "fatal": False,
                    }],
                    "surviving_hypothesis_ids": ["H1"],
                    "weakest_assumption": "x" * 12,
                },
            )
        )
    except ValueError as exc:
        assert "in order" in str(exc)
    else:
        raise AssertionError("stage skipping should fail")

    done = o.submit(
        StageSubmission(
            run_id=rid,
            stage_id="S01",
            result={
                "hypotheses": [{
                    "id": "H1",
                    "claim_ids": ["claim_1", "claim_2"],
                    "statement": "The global group changes at the critical point.",
                    "assumptions": ["Both claims refer to the same connected group."],
                    "testable_consequence": "Compute the root and character lattices at r=1.",
                }],
                "unresolved_terms": [],
            },
        )
    )
    assert done["next"]["role"] == "falsifier"
    assert done["entry_hash"] != run["head_hash"]


def test_full_run_requires_boundary_attack_and_finalizes(tmp_path):
    o = _orchestrator(tmp_path)
    rid = o.start(StartReviewInput(text=PAPER), PAPER)["run_id"]
    o.next_stage(rid)
    o.submit(StageSubmission(run_id=rid, stage_id="S01", result={
        "hypotheses": [{
            "id": "H1",
            "claim_ids": ["claim_1", "claim_2"],
            "statement": "The generic group statement may fail at r=1.",
            "assumptions": [],
            "testable_consequence": "Compare the lattices on both sides of r=1.",
        }],
        "unresolved_terms": [],
    }))
    o.submit(StageSubmission(run_id=rid, stage_id="S02", result={
        "attacks": [{
            "hypothesis_id": "H1",
            "target_claim_ids": ["claim_1", "claim_2"],
            "attack_type": "boundary_change",
            "argument": "A generic abelian description need not survive gauge enhancement.",
            "fatal": False,
        }],
        "surviving_hypothesis_ids": ["H1"],
        "weakest_assumption": "The same global group is intended at every radius.",
    }))
    o.submit(StageSubmission(run_id=rid, stage_id="S03", result={
        "findings": [{
            "target": "H1",
            "verdict": "present",
            "reason": "The manuscript must distinguish the generic and critical groups.",
            "required_revision": "State the connected group separately at r=1.",
            "deterministic_check": "character lattice and root lattice",
        }],
        "overall": "revise",
        "blocking_issues": [],
        "limitations": ["The exact enhanced group still needs a domain calculation."],
    }))
    out = o.finalize(rid)
    checks = {c["check"]: c["passed"] for c in out["report"]["deterministic_checks"]}
    assert checks["claim_reference_integrity"]
    assert checks["role_separation"]
    assert checks["critical_boundary_probe"]
    assert "DESi for claim structure" in out["markdown"]
    assert out["report"]["verdict"] == "REVIEW_ASSISTANCE_ONLY"
