"""Adapter to the REAL DESi governance library.

This is the ONLY module that imports ``desi``. It exposes the genuine
DESi public API used by the workbench. Nothing here re-implements or
mutates the DESi core:

  * desi.scientific_rendering.forbidden_hits   - hype / forbidden-term scan
  * desi.core.replay_kernel.replay_hash        - byte-stable artifact hash
  * desi.core.replay_kernel.canonical_json     - byte-stable serialization
  * desi.core.governance_core.core_identity    - protected-core identity
  * desi.reviewer.reviewer_port.AUDIT_FRAMING  - epistemic-audit framing

If the workbench ever needs a primitive the core does not provide, it is
solved locally as an adapter and recorded in docs/core_api_requests.md.
No core change is made without a separate task.
"""
from __future__ import annotations

import re
from importlib import metadata
from typing import Callable

from desi.core.governance_core import core_identity
from desi.core.replay_kernel import canonical_json, replay_hash
from desi.reviewer.reviewer_port import AUDIT_FRAMING
from desi.scientific_rendering import forbidden_hits

try:
    DESI_VERSION = metadata.version("desi-governance")
except metadata.PackageNotFoundError:  # pragma: no cover
    DESI_VERSION = "unknown"

DESI_LIBRARY = "desi-governance"


def hype_term_hits(text: str) -> list[str]:
    """Real DESi forbidden/hype-term scan over arbitrary text."""
    return list(forbidden_hits(text))


def stable_hash(obj: object) -> str:
    """Real DESi replay hash of an object (byte-stable)."""
    return replay_hash(obj)


def to_canonical_json(obj: object) -> str:
    """Real DESi canonical JSON serialization (byte-stable)."""
    return canonical_json(obj)


def identity() -> float:
    """Real DESi protected-core identity (1.0 iff the core is intact)."""
    return core_identity()


def audit_framing() -> str:
    """The DESi reviewer-port epistemic-audit framing statement."""
    return AUDIT_FRAMING


def governance_health() -> dict:
    """A small, side-effect-free health view of the DESi library."""
    return {
        "library": DESI_LIBRARY,
        "version": DESI_VERSION,
        "core_identity": identity(),
        "audit_framing": audit_framing(),
        "spl_projection_available": spl_available(),
    }


def governance_intact() -> bool:
    """True iff the protected-core identity is exactly 1.0."""
    return identity() == 1.0


# --- C: stable claim identity (offline, deterministic) ----------------------
_WS = re.compile(r"\s+")


def canonical_text(text: str) -> str:
    """Normalize a claim for stable identity: lowercase, collapse whitespace,
    strip trailing sentence punctuation. Operators/content are preserved."""
    return _WS.sub(" ", text.strip().lower()).rstrip(" ?!.")


def claim_identity(text: str) -> str:
    """Replay-stable identity for a claim's normalized text (DESi replay_hash)."""
    return replay_hash(canonical_text(text))


# --- A: real DESi SPL semantic projection (ONLINE, opt-in) ------------------
def spl_available() -> bool:
    """True iff the DESi SPL adapter is importable in this install."""
    try:
        import desi.spl_adapter  # noqa: F401
        return True
    except Exception:  # pragma: no cover
        return False


def spl_project(text: str, llm_call: Callable[[str], str]) -> list[dict]:
    """REAL DESi SPL semantic projection via the LLM backend. ONLINE / opt-in.

    ``llm_call`` is a ``(prompt: str) -> raw_text: str`` callable (injectable, so
    this is testable offline with a scripted call). Returns canonical claims as
    ``[{id, content, method}]`` with method ``llm_semantic_projection``.

    Fail-closed: any backend error yields ``[]`` so the offline review is never
    broken by a live-path failure.
    """
    try:
        from desi.spl_adapter import LLMSemanticBackend, SPLAdapter

        adapter = SPLAdapter(backend=LLMSemanticBackend(llm_call=llm_call))
        result = adapter.project_text(text)
        return [
            {
                "id": getattr(c, "claim_id", "") or "",
                "content": getattr(c, "content", ""),
                "method": getattr(c, "method", "llm_semantic_projection"),
            }
            for c in result.claims
        ]
    except Exception:  # fail-closed: never let the live path break the review
        return []


def build_llm_call(api_key: str, base_url: str, model: str) -> Callable[[str], str]:
    """Build an OpenAI-compatible chat caller (prompt -> raw text). ONLINE.

    stdlib urllib only; used solely when live calls are explicitly enabled.
    The key is passed in by the caller and never stored or logged here.
    """
    import json
    import urllib.request

    base = base_url.rstrip("/")

    def _call(prompt: str) -> str:
        body = json.dumps({
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0,
        }).encode()
        req = urllib.request.Request(
            f"{base}/chat/completions",
            data=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read())
        return data["choices"][0]["message"]["content"]

    return _call
