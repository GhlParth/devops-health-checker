import json
import sys
from collections.abc import Callable, Iterator
from typing import Any, TextIO


MCP_PROTOCOL_VERSION = "2024-11-05"


class MCPServer:
    """Expose the validated local tool registry through MCP-style JSON-RPC."""

    def __init__(self, registry):
        self.registry = registry

    def handle_request(self, request: dict[str, Any]) -> dict[str, Any] | None:
        if not isinstance(request, dict) or request.get("jsonrpc") != "2.0":
            return self._error(request.get("id"), -32600, "Invalid Request")

        request_id = request.get("id")
        method = request.get("method")
        params = request.get("params") or {}

        if method == "notifications/initialized":
            return None
        if method == "initialize":
            return self._success(
                request_id,
                {
                    "protocolVersion": MCP_PROTOCOL_VERSION,
                    "capabilities": {"tools": {"listChanged": False}},
                    "serverInfo": {
                        "name": "devops-health-checker",
                        "version": "0.1.0",
                    },
                },
            )
        if method == "tools/list":
            return self._success(request_id, {"tools": self._list_tools()})
        if method == "tools/call":
            return self._call_tool(request_id, params)

        return self._error(request_id, -32601, f"Method not found: {method}")

    def _list_tools(self) -> list[dict[str, Any]]:
        tools = []
        for tool in self.registry.list_tools():
            properties = {}
            required = []
            for parameter in tool.schema.parameters:
                properties[parameter.name] = {
                    "type": parameter.type,
                    "description": parameter.description,
                }
                if parameter.required:
                    required.append(parameter.name)

            tools.append(
                {
                    "name": tool.name,
                    "description": tool.description,
                    "inputSchema": {
                        "type": "object",
                        "properties": properties,
                        "required": required,
                    },
                    "annotations": {
                        "readOnlyHint": tool.read_only,
                    },
                }
            )
        return tools

    def _call_tool(
        self,
        request_id: Any,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        if not isinstance(params, dict) or not isinstance(params.get("name"), str):
            return self._error(request_id, -32602, "tools/call requires a tool name")

        arguments = params.get("arguments", {})
        if not isinstance(arguments, dict):
            return self._error(request_id, -32602, "arguments must be an object")

        try:
            execution = self.registry.execute(params["name"], arguments)
        except KeyError as error:
            return self._error(request_id, -32602, str(error))
        except Exception as error:
            return self._error(request_id, -32603, str(error))

        result = execution.to_dict()
        payload = result["result"]
        if not result["success"]:
            payload = {"error": result["error"]}
        return self._success(
            request_id,
            {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(payload),
                    }
                ],
                "isError": not result["success"],
                "structuredContent": payload,
            },
        )

    @staticmethod
    def _success(request_id: Any, result: dict[str, Any]) -> dict[str, Any]:
        return {"jsonrpc": "2.0", "id": request_id, "result": result}

    @staticmethod
    def _error(request_id: Any, code: int, message: str) -> dict[str, Any]:
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": code, "message": message},
        }


class MCPClient:
    """Minimal MCP consumer for request/response transports."""

    def __init__(self, transport: Callable[[dict[str, Any]], dict[str, Any] | None]):
        self.transport = transport
        self._request_id = 0

    def initialize(self) -> dict[str, Any]:
        return self._request("initialize", {})

    def list_tools(self) -> list[dict[str, Any]]:
        return self._request("tools/list", {}).get("tools", [])

    def call_tool(
        self,
        name: str,
        arguments: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self._request(
            "tools/call",
            {"name": name, "arguments": arguments or {}},
        )

    def _request(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        self._request_id += 1
        response = self.transport(
            {
                "jsonrpc": "2.0",
                "id": self._request_id,
                "method": method,
                "params": params,
            }
        )
        if not response:
            raise RuntimeError("MCP transport returned no response")
        if "error" in response:
            raise RuntimeError(response["error"]["message"])
        return response["result"]


def iter_stdio_requests(stream: TextIO) -> Iterator[dict[str, Any]]:
    for line in stream:
        if line.strip():
            yield json.loads(line)


def run_stdio_server(
    server: MCPServer,
    input_stream: TextIO = sys.stdin,
    output_stream: TextIO = sys.stdout,
) -> None:
    for request in iter_stdio_requests(input_stream):
        response = server.handle_request(request)
        if response is not None:
            output_stream.write(json.dumps(response) + "\n")
            output_stream.flush()
