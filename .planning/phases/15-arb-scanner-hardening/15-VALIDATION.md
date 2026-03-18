# Phase 15: Arb Scanner Hardening — Validation Architecture

Extracted from `15-RESEARCH.md` (Validation Architecture section).

---

## Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (project-wide) |
| Config file | `pyproject.toml` (root or per-package) |
| Quick run command | `uv run pytest packages/analytics/tests/ -x -q` |
| Full suite command | `uv run pytest packages/ -x -q` |

---

## Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ARB-01 | `discover_and_wire()` fetches markets, matches pairs, calls `register_pair()` and `wire()` | unit (mocked clients) | `uv run pytest packages/analytics/tests/test_realtime_scanner.py::test_discover_and_wire -x` | Wave 0 |
| ARB-01 | Auto-discovery produces correct `MarketPair.polymarket_no_token` from Gamma token array | unit | `uv run pytest packages/analytics/tests/test_realtime_scanner.py::test_no_token_extraction -x` | Wave 0 |
| ARB-02 | `asyncio.gather()` fires both order placements simultaneously | unit (mocked order clients) | `uv run pytest packages/analytics/tests/test_realtime_scanner.py::test_dual_order_placement -x` | Wave 0 |
| ARB-03 | `_check_pair()` returns early + logs warning when Kalshi data stale | unit | `uv run pytest packages/analytics/tests/test_realtime_scanner.py::test_staleness_guard_kalshi -x` | Wave 0 |
| ARB-03 | `_check_pair()` returns early + logs warning when Poly data stale | unit | `uv run pytest packages/analytics/tests/test_realtime_scanner.py::test_staleness_guard_poly -x` | Wave 0 |
| ARB-03 | `_check_pair()` does NOT fire staleness guard when both timestamps are 0.0 (uninitialized) | unit | `uv run pytest packages/analytics/tests/test_realtime_scanner.py::test_staleness_guard_uninit -x` | Wave 0 |
| ARB-04 | `poly_no_ask` uses real orderbook ask when `polymarket_no_token` is None | unit (mocked get_orderbook) | `uv run pytest packages/analytics/tests/test_realtime_scanner.py::test_no_token_real_ask -x` | Wave 0 |
| ARB-04 | `poly_no_ask` uses `1 - yes_ask` derivation when NO token orderbook returns no liquidity | unit | `uv run pytest packages/analytics/tests/test_realtime_scanner.py::test_no_token_fallback -x` | Wave 0 |

---

## Sampling Rate

- **Per task commit:** `uv run pytest packages/analytics/tests/test_realtime_scanner.py -x -q`
- **Per wave merge:** `uv run pytest packages/ -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

---

## Wave 0 Gaps

- [ ] `packages/analytics/tests/test_realtime_scanner.py` — covers all ARB-01 through ARB-04 scenarios (does not exist yet)
- [ ] `packages/analytics/tests/__init__.py` — may be needed if tests/ dir doesn't exist
- [ ] `packages/data_feeds/src/sharpedge_feeds/polymarket_clob_orders.py` — stub module for ARB-02 (Wave 0 stub only)
