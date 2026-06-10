"""Layer 9: deterministic cross-review claim similarity (exact + lexical)."""
from __future__ import annotations

from app.claim_ledger import ClaimLedger


def _row(cid, chash, norm, text):
    return (cid, chash, norm, "Abstract", "main_claim", text)


def test_exact_and_lexical_and_self_exclusion(tmp_path):
    led = ClaimLedger(tmp_path / "l.db")
    led.record_review("R1", [
        _row("c1", "h-abc", "we propose a novel method that solves x",
             "We propose a novel method that solves X."),
        _row("c2", "h-zzz", "results show 99 percent accuracy",
             "Results show 99% accuracy."),
    ])

    # exact: same content_hash, different review
    m = led.find_matches("h-abc", "unrelated tokens entirely", exclude_review_id="R2")
    assert any(x["match_type"] == "exact" and x["prior_claim_id"] == "c1" for x in m)

    # lexical: high token overlap, different hash
    m2 = led.find_matches("h-new", "we propose a novel method that solves x",
                          exclude_review_id="R2", jaccard_threshold=0.6)
    top = m2[0]
    assert top["match_type"] in ("exact", "lexical")
    assert top["prior_claim_id"] == "c1" and top["score"] >= 0.6

    # self-exclusion: querying as R1 never matches R1's own claims
    assert led.find_matches("h-abc", "we propose a novel method that solves x",
                            exclude_review_id="R1") == []
    led.close()


def test_no_match_below_threshold(tmp_path):
    led = ClaimLedger(tmp_path / "l.db")
    led.record_review("R1", [_row("c1", "h1", "alpha beta gamma delta", "Alpha beta gamma delta.")])
    assert led.find_matches("h2", "completely unrelated words here",
                            exclude_review_id="R2", jaccard_threshold=0.6) == []
    led.close()


def test_cross_review_detected_via_api(client):
    uniq = "The frobnicator zorps the quux by 42 percent under glommas"
    r1 = client.post("/api/review",
                     json={"title": "XR1", "text": f"# XR1\n## Abstract\n{uniq}."}).json()
    r2 = client.post("/api/review",
                     json={"title": "XR2", "text": f"# XR2\n## Abstract\n{uniq}."}).json()
    # r2 should see r1's identical claim as a prior match
    priors = {m["prior_review_id"] for m in r2["cross_review"]}
    assert r1["review_id"] in priors
    assert any(m["match_type"] == "exact" for m in r2["cross_review"])
