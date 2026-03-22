"""In-memory sliding-window rate limit for POST /api/v1/copilot/chat.

Per-process only; horizontal scale needs a shared store (e.g. Redis) later.
Env:
  COPILOT_RATE_LIMIT_PER_MINUTE — max requests per rolling 60s window (default 20).
  COPILOT_RATE_BURST — optional extra slots added to that cap (e.g. 5 → 25 total).
"""

from __future__ import annotations

import asyncio
import os
import time
from collections import deque

# Grep / ops: primary env knobs for copilot chat throttling
COPILOT_RATE_LIMIT_PER_MINUTE_ENV = "COPILOT_RATE_LIMIT_PER_MINUTE"
COPILOT_RATE_BURST_ENV = "COPILOT_RATE_BURST"

_DEFAULT_PER_MINUTE = 20
_WINDOW_SECONDS = 60.0

_limiter: _SlidingWindowLimiter | None = None
_limiter_lock = asyncio.Lock()


def _max_requests_for_window() -> int:
    base = int(os.environ.get(COPILOT_RATE_LIMIT_PER_MINUTE_ENV, str(_DEFAULT_PER_MINUTE)))
    burst_raw = os.environ.get(COPILOT_RATE_BURST_ENV)
    if burst_raw is not None and str(burst_raw).strip() != "":
        return max(1, base + max(0, int(burst_raw)))
    return max(1, base)


class _SlidingWindowLimiter:
    """Async-safe sliding window: at most N timestamps in the last window_seconds."""

    def __init__(self, window_seconds: float) -> None:
        self._window_seconds = window_seconds
        self._buckets: dict[str, deque[float]] = {}
        self._inner = asyncio.Lock()

    async def allow(self, key: str) -> bool:
        max_requests = _max_requests_for_window()
        async with self._inner:
            now = time.monotonic()
            dq = self._buckets.setdefault(key, deque())
            cutoff = now - self._window_seconds
            while dq and dq[0] < cutoff:
                dq.popleft()
            if len(dq) >= max_requests:
                return False
            dq.append(now)
            return True


async def _get_limiter() -> _SlidingWindowLimiter:
    global _limiter
    async with _limiter_lock:
        if _limiter is None:
            _limiter = _SlidingWindowLimiter(_WINDOW_SECONDS)
        return _limiter


def reset_copilot_rate_limiter() -> None:
    """Clear limiter state (tests only)."""
    global _limiter
    _limiter = None


def client_rate_limit_key(request, user_id: str | None) -> str:
    """Stable key: authenticated user id, else first X-Forwarded-For hop or client host."""
    if user_id:
        return f"uid:{user_id}"
    fwd = request.headers.get("x-forwarded-for") or request.headers.get("X-Forwarded-For")
    if fwd:
        return f"ip:{fwd.split(',')[0].strip()}"
    client = request.client
    host = client.host if client else "unknown"
    return f"ip:{host}"


async def enforce_copilot_rate_limit(request, user_id: str | None) -> None:
    """Raise HTTPException(429) when the key is over the window cap."""
    from fastapi import HTTPException

    key = client_rate_limit_key(request, user_id)
    limiter = await _get_limiter()
    if not await limiter.allow(key):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
