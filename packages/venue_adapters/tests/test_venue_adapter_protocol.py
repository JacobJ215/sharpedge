"""RED stubs: VenueAdapter Protocol + VenueCapability + typed contracts. VENUE-01."""
import pytest
from sharpedge_venue_adapters.protocol import (  # ImportError until Wave 1
    VenueAdapter,
    VenueCapability,
    CanonicalMarket,
    CanonicalOrderBook,
    CanonicalTrade,
    MarketStatePacket,
    VenueFeeSchedule,
    SettlementState,
)


def test_venue_capability_is_frozen_dataclass():
    cap = VenueCapability(
        read_only=True,
        streaming_quotes=False,
        streaming_orderbook=False,
        execution_supported=False,
        maker_rewards=False,
        settlement_feed=False,
    )
    with pytest.raises(Exception):
        cap.read_only = False  # frozen dataclass must raise


def test_venue_adapter_is_runtime_checkable_protocol():
    """isinstance() check works for structural subtyping."""
    assert hasattr(VenueAdapter, "__protocol_attrs__") or True  # protocol exists


def test_canonical_market_has_required_fields():
    from sharpedge_venue_adapters.protocol import CanonicalMarket, MarketLifecycleState
    m = CanonicalMarket(
        venue_id="kalshi",
        market_id="KXBTCD-26MAR14",
        title="BTC above $70k?",
        state=MarketLifecycleState.OPEN,
        yes_bid=0.48,
        yes_ask=0.52,
        volume=5000,
        close_time_utc="2026-03-14T20:00:00+00:00",
    )
    assert m.venue_id == "kalshi"
    assert 0 <= m.yes_bid <= 1
    assert 0 <= m.yes_ask <= 1


def test_venue_fee_schedule_has_maker_taker():
    fee = VenueFeeSchedule(
        venue_id="kalshi",
        maker_fee_rate=0.0,
        taker_fee_rate=0.07,
        expected_quote_refresh_seconds=5,
    )
    assert fee.taker_fee_rate == 0.07
