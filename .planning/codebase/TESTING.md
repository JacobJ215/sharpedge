# Testing Patterns

**Analysis Date:** 2026-03-21

## Test Framework

**Runner:**

- **Python:** `pytest` (workspace dev dependency in root `pyproject.toml`; package-specific pins e.g. `pytest>=9.0.2` in `packages/trading_swarm/pyproject.toml`).
- **Web:** Vitest `^2.1.0` — config: `apps/web/vitest.config.ts`.
- **Mobile:** `flutter_test` from Flutter SDK — declared in `apps/mobile/pubspec.yaml` under `dev_dependencies`.

**Assertion Library:**

- **Web:** Vitest `expect` + `@testing-library/jest-dom` matchers (loaded in `apps/web/src/test-setup.ts`).
- **Python:** Plain `assert` and `pytest` fixtures.
- **Dart:** `package:flutter_test/flutter_test.dart` `expect` / `finders`.

**Run Commands:**

```bash
# Python — entire uv workspace (from repo root; see README.md)
uv run pytest

# Web — from apps/web
npm test                 # vitest run
npm run test:watch       # vitest watch

# Dart / Flutter — from apps/mobile
flutter test
```

**Jest:** Not used; web tests use Vitest only (`apps/web/package.json`).

## Test File Organization

**Location:**

- **Repo-level Python:** `tests/unit/...`, `tests/integration/...` with root `tests/conftest.py`.
- **Python packages:** Co-located package tests under `packages/<name>/tests/` (e.g. `packages/venue_adapters/tests/`, `packages/trading_swarm/tests/`).
- **Apps:** `apps/webhook_server/tests/`, `apps/bot/tests/`.
- **Web (Vitest):** Under `apps/web/src/test/` with `*.test.tsx` files (not co-located next to components).
- **Flutter:** `apps/mobile/test/*.dart` (e.g. `widget_test.dart`, `offline_cache_test.dart`).

**Naming:**

- Python: `test_*.py` and `tests/` directories; pytest `testpaths = ["tests"]` in packages that set `[tool.pytest.ini_options]` (e.g. `packages/venue_adapters/pyproject.toml`, `packages/trading_swarm/pyproject.toml`).
- Vitest: `*.test.tsx` in `apps/web/src/test/`.
- Flutter: `*_test.dart` suffix.

**Structure:**

```text
tests/
├── conftest.py
├── unit/
│   └── ...
└── integration/
packages/<pkg>/tests/
apps/web/src/test/
apps/mobile/test/
```

## Test Structure

**Suite Organization:**

Vitest uses `describe` / `it` with explicit imports from `vitest`:

```typescript
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { AlphaBadge } from '@/components/ui/alpha-badge'

describe('AlphaBadge', () => {
  it('renders PREMIUM badge with correct text', () => {
    render(<AlphaBadge badge="PREMIUM" />)
    expect(screen.getByText('PREMIUM')).toBeTruthy()
  })
})
```

(Source: `apps/web/src/test/dashboard.test.tsx`.)

**Patterns:**

- **Setup:** `beforeEach(() => { vi.clearAllMocks() })` for mocked modules (`apps/web/src/test/auth-guard.test.tsx`).
- **Teardown:** Rely on Vitest isolation; Python uses function-scoped fixtures by default.
- **Assertion:** Testing Library `screen` / `waitFor` for async UI; Python plain asserts.

## Mocking

**Framework:**

- **Web:** Vitest `vi.mock` for ESM-friendly mocks (`apps/web/src/test/auth-guard.test.tsx` mocks `next/navigation` and `@/lib/supabase` before dynamic imports).
- **Python:** `unittest.mock` (`MagicMock`, `AsyncMock`) in package `conftest.py` files (e.g. `packages/venue_adapters/tests/conftest.py`).

**Patterns:**

```typescript
const mockReplace = vi.fn()
vi.mock('next/navigation', () => ({
  useRouter: () => ({ replace: mockReplace }),
}))
```

(Source: `apps/web/src/test/auth-guard.test.tsx`.)

**What to Mock:**

- Next.js router, Supabase client, and other browser/external boundaries in unit component tests.
- HTTP and venue IO in Python unit tests via fixtures and mocks.

**What NOT to Mock:**

- **Contract tests** intentionally call real APIs when env vars are present — gated by pytest markers and skip fixtures (`packages/trading_swarm/tests/contract/conftest.py`, markers `contract` / `smoke` in `packages/trading_swarm/pyproject.toml`).

## Fixtures and Factories

**Test Data:**

Root shared fixtures:

```python
import pytest

@pytest.fixture
def sample_ev_calc():
    """Minimal EVCalculation-like dict for testing alpha composition."""
    return {"prob_edge_positive": 0.72, "odds": -110}
```

(Source: `tests/conftest.py`.)

Package-scoped fixtures for domain objects (e.g. `mock_orderbook`, `mock_market_dict` in `packages/venue_adapters/tests/conftest.py`).

**Location:**

- `tests/conftest.py` — cross-cutting repo tests.
- `packages/<pkg>/tests/conftest.py` — package-specific.
- `packages/trading_swarm/tests/contract/conftest.py` — credential checks and `pytest.skip`.

## Coverage

**Requirements:** No enforced coverage threshold found in `vitest.config.ts` or root `pyproject.toml`.

**View Coverage:** Add `--cov` when running pytest if you introduce `pytest-cov`; not configured by default in the explored manifests.

## Test Types

**Unit Tests:**

- Python: Fast, isolated logic under `tests/unit/...` and `packages/*/tests/test_*.py` (e.g. `tests/unit/models/test_alpha.py`).
- Web: Component behavior in `apps/web/src/test/*.test.tsx`.

**Integration Tests:**

- Python: `tests/integration/` (e.g. `test_rls_endpoints.py` with `FastAPI` `TestClient`, skip unless `SUPABASE_URL` set).
- Trading swarm: `packages/trading_swarm/tests/test_integration_pipeline.py`, `tests/integration/test_alpha_pipeline.py`.

**E2E Tests:**

- Not detected as a separate Playwright/Cypress suite; Flutter `testWidgets` provides widget-level smoke (`apps/mobile/test/widget_test.dart`).

## CI/CD

**CI Pipeline:** No `.github/workflows/*.yml` files detected in the workspace snapshot; integration tests document themselves as skipped without env (e.g. `tests/integration/test_rls_endpoints.py`).

**Local parity:** Use `uv run pytest` and `npm test` in `apps/web` before claiming green builds.

## Common Patterns

**Async Testing:**

```typescript
mockGetSession.mockResolvedValue({ data: { session: null } })
const { default: DashboardLayout } = await import('@/app/(dashboard)/layout')
render(<DashboardLayout>children</DashboardLayout>)
await waitFor(() => {
  expect(mockReplace).toHaveBeenCalledWith('/auth/login')
})
```

(Source: `apps/web/src/test/auth-guard.test.tsx`.)

**Error Testing / Environment Gating:**

```python
pytestmark = pytest.mark.skipif(
    not os.getenv("SUPABASE_URL"),
    reason="integration test — requires SUPABASE_URL",
)
```

(Source: `tests/integration/test_rls_endpoints.py`.)

**Flutter smoke:**

```dart
void main() {
  testWidgets('App smoke test', (WidgetTester tester) async {
    await tester.pumpWidget(const SharpEdgeApp());
    expect(find.text('SharpEdge'), findsWidgets);
  });
}
```

(Source: `apps/mobile/test/widget_test.dart`.)

---

*Testing analysis: 2026-03-21*
