"""LLM Calibrator — adjusts base RF probability using OpenAI API narrative analysis."""
from __future__ import annotations

import logging
import os
import re
from typing import Protocol

import openai

logger = logging.getLogger(__name__)

_MODEL = "gpt-5.4-nano-2026-03-17"
_TIMEOUT = 10.0  # seconds
_MAX_RETRIES = 2
_MAX_ADJUSTMENT = 0.10
_PROB_FLOOR = 0.05
_PROB_CEILING = 0.95

_SYSTEM_PROMPT = """You are a prediction market calibrator. Respond with ONLY a single decimal number between 0 and 1. No words, no explanation, no punctuation — just the number.

Example valid responses: 0.6200  0.4831  0.7500
Example INVALID responses: "The probability is 0.62" or "Based on..." or any text whatsoever.

Rules:
- Adjust the base probability up or down based on the narrative sentiment and signal quality
- Maximum adjustment: ±0.10 from the base probability
- If narrative is neutral or you are uncertain, return the base probability unchanged
- Round to 4 decimal places
- YOUR ENTIRE RESPONSE MUST BE ONLY THE NUMBER, NOTHING ELSE"""


class LLMCalibratorProtocol(Protocol):
    def calibrate(self, base_prob: float, narrative: str) -> float: ...


class LLMCalibrator:
    """Adjusts base probability using OpenAI API with timeout and fallback."""

    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key or os.environ.get("OPENAI_API_KEY", "")

    def calibrate(self, base_prob: float, narrative: str) -> float:
        """Calibrate base_prob using narrative. Returns base_prob on any failure."""
        if not self._api_key:
            logger.warning("OPENAI_API_KEY not set — returning base probability unchanged")
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
        client = openai.OpenAI(api_key=self._api_key, timeout=_TIMEOUT)
        user_message = (
            f"Base probability: {base_prob:.4f}\n\n"
            f"Narrative:\n{narrative}\n\n"
            f"Output ONLY the calibrated probability as a single decimal number:"
        )
        response = client.chat.completions.create(
            model=_MODEL,
            max_tokens=16,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
        )
        raw = response.choices[0].message.content.strip()
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
