"""Redis caching layer for odds data."""

import json
import logging

import redis

from sharpedge_odds.constants import ODDS_CACHE_TTL

logger = logging.getLogger("sharpedge.odds.cache")


class OddsCache:
    """Redis-backed cache for odds data."""

    def __init__(self, redis_url: str) -> None:
        self._redis: redis.Redis | None = None
        self._redis_url = redis_url

    def _get_client(self) -> redis.Redis:
        if self._redis is None:
            try:
                self._redis = redis.from_url(self._redis_url, decode_responses=True)
                self._redis.ping()
            except Exception:
                logger.warning("Redis not available, caching disabled.")
                self._redis = None  # type: ignore[assignment]
                raise
        return self._redis

    def get(self, key: str) -> list[dict] | None:
        """Get cached data by key."""
        try:
            client = self._get_client()
            data = client.get(f"odds:{key}")
            if data:
                return json.loads(data)
        except Exception:
            pass
        return None

    def set(self, key: str, data: list[dict], ttl: int = ODDS_CACHE_TTL) -> None:
        """Cache data with TTL."""
        try:
            client = self._get_client()
            client.setex(f"odds:{key}", ttl, json.dumps(data, default=str))
        except Exception:
            logger.debug("Failed to cache odds data for key %s.", key)

    def invalidate(self, pattern: str = "*") -> None:
        """Invalidate cached data matching pattern."""
        try:
            client = self._get_client()
            keys = client.keys(f"odds:{pattern}")
            if keys:
                client.delete(*keys)
        except Exception:
            pass
