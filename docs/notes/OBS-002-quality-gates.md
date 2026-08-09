---
id: OBS-002
title: Test coverage and automated quality gates
type: OBS
date: 2026-08-09
depends-on: []
superseded-by: null
---

## C — Context

What stops a bad change from reaching `main` today, and what does not.

## D — Definitions

- **D1 · Gate.** A check that runs *without being remembered* — i.e. enforced by CI, a
  pre-commit hook, or a build step. A command a human must choose to type is not a gate.

## E — Evidence

- **E1 · Backend suite passes.** `python -m pytest tests/ -q` → **426 passed** in 10.95s,
  10 warnings. 39 test files, 5,131 LOC.
- **E2 · Frontend tests: zero.** No `*.test.*` or `*.spec.*` under `frontend/src`. No test
  runner in `frontend/package.json` — the only scripts are `dev`, `build`, `preview`,
  `prepare`, `check`, `check:watch`. 92 components, 0 tests.
- **E3 · Type-check is clean.** `npx svelte-check --tsconfig ./tsconfig.json` →
  **0 errors and 0 warnings** across 133 files.
- **E4 · No CI.** No `.github/` directory exists. Nothing runs on push or PR.
- **E5 · No pre-commit.** No `.pre-commit-config.yaml`.
- **E6 · No Python linter or formatter configured.** `pyproject.toml` declares no
  `[tool.ruff]`, `[tool.black]`, or `[tool.mypy]` section. Dev extras are `pytest` and
  `pytest-cov` only.
- **E7 · No JS linter or formatter configured.** No ESLint or Prettier config, and neither
  appears in `devDependencies`.
- **E8 · No coverage threshold.** `pytest-cov` is installed but no `--cov-fail-under` is
  configured anywhere; coverage is never measured in a gate.
- **E9 · Untested backend areas.** No test file targets `planner.py`, `filler.py`,
  `reorder.py`, `cli.py`, or `db/store.py` by name. 13 of 39 test files cover the API layer.
- **E10 · Warnings are accumulating.** 10 `DeprecationWarning`s for `datetime.utcnow()`
  across `albums.py`, `metadata/correct.py` and others, unaddressed.

## K — Conclusions

- **K1 · Gate count is zero.** By D1, this repository has **no** automated quality gates.
  Every check in E1/E3 is real and currently green, but green *by discipline*, not by
  construction. The failure mode is not "the checks are bad" — it is "the checks stop
  running the first time someone is in a hurry."
- **K2.** The 426-test backend suite is a genuine asset: fast (11s), broad across the
  domain layer, and passing. It is the strongest engineering artifact in the project.
- **K3.** The frontend has 54% of the code (`OBS-001/K2`) and 0% of the tests. Every
  regression there is found by the author, by hand, in a browser.
- **K4.** E10 is the signature of missing gates: warnings that a CI run would surface
  weekly instead accumulate silently for months.

## Q — Open

- **Q1.** What is actual backend line coverage? Never measured (E8), so K2's "broad" is
  inferred from test-file topology, not from data.
