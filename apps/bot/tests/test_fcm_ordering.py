"""GREEN verification tests for WIRE-05: FCM fires before Discord append.

Tests verify:
1. send_fcm_notifications_for_play(play) is called BEFORE _pending_value_alerts.append(play)
2. FCM is NOT called for SPECULATIVE (low-alpha) plays
3. FCM token registration on shell init (device-only — skipped)

Source-inspection is used for ordering because value_scanner_job has a transitive
import issue with sharpedge_analytics.enrich_with_alpha that prevents clean module
loading in unit tests without full dependency mocking.
"""

from __future__ import annotations

import pathlib
import sys
import types
import unittest.mock

import pytest

_JOB_FILE = (
    pathlib.Path(__file__).parent.parent / "src" / "sharpedge_bot" / "jobs" / "value_scanner_job.py"
)


# ---------------------------------------------------------------------------
# Module loader with mocked transitive dependencies
# ---------------------------------------------------------------------------


def _load_value_scanner_job():
    """Load value_scanner_job with all transitive imports mocked out.

    Returns the loaded module so tests can call send_fcm_notifications_for_play
    directly without triggering broken sharpedge_analytics.enrich_with_alpha import.
    """
    module_name = "sharpedge_bot.jobs.value_scanner_job_testload"

    if module_name in sys.modules:
        return sys.modules[module_name]

    # Stub out every transitive dependency that would fail to import
    _stubs = {
        "sharpedge_analytics": {
            "scan_for_value": None,
            "scan_for_value_no_vig": None,
            "rank_value_plays": None,
            "enrich_with_alpha": None,
            "ValuePlay": object,
            "Confidence": object,
        },
        "sharpedge_analytics.pm_edge_scanner": {"scan_pm_edges": lambda **kw: []},
        "sharpedge_analytics.pm_correlation": {"detect_correlated_positions": lambda **kw: []},
        "sharpedge_agent_pipeline": {},
        "sharpedge_agent_pipeline.alerts": {},
        "sharpedge_agent_pipeline.alerts.alpha_ranker": {"rank_by_alpha": lambda x: x},
        "sharpedge_bot.services": {},
        "sharpedge_bot.services.odds_service": {"get_odds_client": lambda: None},
        "sharpedge_db": {},
        "sharpedge_db.client": {"get_supabase_client": lambda: None},
        "sharpedge_shared": {},
        "sharpedge_shared.types": {"Sport": object},
    }
    for mod_name, attrs in _stubs.items():
        if mod_name not in sys.modules:
            fake = types.ModuleType(mod_name)
            for attr, val in attrs.items():
                setattr(fake, attr, val)
            sys.modules[mod_name] = fake

    import importlib.util

    spec = importlib.util.spec_from_file_location(module_name, str(_JOB_FILE))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = mod
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# Test 1: FCM called before Discord append (source-inspection + mock ordering)
# ---------------------------------------------------------------------------


def test_fcm_called_before_discord_append() -> None:
    """FCM is dispatched before play is appended to the Discord pending queue.

    Verifies ordering at the source level: send_fcm_notifications_for_play(play)
    must appear before _pending_value_alerts.append(play) in the scan loop body.
    """
    source = _JOB_FILE.read_text()

    fcm_idx = source.find("send_fcm_notifications_for_play(play)")
    discord_idx = source.find("_pending_value_alerts.append(play)")

    assert fcm_idx != -1, "send_fcm_notifications_for_play(play) not found in source"
    assert discord_idx != -1, "_pending_value_alerts.append(play) not found in source"
    assert fcm_idx < discord_idx, (
        f"FCM call (char pos {fcm_idx}) must appear before Discord append "
        f"(char pos {discord_idx}). WIRE-05 requires FCM fires before Discord append."
    )

    # Belt-and-suspenders: verify line numbers agree with char positions
    lines = source.splitlines()
    fcm_lines = [i for i, ln in enumerate(lines) if "send_fcm_notifications_for_play(play)" in ln]
    discord_lines = [i for i, ln in enumerate(lines) if "_pending_value_alerts.append(play)" in ln]

    assert fcm_lines, "send_fcm_notifications_for_play(play) line not found"
    assert discord_lines, "_pending_value_alerts.append(play) line not found"
    assert min(fcm_lines) < min(discord_lines), (
        f"FCM at line {min(fcm_lines) + 1} must precede Discord append at line {min(discord_lines) + 1}"
    )


# ---------------------------------------------------------------------------
# Test 2: FCM NOT called for low-alpha (SPECULATIVE) plays
# ---------------------------------------------------------------------------


def test_fcm_not_called_for_low_alpha() -> None:
    """send_fcm_notifications_for_play returns 0 and skips push for SPECULATIVE plays.

    A play with alpha_score < 0.5 gets badge = SPECULATIVE and must NOT trigger
    any FCM send attempt — the function returns 0 immediately after badge check.
    """
    mod = _load_value_scanner_job()

    speculative_play = {
        "id": "test-play-001",
        "alpha_score": 0.10,  # well below 0.50 threshold for SPECULATIVE
        "game": "Team A vs Team B",
        "bet_type": "spread",
        "ev_percentage": 1.5,
        "sportsbook": "fanduel",
    }

    with unittest.mock.patch("supabase.create_client") as mock_supabase:
        result = mod.send_fcm_notifications_for_play(speculative_play)

    assert result == 0, f"Expected 0 FCM sends for SPECULATIVE play, got {result}"
    mock_supabase.assert_not_called()


# ---------------------------------------------------------------------------
# Test 3: FCM token registration on shell init (device-only — skipped)
# ---------------------------------------------------------------------------


@pytest.mark.skip(reason="mobile verification — covered by WIRE-05 device checkpoint")
def test_fcm_token_registration_on_shell_init() -> None:
    """FCM token is registered when the user logs into the mobile app.

    Cannot be unit-tested directly; requires physical device verification.
    See: apps/mobile/lib/main.dart _ShellState.initState registerToken() call.
    Verified manually via WIRE-05 device checkpoint.
    """
    pass
