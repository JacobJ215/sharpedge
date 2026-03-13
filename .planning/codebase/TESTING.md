# Testing

> Test framework, structure, patterns, mocking conventions, and coverage approach.

---

## Framework & Tools

| Tool | Version | Purpose |
|------|---------|---------|
| `pytest` | >=8.0 | Test runner |
| `pytest-asyncio` | >=0.24 | Async test support |
| `pytest-mock` | >=3.14 | Mocking via `mocker` fixture |
| `mypy` | >=1.14 | Static type checking |
| `ruff` | >=0.9 | Linting (also catches test smells) |

Config lives in root `pyproject.toml` under `[tool.uv]` dev-dependencies.

---

## Current Coverage

**Zero tests exist.** There are no test files anywhere in the codebase. This is the single biggest quality gap.

---

## Recommended Structure

```
tests/
├── unit/
│   ├── models/
│   │   ├── test_ev_calculator.py
│   │   ├── test_no_vig.py
│   │   ├── test_arbitrage.py
│   │   └── test_backtesting.py
│   ├── analytics/
│   │   ├── test_movement.py
│   │   ├── test_value_scanner.py
│   │   └── test_key_numbers.py
│   └── shared/
│       └── test_types.py
├── integration/
│   ├── test_odds_client.py
│   ├── test_database_queries.py
│   └── test_bot_commands.py
└── conftest.py
```

---

## Async Pattern

All Discord bot code and external API clients are async. Use `pytest-asyncio`:

```python
import pytest

@pytest.mark.asyncio
async def test_something_async():
    result = await some_async_function()
    assert result is not None
```

---

## Mocking External Services

Use `pytest-mock` (`mocker` fixture) to mock Supabase, OpenAI, and external API clients:

```python
def test_ev_calculation(mocker):
    mock_odds = mocker.patch("sharpedge_odds.client.OddsAPIClient.get_odds")
    mock_odds.return_value = [...]
    result = calculate_ev(...)
    assert result.ev_pct > 0
```

For async clients:
```python
@pytest.mark.asyncio
async def test_kalshi_scan(mocker):
    mock_client = mocker.AsyncMock()
    mock_client.get_active_markets.return_value = [...]
    ...
```

---

## Running Tests

```bash
# All tests
uv run pytest

# Specific package
uv run pytest tests/unit/models/

# With coverage (once tests exist)
uv run pytest --cov=packages/ --cov-report=html

# Type checking
uv run mypy packages/ apps/
```

---

## Priority Test Targets (highest risk, no coverage)

1. `packages/models/src/sharpedge_models/ev_calculator.py` — core EV math, Bayesian confidence
2. `packages/models/src/sharpedge_models/arbitrage.py` — financial calculations
3. `packages/models/src/sharpedge_models/no_vig.py` — no-vig fair odds math
4. `packages/analytics/src/sharpedge_analytics/value_scanner.py` — value detection pipeline
5. `packages/analytics/src/sharpedge_analytics/movement.py` — line movement classification
