# DESi Workbench - Quickstart

Two terminals, ~2 minutes.

## 1. Backend (terminal A)

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ../../DESi        # real desi-governance (public repo)
pip install -e .
uvicorn app.main:app --reload    # http://localhost:8000
```

Check it: `curl http://localhost:8000/health` → `core_identity: 1.0`.

## 2. Frontend (terminal B)

```bash
cd frontend
npm install
npm run dev                      # http://localhost:3000
```

## 3. Try it

1. Open http://localhost:3000
2. Click **Load sample** (or paste your own `.md` / `.txt`)
3. Click **Review**
4. Explore: claim list → claim detail (with `method` + `content_hash`) →
   graph → risks & gaps → **cross-review similarity** → replay trace →
   **Download report.md**. Review a second paper that repeats a claim to
   see the cross-review match light up.

## API in one call

```bash
curl -X POST http://localhost:8000/api/review \
  -H "Content-Type: application/json" \
  -d '{"title":"Demo","text":"We present the first novel method that solves it.","mode":"offline"}'
```

Same input always yields the same `review_id` and output (deterministic,
offline). The only verdict is `REVIEW_ASSISTANCE_ONLY`.
