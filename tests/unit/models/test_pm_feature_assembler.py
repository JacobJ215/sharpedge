"""GREEN tests for PMFeatureAssembler — Phase 9 plan 03.

assemble() is fully implemented. Tests verify correct feature vector
lengths per category and correct universal feature extraction.
detect_category() tests remain GREEN (unchanged from plan 01).
"""

import numpy as np
import pytest
from unittest.mock import MagicMock

from sharpedge_models.pm_feature_assembler import PMFeatureAssembler


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

UNIVERSAL_MARKET = {
    "market_prob": 0.6,
    "bid_ask_spread": 0.04,
    "last_price": 0.58,
    "volume": 5000.0,
    "open_interest": 200.0,
    "days_to_close": 7,
    "event_ticker": "KXGENERIC",
    "question": "Will the sun rise tomorrow?",
}

POLITICAL_MARKET = {
    **UNIVERSAL_MARKET,
    "event_ticker": "KXPOL-PRES-24",
    "question": "Will the election result be certified?",
    "polling_average": 0.52,
    "election_proximity_days": 14,
}

ECONOMIC_MARKET = {
    **UNIVERSAL_MARKET,
    "event_ticker": "KXFED-RATE-MAR",
    "question": "Will the Fed raise rates?",
    "days_since_last_release": 15,
    "is_release_imminent": False,
}

CRYPTO_MARKET = {
    **UNIVERSAL_MARKET,
    "event_ticker": "KXBTC-100K",
    "question": "Will Bitcoin reach $100k?",
    "underlying_asset_price": 67000.0,
    "price_change_7d": 0.12,
}

ENTERTAINMENT_MARKET = {
    **UNIVERSAL_MARKET,
    "event_ticker": "KXENT-OSCAR",
    "question": "Will the oscar winner be announced?",
}

WEATHER_MARKET = {
    **UNIVERSAL_MARKET,
    "event_ticker": "KXWTH-HUR",
    "question": "Will a hurricane hit Florida?",
}


# ---------------------------------------------------------------------------
# assemble() — vector length tests
# ---------------------------------------------------------------------------

def test_assemble_universal_features_length():
    """Universal-only (entertainment default) market returns length 6."""
    assembler = PMFeatureAssembler()
    arr = assembler.assemble(UNIVERSAL_MARKET)
    assert isinstance(arr, np.ndarray)
    assert len(arr) == 6


def test_assemble_political_features_length():
    """Political market returns length 8 (6 universal + 2 add-ons)."""
    assembler = PMFeatureAssembler()
    arr = assembler.assemble(POLITICAL_MARKET)
    assert isinstance(arr, np.ndarray)
    assert len(arr) == 8


def test_assemble_economic_features_length():
    """Economic market returns length 8 (6 universal + 2 add-ons)."""
    assembler = PMFeatureAssembler()
    arr = assembler.assemble(ECONOMIC_MARKET)
    assert isinstance(arr, np.ndarray)
    assert len(arr) == 8


def test_assemble_crypto_features_length():
    """Crypto market returns length 8 (6 universal + 2 add-ons)."""
    assembler = PMFeatureAssembler()
    arr = assembler.assemble(CRYPTO_MARKET)
    assert isinstance(arr, np.ndarray)
    assert len(arr) == 8


def test_assemble_entertainment_features_length():
    """Entertainment market returns length 6 (universal only)."""
    assembler = PMFeatureAssembler()
    arr = assembler.assemble(ENTERTAINMENT_MARKET)
    assert isinstance(arr, np.ndarray)
    assert len(arr) == 6


def test_assemble_weather_features_length():
    """Weather market returns length 6 (universal only)."""
    assembler = PMFeatureAssembler()
    arr = assembler.assemble(WEATHER_MARKET)
    assert isinstance(arr, np.ndarray)
    assert len(arr) == 6


# ---------------------------------------------------------------------------
# assemble() — universal feature extraction correctness
# ---------------------------------------------------------------------------

def test_assemble_universal_feature_values():
    """Universal features extracted at correct indices with correct values."""
    assembler = PMFeatureAssembler()
    market = {
        "market_prob": 0.6,
        "bid_ask_spread": 0.04,
        "last_price": 0.58,
        "volume": 5000.0,
        "open_interest": 200.0,
        "days_to_close": 7,
        "event_ticker": "KXENT-GENERIC",
        "question": "Generic question",
    }
    arr = assembler.assemble(market)
    # market_prob (no yes_bid/yes_ask → uses market_prob directly)
    assert arr[0] == pytest.approx(0.6)
    # bid_ask_spread (no yes_bid/yes_ask → uses bid_ask_spread directly)
    assert arr[1] == pytest.approx(0.04)
    # last_price
    assert arr[2] == pytest.approx(0.58)
    # volume
    assert arr[3] == pytest.approx(5000.0)
    # open_interest
    assert arr[4] == pytest.approx(200.0)
    # days_to_close
    assert arr[5] == pytest.approx(7.0)


