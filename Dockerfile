FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DESI_MCP_HOST=0.0.0.0 \
    DESI_MCP_PORT=8000 \
    DESI_MCP_DB=/data/epistemic_review.sqlite3

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends git ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY backend /app/backend

RUN python -m pip install --upgrade pip \
    && python -m pip install "desi-governance @ git+https://github.com/hstre/DESi@f0984f440a60293a51f002d388cd030be27acf1e" \
    && python -m pip install "/app/backend[files]"

WORKDIR /app/backend
RUN mkdir -p /data

VOLUME ["/data"]
EXPOSE 8000

CMD ["python", "-m", "app.mcp_server"]
