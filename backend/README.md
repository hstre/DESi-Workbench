# DESi Workbench - backend

FastAPI service that makes the DESi governance library visible (claim
extraction, evidence gaps, overclaim risks, reproducibility risks, claim
graph, replay/audit trace, Markdown report). It uses the real
`desi-governance` library and does **not** modify or re-implement the
DESi core. Offline by default; single verdict `REVIEW_ASSISTANCE_ONLY`.

See the repository [README](../README.md) and [INSTALL](../INSTALL.md).

## Run

```bash
pip install -e ../../DESi        # the real desi-governance (public repo)
pip install -e ".[test]"
uvicorn app.main:app --reload
pytest
```

## Endpoints

`GET /health` · `GET /config` · `POST /api/review` ·
`GET /api/review/{id}` · `GET /api/review/{id}/report.md` ·
`GET /api/review/{id}/graph`
