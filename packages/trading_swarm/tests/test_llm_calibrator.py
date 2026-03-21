"""Tests for LLMCalibrator — all OpenAI API calls mocked."""
from unittest.mock import MagicMock, patch

import pytest

from sharpedge_trading.signals.llm_calibrator import LLMCalibrator, _MAX_ADJUSTMENT, _PROB_CEILING, _PROB_FLOOR


def _make_mock_response(text: str) -> MagicMock:
    message = MagicMock()
    message.content = text
    choice = MagicMock()
    choice.message = message
    response = MagicMock()
    response.choices = [choice]
    return response


@pytest.fixture
def calibrator():
    return LLMCalibrator(api_key="test-key")


def test_calibrate_returns_adjusted_probability(calibrator):
    with patch("sharpedge_trading.signals.llm_calibrator.openai") as mock_openai:
        mock_client = MagicMock()
        mock_openai.OpenAI.return_value = mock_client
        mock_client.chat.completions.create.return_value = _make_mock_response("0.62")

        result = calibrator.calibrate(0.55, "Bullish sentiment from multiple sources")

    assert result == 0.62


def test_calibrate_clamps_upward_adjustment(calibrator):
    # API returns base + 0.20 (too high), should be clamped to base + 0.10
    with patch("sharpedge_trading.signals.llm_calibrator.openai") as mock_openai:
        mock_client = MagicMock()
        mock_openai.OpenAI.return_value = mock_client
        mock_client.chat.completions.create.return_value = _make_mock_response("0.75")  # 0.55 + 0.20

        result = calibrator.calibrate(0.55, "Narrative")

    assert result == round(0.55 + _MAX_ADJUSTMENT, 4)


def test_calibrate_clamps_downward_adjustment(calibrator):
    with patch("sharpedge_trading.signals.llm_calibrator.openai") as mock_openai:
        mock_client = MagicMock()
        mock_openai.OpenAI.return_value = mock_client
        mock_client.chat.completions.create.return_value = _make_mock_response("0.35")  # 0.55 - 0.20

        result = calibrator.calibrate(0.55, "Narrative")

    assert result == round(0.55 - _MAX_ADJUSTMENT, 4)


def test_calibrate_clamps_to_absolute_floor(calibrator):
    # base = 0.06, API says 0.01 → clamp ±0.10 gives floor 0.0, then absolute floor 0.05
    with patch("sharpedge_trading.signals.llm_calibrator.openai") as mock_openai:
        mock_client = MagicMock()
        mock_openai.OpenAI.return_value = mock_client
        mock_client.chat.completions.create.return_value = _make_mock_response("0.01")

        result = calibrator.calibrate(0.06, "Narrative")

    assert result >= _PROB_FLOOR


def test_calibrate_clamps_to_absolute_ceiling(calibrator):
    with patch("sharpedge_trading.signals.llm_calibrator.openai") as mock_openai:
        mock_client = MagicMock()
        mock_openai.OpenAI.return_value = mock_client
        mock_client.chat.completions.create.return_value = _make_mock_response("0.99")

        result = calibrator.calibrate(0.94, "Narrative")

    assert result <= _PROB_CEILING


def test_calibrate_returns_base_on_api_exception(calibrator):
    with patch("sharpedge_trading.signals.llm_calibrator.openai") as mock_openai:
        mock_client = MagicMock()
        mock_openai.OpenAI.return_value = mock_client
        mock_client.chat.completions.create.side_effect = Exception("Connection timeout")

        result = calibrator.calibrate(0.55, "Narrative")

    assert result == 0.55


def test_calibrate_returns_base_on_invalid_response(calibrator):
    with patch("sharpedge_trading.signals.llm_calibrator.openai") as mock_openai:
        mock_client = MagicMock()
        mock_openai.OpenAI.return_value = mock_client
        mock_client.chat.completions.create.return_value = _make_mock_response("not-a-number")

        result = calibrator.calibrate(0.55, "Narrative")

    assert result == 0.55


def test_calibrate_returns_base_when_no_api_key():
    calibrator = LLMCalibrator(api_key="")
    result = calibrator.calibrate(0.55, "Narrative")
    assert result == 0.55


def test_calibrate_retries_on_failure(calibrator):
    """Should retry up to _MAX_RETRIES times before giving up."""
    with patch("sharpedge_trading.signals.llm_calibrator.openai") as mock_openai:
        mock_client = MagicMock()
        mock_openai.OpenAI.return_value = mock_client
        mock_client.chat.completions.create.side_effect = [
            Exception("first failure"),
            Exception("second failure"),
        ]

        result = calibrator.calibrate(0.55, "Narrative")

    assert result == 0.55
    assert mock_client.chat.completions.create.call_count == 2
