"""C: every heuristic claim carries provenance (method) and a replay-stable
identity (content_hash). Fully offline + deterministic."""
from __future__ import annotations

from app.config import Settings
from app.desi_adapter import claim_identity
from app.review_pipeline import run_review

SAMPLE = (
    "We present the first method that solves generalization. "
    "It achieves 99% accuracy on the task."
)


def test_claims_carry_method_and_stable_identity():
    r1 = run_review("T", SAMPLE, Settings())
    assert r1.claims, "expected some heuristic claims"
    for c in r1.claims:
        assert c.method == "workbench_heuristic"
        assert len(c.content_hash) >= 16            # a real DESi replay hash
        assert c.content_hash == claim_identity(c.text)
    # deterministic: identical text -> identical per-claim identity
    r2 = run_review("T", SAMPLE, Settings())
    assert [c.content_hash for c in r1.claims] == [c.content_hash for c in r2.claims]
