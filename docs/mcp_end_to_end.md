# End-to-end MCP verification

This runbook verifies the DESi–Kevin–Doktores plugin without an external LLM
API key. The MCP host supplies language; the server controls protocol, schemas,
references, state and provenance.

## 1. Install the native ecosystem

From `backend/`:

```bash
pip install "desi-governance @ git+https://github.com/hstre/DESi@f0984f440a60293a51f002d388cd030be27acf1e"
pip install -e ".[files,test,ecosystem]"
export DESI_REQUIRE_ECOSYSTEM=1
```

## 2. Run the strict suite

```bash
python -m compileall -q app
python -m pytest -q tests
```

The strict ecosystem tests require the pinned Kevin and Doktores packages and
verify that Kevin's native `SpacePredictor` is actually used.

## 3. Start the MCP server

```bash
export DESI_MCP_HOST=127.0.0.1
export DESI_MCP_PORT=8000
export DESI_MCP_DB=/tmp/desi-mcp.sqlite3
python -m app.mcp_server
```

The endpoint is:

```text
http://127.0.0.1:8000/mcp
```

## 4. Verify the transport with a real MCP client

In a second shell:

```bash
cd backend
python scripts/mcp_smoke.py --url http://127.0.0.1:8000/mcp
```

Expected output starts with:

```text
MCP_TRANSPORT_OK
```

A plain `curl` request is not a valid MCP health test because Streamable HTTP
may deliberately keep a session open.

## 5. Inspect the contract

```bash
npx @modelcontextprotocol/inspector@latest
```

Connect to the endpoint and call tools in this order:

1. `get_capabilities`
2. `start_review`
3. `get_next_stage`
4. `submit_stage`
5. repeat 3–4 until complete
6. `finalize_review`

The server exposes exactly five tools. It must reject skipped stages, malformed
role outputs, unknown claim/hypothesis/experiment references, unverifiable
literature evidence presented without a reference, and attempts to replace a
completed stage.

## 6. Seven-role run

A complete review executes:

1. theorist
2. literature scout
3. falsifier
4. experimental designer
5. method reviewer
6. paper builder
7. adversarial reviewer

The host must not merge roles. Only the adversarial reviewer may emit the final
`accept | revise | reject` recommendation.

## 7. Docker

From the repository root:

```bash
docker build -t desi-epistemic-review .
docker run --rm \
  -p 8000:8000 \
  -v desi-review-data:/data \
  --name desi-epistemic-review \
  desi-epistemic-review
```

The container installs DESi, Kevin and Doktores and sets
`DESI_REQUIRE_ECOSYSTEM=1`, so deployment fails closed instead of silently
shipping fallback-only operation.

## 8. Golden boundary check

Use the integration fixture or the final manuscript. The protocol should
surface the coexistence of a generic `U(1)^2` statement and gauge enhancement
at `r=1`, route a boundary/limit probe, and require the falsifier to submit a
`boundary_change` attack. This validates the epistemic workflow, not a
predetermined physics conclusion.

## 9. Exit criteria

- Python 3.11 and 3.12 fallback-capable tests pass.
- Strict native-ecosystem tests pass.
- The Docker image builds with pinned DESi, Kevin and Doktores packages.
- A real MCP client initializes and discovers all five tools.
- A complete seven-role run finalizes without manual stage repair.
- Repeated identical input produces the same run ID and deterministic audit layer.
- The final report preserves role provenance and hash-chain metadata.
