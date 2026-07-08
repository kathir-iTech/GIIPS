# Stage 1: Build — install dependencies into a known prefix
FROM python:3.11-slim-bookworm AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc g++ libffi-dev libssl-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/ai-engine

COPY ai-engine/backend/requirements.txt ./backend/
COPY ai-engine/backend/requirements-ai.txt ./backend/

RUN pip install --no-cache-dir --prefix=/install \
    -r ./backend/requirements.txt

# Optional: uncomment to include AI deps in the runtime image
# RUN pip install --no-cache-dir --prefix=/install \
#     -r ./backend/requirements-ai.txt


# Stage 2: Runtime — strip everything except what's needed to serve
FROM python:3.11-slim-bookworm AS runtime

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user so we're not running the app as root
RUN useradd -m -u 1000 appuser

WORKDIR /app

# Copy installed Python packages from builder
COPY --from=builder --chown=appuser:appuser /install /usr/local

# Copy application source code
# We need the full ai-engine tree because runtime imports like
# `from classification.train import ComplaintClassifier` resolve
# against `ai-engine/` on sys.path.
COPY --chown=appuser:appuser ai-engine/ ./ai-engine/

# Persistent data dirs
RUN mkdir -p /app/ai-engine/data /app/ai-engine/models/classification \
    && chown -R appuser:appuser /app/ai-engine

USER appuser

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/ai-engine/backend:$PYTHONPATH \
    AI_ENGINE_DATA_DIR=/app/ai-engine/data \
    AI_ENGINE_MODELS_DIR=/app/ai-engine/models

# Healthcheck — probes FastAPI's /health endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -fsS http://localhost:8000/health || exit 1

# Default entrypoint — uvicorn for dev / ASGI serving
# Override to gunicorn for production:
#   gunicorn ai-engine.backend.app:app \
#     --worker-class uvicorn.workers.UvicornWorker \
#     --workers 2 --bind 0.0.0.0:8000 --log-level info
EXPOSE 8000

CMD ["uvicorn", "ai-engine.backend.app:app", "--host", "0.0.0.0", "--port", "8000", "--log-level", "info", "--workers", "1"]
