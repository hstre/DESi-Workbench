# DESi Workbench

The first usable surface for **DESi**. The Workbench makes DESi's core
functions visible for reviewing papers and text. It does **not** replace,
modify, or re-implement DESi — it uses the real `desi-governance`
library as an installable dependency.

> **Single verdict: `REVIEW_ASSISTANCE_ONLY`.** This is an epistemic-audit
> assistant, not a peer reviewer.

## 1. What is DESi Workbench?

A small web app (FastAPI backend + Next.js frontend) that takes a paper or
pasted text and surfaces what DESi can see about it: extracted claims,
evidence gaps, overclaim risks, reproducibility risks, a simple claim
graph, a replay/audit trace, and an exportable report.

### ELI5

DESi Workbench is like a lab-notebook checker for texts. It asks:
- Which claims are being made?
- Which evidence is missing?
- Where does the text sound stronger than the data can carry?

## 2. What the MVP can do

- Input a paper as `.txt`, `.md`, or pasted text.
- Extract claims and classify them: `main_claim`, `method_claim`,
  `evidence_claim`, `result_claim`, `limitation_claim`, `novelty_claim`,
  `generalization_claim`.
- Flag unsupported claims, overclaim risks, evidence gaps, and
  reproducibility risks (transparent, deterministic heuristics).
- Build a simple claim graph (JSON; rendered as a light SVG view).
- Show claim list, claim details, graph, evidence gaps, replay/audit
  trace, and an exportable Markdown report.
- Run fully **offline and deterministically** (same input → same output).
- Tag every claim with provenance — `method` (`workbench_heuristic`) and a
  replay-stable `content_hash` (DESi `replay_hash` over the normalized text) —
  following SPL's content/method discipline.
- **Cross-review similarity (a local Layer 9).** Every review's claims are
  appended to a shared, append-only claim ledger; a new review reports which of
  its claims were already seen in prior reviews — **exact** (same `content_hash`)
  or **lexical** (Jaccard token overlap). Deterministic and offline; kept out of
  the replay hash (history-dependent). Semantic/paraphrase similarity would need
  SPL's online LLM projection and is a separate, future opt-in tier.

## 3. What it cannot do (yet)

- It is **not peer review** and never accepts/rejects a paper.
- No PDF parsing yet (`.txt` / `.md` / paste only).
- No LLM calls in the MVP (offline-only; see below).
- No login, multi-user, cloud, or database — file storage only.
- It does not determine truth or guarantee correctness.

## 4. Installation

See [INSTALL.md](INSTALL.md). In short: install the real `desi-governance`
library (from the public `hstre/DESi` repo), then the backend, then the
frontend.

## 5. Start the backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate           # Windows: .venv\Scripts\activate
pip install -e ../../DESi           # the real desi-governance (public repo)
pip install -e .
uvicorn app.main:app --reload       # http://localhost:8000
```

## 6. Start the frontend

```bash
cd frontend
npm install
npm run dev                         # http://localhost:3000
```

## 7. Test with example text

Open http://localhost:3000, click **Load sample**, then **Review**. Or via
the API:

```bash
curl -X POST http://localhost:8000/api/review \
  -H "Content-Type: application/json" \
  -d '{"text": "We present the first novel method that solves it.", "mode": "offline"}'
```

A ready example lives in [`examples/`](examples/) (`sample_paper.md`,
`sample_output.json`).

## 8. Offline by default

`offline_mode=true`, `allow_live_llm_calls=false`. No API key is needed and
no live calls are made. Enabling LLMs later requires **both** flags via a
local `.env`; keys are never logged, sent to the frontend, or written into
reports. See [.env.example](.env.example).

## 9. Not a peer-review replacement

The Workbench assists a human reviewer. It surfaces structure and risks; a
human makes every judgement. The only verdict it emits is
`REVIEW_ASSISTANCE_ONLY`.

## 10. Limits

All findings come from transparent, deterministic heuristics over the
submitted text. Expect false positives and false negatives. Absence of a
flag is not a sign of quality; presence of a flag is not a sign of a
defect. The heuristics are documented in
[backend/app/review_pipeline.py](backend/app/review_pipeline.py) and
[docs/architecture.md](docs/architecture.md).

## Docs

- [QUICKSTART.md](QUICKSTART.md)
- [docs/ELI5_WORKBENCH.md](docs/ELI5_WORKBENCH.md)
- [docs/architecture.md](docs/architecture.md)
- [docs/core_api_requests.md](docs/core_api_requests.md)

## Core stays unchanged

The DESi core (replay kernel, governance core, concept gates, determinism
scanner, artifact format) is never modified. If the Workbench needs a
primitive the core does not provide, it is solved locally as an adapter and
recorded in [docs/core_api_requests.md](docs/core_api_requests.md) — never
changed without a separate task.
