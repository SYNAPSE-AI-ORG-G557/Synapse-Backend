# Build argument to force rebuild - Railway cache busting
ARG BUILD_DATE=2025-01-19
ARG CACHE_BUST=railway-deploy-fix-v5

# --- Stage 1: Builder ---
FROM python:3.11-slim-bookworm AS builder
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential libpq-dev && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Optional: if you truly need to remove this dep
RUN pip uninstall -y pytest-anyio || true

# --- Stage 2: Final ---
FROM python:3.11-slim-bookworm
WORKDIR /code

# Set PYTHONPATH to include all necessary paths for module resolution
ENV PYTHONPATH="/code:/code/src:/code/app:/code/src/core:/code/src/api"

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11 /usr/local/lib/python3.11
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder /usr/local/include /usr/local/include
COPY --from=builder /usr/local/share /usr/local/share

# Copy application code - src first, then app
COPY ./src /code/src
COPY ./app /code/app

# Verify the directory structure and imports work
RUN echo "=== Verifying directory structure ===" && \
    ls -la /code/ && \
    echo "=== Contents of /code/src ===" && \
    ls -la /code/src/ && \
    echo "=== Contents of /code/app ===" && \
    ls -la /code/app/ && \
    echo "=== PYTHONPATH ===" && \
    echo $PYTHONPATH && \
    echo "=== Testing Python imports ===" && \
    python -c "import sys; print('Python path:', sys.path)" && \
    python -c "from src.core.config import settings; print('Import successful!')"

# Create non-root user and give it ownership of the code we just copied
RUN useradd --create-home appuser && chown -R appuser:appuser /code
USER appuser

EXPOSE 8000
CMD ["gunicorn", "app.main:app", "-k", "uvicorn.workers.UvicornWorker", "-b", "0.0.0.0:8000"]
    