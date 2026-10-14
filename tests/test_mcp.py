import io
import json

from devops_health_checker.mcp import MCPClient, MCPServer, run_stdio_server
from devops_health_checker.registry import ToolRegistry
from devops_health_checker.schemas import ToolParameter, ToolSchema


def create_registry():
    registry = ToolRegistry()
    registry.register(
        name="echo",
        description="Echo a message.",
        function=lambda message: {"message": message},
        schema=ToolSchema(
            name="echo",
            description="Echo a message.",
            parameters=[
                ToolParameter(
                    name="message",
                    type="string",
                    description="Message to echo.",
                    required=True,
                )
            ],
        ),
    )
    return registry


def test_mcp_lists_registered_tools() -> None:
    response = MCPServer(create_registry()).handle_request(
        {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}
    )

    assert response["result"]["tools"][0]["name"] == "echo"
    assert response["result"]["tools"][0]["inputSchema"]["required"] == ["message"]


def test_mcp_client_calls_validated_tool() -> None:
    server = MCPServer(create_registry())
    client = MCPClient(server.handle_request)

    assert client.initialize()["protocolVersion"] == "2024-11-05"
    result = client.call_tool("echo", {"message": "hello"})

    assert result["isError"] is False
    assert json.loads(result["content"][0]["text"]) == {"message": "hello"}


def test_mcp_returns_validation_error_without_executing_tool() -> None:
    server = MCPServer(create_registry())

    response = server.handle_request(
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {"name": "echo", "arguments": {"unexpected": 1}},
        }
    )

    assert response["result"]["isError"] is True
    assert "Unknown parameter" in response["result"]["content"][0]["text"]


def test_mcp_stdio_round_trip() -> None:
    server = MCPServer(create_registry())
    input_stream = io.StringIO(
        json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/list"}) + "\n"
    )
    output_stream = io.StringIO()

    run_stdio_server(server, input_stream, output_stream)

    response = json.loads(output_stream.getvalue())
    assert response["result"]["tools"][0]["name"] == "echo"
