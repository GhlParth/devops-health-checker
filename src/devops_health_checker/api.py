"""FastAPI-based HTTP API server.

Improvements over the original ThreadingHTTPServer implementation:
- Async I/O with Uvicorn (LLM calls don't block other requests)
- Rate limiting via slowapi (per-IP token bucket)
- Prometheus /metrics endpoint
- Input validation + prompt-injection guard
- OpenAPI docs at /docs and /redoc
- Graceful shutdown on SIGTERM / SIGINT
- Proper request logging middleware
- Legacy compatibility wrapper create_api_server
"""

from __future__ import annotations

import asyncio
import os
import re
import signal
import socket
from contextlib import asynccontextmanager
from typing import Annotated, Any

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, PlainTextResponse, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from pydantic import BaseModel, Field
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from devops_health_checker.agent import DevOpsAgent
from devops_health_checker.logger import setup_logger
from devops_health_checker.tools.registry import create_tool_registry

logger = setup_logger("devops-health-checker.api")

# ─── Rate limiter ─────────────────────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address)

# ─── Prompt injection guard ───────────────────────────────────────────────────
_MAX_INPUT_LEN = int(os.getenv("MAX_INPUT_LEN", "4000"))
_INJECTION_PATTERNS = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"ignore\s+(previous|above|all)\s+instructions",
        r"reveal\s+(your\s+)?(system\s+)?prompt",
        r"jailbreak",
        r"DAN\s+mode",
        r"you\s+are\s+now\s+",
    ]
]


def _validate_user_input(text: str, field: str = "input") -> str:
    text = text.strip()
    if not text:
        raise HTTPException(
            status_code=400,
            detail=f"{field} must be a non-empty string",
        )
    if len(text) > _MAX_INPUT_LEN:
        raise HTTPException(
            status_code=400,
            detail=f"{field} exceeds maximum length of {_MAX_INPUT_LEN} characters",
        )
    for pattern in _INJECTION_PATTERNS:
        if pattern.search(text):
            raise HTTPException(
                status_code=400,
                detail=f"Input rejected: potentially unsafe content detected in {field}",
            )
    return text


# ─── Auth ─────────────────────────────────────────────────────────────────────
_security = HTTPBearer(auto_error=False)


def _get_configured_token() -> str | None:
    return os.getenv("DEVOPS_API_TOKEN") or None


async def verify_token(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_security)],
) -> None:
    configured_token = getattr(request.app.state, "api_token", None) or _get_configured_token()
    if not configured_token:
        return  # Auth disabled — dev mode
    if credentials is None or credentials.credentials != configured_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ─── Request Schemas ──────────────────────────────────────────────────────────
class KnowledgeRequest(BaseModel):
    query: str = Field(..., description="DevOps / infrastructure question")
    top_k: int = Field(5, ge=1, le=20, description="Max results to return")


class AgentRequest(BaseModel):
    message: str = Field(..., description="Natural-language infrastructure question")


# ─── Lifespan ─────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("DevOps Health Checker API starting up")
    yield
    logger.info("DevOps Health Checker API shutting down")


