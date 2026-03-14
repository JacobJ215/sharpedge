"""Tests for AGENT-04: trim_conversation keeps message history within token budget."""
import tiktoken

from sharpedge_agent_pipeline.copilot.session import trim_conversation, MAX_TOKENS

_ENCODER = tiktoken.encoding_for_model("gpt-4o")
_MESSAGE_OVERHEAD = 4  # role + structural tokens per message


def _approx_tokens(messages: list[dict]) -> int:
    """Count actual tiktoken tokens for a message list."""
    return sum(len(_ENCODER.encode(str(m.get("content") or ""))) + _MESSAGE_OVERHEAD for m in messages)


def test_trim_conversation_under_limit():
    """Short messages (well under token limit) are NOT trimmed."""
    messages = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi! How can I help?"},
    ]
    result = trim_conversation(messages)
    assert len(result) == len(messages), "Short conversation must not be trimmed"


def test_trim_conversation_over_limit():
    """200 messages with content that exceeds MAX_TOKENS are trimmed to stay within budget."""
    # Each message contains 1000 varied words (~1000 tokens + overhead).
    # 200 messages * ~1000 tokens = ~200,000 tokens >> 80,000 MAX_TOKENS.
    content = " ".join(f"tok{i}" for i in range(1000))
    messages = [
        {"role": "user" if i % 2 == 0 else "assistant", "content": content}
        for i in range(200)
    ]
    # Verify our test data actually exceeds the budget
    assert _approx_tokens(messages) > MAX_TOKENS, "Test data must exceed MAX_TOKENS"

    result = trim_conversation(messages)
    # Must have fewer messages than input
    assert len(result) < len(messages), "Over-limit conversation must be trimmed"
    # Verify result is actually within token budget using tiktoken
    actual_tokens = _approx_tokens(result)
    assert actual_tokens <= MAX_TOKENS, f"Trimmed result still exceeds MAX_TOKENS: {actual_tokens}"
