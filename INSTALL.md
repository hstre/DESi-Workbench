# Installing DESi Workbench

Requirements: Python >= 3.11, Node >= 18 (tested on 22).

The Workbench depends on the real `desi-governance` library, which lives in
the public [`hstre/DESi`](https://github.com/hstre/DESi) repository (it is
not published to PyPI). Check it out alongside this repo.

```
parent/
  DESi/                # hstre/DESi  (provides desi-governance)
  DESi-Workbench/      # this repo
```

## Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e ../../DESi          # the real desi-governance
pip install -e ".[test]"
uvicorn app.main:app --reload      # serves http://localhost:8000
pytest                             # run the backend tests
```

### Windows (PowerShell)

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ..\..\DESi
pip install -e ".[test]"
uvicorn app.main:app --reload
pytest
```

(If `desi-governance` is installed some other way, skip the
`pip install -e ../../DESi` step.)

## Frontend

```bash
cd frontend
npm install
npm run dev                        # serves http://localhost:3000
npm run build                      # production build
npm test                           # vitest
```

Set `NEXT_PUBLIC_API_BASE` if the backend is not at `http://localhost:8000`.

## Docker (optional)

```bash
docker compose up --build
# open http://localhost:3000
```

The backend image installs `desi-governance` from the public git repo
during the build; Neo4j is not required.

## Offline & secrets

Offline by default (`DESI_WORKBENCH_OFFLINE_MODE=true`,
`DESI_WORKBENCH_ALLOW_LIVE_LLM_CALLS=false`). No API key is needed. Copy
[.env.example](.env.example) to `.env` for local overrides; never commit
keys. `data/` and `.env` are gitignored.
