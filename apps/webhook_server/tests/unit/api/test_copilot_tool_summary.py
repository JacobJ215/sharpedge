"""Unit tests for copilot SSE tool input summarization (Phase 4 allowlist)."""

from sharpedge_webhooks.routes.v1.copilot import _summarize_tool_input


def test_summarize_tool_input_allowlists_keys():
    s = _summarize_tool_input(
        "search_games",
        {"sport": "NBA", "game_id": "abc123", "user_id": "secret", "extra": "nope"},
    )
    assert "NBA" in s
    assert "abc123" in s
    assert "secret" not in s
    assert "nope" not in s
    assert s.startswith("search_games")
    assert len(s) <= 120


def test_summarize_tool_input_non_dict():
    assert _summarize_tool_input("x", None) == "x"
    assert len(_summarize_tool_input("tool", [])) <= 120
