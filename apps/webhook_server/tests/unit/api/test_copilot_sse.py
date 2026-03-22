"""
Tests for API-03: POST /api/v1/copilot/chat SSE streaming endpoint.
Uses TestClient with mocked copilot graph (no real LangGraph/OpenAI needed).
"""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from sharpedge_webhooks.copilot_rate_limit import reset_copilot_rate_limiter


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


@pytest.fixture(autouse=True)
def _reset_copilot_rate_limit_between_tests():
    """Isolate in-memory limiter + env defaults across tests."""
    reset_copilot_rate_limiter()
    yield
    reset_copilot_rate_limiter()


def test_copilot_sse_content_type_when_no_graph(client):
    """POST /api/v1/copilot/chat must return Content-Type: text/event-stream even when graph is None."""
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


async def _fake_sse_stream(*_args, **_kwargs):
    """Token stream using explicit event:message (matches Phase 4 SSE contract)."""
    yield "event: message\ndata: ok\n\n"
    yield "data: [DONE]\n\n"


async def _fake_sse_stream_with_copilot_tool(*_args, **_kwargs):
    yield "event: message\ndata: Hello\n\n"
    yield (
        'event: copilot_tool\ndata: {"phase":"start","name":"search_games",'
        '"summary":"search_games sport=NBA"}\n\n'
    )
    yield "event: message\ndata: world\n\n"
    yield (
        'event: copilot_tool\ndata: {"phase":"end","name":"search_games","summary":"done"}\n\n'
    )
    yield "data: [DONE]\n\n"


def test_copilot_sse_mock_emits_copilot_tool_frames(app, client):
    """Mocked stream includes event:copilot_tool with phase=start JSON (Phase 4 contract)."""
    app.state.copilot_persist_threads = True
    app.state.copilot_graph = object()
    with patch(
        "sharpedge_webhooks.routes.v1.copilot._stream_copilot",
        new=_fake_sse_stream_with_copilot_tool,
    ):
        response = client.post(
            "/api/v1/copilot/chat",
            json={"message": "hello", "thread_id": "t1"},
        )
    assert response.status_code == 200
    assert "event: copilot_tool" in response.text
    assert '"phase": "start"' in response.text or '"phase":"start"' in response.text
    assert "search_games" in response.text


def test_copilot_requires_thread_id_when_persistence_enabled(app, client):
    """When Postgres checkpointer is active, missing thread_id returns 400."""
    app.state.copilot_persist_threads = True
    app.state.copilot_graph = object()
    response = client.post("/api/v1/copilot/chat", json={"message": "hello"})
    assert response.status_code == 400


def test_copilot_rate_limit_second_request_returns_429(monkeypatch, client):
    """In-memory limit: second POST within the window returns 429."""
    monkeypatch.setenv("COPILOT_RATE_LIMIT_PER_MINUTE", "1")
    monkeypatch.delenv("COPILOT_RATE_BURST", raising=False)
    reset_copilot_rate_limiter()
    with patch(
        "sharpedge_webhooks.routes.v1.copilot.build_copilot_graph",
        return_value=None,
    ):
        first = client.post("/api/v1/copilot/chat", json={"message": "hello"})
        second = client.post("/api/v1/copilot/chat", json={"message": "again"})
    assert first.status_code == 200
    assert second.status_code == 429
    assert "Rate limit" in (second.json().get("detail") or "")


def test_copilot_streams_when_persistence_enabled_and_thread_id_present(app, client):
    """With persistence on, thread_id satisfies validation and SSE still works."""
    app.state.copilot_persist_threads = True
    app.state.copilot_graph = object()
    with patch(
        "sharpedge_webhooks.routes.v1.copilot._stream_copilot",
        new=_fake_sse_stream,
    ):
        response = client.post(
            "/api/v1/copilot/chat",
            json={"message": "hello", "thread_id": "client-thread-1"},
        )
    assert response.status_code == 200
    assert "text/event-stream" in response.headers.get("content-type", "")
    assert "data: [DONE]" in response.text
