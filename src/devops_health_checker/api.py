import hmac
import json
import os
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from devops_health_checker.agent import DevOpsAgent
from devops_health_checker.tools.registry import create_tool_registry


MAX_REQUEST_BYTES = 1_048_576


def create_api_server(
    host: str = "127.0.0.1",
    port: int = 8080,
    registry=None,
    api_token: str | None = None,
):
    tool_registry = registry or create_tool_registry()
    configured_token = api_token if api_token is not None else os.getenv(
        "DEVOPS_API_TOKEN"
    )

    class APIHandler(BaseHTTPRequestHandler):
        def _send_json(self, status: int, payload: dict[str, Any]) -> None:
            body = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _authorized(self) -> bool:
            if not configured_token:
                return True
            authorization = self.headers.get("Authorization", "")
            return hmac.compare_digest(
                authorization,
                f"Bearer {configured_token}",
            )

        def _read_json(self) -> dict[str, Any] | None:
            content_length = self.headers.get("Content-Length")
            try:
                length = int(content_length or "0")
            except ValueError:
                return None
            if length <= 0 or length > MAX_REQUEST_BYTES:
                return None
            try:
                payload = json.loads(self.rfile.read(length))
            except (UnicodeDecodeError, json.JSONDecodeError):
                return None
            return payload if isinstance(payload, dict) else None

        def do_GET(self) -> None:
            if self.path == "/health":
                self._send_json(HTTPStatus.OK, {"status": "ok"})
                return
            if self.path == "/tools":
                self._send_json(
                    HTTPStatus.OK,
                    {
                        "tools": [
                            {
                                "name": tool.name,
                                "description": tool.description,
                                "read_only": tool.read_only,
                            }
                            for tool in tool_registry.list_tools()
                        ]
                    },
                )
                return
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "Not found"})

        def do_POST(self) -> None:
            if self.path not in {"/knowledge", "/agent"}:
                self._send_json(HTTPStatus.NOT_FOUND, {"error": "Not found"})
                return
            if not self._authorized():
                self._send_json(HTTPStatus.UNAUTHORIZED, {"error": "Unauthorized"})
                return

            payload = self._read_json()
            if payload is None:
                self._send_json(
                    HTTPStatus.BAD_REQUEST,
                    {"error": "Request must be a JSON object under 1 MiB"},
                )
                return

            if self.path == "/knowledge":
                self._handle_knowledge(payload)
            else:
                self._handle_agent(payload)

        def _handle_knowledge(self, payload: dict[str, Any]) -> None:
            query = payload.get("query")
            if not isinstance(query, str) or not query.strip():
                self._send_json(
                    HTTPStatus.BAD_REQUEST,
                    {"error": "query must be a non-empty string"},
                )
                return
            arguments = {"query": query}
            if "top_k" in payload:
                arguments["top_k"] = payload["top_k"]
            execution = tool_registry.execute("search_devops_knowledge", arguments)
            self._send_json(
                HTTPStatus.OK if execution.success else HTTPStatus.BAD_REQUEST,
                execution.to_dict(),
            )

        def _handle_agent(self, payload: dict[str, Any]) -> None:
            message = payload.get("message")
            if not isinstance(message, str) or not message.strip():
                self._send_json(
                    HTTPStatus.BAD_REQUEST,
                    {"error": "message must be a non-empty string"},
                )
                return
            try:
                answer = DevOpsAgent(tool_registry).run(message)
            except Exception as error:
                self._send_json(
                    HTTPStatus.BAD_GATEWAY,
                    {"error": f"Agent execution failed: {error}"},
                )
                return
            self._send_json(HTTPStatus.OK, {"answer": answer})

        def log_message(self, format, *args) -> None:
            return

    return ThreadingHTTPServer((host, port), APIHandler)


def run_api_server() -> None:
    host = os.getenv("DEVOPS_API_HOST", "0.0.0.0")
    port = int(os.getenv("DEVOPS_API_PORT", "8080"))
    server = create_api_server(host, port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
