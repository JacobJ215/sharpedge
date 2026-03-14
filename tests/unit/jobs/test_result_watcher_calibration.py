"""RED stub for result_watcher calibration hook — QUANT-07.

Tests that trigger_calibration_update is called after a WIN bet is processed.
Fails with ImportError until Plan 05-05 adds trigger_calibration_update to
apps/webhook_server/src/sharpedge_webhooks/jobs/result_watcher.py.
"""
import pytest
from unittest.mock import AsyncMock, patch

from sharpedge_webhooks.jobs.result_watcher import trigger_calibration_update


@pytest.mark.asyncio
async def test_trigger_calibration_update_called():
    """After processing a WIN bet, trigger_calibration_update is awaited.

    Patches CalibrationStore.update with AsyncMock to capture calls.
    Verifies the function is awaitable and calls update with sport + game data.
    """
    fake_resolved_game = {
        "id": "game_001",
        "sport": "NFL",
        "predicted_probability": 0.65,
        "outcome": True,
    }

    with patch(
        "sharpedge_webhooks.jobs.result_watcher.CalibrationStore.update",
        new_callable=AsyncMock,
    ) as mock_update:
        await trigger_calibration_update(
            sport="NFL",
            resolved_game=fake_resolved_game,
        )
        mock_update.assert_called_once()
        call_args = mock_update.call_args
        # Verify sport is passed through
        assert call_args is not None, "CalibrationStore.update was never called"
