"""LLM Calibrator — adjusts base RF probability using Claude API narrative analysis."""
from __future__ import annotations

import logging
import os
import re
from typing import Protocol

import anthropic

logger = logging.getLogger(__name__)

_MODEL = "claude-sonnet-4-6"
_TIMEOUT = 10.0  # seconds
_MAX_RETRIES = 2
_MAX_ADJUSTMENT = 0.10
_PROB_FLOOR = 0.05
_PROB_CEILING = 0.95

_SYSTEM_PROMPT = """You are a prediction market calibrator. Given a research narrative about a market event
and a base probability from a machine learning model, you must adjust the probability up or down based
on the narrative sentiment and signal quality.

Rules:
- Output ONLY a float between 0 and 1, nothing else
- Do not output any explanation, just the number
- Maximum adjustment from base probability: ±0.10
- If the narrative is neutral or you are uncertain, return the base probability unchanged
- Round to 4 decimal places"""


class LLMCalibratorProtocol(Protocol):
    def calibrate(self, base_prob: float, narrative: str) -> float: ...


class LLMCalibrator:
    """Adjusts base probability using Claude API with timeout and fallback."""

    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")

    def calibrate(self, base_prob: float, narrative: str) -> float:
        """Calibrate base_prob using narrative. Returns base_prob on any failure."""
        if not self._api_key:
            logger.warning("ANTHROPIC_API_KEY not set — returning base probability unchanged")
            return base_prob

        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                result = self._call_api(base_prob, narrative)
                return result
            except Exception as exc:  # noqa: BLE001
                logger.warning("LLM calibration attempt %d/%d failed: %s", attempt, _MAX_RETRIES, exc)

        logger.warning("LLM calibration exhausted retries — returning base probability unchanged")
        return base_prob

    def _call_api(self, base_prob: float, narrative: str) -> float:
        client = anthropic.Anthropic(api_key=self._api_key, timeout=_TIMEOUT)
        user_message = (
            f"Base probability: {base_prob:.4f}\n\n"
            f"Narrative:\n{narrative}\n\n"
            f"Calibrated probability:"
        )
        # Prefill the assistant turn with "0." to force a decimal numeric response.
        # The model will complete e.g. "0." → "5000" and we prepend to reconstruct "0.5000".
        # Clamps to [0.05, 0.95] afterward so constraining to [0, 1) is safe.
        _PREFILL = "0."
        response = client.messages.create(
            model=_MODEL,
            max_tokens=8,
            system=_SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": user_message},
                {"role": "assistant", "content": _PREFILL},
            ],
        )
        raw = _PREFILL + response.content[0].text.strip()
        try:
            calibrated = float(raw)
        except ValueError:
            match = re.search(r'\b(0\.\d+|1\.0*|0\.0*|1|0)\b', raw)
            if match:
                calibrated = float(match.group(1))
            else:
                raise ValueError(f"Could not extract float from LLM response: {raw[:120]}")

        # Clamp to ±10% of base_prob, then to absolute [0.05, 0.95]
        calibrated = max(base_prob - _MAX_ADJUSTMENT, min(base_prob + _MAX_ADJUSTMENT, calibrated))
        calibrated = max(_PROB_FLOOR, min(_PROB_CEILING, calibrated))
        return round(calibrated, 4)
