# DESi Workbench - Architecture

## Overview

```
 Browser (Next.js / React / TS)
        │  HTTP (JSON)
        ▼
 FastAPI backend  ──uses──▶  desi-governance (the REAL DESi library)
        │
        ▼
 data/reviews/{id}/  (input.txt, review.json, report.md)
```

The Workbench is a thin, visible surface over DESi. It does not modify or
re-implement the DESi core.

## Backend (`backend/app/`)

| Module | Responsibility |
|---|---|
| `main.py` | FastAPI app + endpoints, CORS, offline/governance gates |
| `config.py` | offline-by-default settings; secret-free `public_dict()` |
| `desi_adapter.py` | the ONLY module importing `desi`; wraps the real public API |
| `models.py` | Pydantic request/response models |
| `review_pipeline.py` | deterministic heuristic pipeline (documented rules) |
| `graph_builder.py` | simple claim graph (JSON) |
| `claim_ledger.py` | shared, append-only claim ledger (local Layer 9): cross-review similarity |
| `report_renderer.py` | Markdown report |
| `storage.py` | file storage under `data/reviews/{id}/` |

### Use of the real DESi public API (never faked)

- `desi.scientific_rendering.forbidden_hits` — hype/forbidden-term scan
- `desi.core.replay_kernel.replay_hash` — byte-stable input/output hashes
- `desi.core.replay_kernel.canonical_json` — byte-stable serialization
- `desi.core.governance_core.core_identity` — protected-core gate; the
  backend refuses to emit a review if `core_identity() != 1.0`
- `desi.reviewer.reviewer_port.AUDIT_FRAMING` — epistemic-audit framing

All of these are reached through `desi_adapter.py`. No other module
imports `desi`.

## Determinism & replay

- `review_id == replay.input_hash == replay_hash({title, text})`, so the
  same input always maps to the same review.
- `replay.output_hash == replay_hash(content)` where `content` is the
  full artifact minus the `replay` block.
- No timestamps, randomness, or PRNG anywhere in the pipeline.
- `review.json` is stored as DESi `canonical_json` (byte-stable).
- `cross_review` (below) is **history-dependent** and is deliberately kept
  OUTSIDE the replay hash.

## Claim provenance & cross-review similarity (local Layer 9)

- **Provenance + identity.** Every claim carries `method` (`workbench_heuristic`)
  and a replay-stable `content_hash` = `replay_hash(canonical_text(claim))` —
  SPL's content/method discipline, applied at the claim level.
- **Shared claim ledger** (`claim_ledger.py`): an append-only SQLite store
  (under `data/`) of every review's claims. On each review the backend reports
  which claims were already seen in **prior** reviews — `exact` (same
  `content_hash`) or `lexical` (Jaccard token overlap ≥ threshold), never
  self-matching — as `ReviewResponse.cross_review`. Deterministic and offline.
- **Honest boundary.** Semantic/paraphrase similarity is NOT done here; that
  needs SPL's online LLM projection (`desi.spl_adapter`) and would be a separate,
  future opt-in tier. The deterministic SPL backend in the library is a narrow
  demo by design.

## Claim graph

Built as plain JSON (no Neo4j in the MVP). Node types: `paper`, `claim`,
`overclaim_risk`, `evidence_gap`, `reproducibility_risk`. Edge types:
`contains`, `has_overclaim_risk`, `has_gap`, `has_reproducibility_risk`.
The frontend renders it with a dependency-free layered SVG view (React
Flow can be swapped in later if richer interaction is needed — kept out of
the MVP to avoid a heavy dependency).

## Frontend (`frontend/`)

Next.js App Router, single page. Layout: left = input/upload, center =
claim list + detail (with per-claim `method` + `content_hash`), right =
graph + risks + cross-review similarity + replay/audit, bottom = report
export. Typed client in `lib/api.ts`. No login, no multi-user, no cloud,
no mutation.

## Offline & secrets

Offline by default (two independent gates). API keys are never read into
serialized config, logged, sent to the frontend, or written into reports;
only the env-var name and a presence flag are exposed.
