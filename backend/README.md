# DESi Workbench - backend

FastAPI service that makes the DESi governance library visible: claim
extraction (transparent heuristic) with per-claim provenance (`method`)
and a replay-stable `content_hash`, evidence gaps, overclaim risks,
reproducibility risks, a claim graph, **cross-review similarity** (a local
Layer 9 claim ledger: exact + lexical), a replay/audit trace, and a
Markdown report. It uses the real `desi-governance` library for hashing,
the forbidden-term scan, the protected-core gate and audit framing, and
does **not** modify or re-implement the DESi core. Offline by default;
single scope verdict `REVIEW_ASSISTANCE_ONLY`.

The backend exposes two surfaces on one server and one shared SQLite state:

- **Browser cockpit at `/`** — load TXT, Markdown, DOCX or PDF; inspect DESi and Kevin; follow all seven Doktores roles; validate structured role results; view and save the final report and replay artifact.
- **Streamable-HTTP MCP at `/mcp`** — lets ChatGPT or another MCP host supply the language layer while the server enforces protocol, schemas, references and state.

The review circle combines:

- **DESi** — deterministic claim extraction and governance checks.
- **Kevin** — native blind-spot routing through `SpacePredictor` when installed; otherwise the run records an explicit bounded fallback.
- **Doktores** — the full seven-role protocol: theorist → literature scout → falsifier → experimental designer → method reviewer → paper builder → adversarial reviewer.
- **MCP host model** — language and general domain reasoning inside role-bounded packets.
- **Human/Joni governance layer** — the decision gate. The server never confirms a belief.

The native Doktores package is capability-checked and versioned in every run.
The MCP workflow is deliberately host-mediated rather than calling
`Doktores().run()`; this distinction is disclosed by `get_capabilities` and in
the final artifact.

See the repository [README](../README.md), [INSTALL](../INSTALL.md), and
[MCP guide](../docs/mcp_epistemic_review.md).

## Run the existing API

```bash
pip install -e ../../DESi
pip install -e ".[test]"
uvicorn app.main:app --reload
pytest
```

## Run cockpit and MCP server with native Kevin and Doktores

```bash
pip install "desi-governance @ git+https://github.com/hstre/DESi@f0984f440a60293a51f002d388cd030be27acf1e"
pip install -e ".[files,ecosystem]"
export DESI_REQUIRE_ECOSYSTEM=1
desi-workbench-mcp
# or: python -m app.mcp_server
```

Open:

```text
Browser cockpit: http://localhost:8000/
MCP endpoint:    http://localhost:8000/mcp
```

For fallback-capable local operation, omit the `ecosystem` extra and
`DESI_REQUIRE_ECOSYSTEM`. Every run records which engine actually executed.

## MCP tools

1. `get_capabilities`
2. `start_review`
3. `get_next_stage`
4. `submit_stage`
5. `finalize_review`

## Verification

```bash
python -m pytest -q tests
python scripts/mcp_smoke.py
```

The test suite covers the browser assets and JSON API, text and base64 file
loading, state restoration and first-stage activation. The smoke script uses a
real Streamable-HTTP MCP client and verifies the complete tool surface.

## Legacy HTTP endpoints

`GET /health` · `GET /config` · `POST /api/review` ·
`GET /api/review/{id}` · `GET /api/review/{id}/report.md` ·
`GET /api/review/{id}/graph`