def test_assemble_yes_bid_ask_computes_market_prob():
    """market_prob computed as mid when yes_bid/yes_ask present."""
    assembler = PMFeatureAssembler()
    market = {
        "yes_bid": 0.55,
        "yes_ask": 0.65,
        "last_price": 0.60,
        "volume": 100.0,
        "open_interest": 50.0,
        "days_to_close": 3,
        "event_ticker": "KXENT-X",
        "question": "Test",
    }
    arr = assembler.assemble(market)
    assert arr[0] == pytest.approx(0.60)  # (0.55 + 0.65) / 2
    assert arr[1] == pytest.approx(0.10)  # 0.65 - 0.55


def test_assemble_days_to_close_clamped_to_zero():
    """Negative days_to_close is clamped to 0."""
    assembler = PMFeatureAssembler()
    market = {**ENTERTAINMENT_MARKET, "days_to_close": -5}
    arr = assembler.assemble(market)
    assert arr[5] == pytest.approx(0.0)


def test_assemble_returns_float64_dtype():
    """All assembled arrays use float64 dtype."""
    assembler = PMFeatureAssembler()
    for market in [POLITICAL_MARKET, ECONOMIC_MARKET, CRYPTO_MARKET, ENTERTAINMENT_MARKET, WEATHER_MARKET]:
        arr = assembler.assemble(market)
        assert arr.dtype == np.float64


# ---------------------------------------------------------------------------
# assemble() — offline/no-client behavior
# ---------------------------------------------------------------------------

def test_assemble_political_offline_returns_defaults():
    """Without FEC client, political add-ons use market data or safe defaults."""
    assembler = PMFeatureAssembler()  # no fec injected
    arr = assembler.assemble(POLITICAL_MARKET)
    assert len(arr) == 8
    # Index 6 = polling_average from market dict (0.52)
    assert arr[6] == pytest.approx(0.52)
    # Index 7 = election_proximity_days from market dict (14)
    assert arr[7] == pytest.approx(14.0)


def test_assemble_economic_offline_returns_defaults():
    """Without BLS client, economic add-ons use market data or safe defaults."""
    assembler = PMFeatureAssembler()  # no bls injected
    arr = assembler.assemble(ECONOMIC_MARKET)
    assert len(arr) == 8
    # Index 6 = days_since_last_release from market dict (15)
    assert arr[6] == pytest.approx(15.0)
    # Index 7 = is_release_imminent from market dict (False → 0.0)
    assert arr[7] == pytest.approx(0.0)


def test_assemble_crypto_offline_returns_defaults():
    """Without CoinGecko client, crypto add-ons use market data or safe defaults."""
    assembler = PMFeatureAssembler()  # no coingecko injected
    arr = assembler.assemble(CRYPTO_MARKET)
    assert len(arr) == 8
    # Index 6 = underlying_asset_price from market dict (67000.0)
    assert arr[6] == pytest.approx(67000.0)
    # Index 7 = price_change_7d from market dict (0.12)
    assert arr[7] == pytest.approx(0.12)


# ---------------------------------------------------------------------------
# assemble() — client injection tests
# ---------------------------------------------------------------------------

def test_assemble_political_with_fec_client():
    """FEC client is called when injected; result used for add-ons."""
    mock_fec = MagicMock()
    mock_fec.get_polling_average.return_value = 0.48
    mock_fec.get_election_proximity_days.return_value = 30
    assembler = PMFeatureAssembler(fec=mock_fec)
    arr = assembler.assemble(POLITICAL_MARKET)
    assert len(arr) == 8
    assert arr[6] == pytest.approx(0.48)
    assert arr[7] == pytest.approx(30.0)


def test_assemble_crypto_with_coingecko_client():
    """CoinGecko client is called when injected; result used for add-ons."""
    mock_cg = MagicMock()
    mock_cg.get_price.return_value = 95000.0
    mock_cg.get_price_change_7d.return_value = -0.05
    assembler = PMFeatureAssembler(coingecko=mock_cg)
    arr = assembler.assemble(CRYPTO_MARKET)
    assert len(arr) == 8
    assert arr[6] == pytest.approx(95000.0)
    assert arr[7] == pytest.approx(-0.05)


