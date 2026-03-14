"""Tests for AGENT-04: trim_conversation keeps message history within token budget."""
import pytest

from sharpedge_agent_pipeline.copilot.session import trim_conversation, MAX_TOKENS


@pytest.mark.xfail(strict=True, reason="Wave 1 not yet implemented")
def test_trim_conversation_under_limit():
    """Short messages (well under token limit) are NOT trimmed."""
    messages = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi! How can I help?"},
    ]
    result = trim_conversation(messages)
    assert len(result) == len(messages), "Short conversation must not be trimmed"


@pytest.mark.xfail(strict=True, reason="Wave 1 not yet implemented")
def test_trim_conversation_over_limit():
    """200 messages that exceed MAX_TOKENS are trimmed to stay under budget."""
    # Generate 200 messages with substantial content to exceed token limit
    messages = [
        {"role": "user" if i % 2 == 0 else "assistant", "content": "X " * 200}
        for i in range(200)
    ]
    result = trim_conversation(messages)
    # Must have fewer messages than input
    assert len(result) < len(messages), "Over-limit conversation must be trimmed"
    # Verify result is within token budget (approximate: 4 chars per token)
    total_chars = sum(len(m["content"]) for m in result)
    approx_tokens = total_chars // 4
    assert approx_tokens <= MAX_TOKENS, f"Trimmed result still exceeds MAX_TOKENS: {approx_tokens}"
