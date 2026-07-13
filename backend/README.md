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

The backend now also exposes a domain-neutral Streamable-HTTP MCP review
circle: DESi extracts claims, Kevin routes blind spots, Doktores enforces
separated theorist/falsifier/reviewer roles, and the MCP host model supplies
the language layer.

See the repository [README](../README.md), [INSTALL](../INSTALL.md), and
[MCP guide](../docs/mcp_epistemic_review.md).

## Run the existing API

```bash
pip install -e ../../DESi        # the real desi-governance (public repo)
pip install -e ".[test]"
uvicorn app.main:app --reload
pytest
```

## Run the MCP server

```bash
pip install -e ".[test,files,ecosystem]"
desi-workbench-mcp
# or: python -m app.mcp_server
# endpoint: http://localhost:8000/mcp
```

The `ecosystem` extra is optional. Without Kevin/Doktores imports, the
server records and uses its transparent deterministic fallback rather than
pretending those packages ran.

## HTTP endpoints

`GET /health` · `GET /config` · `POST /api/review` ·
`GET /api/review/{id}` · `GET /api/review/{id}/report.md` ·
`GET /api/review/{id}/graph`

## MCP tools

`start_review` · `get_next_stage` · `submit_stage` · `finalize_review`
