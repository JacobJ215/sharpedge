"""TradingConfig — loads and validates trading parameters from Supabase."""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

# Hard bounds for all config parameters
_BOUNDS: dict[str, tuple[float, float]] = {
    "confidence_threshold": (0.01, 0.10),
    "kelly_fraction": (0.10, 0.50),
    "max_category_exposure": (0.10, 0.50),
    "max_total_exposure": (0.20, 0.60),
    "daily_loss_limit": (0.05, 0.20),
    "min_liquidity": (100.0, 10_000.0),
    "min_edge": (0.01, 0.20),
}

# Defaults used if Supabase is unavailable or key is missing
_DEFAULTS: dict[str, float] = {
    "confidence_threshold": 0.03,
    "kelly_fraction": 0.25,
    "max_category_exposure": 0.20,
    "max_total_exposure": 0.40,
    "daily_loss_limit": 0.10,
    "min_liquidity": 500.0,
    "min_edge": 0.03,
}


def _clamp(key: str, value: float) -> float:
    lo, hi = _BOUNDS[key]
    clamped = max(lo, min(hi, value))
    if clamped != value:
        logger.warning("Config %s=%s clamped to [%s, %s] → %s", key, value, lo, hi, clamped)
    return clamped


@dataclass(frozen=True)
class TradingConfig:
    confidence_threshold: float
    kelly_fraction: float
    max_category_exposure: float
    max_total_exposure: float
    daily_loss_limit: float
    min_liquidity: float
    min_edge: float

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "TradingConfig":
        """Build from a raw key→value dict, applying bounds and defaults."""
        values: dict[str, float] = {}
        for key, default in _DEFAULTS.items():
            try:
                values[key] = _clamp(key, float(raw.get(key, default)))
            except (TypeError, ValueError):
                logger.warning("Config %s has invalid value %r, using default %s", key, raw.get(key), default)
                values[key] = default
        return cls(**values)

    @classmethod
    def defaults(cls) -> "TradingConfig":
        """Return a config object with all default values (used as fallback)."""
        return cls(**_DEFAULTS)


def load_config() -> TradingConfig:
    """Load TradingConfig from Supabase trading_config table.

    Falls back to defaults if Supabase is unavailable.
    """
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_SERVICE_KEY")

    if not supabase_url or not supabase_key:
        logger.warning("SUPABASE_URL or SUPABASE_SERVICE_KEY not set — using default config")
        return TradingConfig.defaults()

    try:
        from supabase import create_client  # type: ignore[import]

        client = create_client(supabase_url, supabase_key)
        response = client.table("trading_config").select("key,value").execute()
        rows = response.data or []
        raw = {row["key"]: row["value"] for row in rows}
        config = TradingConfig.from_dict(raw)
        logger.info("Loaded trading config from Supabase: %s", config)
        return config
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to load trading config from Supabase: %s — using defaults", exc)
        return TradingConfig.defaults()
