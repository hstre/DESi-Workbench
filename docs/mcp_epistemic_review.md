# DESi–Kevin–Doktores MCP epistemic review

The Workbench exposes a Streamable-HTTP MCP server at:

```text
http://localhost:8000/mcp
```

The protocol is `epistemic-review-v1`. It separates language generation from
deterministic routing, validation, state and governance.

## Tool order

1. `get_capabilities`
2. `start_review`
3. Repeatedly call `get_next_stage` and `submit_stage`
4. `finalize_review` after `get_next_stage` reports `complete: true`

Stages cannot be skipped, merged or rewritten after completion.

## Seven Doktores roles

1. **Theorist** — formulates falsifiable hypotheses linked to DESi claim IDs.
2. **Literature Scout** — maps related work, competing explanations, counterexamples, datasets and evidence. Verifiable source types require an explicit reference.
3. **Falsifier** — attacks hypotheses and records survivors. A generic/critical transition requires a `boundary_change` attack.
4. **Experimental Designer** — designs minimal reproducible discriminating tests for surviving hypotheses.
5. **Method Reviewer** — audits every experiment for controls, confounding, measurement risk, stopping rules and reproducibility.
6. **Paper Builder** — produces a traceable publication artifact without adding evidence or issuing a verdict.
7. **Adversarial Reviewer** — alone may recommend `accept`, `revise` or `reject`.

Each packet includes an exact Pydantic JSON schema and only the prior role
outputs that role is allowed to see.

## Engine provenance

`get_capabilities` and every final artifact disclose:

- DESi package version and native claim-audit execution.
- Kevin package version, native `SpacePredictor` status, coverage engine and any fallback reason.
- Doktores package version, seven-role protocol, and the fact that this MCP workflow is host-mediated rather than a call to `Doktores().run()`.

Set:

```bash
export DESI_REQUIRE_ECOSYSTEM=1
```

to fail closed when Kevin or Doktores is absent or API-incompatible. The
published Docker image uses this strict mode.

## File handling

`start_review` accepts either inline text or a ChatGPT file reference through
`openai/fileParams`.

Supported formats:

- UTF-8 text and Markdown
- DOCX through the dependency-free OOXML reader
- PDF through the `files` extra (`PyMuPDF`)

Downloads must remain HTTPS after redirects and are limited to 10 MB. Extracted
manuscript text is limited to 5 MB.

## State and governance

- Repeated identical starts yield the same run ID.
- SQLite stage state is append-only after completion.
- Every activated packet and completed result advances a SHA-256 hash chain.
- Claim, hypothesis and experiment references are checked before a stage is accepted.
- The final scope verdict is always `REVIEW_ASSISTANCE_ONLY`.
- The server does not confirm beliefs or replace peer review.

## Verification

```bash
python -m pytest -q tests
python -m app.mcp_server
python scripts/mcp_smoke.py
```

The smoke script uses an actual MCP client and verifies the complete
Streamable-HTTP tool surface.
