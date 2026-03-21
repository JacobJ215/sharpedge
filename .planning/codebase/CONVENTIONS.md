# Coding Conventions

**Analysis Date:** 2026-03-21

## Naming Patterns

**Files:**

- **Python:** Modules and packages use `snake_case` (e.g. `compose_alpha` in `packages/models/src/...`). Test modules follow `test_*.py` under `tests/` trees.
- **TypeScript/React (web):** App Router routes use Next.js segment folders such as `apps/web/src/app/(dashboard)/...`. Components often use `kebab-case` filenames (e.g. `alpha-badge.tsx`, `kelly-calculator.tsx`) with **PascalCase** default exports.
- **Dart (mobile):** `snake_case` for Dart files (e.g. `main.dart`, tests in `apps/mobile/test/`).

**Functions:**

- **Python:** `snake_case` for functions and methods; test functions are `test_*` (see `tests/unit/models/test_alpha.py`).
- **TypeScript:** `camelCase` for functions and handlers (e.g. `handleSubmit` in page components under `apps/web/src/app/`).

**Variables:**

- **Python:** `snake_case` for locals and module state.
- **TypeScript:** `camelCase` for variables and hooks; React components remain PascalCase.

**Types:**

- **TypeScript:** PascalCase for components and many types; `strict` mode is enabled in `apps/web/tsconfig.json`.
- **Python:** Pydantic models and dataclasses use PascalCase class names (e.g. imports from `sharpedge_models` in tests).

## Code Style

**Formatting:**

- **Python:** Ruff formatter — `quote-style = "double"`, `indent-style = "space"`, `line-length = 100` in `ruff.toml`. Run `uv run ruff format .` (pair with `ruff check` as in `README.md`).
- **TypeScript:** No Prettier or Biome config detected in the repo; rely on TypeScript compiler and editor defaults.
- **Dart:** `flutter_lints` via `apps/mobile/analysis_options.yaml` (includes `package:flutter_lints/flutter.yaml`).

**Linting:**

- **Python:** Ruff — rule sets and ignores in `ruff.toml` (`select`: E, W, F, I, N, UP, B, SIM, T20, TCH, RUF; `ignore`: E501). Isort integration uses `known-first-party` for `sharpedge_*` packages listed in `ruff.toml`.
- **TypeScript:** ESLint config files not detected; quality gate is **`strict: true`** in `apps/web/tsconfig.json`.
- **Dart:** `analysis_options.yaml` enables `avoid_print`, `prefer_const_constructors`, `prefer_const_declarations`.

## Import Organization

**Order (Python):**

1. Standard library
2. Third-party
3. First-party `sharpedge_*` packages (Ruff isort `known-first-party` in `ruff.toml`)

**Path Aliases (web):**

- `@/*` → `apps/web/src/*` (see `apps/web/tsconfig.json` and `apps/web/vitest.config.ts` `resolve.alias`).

**Order (TypeScript):**

- Typical pattern: external packages first, then `@/...` aliases (see `apps/web/src/test/dashboard.test.tsx`).

## Error Handling

**Patterns:**

- **Python HTTP boundaries:** FastAPI apps expose routes with `TestClient` in integration tests (`tests/integration/test_rls_endpoints.py` uses `raise_server_exceptions=False` on the client for controlled error paths).
- **Integration gating:** Use `pytest.mark.skipif` or session fixtures that `pytest.skip` when credentials or env vars are missing (e.g. `packages/trading_swarm/tests/contract/conftest.py`, module-level `pytestmark` in `tests/integration/test_rls_endpoints.py`).
- **TypeScript UI:** Async auth and routing flows use `waitFor` from Testing Library after rendering (see `apps/web/src/test/auth-guard.test.tsx`).

## Logging

**Framework:** Language-default (`print` discouraged in Dart via `avoid_print`; Ruff includes `T20` for print usage in Python).

**Patterns:**

- Prefer structured logging at service boundaries where implemented; no single shared logging wrapper documented in config files.

## Comments

**When to Comment:**

- File-level docstrings in Python for integration test requirements and env vars (e.g. `tests/integration/test_rls_endpoints.py`).
- Block comments above Vitest suites for feature wiring references (e.g. `apps/web/src/test/auth-guard.test.tsx`).

**JSDoc/TSDoc:**

- Sparse; tests and complex UI sometimes use short leading comment blocks rather than full TSDoc on every export.

## Function Design

**Size:** No enforced line limits in TypeScript; Python line length 100 via Ruff (E501 ignored in lint, handled by formatter).

**Parameters:** Pydantic and typed signatures at package boundaries (`sharpedge-venue-adapters` depends on `pydantic>=2.0` per `packages/venue_adapters/pyproject.toml`).

**Return Values:** Explicit types in strict TS; Python tests assert on dataclasses and primitives (`tests/unit/models/test_alpha.py`).

## Module Design

**Exports:** Next.js App Router uses default exports for `page.tsx` / `layout.tsx`; React components under `apps/web/src/components/` use named exports where tests import them (e.g. `AlphaBadge` from `@/components/ui/alpha-badge` in `apps/web/src/test/dashboard.test.tsx`).

**Barrel Files:** Not required project-wide; import from concrete module paths.

## Boundaries & Validation

- **Config/secrets:** Environment variables documented in `README.md` and test modules; do not commit `.env` (see workspace rules). `.env.example` is the template reference.
- **API surface:** Webhook server entry at `sharpedge_webhooks.main:app` for HTTP tests (`tests/integration/test_rls_endpoints.py`).
- **Data validation:** Pydantic v2 in packages that declare it; keep validation at IO boundaries (HTTP, adapters, external JSON).

---

*Convention analysis: 2026-03-21*
