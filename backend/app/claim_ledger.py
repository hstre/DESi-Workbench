"""A small local Layer 9 for the Workbench: a shared, append-only claim ledger.

Every review's claims are appended here, so a later review can ask: *has this
claim (or one resembling it) been seen in a PRIOR review?* Determination is
deterministic and offline:

  * **exact**  — same ``content_hash`` (DESi replay-hash of normalized text);
  * **lexical** — Jaccard overlap of normalized token sets >= a threshold.

Semantic (paraphrase) similarity is deliberately NOT done here — that needs
SPL's online LLM projection and would be a separate, opt-in enrichment tier.

SQLite via the standard library only. ``busy_timeout`` is set before the WAL
switch and the switch is retried, so concurrent instances don't trip on
'database is locked'.
"""
from __future__ import annotations

import re
import sqlite3
import time
from pathlib import Path

from .config import Settings
from .desi_adapter import canonical_text

_SCHEMA = """
CREATE TABLE IF NOT EXISTS claims (
    seq             INTEGER PRIMARY KEY,
    review_id       TEXT NOT NULL,
    claim_id        TEXT NOT NULL,
    content_hash    TEXT NOT NULL,
    normalized_text TEXT NOT NULL,
    section         TEXT NOT NULL DEFAULT '',
    category        TEXT NOT NULL DEFAULT '',
    text            TEXT NOT NULL DEFAULT '',
    UNIQUE(review_id, claim_id)
);
CREATE INDEX IF NOT EXISTS idx_claims_chash ON claims(content_hash);
CREATE INDEX IF NOT EXISTS idx_claims_review ON claims(review_id);
"""

_WORD = re.compile(r"\w+")


def _tokens(normalized: str) -> frozenset[str]:
    return frozenset(_WORD.findall(normalized))


def _jaccard(a: frozenset[str], b: frozenset[str]) -> float:
    if not a or not b:
        return 0.0
    union = len(a | b)
    return len(a & b) / union if union else 0.0


def ledger_path(settings: Settings) -> Path:
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    return settings.data_dir / "_claim_ledger.db"


class ClaimLedger:
    def __init__(self, path: str | Path):
        self._con = sqlite3.connect(str(path), timeout=30.0, isolation_level=None)
        self._con.row_factory = sqlite3.Row
        self._con.execute("PRAGMA busy_timeout=30000")
        for _ in range(100):
            try:
                self._con.execute("PRAGMA journal_mode=WAL")
                break
            except sqlite3.OperationalError:
                time.sleep(0.05)
        self._con.execute("PRAGMA synchronous=NORMAL")
        self._con.executescript(_SCHEMA)

    def record_review(self, review_id: str, claims: list[tuple]) -> None:
        """Append a review's claims (idempotent per (review_id, claim_id)).

        Each tuple: (claim_id, content_hash, normalized_text, section, category, text).
        """
        self._con.executemany(
            "INSERT OR IGNORE INTO claims"
            "(review_id, claim_id, content_hash, normalized_text, section, category, text)"
            " VALUES(?,?,?,?,?,?,?)",
            [(review_id, *c) for c in claims],
        )

    def find_matches(
        self,
        content_hash: str,
        normalized_text: str,
        *,
        exclude_review_id: str,
        jaccard_threshold: float = 0.6,
        limit: int = 5,
    ) -> list[dict]:
        """Prior-review claims that match this one. Exact (content_hash) first,
        then lexical (Jaccard >= threshold); never from ``exclude_review_id``."""
        exact_ids: set[tuple[str, str]] = set()
        out: list[dict] = []

        # exact: same content_hash in other reviews
        for r in self._con.execute(
            "SELECT review_id, claim_id, text FROM claims "
            "WHERE content_hash=? AND review_id<>? ORDER BY seq",
            (content_hash, exclude_review_id),
        ):
            exact_ids.add((r["review_id"], r["claim_id"]))
            out.append({
                "match_type": "exact", "score": 1.0,
                "prior_review_id": r["review_id"], "prior_claim_id": r["claim_id"],
                "prior_text": r["text"],
            })

        # lexical: Jaccard over normalized token sets, other reviews, not already exact
        my_tokens = _tokens(normalized_text)
        if my_tokens:
            for r in self._con.execute(
                "SELECT review_id, claim_id, normalized_text, text FROM claims "
                "WHERE review_id<>? ORDER BY seq",
                (exclude_review_id,),
            ):
                key = (r["review_id"], r["claim_id"])
                if key in exact_ids:
                    continue
                score = _jaccard(my_tokens, _tokens(r["normalized_text"]))
                if score >= jaccard_threshold:
                    out.append({
                        "match_type": "lexical", "score": round(score, 4),
                        "prior_review_id": r["review_id"], "prior_claim_id": r["claim_id"],
                        "prior_text": r["text"],
                    })

        out.sort(key=lambda m: -m["score"])
        return out[:limit]

    def close(self) -> None:
        self._con.close()


def process(settings: Settings, review) -> list:
    """Annotate ``review`` against the shared ledger, then record its claims.

    Returns a list of CrossClaimMatch. Matching happens BEFORE recording, and
    a review never matches itself (``exclude_review_id``).
    """
    from .models import CrossClaimMatch

    led = ClaimLedger(ledger_path(settings))
    try:
        matches: list[CrossClaimMatch] = []
        for c in review.claims:
            for m in led.find_matches(
                c.content_hash, canonical_text(c.text), exclude_review_id=review.review_id
            ):
                matches.append(CrossClaimMatch(claim_id=c.id, **m))
        led.record_review(
            review.review_id,
            [(c.id, c.content_hash, canonical_text(c.text), c.section, c.category, c.text)
             for c in review.claims],
        )
        return matches
    finally:
        led.close()
