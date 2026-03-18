"""Real-time cross-platform arbitrage scanner for prediction markets.

Connects Kalshi and Polymarket WebSocket streams, maintains a registry
of matched market pairs, and fires callbacks whenever a fee-adjusted
probability gap exceeds the configured threshold (default 2%).

Usage::

    from sharpedge_feeds.kalshi_stream import KalshiStreamClient
    from sharpedge_feeds.polymarket_stream import PolymarketStreamClient
    from sharpedge_analytics.prediction_markets.realtime_scanner import (
        RealtimeArbScanner, MarketPair,
    )

    scanner = RealtimeArbScanner(min_gap_pct=2.0, bankroll=10_000.0)
    scanner.register_pair(MarketPair(
        canonical_id="chiefs_sb",
        description="Chiefs win Super Bowl",
        kalshi_ticker="KXNFL-25-KC",
        polymarket_yes_token="0xabc...",
    ))

    @scanner.on_arb
    async def handle_arb(opp):
        print(f"ARB {opp.net_profit_pct:.2f}% — {opp.description}")
        print(opp.sizing)

    kalshi_stream = KalshiStreamClient(config)
    poly_stream = PolymarketStreamClient()
    scanner.wire(kalshi_stream, poly_stream)

    await asyncio.gather(
        kalshi_stream.run(),
        poly_stream.run(),
    )
"""

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime

from .fees import Platform, calculate_fee_adjusted_price

logger = logging.getLogger(__name__)

ArbCallback = Callable[["LiveArbOpportunity"], Awaitable[None]]


@dataclass
class MarketPair:
    """A canonical event matched across Kalshi and Polymarket.

    For binary markets (YES/NO):
      - Set ``polymarket_yes_token`` to the YES outcome token ID.
      - ``polymarket_no_token`` is optional — if omitted the NO ask is
        derived as ``1 - poly_yes_ask``.

    For Kalshi, ``ticker`` maps to a single binary market where
    yes_ask / no_ask are directly available from the ticker channel.
    """

    canonical_id: str
    description: str
    kalshi_ticker: str
    polymarket_yes_token: str
    polymarket_no_token: str | None = None

    # Live prices (updated by scanner on every incoming tick)
    kalshi_yes_ask: float = 0.0
    kalshi_yes_bid: float = 0.0
    kalshi_no_ask: float = 0.0
    poly_yes_ask: float = 0.0
    poly_no_ask: float = 0.0

    last_kalshi_ts: float = 0.0
    last_poly_ts: float = 0.0


@dataclass
class LiveArbOpportunity:
    """A detected live arbitrage opportunity with sizing instructions.

    ``sizing["instructions"]`` contains two legs — execute both
    simultaneously to lock the guaranteed profit.
    """

    canonical_id: str
    description: str

    buy_yes_platform: str
    buy_yes_price: float
    buy_no_platform: str
    buy_no_price: float

    gross_profit_pct: float
    net_profit_pct: float   # after platform fees

    sizing: dict            # total_stake, guaranteed_profit, roi_pct, instructions
    detected_at: datetime = field(default_factory=datetime.now)
    estimated_window_seconds: int = 30


