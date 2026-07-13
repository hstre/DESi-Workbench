# MCP Epistemic Review v0

This branch exposes the existing DESi Workbench as a small Streamable-HTTP MCP server for ChatGPT and other MCP hosts.

## Boundary

The server does **not** contain a hidden reviewer model and does not claim domain expertise. It divides the work:

- **DESi**: deterministic claim extraction, stable identities and overreach/evidence flags.
- **Kevin**: domain-neutral blind-spot axes and content-free method selection.
- **Doktores**: separated theorist, falsifier and adversarial-reviewer contracts.
- **MCP host model**: language and general domain reasoning inside the supplied role packet.
- **Human**: decides whether any finding changes the manuscript.

The only scope verdict emitted by the server is `REVIEW_ASSISTANCE_ONLY`.

## Tools

1. `start_review` — ingest text or an authorised ChatGPT file reference; run DESi and Kevin.
2. `get_next_stage` — return the next role packet and exact output schema.
3. `submit_stage` — validate and append one role result to the hash chain.
4. `finalize_review` — produce JSON + Markdown after every role is complete.

The server instructions require this sequence and forbid role skipping.

## Install

```bash
cd backend
pip install -e ".[test,files,ecosystem]"
```

The ecosystem extra pins Kevin and Doktores to audited commits. It is optional: when Kevin is not importable the server uses a transparent set-coverage fallback and records that engine in the artifact.

## Run

```bash
python -m app.mcp_server
# MCP endpoint: http://localhost:8000/mcp
```

Test it with MCP Inspector, then add the HTTPS `/mcp` endpoint in ChatGPT developer mode.

## File support

- UTF-8 `.txt`, `.md`, `.markdown`
- `.docx` through a dependency-free OOXML reader
- `.pdf` when the `files` extra is installed (PyMuPDF)

File references are declared through `_meta["openai/fileParams"]`; the temporary download URL is accepted only over HTTPS and read with a hard size limit.

## State and replay

`DESI_MCP_DB` controls the SQLite path (default `data/epistemic_review.sqlite3`). Stage results are append-only after completion. Each stage hash binds:

- run id,
- role,
- role input,
- validated output,
- previous stage hash.

Repeated `start_review` calls with the same document, modes and focus return the same run.

## v0 integration test

The frozen toy manuscript contains both a generic `U(1)^2` claim and gauge enhancement at `r=1`. The protocol must route a boundary probe and the falsifier must submit a `boundary_change` attack before the deterministic critical-boundary check passes. The test checks the method, not the final physics answer.
