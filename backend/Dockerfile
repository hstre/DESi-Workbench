FROM python:3.11-slim

WORKDIR /app

# Install the real (public) desi-governance library first so the backend's
# dependency is satisfied from source, not from PyPI (it is not published).
RUN pip install --no-cache-dir "git+https://github.com/hstre/DESi.git"

COPY . /app
RUN pip install --no-cache-dir .

ENV DESI_WORKBENCH_DATA_DIR=/data/reviews \
    DESI_WORKBENCH_OFFLINE_MODE=true \
    DESI_WORKBENCH_ALLOW_LIVE_LLM_CALLS=false

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