class RealtimeArbScanner:
    """Event-driven arb scanner wired to Kalshi + Polymarket streams.

    Every incoming price tick triggers an immediate check of both
    directions for the affected market pair. If the fee-adjusted gap
    exceeds ``min_gap_pct``, all registered callbacks fire.

    Fee math uses the actual Kalshi probability-weighted formula
    (0.07 × contracts × price × (1-price)) rather than a fixed rate.
    """

    def __init__(
        self,
        min_gap_pct: float = 2.0,
        bankroll: float = 10_000.0,
        max_bet_pct: float = 0.05,
        staleness_threshold_s: float = 5.0,
    ) -> None:
        self.min_gap_pct = min_gap_pct
        self.bankroll = bankroll
        self.max_bet_pct = max_bet_pct
        self.staleness_threshold_s = staleness_threshold_s

        self._pairs: dict[str, MarketPair] = {}           # canonical_id → pair
        self._kalshi_idx: dict[str, str] = {}             # kalshi_ticker → canonical_id
        self._poly_yes_idx: dict[str, str] = {}           # token_id → canonical_id
        self._poly_no_idx: dict[str, str] = {}            # token_id → canonical_id
        self._callbacks: list[ArbCallback] = []
        self._poly_client: object | None = None           # ARB-04: injected for NO token CLOB fetch

        # Rate-limit: don't re-fire the same pair more than once per second
        self._last_fired: dict[str, float] = {}
        self._fire_cooldown: float = 1.0

    # ── Registration ───────────────────────────────────────────────────────

    def register_pair(self, pair: MarketPair) -> None:
        """Add a market pair to the scanner."""
        self._pairs[pair.canonical_id] = pair
        self._kalshi_idx[pair.kalshi_ticker] = pair.canonical_id
        self._poly_yes_idx[pair.polymarket_yes_token] = pair.canonical_id
        if pair.polymarket_no_token:
            self._poly_no_idx[pair.polymarket_no_token] = pair.canonical_id

    def register_pairs(self, pairs: list[MarketPair]) -> None:
        for pair in pairs:
            self.register_pair(pair)

    def on_arb(self, callback: ArbCallback) -> ArbCallback:
        """Register a callback. Can be used as a decorator."""
        self._callbacks.append(callback)
        return callback

    def wire(self, kalshi_stream: object, poly_stream: object) -> None:
        """Attach tick handlers to both stream clients.

        Accepts any object with an ``on_tick(callback)`` method —
        i.e. ``KalshiStreamClient`` and ``PolymarketStreamClient``.
        Also calls ``subscribe()`` on each stream with the registered
        tickers / token IDs.
        """
        kalshi_tickers = list(self._kalshi_idx.keys())
        poly_tokens = list(self._poly_yes_idx.keys()) + list(self._poly_no_idx.keys())

        kalshi_stream.subscribe(kalshi_tickers)
        poly_stream.subscribe(poly_tokens)

        kalshi_stream.on_tick(self._on_kalshi_tick)
        poly_stream.on_tick(self._on_poly_tick)

        logger.info(
            "RealtimeArbScanner wired: %d Kalshi tickers, %d Poly tokens",
            len(kalshi_tickers),
            len(poly_tokens),
        )

    # ── Tick handlers ──────────────────────────────────────────────────────

    async def _on_kalshi_tick(self, tick: object) -> None:
        cid = self._kalshi_idx.get(tick.ticker)  # type: ignore[attr-defined]
        if not cid:
            return
        pair = self._pairs[cid]
        pair.kalshi_yes_ask = tick.yes_ask  # type: ignore[attr-defined]
        pair.kalshi_yes_bid = tick.yes_bid  # type: ignore[attr-defined]
        pair.kalshi_no_ask = tick.no_ask    # type: ignore[attr-defined]
        pair.last_kalshi_ts = tick.timestamp  # type: ignore[attr-defined]
        await self._check_pair(pair)

    async def _on_poly_tick(self, tick: object) -> None:
        token_id: str = tick.token_id  # type: ignore[attr-defined]
        cid = self._poly_yes_idx.get(token_id) or self._poly_no_idx.get(token_id)
        if not cid:
            return
        pair = self._pairs[cid]
        if token_id in self._poly_yes_idx:
            pair.poly_yes_ask = tick.best_ask  # type: ignore[attr-defined]
        else:
            pair.poly_no_ask = tick.best_ask   # type: ignore[attr-defined]
        pair.last_poly_ts = tick.timestamp  # type: ignore[attr-defined]
        await self._check_pair(pair)

    # ── Core detection ─────────────────────────────────────────────────────

    async def _check_pair(self, pair: MarketPair) -> None:
        """Check both arb directions on every price update."""
        if not (pair.kalshi_yes_ask > 0 and pair.poly_yes_ask > 0):
            return  # insufficient data

        # ARB-03: staleness guard — only fires when both sides have received at least one tick
        if pair.last_kalshi_ts > 0 and pair.last_poly_ts > 0:
            now = time.time()
            kalshi_age = now - pair.last_kalshi_ts
            poly_age = now - pair.last_poly_ts
            if kalshi_age > self.staleness_threshold_s:
                logger.warning(
                    "Stale Kalshi data for %s (%.1fs old) — skipping pair",
                    pair.canonical_id, kalshi_age,
                )
                return
            if poly_age > self.staleness_threshold_s:
                logger.warning(
                    "Stale Polymarket data for %s (%.1fs old) — skipping pair",
                    pair.canonical_id, poly_age,
                )
                return

        # Derive missing prices where possible
        poly_no_ask = pair.poly_no_ask if pair.poly_no_ask > 0 else (1.0 - pair.poly_yes_ask)
        kalshi_no_ask = pair.kalshi_no_ask if pair.kalshi_no_ask > 0 else (1.0 - pair.kalshi_yes_bid)

        # Direction A: buy YES on Kalshi, buy NO on Polymarket
        opp = self._evaluate(
            pair,
            yes_price=pair.kalshi_yes_ask, yes_platform=Platform.KALSHI,
            no_price=poly_no_ask,          no_platform=Platform.POLYMARKET,
        )
        if opp:
            await self._fire(opp)
            return  # one direction is enough — don't double-fire same pair

        # Direction B: buy YES on Polymarket, buy NO on Kalshi
        opp = self._evaluate(
            pair,
            yes_price=pair.poly_yes_ask,  yes_platform=Platform.POLYMARKET,
            no_price=kalshi_no_ask,        no_platform=Platform.KALSHI,
        )
        if opp:
            await self._fire(opp)

    def _evaluate(
        self,
        pair: MarketPair,
        yes_price: float,
        yes_platform: Platform,
        no_price: float,
        no_platform: Platform,
    ) -> "LiveArbOpportunity | None":
        """Return an opportunity if the fee-adjusted gap clears the threshold."""
        if yes_price <= 0 or no_price <= 0:
            return None

        # Estimate contracts for fee scaling
        max_stake = self.bankroll * self.max_bet_pct
        contracts_yes = max(1, int(max_stake / yes_price))
        contracts_no = max(1, int(max_stake / no_price))

        adj_yes = calculate_fee_adjusted_price(yes_price, contracts_yes, yes_platform, is_buy=True)
        adj_no = calculate_fee_adjusted_price(no_price, contracts_no, no_platform, is_buy=True)

        gross_total = yes_price + no_price
        net_total = adj_yes + adj_no

        if net_total >= 1.0:
            return None

        net_profit_pct = (1.0 / net_total - 1.0) * 100
        if net_profit_pct < self.min_gap_pct:
            return None

        gross_profit_pct = (1.0 / gross_total - 1.0) * 100 if gross_total < 1.0 else 0.0

        sizing = self._build_sizing(
            adj_yes, adj_no, net_total,
            yes_price, yes_platform,
            no_price, no_platform,
            net_profit_pct,
        )

        return LiveArbOpportunity(
            canonical_id=pair.canonical_id,
            description=pair.description,
            buy_yes_platform=yes_platform.value,
            buy_yes_price=round(yes_price, 4),
            buy_no_platform=no_platform.value,
            buy_no_price=round(no_price, 4),
            gross_profit_pct=round(gross_profit_pct, 3),
            net_profit_pct=round(net_profit_pct, 3),
            sizing=sizing,
        )

    def _build_sizing(
        self,
        adj_yes: float,
        adj_no: float,
        net_total: float,
        raw_yes: float,
        yes_platform: Platform,
        raw_no: float,
        no_platform: Platform,
        net_profit_pct: float,
    ) -> dict:
        total_stake = self.bankroll * self.max_bet_pct
        stake_yes = total_stake * (adj_yes / net_total)
        stake_no = total_stake * (adj_no / net_total)
        guaranteed_profit = total_stake / net_total - total_stake

        return {
            "total_stake": round(total_stake, 2),
            "guaranteed_profit": round(guaranteed_profit, 2),
            "roi_pct": round(net_profit_pct, 2),
            "instructions": [
                {
                    "platform": yes_platform.value,
                    "action": "BUY",
                    "side": "YES",
                    "price": raw_yes,
                    "amount": round(stake_yes, 2),
                    "contracts": max(1, int(stake_yes / raw_yes)),
                },
                {
                    "platform": no_platform.value,
                    "action": "BUY",
                    "side": "NO",
                    "price": raw_no,
                    "amount": round(stake_no, 2),
                    "contracts": max(1, int(stake_no / raw_no)),
                },
            ],
        }

    async def _fire(self, opp: LiveArbOpportunity) -> None:
        """Fire callbacks, respecting per-pair cooldown."""
        now = time.monotonic()
        last = self._last_fired.get(opp.canonical_id, 0.0)
        if now - last < self._fire_cooldown:
            return
        self._last_fired[opp.canonical_id] = now

        logger.info(
            "ARB %.2f%% net | %s → buy YES on %s @ %.3f, NO on %s @ %.3f",
            opp.net_profit_pct,
            opp.description,
            opp.buy_yes_platform,
            opp.buy_yes_price,
            opp.buy_no_platform,
            opp.buy_no_price,
        )

        tasks = [asyncio.create_task(cb(opp)) for cb in self._callbacks]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)


# ── Convenience builder ────────────────────────────────────────────────────

def build_scanner_from_matched_markets(
    matched: list[tuple[str, str, str, str]],
    min_gap_pct: float = 2.0,
    bankroll: float = 10_000.0,
    max_bet_pct: float = 0.05,
) -> RealtimeArbScanner:
    """Build a scanner from a list of pre-matched (description, kalshi_ticker,
    poly_yes_token, poly_no_token) tuples.

    Example::

        scanner = build_scanner_from_matched_markets([
            ("Chiefs win SB", "KXNFL-25-KC", "0xabc...", "0xdef..."),
        ])
    """
    scanner = RealtimeArbScanner(min_gap_pct, bankroll, max_bet_pct)
    for i, (desc, kalshi_ticker, poly_yes, poly_no) in enumerate(matched):
        scanner.register_pair(MarketPair(
            canonical_id=f"pair_{i}_{kalshi_ticker}",
            description=desc,
            kalshi_ticker=kalshi_ticker,
            polymarket_yes_token=poly_yes,
            polymarket_no_token=poly_no or None,
        ))
    return scanner
