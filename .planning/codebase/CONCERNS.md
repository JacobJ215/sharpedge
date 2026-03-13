# Codebase Concerns

> Technical debt, known issues, security gaps, performance risks, and fragile areas.

---

## Critical Tech Debt

- **Unimplemented DB methods** — `packages/models/src/sharpedge_models/backtesting.py` lines 339–366: 4 stub methods blocking production backtesting persistence
- **Deprecated datetime usage** — `datetime.utcnow()` used in models package (not in database layer); should be `datetime.now(timezone.utc)`
- **Zero test coverage** — No tests exist across the entire codebase

---

## Security Issues

- **Missing env var validation** — Only the bot package validates env vars; models and analytics packages use them without validation
- **No input validation on agent tools** — Tools accepting game queries have no schema/input validation
- **No rate limiting** — Webhook handlers have no rate limiting

---

## Performance Bottlenecks

- **Oversized modules** — `visualizations` module is 896 lines; `bot/tools` module is 576 lines — both need refactoring per the <500 line limit
- **No connection pooling** — External API calls have no connection pooling or request timeouts
- **No caching layer** — Redis not yet implemented; all data fetched fresh each request

---

## Fragile Areas

- **Webhook payload parsing** — No schema validation on incoming webhook payloads
- **No retry logic** — External API calls (Odds API, Kalshi, Polymarket) have no retry/backoff
- **Silent failure** — Analytics package gracefully degrades when not installed, masking errors in production

---

## Missing Infrastructure

- **No monitoring/alerting** — No Sentry or equivalent error tracking integration
- **No DB migrations** — No Alembic or migration tooling for schema evolution
- **No rate limit config** — Background jobs have no configurable rate limiting
- **No test fixtures/factories** — No shared test data factories, making tests harder to add

---

## Known Issues

- Walk-forward backtester persistence layer stubs (`save_result`, `load_results`, etc.) mean backtest results are not stored and cannot be queried historically
- Arbitrage detection and EV calculations are not covered by any automated tests, making regressions undetectable
