"""RED stub tests for PMFeatureAssembler — Phase 9 plan 01.

All assemble() tests MUST fail with NotImplementedError (RED state).
detect_category() tests are GREEN (implemented in stub).
"""

import numpy as np
import pytest

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
# assemble() RED tests — all must raise NotImplementedError
# ---------------------------------------------------------------------------

def test_assemble_universal_features():
    """Universal-only market should return ndarray of length >= 6."""
    assembler = PMFeatureAssembler()
    with pytest.raises(NotImplementedError):
        assembler.assemble(UNIVERSAL_MARKET)


def test_assemble_political_features():
    """Political market should return ndarray of length >= 8."""
    assembler = PMFeatureAssembler()
    with pytest.raises(NotImplementedError):
        assembler.assemble(POLITICAL_MARKET)


def test_assemble_economic_features():
    """Economic market should return ndarray of length >= 8."""
    assembler = PMFeatureAssembler()
    with pytest.raises(NotImplementedError):
        assembler.assemble(ECONOMIC_MARKET)


def test_assemble_crypto_features():
    """Crypto market should return ndarray of length >= 8."""
    assembler = PMFeatureAssembler()
    with pytest.raises(NotImplementedError):
        assembler.assemble(CRYPTO_MARKET)


def test_assemble_entertainment_features():
    """Entertainment market should return ndarray of length == 6."""
    assembler = PMFeatureAssembler()
    with pytest.raises(NotImplementedError):
        assembler.assemble(ENTERTAINMENT_MARKET)


def test_assemble_weather_features():
    """Weather market should return ndarray of length == 6."""
    assembler = PMFeatureAssembler()
    with pytest.raises(NotImplementedError):
        assembler.assemble(WEATHER_MARKET)


# ---------------------------------------------------------------------------
# detect_category() GREEN tests — implemented in stub
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
