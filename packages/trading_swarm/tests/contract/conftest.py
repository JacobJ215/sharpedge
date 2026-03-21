"""Shared fixtures for contract tests — all real API calls, all skipped without credentials."""
import os

import pytest


def _missing(*env_vars: str) -> str | None:
    """Return a skip reason if any env var is missing, else None."""
    missing = [v for v in env_vars if not os.environ.get(v)]
    if missing:
        return f"Missing env vars: {', '.join(missing)}"
    return None


@pytest.fixture(scope="session")
def require_kalshi():
    reason = _missing("KALSHI_API_KEY")
    if reason:
        pytest.skip(reason)


@pytest.fixture(scope="session")
def require_anthropic():
    reason = _missing("ANTHROPIC_API_KEY")
    if reason:
        pytest.skip(reason)


@pytest.fixture(scope="session")
def require_supabase():
    reason = _missing("SUPABASE_URL", "SUPABASE_SERVICE_KEY")
    if reason:
        pytest.skip(reason)
