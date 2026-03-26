# ── Stage 1: Base ─────────────────────────────────────────────────────────────
FROM python:3.11-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# System deps for psycopg2, ta-lib, etc.
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ libpq-dev curl git \
    && rm -rf /var/lib/apt/lists/*

# ── Stage 2: Dependencies ─────────────────────────────────────────────────────
FROM base AS deps

COPY requirements.txt .
# Install CPU-only TensorFlow to reduce image size
RUN pip install --no-cache-dir \
    tensorflow-cpu==2.16.1 \
    && pip install --no-cache-dir -r requirements.txt

# ── Stage 3: Runtime ──────────────────────────────────────────────────────────
FROM deps AS runtime

COPY . .

RUN mkdir -p logs models/saved

# Non-root user for security
RUN useradd -m -u 1000 alphasignal && chown -R alphasignal:alphasignal /app
USER alphasignal

EXPOSE 8000 8501

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1
