# DESi Workbench MVP — GO / NO-GO

**Result: `DESI_WORKBENCH_MVP_READY` (GO)**

Pipeline version: `workbench-mvp-0.1.0a0` · DESi library: `desi-governance`
0.1.0a0 · verdict: `REVIEW_ASSISTANCE_ONLY`.

## Criteria

| # | Criterion | Status | Evidence |
|---|---|---|---|
| 1 | backend starts | ✅ | `uvicorn app.main:app` serves `GET /health` 200, `core_identity=1.0` |
| 2 | frontend starts | ✅ | `next build` compiles; `next start` serves the page (markers: "DESi Workbench", "REVIEW_ASSISTANCE_ONLY", "Load sample") |
| 3 | sample review works | ✅ | `POST /api/review` on `examples/sample_paper.md` → 14 claims, 10 overclaims, 11 evidence gaps, 5 reproducibility risks |
| 4 | offline default enforced | ✅ | `GET /config` → `offline_mode=true`, `allow_live_llm_calls=false`, `live_calls_enabled=false` |
| 5 | no live calls by default | ✅ | pipeline runs with sockets patched to raise (test `test_no_network_during_pipeline`); `mode="live"` rejected with 400 |
| 6 | no DESi-core mutation | ✅ | `git status` in the DESi repo is clean; only `app/desi_adapter.py` imports the `desi` library |
| 7 | report generated | ✅ | `GET /api/review/{id}/report.md` returns all sections (Scope … Limitations) |
| 8 | graph generated | ✅ | `GET /api/review/{id}/graph` → 41 nodes / 40 edges; all edges reference existing nodes; node ids unique |
| 9 | deterministic same-input output | ✅ | identical input → identical `review_id` and `replay.output_hash` (test `test_deterministic_same_input`) |

## Test results

- **Backend:** `pytest` → 14 passed (health, config, review offline,
  overclaim/repro detection, determinism, graph validity, report
  generation, offline/no-network, no-secret-leak, live-mode rejected).
- **Frontend:** `tsc --noEmit` clean · `vitest` → 2 passed (app renders;
  submit sample → shows claims + report link) · `next build` succeeds.

## Governance & safety

- The DESi core (replay kernel, governance core, concept gates,
  determinism scanner, artifact format) is **unchanged**. The Workbench
  uses the real `desi-governance` public API only, via a single adapter.
- Offline by default; two independent gates required for any live call
  (the MVP makes none). API keys are never read into config, logged, sent
  to the frontend, or written into reports (test `test_api_key_never_leaks`).
- `data/`, `.env`, `*.key`, `secrets/` are gitignored.

## Known MVP limits

- No PDF input (`.txt` / `.md` / paste only).
- No LLM calls (offline-only heuristics).
- File storage only (no database); no login/multi-user/cloud.
- Heuristics are transparent and deterministic — expect false positives
  and negatives; a human reviewer makes every judgement.

## Note on environment verification

Backend was run and exercised via HTTP in this environment. The frontend
was type-checked, unit-tested, production-built, and served via
`next start` (HTML verified); a full browser click-through was not run
here (no headless browser available), but the typed API contract,
component tests, and build all pass.
