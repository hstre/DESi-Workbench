"""Domain-neutral epistemic review orchestration for the DESi Workbench.

The package keeps the roles separate:

* DESi extracts and identities claims.
* Kevin maps structural blind spots and selects content-free methods.
* Doktores supplies the role protocol; the host model performs the language work.
* The Workbench stores every stage in an append-only, hash-chained run log.

No component may declare a paper true. The only terminal recommendation is
``REVIEW_ASSISTANCE_ONLY``.
"""

from .orchestrator import EpistemicReviewOrchestrator

__all__ = ["EpistemicReviewOrchestrator"]
