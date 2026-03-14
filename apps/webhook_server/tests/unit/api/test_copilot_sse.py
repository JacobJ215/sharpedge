"""
Tests for API-03: POST /api/v1/copilot/chat SSE streaming endpoint.
Uses TestClient with mocked copilot graph (no real LangGraph/OpenAI needed).
"""
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def app():
    """Create a minimal FastAPI app with just the copilot router mounted."""
    from fastapi import FastAPI
    from sharpedge_webhooks.routes.v1.copilot import router

    _app = FastAPI()
    _app.include_router(router, prefix="/api/v1")
    return _app


@pytest.fixture
def client(app):
    return TestClient(app, raise_server_exceptions=True)


def test_copilot_sse_content_type_when_no_graph(client):
    """POST /api/v1/copilot/chat must return Content-Type: text/event-stream even when graph is None."""
    with patch(
        "sharpedge_webhooks.routes.v1.copilot._stream_copilot",
        side_effect=None,
    ):
        # Patch build_copilot_graph to return None (no OPENAI_API_KEY)
        with patch(
            "sharpedge_webhooks.routes.v1.copilot.build_copilot_graph",
            return_value=None,
        ):
            response = client.post("/api/v1/copilot/chat", json={"message": "hello"})

    assert response.status_code == 200
    assert "text/event-stream" in response.headers.get("content-type", "")


def test_copilot_sse_streams_data_lines_when_no_graph(client):
    """POST /api/v1/copilot/chat response body must contain 'data:' lines (SSE format) even in fallback mode."""
    with patch(
        "sharpedge_webhooks.routes.v1.copilot.build_copilot_graph",
        return_value=None,
    ):
        response = client.post("/api/v1/copilot/chat", json={"message": "hello"})

    assert response.status_code == 200
    assert "data:" in response.text


def test_copilot_sse_sends_done_terminator(client):
    """POST /api/v1/copilot/chat must emit 'data: [DONE]' as the final SSE event."""
    with patch(
        "sharpedge_webhooks.routes.v1.copilot.build_copilot_graph",
        return_value=None,
    ):
        response = client.post("/api/v1/copilot/chat", json={"message": "hello"})

    assert "data: [DONE]" in response.text
