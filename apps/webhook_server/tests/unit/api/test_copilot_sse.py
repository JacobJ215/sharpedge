"""
RED stubs for API-03: POST /api/v1/copilot/chat SSE streaming endpoint tests.
Import will fail until routes/v1/copilot is implemented — that is intentional.
"""
import pytest

# This import does not exist yet — ImportError is the RED state.
# Tests are skipped so collection succeeds without failures.
# from sharpedge_webhooks.routes.v1.copilot import router  # noqa: F401


@pytest.mark.skip(reason="RED — routes/v1/copilot not yet implemented")
def test_copilot_sse_content_type():
    """POST /api/v1/copilot/chat must return Content-Type: text/event-stream."""
    from httpx import Client  # pragma: no cover
    client = Client(base_url="http://testserver")  # pragma: no cover
    response = client.post(  # pragma: no cover
        "/api/v1/copilot/chat",
        json={"message": "hello"},
        headers={"Authorization": "Bearer <valid_jwt>"},
    )
    assert response.status_code == 200  # pragma: no cover
    assert "text/event-stream" in response.headers.get("content-type", "")  # pragma: no cover


@pytest.mark.skip(reason="RED — routes/v1/copilot not yet implemented")
def test_copilot_sse_streams_data():
    """POST /api/v1/copilot/chat response body must start with 'data:' (SSE format)."""
    from httpx import Client  # pragma: no cover
    client = Client(base_url="http://testserver")  # pragma: no cover
    response = client.post(  # pragma: no cover
        "/api/v1/copilot/chat",
        json={"message": "hello"},
        headers={"Authorization": "Bearer <valid_jwt>"},
    )
    assert response.status_code == 200  # pragma: no cover
    assert response.text.startswith("data:")  # pragma: no cover
