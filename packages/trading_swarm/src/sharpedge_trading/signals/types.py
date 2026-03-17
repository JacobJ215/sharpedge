"""Signal types returned by all signal clients."""
from __future__ import annotations
from dataclasses import dataclass


@dataclass
class RawSignal:
    source: str       # 'reddit', 'twitter', 'rss_ap', 'rss_reuters', etc.
    text: str         # headline or post title/body snippet
    age_seconds: float  # seconds since published
    confidence: float   # 0-1 source reliability weight
