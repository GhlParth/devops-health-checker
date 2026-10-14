# ─── Stage 1: Build / dependency resolution ───────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

# Install uv
RUN pip install --no-cache-dir uv

# Copy dependency manifests first (maximize layer cache)
COPY pyproject.toml uv.lock README.md ./

# Resolve & install external dependencies
RUN uv sync --no-dev --frozen --no-install-project

# Copy application sources and knowledge base, then install project
COPY src ./src
COPY knowledge ./knowledge
RUN uv sync --no-dev --frozen


# ─── Stage 2: Runtime ──────────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

# Security: never run as root
USER 65534:65534

WORKDIR /app

# Copy the pre-built venv, app code and knowledge base from builder stage
COPY --from=builder --chown=65534:65534 /build/.venv /app/.venv
COPY --from=builder --chown=65534:65534 /build/src /app/src
COPY --from=builder --chown=65534:65534 /build/knowledge /app/knowledge

# Environment configuration
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app/src" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DEVOPS_API_HOST=0.0.0.0 \
    DEVOPS_API_PORT=8080 \
    UV_CACHE_DIR=/tmp/uv-cache \
    REPORT_OUTPUT_PATH=/tmp/reports/health-report.json \
    LOG_FORMAT=json

EXPOSE 8080

# Metadata labels
LABEL org.opencontainers.image.title="devops-health-checker" \
      org.opencontainers.image.description="Agentic DevOps infrastructure health checker" \
      org.opencontainers.image.source="https://github.com/your-org/devops-health-checker"

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')" || exit 1

CMD ["devops-health-checker", "--api-server"]
