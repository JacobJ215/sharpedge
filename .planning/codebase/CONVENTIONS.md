# Coding Conventions

**Analysis Date:** 2026-03-13

## Naming Patterns

**Files:**
- Python source files use `snake_case`: `odds_math.py`, `rate_limiter.py`
- Package directories match import names: `sharpedge_bot`, `sharpedge_db`, `sharpedge_shared`
- Module organization by domain: `/queries/`, `/routes/`, `/agents/`, `/middleware/`, `/utils/`

**Functions:**
- All functions use `snake_case`: `american_to_decimal()`, `calculate_kelly()`, `create_game_analyst()`
- Async functions clearly named with `async` keyword: `async def run_game_analysis()`
- Private helper functions prefixed with underscore: `_sync_discord_role()`, `_format_limit_message()`
- Functions have clear, descriptive names indicating their action: `get_or_create_user()`, `record_usage()`

**Variables:**
- Local variables use `snake_case`: `discord_id`, `subscription_id`, `true_probability`
- Constants use `UPPER_SNAKE_CASE`: `RATE_LIMITS`, `TIER_PRICES`, `COLOR_SUCCESS`
- Type-annotated with hints at declaration point
- Boolean variables prefixed with `is_` or `has_`: `is_positive_ev`, `is_production`, `is_calibrated`

**Types:**
- Enums inherit from `StrEnum` for string-based enums: `class Sport(StrEnum)`, `class BetResult(StrEnum)`
- Dataclasses use `@dataclass` decorator with frozen=True for immutable constants: `@dataclass(frozen=True)`
- Type unions use `|` syntax: `str | None`, `Decimal | None` (Python 3.10+ style)
- Required imports at top: `from typing import Any`, implicit for Optional types

## Code Style

**Formatting:**
- Tool: `ruff` (code formatter and linter)
- Line length: 100 characters (configured in `ruff.toml`)
- Quote style: Double quotes (`"`) for all strings
- Indentation: Spaces (4 spaces per level)

**Linting:**
- Tool: `ruff` with comprehensive rule set
- Active rule sets: E (errors), W (warnings), F (flakes), I (isort), N (naming), UP (upgrades), B (bugbear), SIM (simplify), T20 (print statements), TCH (type checking), RUF (ruff-specific)
- Ignored: E501 (line length handled by formatter)

## Import Organization

**Order:**
1. Standard library imports: `import os`, `from datetime import datetime`, `from typing import Any`
2. Third-party imports: `import discord`, `from pydantic import BaseModel`, `from fastapi import FastAPI`
3. First-party imports: `from sharpedge_bot.agents.tools import ...`, `from sharpedge_db.models import ...`

**Path Aliases:**
- No path aliases (use absolute imports)
- First-party packages defined in `ruff.toml`: `sharpedge_bot`, `sharpedge_webhooks`, `sharpedge_db`, `sharpedge_models`, `sharpedge_odds`, `sharpedge_shared`
- Imports use full module path: `from sharpedge_db.models import User`, not relative paths

**Example:**
```python
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import discord
import httpx
from fastapi import APIRouter, HTTPException, Request

from sharpedge_db.queries.users import get_user_by_discord_id
from sharpedge_shared.types import Tier
```

## Error Handling

**Patterns:**
- Custom exception hierarchy in `sharpedge_shared.errors`: base `SharpEdgeError` with specialized subclasses
- Specific exceptions for known failure modes: `RateLimitExceeded`, `TierRestricted`, `ExternalAPIError`, `InsufficientData`
- HTTP endpoints raise `HTTPException` with status codes: `raise HTTPException(status_code=400, detail="...")`
- Exceptions carry context: `RateLimitExceeded(feature="analysis", reset_at=datetime.now())`

**Example from `stripe.py`:**
```python
try:
    event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
except ValueError:
    raise HTTPException(status_code=400, detail="Invalid payload")
except stripe.error.SignatureVerificationError:
    raise HTTPException(status_code=400, detail="Invalid signature")
```

## Logging

**Framework:** Python's standard `logging` module

**Patterns:**
- Logger created per module: `logger = logging.getLogger("sharpedge.agents.game_analyst")`
- Naming convention: `sharpedge.<domain>.<function>`
- Levels used appropriately: `logger.info()` for state changes, `logger.warning()` for issues
- User-actionable information in logs: `logger.info("User %s upgraded to %s", discord_id, tier)`

**Example from `stripe.py`:**
```python
logger = logging.getLogger("sharpedge.webhooks.stripe")
logger.info("Stripe event: %s", event_type)
logger.warning("Checkout session missing discord_id metadata.")
logger.info("User %s upgraded to %s (sub: %s)", discord_id, tier, subscription_id)
```

## Comments

**When to Comment:**
- Algorithm explanations: complex math (Kelly criterion, EV calculation)
- Non-obvious business logic: why a check exists, not what the code does
- Warnings about edge cases: "never recommend negative sizing", "Resets to free on cancellation"
- Disclaim limitations: "Confidence metrics are only as good as our calibration data"

**JSDoc/TSDoc:**
- Google-style docstrings for all public functions
- Format: description, Args section, Returns section
- Example from `odds_math.py`:
```python
def american_to_decimal(odds: int) -> Decimal:
    """Convert American odds to decimal odds.

    +150 → 2.50 (win $150 on $100)
    -110 → 1.909 (win $90.91 on $100)
    """
```

**Module-level docstrings:**
- Single-line at top for simple modules
- Multi-line with purpose statement and capabilities for complex modules (e.g., `ev_calculator.py`)

## Function Design

**Size:**
- Keep functions under 50 lines (observed pattern in codebase)
- Complex logic broken into private helpers: `_sync_discord_role()`, `_tier_from_items()`

**Parameters:**
- Use explicit keyword arguments for clarity: `async def run_game_analysis(game_query: str, sport: str = "")`
- Default values on optional params: `async def calculate_kelly(..., bankroll: Decimal | None = None)`
- No positional-only parameters; all parameters named

**Return Values:**
- Always type-annotated: `def american_to_decimal(odds: int) -> Decimal`
- Async functions return the unwrapped type: `async def run_game_analysis(...) -> str`
- Dataclass returns for complex results: `-> KellyResult`, `-> EVCalculation`

## Module Design

**Exports:**
- Barrel files use `__all__` for explicit exports: `__init__.py` in `sharpedge_db` lists exported classes and modules
- Public APIs documented in `__all__`: models, client, query modules

**Barrel Files:**
- Used strategically for packages with multiple modules
- Example from `sharpedge_db/__init__.py`:
```python
from sharpedge_db.client import get_supabase_client
from sharpedge_db.models import Alert, Bet, OddsHistory, Projection, Usage, User
__all__ = [
    "Alert", "Bet", "OddsHistory", "Projection", "Usage", "User",
    "get_supabase_client", "users", "bets", "usage", ...
]
```

**Cross-module imports:**
- Import specific items: `from sharpedge_db.models import Bet`
- Import modules: `from sharpedge_db.queries import users`
- Chain imports within query modules for convenience

---

*Convention analysis: 2026-03-13*