# ─── App factory ─────────────────────────────────────────────────────────────
def create_app(registry: Any = None, api_token: str | None = None) -> FastAPI:
    tool_registry = registry or create_tool_registry()

    app = FastAPI(
        title="DevOps Health Checker",
        version="0.1.0",
        description=(
            "Agentic infrastructure health checker for AWS, Kubernetes, and GitHub. "
            "Authenticate with Bearer token when DEVOPS_API_TOKEN is set."
        ),
        lifespan=lifespan,
    )

    if api_token is not None:
        app.state.api_token = api_token

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.detail, "detail": exc.detail},
            headers=exc.headers,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        errors = exc.errors()
        loc = errors[0].get("loc", []) if errors else []
        field_name = loc[-1] if loc else "query"
        detail_msg = f"{field_name} must be a non-empty string"
        return JSONResponse(
            status_code=400,
            content={"error": detail_msg, "detail": detail_msg},
        )

    # ── Request logging middleware ───────────────────────────────────────────
    @app.middleware("http")
    async def log_requests(request: Request, call_next: Any) -> Response:
        response = await call_next(request)
        logger.info(
            "HTTP request",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "client": request.client.host if request.client else "unknown",
            },
        )
        return response

    # ── Health ───────────────────────────────────────────────────────────────
    @app.get("/health", tags=["ops"], summary="Liveness / readiness probe")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    # ── Prometheus metrics ───────────────────────────────────────────────────
    @app.get(
        "/metrics",
        tags=["ops"],
        summary="Prometheus metrics",
        response_class=PlainTextResponse,
    )
    async def metrics() -> PlainTextResponse:
        data = generate_latest()
        return PlainTextResponse(content=data, media_type=CONTENT_TYPE_LATEST)

    # ── Tool list ────────────────────────────────────────────────────────────
    @app.get("/tools", tags=["tools"], summary="List registered health-check tools")
    async def list_tools() -> dict[str, list[dict]]:
        return {
            "tools": [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "read_only": tool.read_only,
                }
                for tool in tool_registry.list_tools()
            ]
        }

    # ── Knowledge search ─────────────────────────────────────────────────────
    @app.post(
        "/knowledge",
        tags=["knowledge"],
        summary="Search the local DevOps knowledge base",
        dependencies=[Depends(verify_token)],
    )
    @limiter.limit("30/minute")
    async def knowledge(request: Request, body: KnowledgeRequest) -> dict:
        query = _validate_user_input(body.query, "query")
        execution = await asyncio.to_thread(
            tool_registry.execute,
            "search_devops_knowledge",
            {"query": query, "top_k": body.top_k},
        )
        if not execution.success:
            raise HTTPException(status_code=400, detail=execution.error)
        return execution.to_dict()

    # ── Agent ────────────────────────────────────────────────────────────────
    @app.post(
        "/agent",
        tags=["agent"],
        summary="Ask the AI DevOps agent a question",
        dependencies=[Depends(verify_token)],
    )
    @limiter.limit("10/minute")
    async def agent(request: Request, body: AgentRequest) -> dict[str, str]:
        message = _validate_user_input(body.message, "message")
        try:
            answer = await asyncio.to_thread(
                DevOpsAgent(tool_registry).run,
                message,
            )
        except Exception as exc:
            logger.exception("Agent execution failed", extra={"error": str(exc)})
            raise HTTPException(
                status_code=502,
                detail=f"Agent execution failed: {exc}",
            ) from exc
        return {"answer": answer}

    return app


# ─── Legacy compatibility server ─────────────────────────────────────────────
class LegacyApiServer:
    """Compatibility server wrapper for tests and legacy callers."""

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 0,
        registry: Any = None,
        api_token: str | None = None,
    ):
        self.app = create_app(registry=registry, api_token=api_token)
        self.host = host
        if port == 0:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.bind((host, 0))
                self.server_port = sock.getsockname()[1]
        else:
            self.server_port = port

        self.config = uvicorn.Config(
            app=self.app,
            host=self.host,
            port=self.server_port,
            log_level="error",
        )
        self.server = uvicorn.Server(self.config)

    def serve_forever(self) -> None:
        self.server.run()

    def shutdown(self) -> None:
        self.server.should_exit = True

    def server_close(self) -> None:
        pass


def create_api_server(
    host: str = "127.0.0.1",
    port: int = 8080,
    registry: Any = None,
    api_token: str | None = None,
) -> LegacyApiServer:
    return LegacyApiServer(host=host, port=port, registry=registry, api_token=api_token)


# ─── Entrypoint ───────────────────────────────────────────────────────────────
def run_api_server() -> None:
    host = os.getenv("DEVOPS_API_HOST", "0.0.0.0")
    port = int(os.getenv("DEVOPS_API_PORT", "8080"))
    log_level = os.getenv("LOG_LEVEL", "info").lower()

    app = create_app()

    config = uvicorn.Config(
        app=app,
        host=host,
        port=port,
        log_level=log_level,
        access_log=False,  # handled by our middleware
        loop="auto",
    )
    server = uvicorn.Server(config)

    # Graceful shutdown on SIGTERM (Kubernetes pod termination)
    def _handle_sigterm(signum, frame):  # noqa: ANN001
        logger.info("Received SIGTERM — initiating graceful shutdown")
        server.should_exit = True

    signal.signal(signal.SIGTERM, _handle_sigterm)

    logger.info("Starting API server", extra={"host": host, "port": port})
    server.run()
