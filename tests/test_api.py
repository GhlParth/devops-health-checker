import json
import threading
import urllib.error
import urllib.request

from devops_health_checker.api import create_api_server
from devops_health_checker.tools.registry import create_tool_registry


def request_json(url, method="GET", payload=None, headers=None):
    body = None
    request_headers = headers or {}
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        request_headers["Content-Type"] = "application/json"
    request = urllib.request.Request(
        url,
        data=body,
        headers=request_headers,
        method=method,
    )
    try:
        with urllib.request.urlopen(request) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read())


def start_server(api_token=None):
    server = create_api_server(
        host="127.0.0.1",
        port=0,
        registry=create_tool_registry(),
        api_token=api_token,
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{server.server_port}"
    return server, thread, base_url


def test_api_health_tools_and_knowledge_endpoints():
    server, thread, base_url = start_server()

    try:
        assert request_json(base_url + "/health")[1] == {"status": "ok"}
        status, tools = request_json(base_url + "/tools")
        assert status == 200
        assert "search_devops_knowledge" in {
            tool["name"] for tool in tools["tools"]
        }
        status, knowledge = request_json(
            base_url + "/knowledge",
            method="POST",
            payload={"query": "pod logs"},
        )
        assert status == 200
        assert knowledge["result"]["match_count"] > 0
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_api_requires_token_when_configured():
    server, thread, base_url = start_server(api_token="test-token")

    try:
        status, body = request_json(
            base_url + "/knowledge",
            method="POST",
            payload={"query": "pod"},
        )
        assert status == 401
        assert body["error"] == "Unauthorized"

        status, body = request_json(
            base_url + "/knowledge",
            method="POST",
            payload={"query": "pod"},
            headers={"Authorization": "Bearer test-token"},
        )
        assert status == 200
        assert body["success"] is True
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_api_rejects_invalid_knowledge_request():
    server, thread, base_url = start_server()

    try:
        status, body = request_json(
            base_url + "/knowledge",
            method="POST",
            payload={"query": ""},
        )
        assert status == 400
        assert "non-empty" in body["error"]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
