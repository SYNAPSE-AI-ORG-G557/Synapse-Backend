# Single, optimized Dockerfile for Synapse Backend
# This file replaces ALL other Backend Dockerfiles - no more confusion!

FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/code

# Install system dependencies (this layer rarely changes)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /code

# Copy requirements first (this layer only changes when requirements change)
COPY requirements-clean.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements-clean.txt

# Remove conflicting packages (this layer rarely changes)
RUN pip uninstall -y pytest-anyio

# Create non-root user (this layer rarely changes)
RUN useradd --create-home appuser && chown -R appuser:appuser /code
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# NOTE: We DON'T copy source code here because it's mounted as a volume
# This means Docker will only rebuild when requirements change, not when code changes

# Default command: run uvicorn dev server with hot reload
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]