"""GREEN verification test for WIRE-05: FCM fires before Discord append.

This test verifies that send_fcm_notifications_for_play(play) is called
BEFORE _pending_value_alerts.append(play) in value_scanner_job.py.

This is a GREEN test — FCM is already before Discord in the implementation.

NOTE: value_scanner_job has a transitive import of enrich_with_alpha that is not
exported from sharpedge_analytics.__init__ (pre-existing issue). Tests use
source-inspection to avoid importing the module entirely.
"""
from __future__ import annotations

import pathlib


_JOB_FILE = pathlib.Path(__file__).parent.parent / "src" / "sharpedge_bot" / "jobs" / "value_scanner_job.py"


def test_fcm_called_before_discord_append() -> None:
    """FCM notification is sent before play is appended to Discord pending queue.

    GREEN: value_scanner_job.py calls send_fcm_notifications_for_play(play)
    before appending to _pending_value_alerts.

    Uses source-inspection to verify ordering without importing the module
    (avoids transitive broken import of enrich_with_alpha).
    """
    source = _JOB_FILE.read_text()

    fcm_idx = source.find("send_fcm_notifications_for_play(play)")
    discord_idx = source.find("_pending_value_alerts.append(play)")

    assert fcm_idx != -1, "send_fcm_notifications_for_play(play) not found in source"
    assert discord_idx != -1, "_pending_value_alerts.append(play) not found in source"
    assert fcm_idx < discord_idx, (
        f"FCM call (pos {fcm_idx}) must appear before Discord append (pos {discord_idx}). "
        "WIRE-05 requires FCM fires before Discord append."
    )


def test_fcm_ordering_in_scan_loop() -> None:
    """Verify the call ordering in the scan loop body: FCM precedes Discord append.

    GREEN: belt-and-suspenders check that the two lines exist and FCM comes first.
    """
    source = _JOB_FILE.read_text()
    lines = source.splitlines()

    fcm_lines = [i for i, ln in enumerate(lines) if "send_fcm_notifications_for_play(play)" in ln]
    discord_lines = [i for i, ln in enumerate(lines) if "_pending_value_alerts.append(play)" in ln]

    assert fcm_lines, "send_fcm_notifications_for_play(play) not found in value_scanner_job.py"
    assert discord_lines, "_pending_value_alerts.append(play) not found in value_scanner_job.py"

    # The first FCM call should appear before the first Discord append in the scan loop
    assert min(fcm_lines) < min(discord_lines), (
        f"FCM call at line {min(fcm_lines)} must precede Discord append at line {min(discord_lines)}"
    )
