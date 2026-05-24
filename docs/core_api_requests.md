# Core API Requests

This file records cases where the Workbench needed a primitive that the
DESi core does not provide. The rule:

1. Solve it **locally in the Workbench** as an adapter.
2. Document it **here**.
3. Make **no core change** without a separate task.

The DESi core (replay kernel, governance core, concept gates, determinism
scanner, artifact format) is never modified by the Workbench.

## Core API consumed by the Workbench (exists today — no request needed)

All routed through `backend/app/desi_adapter.py`:

| Need | DESi public API used |
|---|---|
| Hype / forbidden-term scan | `desi.scientific_rendering.forbidden_hits` |
| Byte-stable hashing | `desi.core.replay_kernel.replay_hash` |
| Byte-stable serialization | `desi.core.replay_kernel.canonical_json` |
| Protected-core identity gate | `desi.core.governance_core.core_identity` |
| Epistemic-audit framing | `desi.reviewer.reviewer_port.AUDIT_FRAMING` |

No core gap was hit for these.

## Solved locally in the Workbench (intentionally NOT core requests)

These are product/UX concerns for the Workbench MVP, not governance
primitives. They are implemented locally and deliberately **not** proposed
as core changes:

- **Claim extraction & classification** (`review_pipeline.py`):
  transparent deterministic heuristics over sentences/sections. This is a
  reviewing heuristic, not a governance primitive; it stays in the
  Workbench.
- **Evidence-gap / overclaim-risk / reproducibility-risk detection**:
  Workbench-level heuristics, documented inline.
- **Claim graph builder** (`graph_builder.py`): a simple JSON projection
  for visualization.
- **File storage** (`storage.py`): MVP persistence under `data/reviews/`.

## Candidate requests for a FUTURE task (not implemented, not urgent)

If/when these are wanted, they would be raised as a **separate** core task
— not changed here:

1. A stable, versioned text-segmentation primitive (sentence/section
   splitting) so multiple tools share identical claim boundaries.
2. A first-class "claim" artifact type in the DESi artifact format, so
   claim graphs are replay-governed by the core rather than the Workbench.

Until such a task exists, the Workbench keeps these local and the core
remains unchanged.
