"""RED test stubs for CapitalGate (Phase 13 Wave 0).

All 16 tests must FAIL with NotImplementedError until Plan 02 implements the
gate logic. Zero syntax errors and zero ImportErrors.

Tests are written in GREEN assertion form so Plan 02 requires zero test
file changes.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest
from sharpedge_venue_adapters.capital_gate import (
    CATEGORIES,
    CapitalGate,
    CapitalGateError,
)

if TYPE_CHECKING:
    from pathlib import Path

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def make_gate(tmp_path):
    """Factory: create a CapitalGate pointing at tmp_path for test isolation."""

    def _factory(**kwargs) -> CapitalGate:
        defaults = dict(
            models_dir=tmp_path / "models",
            approval_path=tmp_path / "live_approval.json",
        )
        defaults.update(kwargs)
        return CapitalGate(**defaults)

    return _factory


@pytest.fixture
def populated_models(tmp_path) -> Path:
    """Write 5 empty .joblib files (one per category) into tmp_path/models/."""
    models_dir = tmp_path / "models"
    models_dir.mkdir(parents=True, exist_ok=True)
    for cat in CATEGORIES:
        (models_dir / f"{cat}.joblib").write_bytes(b"")
    return models_dir


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_supabase_mock(rows: list[dict]) -> MagicMock:
    """Return a mock that mimics supabase_client.table().select().gte().execute()."""
    execute_result = MagicMock()
    execute_result.data = rows
    gte_mock = MagicMock()
    gte_mock.execute.return_value = execute_result
    select_mock = MagicMock()
    select_mock.gte.return_value = gte_mock
    table_mock = MagicMock()
    table_mock.select.return_value = select_mock
    client_mock = MagicMock()
    client_mock.table.return_value = table_mock
    return client_mock


def _make_valid_approval(tmp_path: Path, all_passing: bool = True) -> Path:
    """Write a valid live_approval.json and return its path."""
    approval = {
        "approved_at": "2026-03-20T14:32:00+00:00",
        "approved_by": "test-operator",
        "gate_snapshot": {
            "gate_01_models": bool(all_passing),
            "gate_02_paper_period": True,
            "gate_03_approval": False,
            "gate_04_circuit_breaker": True,
        },
    }
    path = tmp_path / "live_approval.json"
    path.write_text(json.dumps(approval))
    return path


# ---------------------------------------------------------------------------
# GATE-01: Model artifacts
# ---------------------------------------------------------------------------


def test_gate01_fails_missing_artifact(make_gate, tmp_path):
    """GATE-01 fails when models_dir is missing at least one .joblib."""
    models_dir = tmp_path / "models"
    models_dir.mkdir()
    # Write only 4 of 5 — omit "weather"
    for cat in CATEGORIES[:-1]:
        (models_dir / f"{cat}.joblib").write_bytes(b"")
    gate = make_gate(models_dir=models_dir)
    status = gate.check()
    gate01 = next(c for c in status.conditions if c.name == "GATE-01")
    assert gate01.passed is False


def test_gate01_passes_all_artifacts(make_gate, populated_models):
    """GATE-01 passes when all 5 .joblib files are present."""
    gate = make_gate(models_dir=populated_models)
    status = gate.check()
    gate01 = next(c for c in status.conditions if c.name == "GATE-01")
    assert gate01.passed is True


# ---------------------------------------------------------------------------
# GATE-02: Paper-trading period
# ---------------------------------------------------------------------------


def test_gate02_fails_insufficient_days(make_gate, tmp_path):
    """GATE-02 fails when fewer than 7 days of shadow_ledger history exist."""
    # Rows only cover 3 unique days
    now = datetime.now(UTC)
    rows = [
        {"predicted_edge": 0.03, "timestamp": (now - timedelta(days=i)).isoformat()}
        for i in range(3)
    ]
    mock_client = _make_supabase_mock(rows)
    gate = make_gate()
    with patch(
        "sharpedge_venue_adapters.capital_gate.create_client",
        return_value=mock_client,
    ):
        status = gate.check()
    gate02 = next(c for c in status.conditions if c.name == "GATE-02")
    assert gate02.passed is False


def test_gate02_fails_low_positive_rate(make_gate, tmp_path):
    """GATE-02 fails when positive_signal_rate < 55% despite sufficient days."""
    now = datetime.now(UTC)
    # 10 rows over 10 days; 4 positive (40%), 6 non-positive (0.0)
    rows = []
    for i in range(10):
        edge = 0.02 if i < 4 else 0.0
        rows.append({"predicted_edge": edge, "timestamp": (now - timedelta(days=i)).isoformat()})
    mock_client = _make_supabase_mock(rows)
    gate = make_gate()
    with patch(
        "sharpedge_venue_adapters.capital_gate.create_client",
        return_value=mock_client,
    ):
        status = gate.check()
    gate02 = next(c for c in status.conditions if c.name == "GATE-02")
    assert gate02.passed is False


def test_gate02_fails_low_mean_edge(make_gate, tmp_path):
    """GATE-02 fails when mean_edge < 1.5% despite sufficient days and rate."""
    now = datetime.now(UTC)
    # 10 rows over 10 days; 8 positive (80%) but low edge (0.005 = 0.5%)
    rows = []
    for i in range(10):
        edge = 0.005 if i < 8 else 0.0
        rows.append({"predicted_edge": edge, "timestamp": (now - timedelta(days=i)).isoformat()})
    mock_client = _make_supabase_mock(rows)
    gate = make_gate()
    with patch(
        "sharpedge_venue_adapters.capital_gate.create_client",
        return_value=mock_client,
    ):
        status = gate.check()
    gate02 = next(c for c in status.conditions if c.name == "GATE-02")
    assert gate02.passed is False


def test_gate02_passes_valid_period(make_gate, tmp_path):
    """GATE-02 passes when 7+ days, rate >= 55%, mean_edge >= 1.5%."""
    now = datetime.now(UTC)
    # 10 rows over 10 days; 8 positive (80%), mean_edge = 0.025 (2.5%)
    rows = []
    for i in range(10):
        edge = 0.025 if i < 8 else 0.0
        rows.append({"predicted_edge": edge, "timestamp": (now - timedelta(days=i)).isoformat()})
    mock_client = _make_supabase_mock(rows)
    gate = make_gate()
    with patch(
        "sharpedge_venue_adapters.capital_gate.create_client",
        return_value=mock_client,
    ):
        status = gate.check()
    gate02 = next(c for c in status.conditions if c.name == "GATE-02")
    assert gate02.passed is True


# ---------------------------------------------------------------------------
# GATE-03: Manual approval
# ---------------------------------------------------------------------------


def test_gate03_fails_no_approval_file(make_gate, tmp_path):
    """GATE-03 fails when live_approval.json does not exist."""
    gate = make_gate()
    # Approval path does not exist (tmp_path / "live_approval.json" not created)
    status = gate.check()
    gate03 = next(c for c in status.conditions if c.name == "GATE-03")
    assert gate03.passed is False


def test_gate03_fails_invalid_json(make_gate, tmp_path):
    """GATE-03 fails when live_approval.json contains invalid JSON."""
    approval_path = tmp_path / "live_approval.json"
    approval_path.write_text("this is not valid json{{{{")
    gate = make_gate(approval_path=approval_path)
    status = gate.check()
    gate03 = next(c for c in status.conditions if c.name == "GATE-03")
    assert gate03.passed is False


def test_gate03_fails_stale_approval(make_gate, tmp_path):
    """GATE-03 fails when approval snapshot shows gate_01_models=False (stale)."""
    approval_path = _make_valid_approval(tmp_path, all_passing=False)
    gate = make_gate(approval_path=approval_path)
    status = gate.check()
    gate03 = next(c for c in status.conditions if c.name == "GATE-03")
    assert gate03.passed is False


def test_gate03_passes_valid_approval(make_gate, tmp_path):
    """GATE-03 passes when valid live_approval.json with all snapshot fields True."""
    approval = {
        "approved_at": "2026-03-20T14:32:00+00:00",
        "approved_by": "test-operator",
        "gate_snapshot": {
            "gate_01_models": True,
            "gate_02_paper_period": True,
            "gate_03_approval": False,
            "gate_04_circuit_breaker": True,
        },
    }
    approval_path = tmp_path / "live_approval.json"
    approval_path.write_text(json.dumps(approval))
    gate = make_gate(approval_path=approval_path)
    status = gate.check()
    gate03 = next(c for c in status.conditions if c.name == "GATE-03")
    assert gate03.passed is True


# ---------------------------------------------------------------------------
# GATE-04: Daily loss circuit breaker
# ---------------------------------------------------------------------------


def test_gate04_no_breach_below_threshold(make_gate, tmp_path):
    """record_daily_loss returns False when loss is below 10% threshold."""
    gate = make_gate()
    # $10 loss on $10,000 bankroll = 0.1% — well below 10%
    result = gate.record_daily_loss(10.0, 10000.0)
    assert result is False


def test_gate04_breach_invalidates_approval(make_gate, tmp_path):
    """record_daily_loss returns True and renames approval file on breach."""
    approval = {
        "approved_at": "2026-03-20T14:32:00+00:00",
        "approved_by": "test-operator",
        "gate_snapshot": {
            "gate_01_models": True,
            "gate_02_paper_period": True,
            "gate_03_approval": False,
            "gate_04_circuit_breaker": True,
        },
    }
    approval_path = tmp_path / "live_approval.json"
    approval_path.write_text(json.dumps(approval))
    gate = make_gate(approval_path=approval_path, daily_loss_pct=0.10)
    # $1100 loss on $10,000 bankroll = 11% — exceeds 10% threshold
    result = gate.record_daily_loss(1100.0, 10000.0)
    assert result is True
    # Approval file renamed to .disabled
    assert not approval_path.exists()
    assert (tmp_path / "live_approval.json.disabled").exists()


def test_gate04_daily_reset(make_gate, tmp_path):
    """Daily loss resets to 0 when UTC date advances to next day."""
    gate = make_gate(daily_loss_pct=0.10)
    # Record $900 loss on $10,000 — below 10% but accumulates
    gate.record_daily_loss(900.0, 10000.0)
    # Advance date by one day
    future_dt = datetime(2099, 1, 2, 0, 0, 1, tzinfo=UTC)
    with patch(
        "sharpedge_venue_adapters.capital_gate.datetime",
        wraps=datetime,
    ) as mock_dt:
        mock_dt.now.return_value = future_dt
        # Fresh day — another $900 should NOT trigger the breaker
        result = gate.record_daily_loss(900.0, 10000.0)
    assert result is False


def test_gate04_check_fails_after_breach(make_gate, tmp_path):
    """check() returns GATE-03 failed after breach renamed approval to .disabled."""
    approval = {
        "approved_at": "2026-03-20T14:32:00+00:00",
        "approved_by": "test-operator",
        "gate_snapshot": {
            "gate_01_models": True,
            "gate_02_paper_period": True,
            "gate_03_approval": False,
            "gate_04_circuit_breaker": True,
        },
    }
    approval_path = tmp_path / "live_approval.json"
    approval_path.write_text(json.dumps(approval))
    gate = make_gate(approval_path=approval_path, daily_loss_pct=0.10)
    gate.record_daily_loss(1100.0, 10000.0)
    # Approval file is now .disabled — GATE-03 must fail
    status = gate.check()
    gate03 = next(c for c in status.conditions if c.name == "GATE-03")
    assert gate03.passed is False


# ---------------------------------------------------------------------------
# assert_ready() contract
# ---------------------------------------------------------------------------


def test_assert_ready_collects_all_failures(make_gate, tmp_path):
    """assert_ready() raises CapitalGateError containing all 4 gate failures."""
    # Gate with nothing configured — all four gates should fail
    gate = make_gate()
    with pytest.raises(CapitalGateError) as exc_info:
        gate.assert_ready()
    msg = str(exc_info.value)
    # All four gate names must appear in the error message
    assert "GATE-01" in msg
    assert "GATE-02" in msg
    assert "GATE-03" in msg
    assert "GATE-04" in msg


def test_assert_ready_raises_capital_gate_error(make_gate, tmp_path):
    """assert_ready() raises CapitalGateError specifically (not generic RuntimeError)."""
    gate = make_gate()
    with pytest.raises(CapitalGateError):
        gate.assert_ready()
