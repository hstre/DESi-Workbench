"""Tests for the 'bring it up to date' work:

C — every heuristic claim carries provenance (`method`) and a replay-stable
    identity (`content_hash`); fully offline + deterministic.
A — an OPT-IN path that runs the REAL DESi SPL semantic projection only when
    live calls are enabled. Driven offline here via a scripted llm_call, so no
    network is touched.
"""
from __future__ import annotations

import json

from app.config import Settings
from app.review_pipeline import run_review

SAMPLE = (
    "We present the first method that solves generalization. "
    "It achieves 99% accuracy on the task."
)


# ---- C: provenance + stable identity (offline, deterministic) --------------

def test_claims_carry_method_and_stable_identity():
    r1 = run_review("T", SAMPLE, Settings())  # offline default
    assert r1.claims, "expected some heuristic claims"
    for c in r1.claims:
        assert c.method == "workbench_heuristic"
        assert len(c.content_hash) >= 16  # a real DESi replay hash
    # deterministic: identical text -> identical per-claim identity
    r2 = run_review("T", SAMPLE, Settings())
    assert [c.content_hash for c in r1.claims] == [c.content_hash for c in r2.claims]


def test_offline_has_no_spl_claims():
    r = run_review("T", SAMPLE, Settings())  # offline -> live disabled
    assert r.spl_claims == []


# ---- A: opt-in SPL projection (online path, scripted offline) --------------

def _scripted_llm(_prompt: str) -> str:
    """Stand-in for a live LLM: returns the JSON shape SPL expects. No network."""
    return json.dumps(
        {
            "units": [
                {
                    "canonical_content": "water boils at 100°C",
                    "raw_span": "water boils at 100 degrees",
                    "confidence": 0.95,
                    "ambiguous": False,
                    "proposed_relations": [],
                }
            ]
        }
    )


def test_optin_spl_projection_when_live():
    live = Settings(offline_mode=False, allow_live_llm_calls=True)
    assert live.live_calls_enabled
    r = run_review("T", "Water boils at 100 degrees.", live, spl_llm_call=_scripted_llm)
    assert r.spl_claims, "expected SPL claims in live mode"
    assert r.spl_claims[0].method == "llm_semantic_projection"
    assert r.spl_claims[0].content  # canonical content present
    # the deterministic offline core is unchanged
    assert all(c.method == "workbench_heuristic" for c in r.claims)


def test_live_without_llm_call_is_safe():
    live = Settings(offline_mode=False, allow_live_llm_calls=True)
    r = run_review("T", SAMPLE, live, spl_llm_call=None)  # nothing supplied
    assert r.spl_claims == []
