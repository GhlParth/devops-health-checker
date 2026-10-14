FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml uv.lock README.md ./
COPY src ./src
COPY knowledge ./knowledge

RUN pip install --no-cache-dir uv \
    && uv sync --no-dev --frozen

ENV DEVOPS_API_HOST=0.0.0.0
ENV DEVOPS_API_PORT=8080
ENV UV_CACHE_DIR=/tmp/uv-cache

EXPOSE 8080

USER 65534:65534

CMD ["/app/.venv/bin/devops-health-checker", "--api-server"]
