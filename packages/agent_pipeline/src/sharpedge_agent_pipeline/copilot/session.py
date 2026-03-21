"""Session management for BettingCopilot — context-window-safe conversation trimming.

Keeps total conversation token count within GPT-4o's context window.
Uses tiktoken for accurate token counting and trims oldest non-system messages first.
"""

import logging
from typing import Any

import tiktoken

__all__ = ["MAX_TOKENS", "trim_conversation"]

MAX_TOKENS = 80_000  # GPT-4o has 128k context; 80k leaves buffer for tool call responses

_logger = logging.getLogger("sharpedge.copilot.session")

# Per-message overhead for chat completion API (role name + structural tokens)
_MESSAGE_OVERHEAD = 4


def _count_tokens(text: str, encoder: tiktoken.Encoding) -> int:
    """Count tokens in a string using the provided encoder."""
    return len(encoder.encode(text))


def _message_tokens(msg: dict[str, Any], encoder: tiktoken.Encoding) -> int:
    """Count total tokens for one message dict including overhead."""
    content = msg.get("content") or ""
    return _count_tokens(str(content), encoder) + _MESSAGE_OVERHEAD


def trim_conversation(
    messages: list[dict[str, Any]],
    model: str = "gpt-5.4-mini-2026-03-17",
) -> list[dict[str, Any]]:
    """Trim message history to fit within the token budget.

    Preserves any system message and trims oldest non-system messages
    when total token count exceeds MAX_TOKENS.

    Args:
        messages: List of message dicts with 'role' and 'content' keys.
        model: OpenAI model name used to select the correct tokenizer.

    Returns:
        Message list with total token count <= MAX_TOKENS.
        Returns the original list unchanged if already within budget.
    """
    if not messages:
        return messages

    try:
        encoder = tiktoken.encoding_for_model(model)
    except KeyError:
        encoder = tiktoken.get_encoding("cl100k_base")

    # Separate system message (always kept) from conversation messages
    system_msgs = [m for m in messages if m.get("role") == "system"]
    conv_msgs = [m for m in messages if m.get("role") != "system"]

    # Count total tokens
    total = sum(_message_tokens(m, encoder) for m in messages)

    if total <= MAX_TOKENS:
        return messages

    # Trim oldest conversation messages until within budget
    system_tokens = sum(_message_tokens(m, encoder) for m in system_msgs)
    budget = MAX_TOKENS - system_tokens

    kept: list[dict[str, Any]] = []
    # Walk from newest to oldest, keep as many as fit
    accumulated = 0
    for msg in reversed(conv_msgs):
        msg_tokens = _message_tokens(msg, encoder)
        if accumulated + msg_tokens <= budget:
            kept.insert(0, msg)
            accumulated += msg_tokens

    result = system_msgs + kept
    _logger.warning("Trimming conversation: %d -> %d messages", len(messages), len(result))
    return result
