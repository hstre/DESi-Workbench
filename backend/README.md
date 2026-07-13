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

The backend also exposes a domain-neutral Streamable-HTTP MCP review circle:

- **DESi** performs deterministic claim extraction and governance checks.
- **Kevin** performs native blind-spot routing through `SpacePredictor` when installed; otherwise the run records an explicit bounded fallback.
- **Doktores** supplies the full seven-role protocol: theorist → literature scout → falsifier → experimental designer → method reviewer → paper builder → adversarial reviewer.
- **The MCP host model** supplies language and general domain reasoning inside role-bounded packets.
- **The human/Joni governance layer** remains the decision gate. The server never confirms a belief.

The native Doktores package is capability-checked and versioned in every run.
The MCP workflow is deliberately host-mediated rather than calling
`Doktores().run()`; this distinction is disclosed by `get_capabilities` and in
the final artifact.

See the repository [README](../README.md), [INSTALL](../INSTALL.md), and
[MCP guide](../docs/mcp_epistemic_review.md).

## Run the existing API

```bash
pip install -e ../../DESi        # the real desi-governance (public repo)
pip install -e ".[test]"
uvicorn app.main:app --reload
pytest
```

## Run the MCP server with native Kevin and Doktores

```bash
pip install "desi-governance @ git+https://github.com/hstre/DESi@f0984f440a60293a51f002d388cd030be27acf1e"
pip install -e ".[files,ecosystem]"
export DESI_REQUIRE_ECOSYSTEM=1
desi-workbench-mcp
# or: python -m app.mcp_server
# endpoint: http://localhost:8000/mcp
```

For fallback-capable local operation, omit the `ecosystem` extra and
`DESI_REQUIRE_ECOSYSTEM`. Every run records which engine actually executed.

## MCP tools

1. `get_capabilities`
2. `start_review`
3. `get_next_stage`
4. `submit_stage`
5. `finalize_review`

## Transport smoke test

With the MCP server running:

```bash
python scripts/mcp_smoke.py
```

The script uses a real Streamable-HTTP MCP client, initializes a session and
verifies the complete public tool surface.

## HTTP endpoints

`GET /health` · `GET /config` · `POST /api/review` ·
`GET /api/review/{id}` · `GET /api/review/{id}/report.md` ·
`GET /api/review/{id}/graph`
