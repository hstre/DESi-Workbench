# End-to-end MCP test

This runbook turns the repository branch into a ChatGPT developer-mode app without adding an external LLM API key. ChatGPT supplies the language work; the MCP server controls the DESi, Kevin and Doktores workflow.

## 1. Build and run the container

From the repository root:

```bash
docker build -t desi-epistemic-review .
mkdir -p data
docker run --rm \
  -p 8000:8000 \
  -v "$(pwd)/data:/data" \
  --name desi-epistemic-review \
  desi-epistemic-review
```

The MCP endpoint is now available locally at:

```text
http://127.0.0.1:8000/mcp
```

## 2. Inspect the raw MCP contract

```bash
npx @modelcontextprotocol/inspector@latest
```

Connect the Inspector to `http://127.0.0.1:8000/mcp`, list the tools, and call them in this order:

1. `start_review`
2. `get_next_stage`
3. `submit_stage`
4. repeat 2–3 until complete
5. `finalize_review`

The server must reject skipped stages, invalid role output, unknown claim or hypothesis references, and attempts to replace an already completed stage.

## 3. Expose the local endpoint over HTTPS

Use OpenAI Secure MCP Tunnel, ngrok, or Cloudflare Tunnel. The resulting public address must end in `/mcp`, for example:

```text
https://example-tunnel.invalid/mcp
```

Do not expose the SQLite file or mount it under a public web path.

## 4. Add the app in ChatGPT

In ChatGPT web:

1. Enable Developer mode under **Settings → Security and login**.
2. Open **Settings → Plugins**.
3. Create a developer-mode app.
4. Use the public HTTPS `/mcp` endpoint.
5. Confirm that ChatGPT discovers exactly four tools.

Suggested metadata:

- **Name:** Epistemic Review
- **Description:** Domain-neutral manuscript audit using DESi claim structure, Kevin blind-spot routing and separated Doktores review roles. Use it to audit, extend and adversarially test a paper without treating the result as peer review.

## 5. Golden prompts

### Direct

> Run a full epistemic review of this manuscript. Do not skip roles and return the final replay-verifiable report.

### Indirect

> I think this paper is finished. Check whether any important boundary case changes the meaning of its central claims.

### Negative

> Summarize this paper in five sentences.

The app should be selected for the direct prompt, be discoverable for the indirect prompt, and remain unused for the negative prompt unless the user explicitly asks for an audit.

## 6. Frozen Klein-bottle check

Use the integration fixture or the final manuscript. The protocol should surface the coexistence of a generic `U(1)^2` statement and gauge enhancement at `r=1`, route a boundary/limit probe, and require the falsifier to submit a `boundary_change` attack. The test validates the epistemic workflow, not a predetermined physics conclusion.

## 7. Exit criteria for v0

The v0 prototype is ready to merge only when:

- Python 3.11 and 3.12 tests pass in CI;
- the Docker image builds;
- MCP Inspector lists and calls all four tools;
- ChatGPT completes one full run without manual stage repair;
- repeated identical input produces the same run ID and deterministic audit layer;
- a malformed stage is rejected;
- the final report preserves role provenance and hash-chain metadata.
