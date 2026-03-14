---
phase: 6
slug: multi-venue-quant-infrastructure
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-14
---

# Phase 6 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | pyproject.toml (existing in each package) |
| **Quick run command** | `cd packages/venue_adapters && uv run pytest tests/ -x -q` |
| **Full suite command** | `uv run pytest packages/venue_adapters/tests/ packages/data_feeds/tests/ -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd packages/venue_adapters && uv run pytest tests/ -x -q`
- **After every plan wave:** Run `uv run pytest packages/venue_adapters/tests/ packages/data_feeds/tests/ -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 6-01-01 | 01 | 0 | VENUE-01 | unit | `uv run pytest tests/test_venue_adapter_protocol.py -x` | ❌ W0 | ⬜ pending |
| 6-01-02 | 01 | 0 | VENUE-02 | unit | `uv run pytest tests/test_market_catalog.py -x` | ❌ W0 | ⬜ pending |
| 6-02-01 | 02 | 1 | VENUE-03 | unit | `uv run pytest tests/test_kalshi_adapter.py -x` | ❌ W0 | ⬜ pending |
| 6-02-02 | 02 | 1 | VENUE-04 | unit | `uv run pytest tests/test_polymarket_adapter.py -x` | ❌ W0 | ⬜ pending |
| 6-03-01 | 03 | 1 | VENUE-05 | unit | `uv run pytest tests/test_sportsbook_adapter.py -x` | ❌ W0 | ⬜ pending |
| 6-03-02 | 03 | 1 | PRICE-01 | unit | `uv run pytest tests/test_no_vig_n_outcome.py -x` | ❌ W0 | ⬜ pending |
| 6-04-01 | 04 | 2 | MICRO-01 | unit | `uv run pytest tests/test_microstructure.py -x` | ❌ W0 | ⬜ pending |
| 6-04-02 | 04 | 2 | DISLO-01 | unit | `uv run pytest tests/test_dislocation.py -x` | ❌ W0 | ⬜ pending |
| 6-05-01 | 05 | 3 | RISK-01 | unit | `uv run pytest tests/test_exposure_book.py -x` | ❌ W0 | ⬜ pending |
| 6-05-02 | 05 | 3 | SETTLE-01 | unit | `uv run pytest tests/test_settlement_ledger.py -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `packages/venue_adapters/tests/test_venue_adapter_protocol.py` — stubs for VENUE-01 (adapter contract)
- [ ] `packages/venue_adapters/tests/test_market_catalog.py` — stubs for VENUE-02 (lifecycle states)
- [ ] `packages/venue_adapters/tests/test_kalshi_adapter.py` — stubs for VENUE-03 (Kalshi CLOB)
- [ ] `packages/venue_adapters/tests/test_polymarket_adapter.py` — stubs for VENUE-04 (Polymarket CLOB)
- [ ] `packages/venue_adapters/tests/test_sportsbook_adapter.py` — stubs for VENUE-05 (multi-book odds)
- [ ] `packages/venue_adapters/tests/test_no_vig_n_outcome.py` — stubs for PRICE-01 (N-outcome devig)
- [ ] `packages/venue_adapters/tests/test_microstructure.py` — stubs for MICRO-01 (fill-hazard model)
- [ ] `packages/venue_adapters/tests/test_dislocation.py` — stubs for DISLO-01 (consensus deviation)
- [ ] `packages/venue_adapters/tests/test_exposure_book.py` — stubs for RISK-01 (exposure/Kelly)
- [ ] `packages/venue_adapters/tests/test_settlement_ledger.py` — stubs for SETTLE-01 (ledger replay)
- [ ] `packages/venue_adapters/tests/conftest.py` — shared fixtures (mock venue responses, sample market states)
- [ ] `packages/venue_adapters/pyproject.toml` — package scaffold with pytest dependency

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Live Kalshi CLOB order book snapshot ingestion | VENUE-03 | Requires live API key + network | Run `uv run python -c "from sharpedge_venue_adapters.kalshi import KalshiAdapter; a = KalshiAdapter(); print(a.getOrderBook('KXBTCD-25MAR14'))"` with real KALSHI_API_KEY |
| Live Polymarket market discovery | VENUE-04 | Requires live network access | Run `uv run python -c "from sharpedge_venue_adapters.polymarket import PolymarketAdapter; a = PolymarketAdapter(); print(a.listMarkets()[:3])"` |
| Multi-book odds ingestion via The Odds API | VENUE-05 | Requires The Odds API key | Run `uv run python -c "from sharpedge_venue_adapters.sportsbook import SportsbookAdapter; a = SportsbookAdapter(api_key=...); print(a.getOrderBook('nba'))"` |
| Settlement replay determinism | SETTLE-01 | Requires populated ledger_entries table | Insert 10 test entries, replay, verify PnL matches manual calculation |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