def test_assemble_economic_with_bls_client():
    """BLS client is called when injected; result used for add-ons."""
    mock_bls = MagicMock()
    mock_bls.get_days_since_last_release.return_value = 20
    mock_bls.get_is_release_imminent.return_value = True
    assembler = PMFeatureAssembler(bls=mock_bls)
    arr = assembler.assemble(ECONOMIC_MARKET)
    assert len(arr) == 8
    assert arr[6] == pytest.approx(20.0)
    assert arr[7] == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# assemble() — never raises
# ---------------------------------------------------------------------------

def test_assemble_never_raises_on_empty_market():
    """Empty market dict does not raise; returns array of length 6."""
    assembler = PMFeatureAssembler()
    arr = assembler.assemble({})
    assert isinstance(arr, np.ndarray)
    assert len(arr) == 6


def test_assemble_never_raises_on_bad_types():
    """Market dict with non-numeric values does not raise."""
    assembler = PMFeatureAssembler()
    bad_market = {
        "market_prob": "not-a-number",
        "last_price": None,
        "volume": {},
        "open_interest": [],
        "days_to_close": "seven",
        "event_ticker": "KXBTC-BAD",
        "question": "Will bitcoin crash?",
        "underlying_asset_price": "oops",
        "price_change_7d": "oops",
    }
    arr = assembler.assemble(bad_market)
    assert isinstance(arr, np.ndarray)
    assert len(arr) == 8  # crypto category


# ---------------------------------------------------------------------------
# detect_category() GREEN tests — unchanged from plan 01
# ---------------------------------------------------------------------------

def test_detect_category_political_by_ticker():
    assembler = PMFeatureAssembler()
    market = {**UNIVERSAL_MARKET, "event_ticker": "KXPOL-2024"}
    assert assembler.detect_category(market) == "political"


def test_detect_category_political_by_question():
    assembler = PMFeatureAssembler()
    market = {**UNIVERSAL_MARKET, "event_ticker": "KXOTH", "question": "Who wins the election?"}
    assert assembler.detect_category(market) == "political"


def test_detect_category_crypto_by_ticker():
    assembler = PMFeatureAssembler()
    market = {**UNIVERSAL_MARKET, "event_ticker": "KXBTC-PRICE"}
    assert assembler.detect_category(market) == "crypto"


def test_detect_category_crypto_by_question_bitcoin():
    assembler = PMFeatureAssembler()
    market = {**UNIVERSAL_MARKET, "event_ticker": "KXOTH", "question": "Will bitcoin hit 100k?"}
    assert assembler.detect_category(market) == "crypto"


def test_detect_category_crypto_by_question_eth():
    assembler = PMFeatureAssembler()
    market = {**UNIVERSAL_MARKET, "event_ticker": "KXOTH", "question": "Will ETH reach $5000?"}
    assert assembler.detect_category(market) == "crypto"


def test_detect_category_economic_by_ticker():
    assembler = PMFeatureAssembler()
    market = {**UNIVERSAL_MARKET, "event_ticker": "KXFED-MAR25"}
    assert assembler.detect_category(market) == "economic"


def test_detect_category_economic_by_question_cpi():
    assembler = PMFeatureAssembler()
    market = {**UNIVERSAL_MARKET, "event_ticker": "KXOTH", "question": "Will CPI drop below 3%?"}
    assert assembler.detect_category(market) == "economic"


def test_detect_category_economic_by_question_inflation():
    assembler = PMFeatureAssembler()
    market = {**UNIVERSAL_MARKET, "event_ticker": "KXOTH", "question": "Will inflation fall this year?"}
    assert assembler.detect_category(market) == "economic"


def test_detect_category_economic_by_question_rate():
    assembler = PMFeatureAssembler()
    market = {**UNIVERSAL_MARKET, "event_ticker": "KXOTH", "question": "Will the rate be cut in June?"}
    assert assembler.detect_category(market) == "economic"


def test_detect_category_entertainment():
    assembler = PMFeatureAssembler()
    market = {**UNIVERSAL_MARKET, "event_ticker": "KXOTH", "question": "Who wins the oscar for best picture?"}
    assert assembler.detect_category(market) == "entertainment"


def test_detect_category_weather():
    assembler = PMFeatureAssembler()
    market = {**UNIVERSAL_MARKET, "event_ticker": "KXOTH", "question": "Will a hurricane make landfall in August?"}
    assert assembler.detect_category(market) == "weather"


def test_unknown_category_defaults_to_entertainment():
    assembler = PMFeatureAssembler()
    market = {**UNIVERSAL_MARKET, "event_ticker": "KXUNK", "question": "Will the stock market crash?"}
    assert assembler.detect_category(market) == "entertainment"
