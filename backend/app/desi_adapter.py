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

from importlib import metadata

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
    }


def governance_intact() -> bool:
    """True iff the protected-core identity is exactly 1.0."""
    return identity() == 1.0
