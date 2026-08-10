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

> **Re-check 2026-08-09 — partly resolved by [[PLN-001]]/P3.** E1–E10 record the state
> `CLM-001` and `CLM-003` derive from. **K1 no longer holds**: the gate count is now four,
> not zero. See **K5**. E2 (zero frontend tests) still stands — that is P8.

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

- **K5 · Resolved 2026-08-09 — the gate count is four.** `.github/workflows/ci.yml` runs
  on push-to-main and every PR: `ruff check` · `ruff format --check` · `pytest` (including
  the P1 migration invariant) · `svelte-check` + `vite build`. Each was verified by being
  broken on purpose. Closes E4, E6, E7 and, by construction, E10 — the four
  `datetime.utcnow()` calls were fixed as part of clearing lint.
- **R1 · The 479 lint findings were mostly noise, but not entirely.** Fixed: 6 `F821`
  undefined-name in `db/store.py` (quoted annotations over function-local imports; the
  14 local imports were unnecessary since `models.py` never imports `store.py`), 3 dead
  assignments, and a `subprocess.run` with no `check=`. Five rules are ignored with written
  reasons in `pyproject.toml`: `B008` as a genuine false positive (FastAPI's `Depends()`
  idiom), and `BLE001`/`S110`/`DTZ005`/`C408`/`RUF059` as real-but-deferred.
- **K6** [R1] ⇒ The deferred ignores are the honest form of a backlog: each entry names a
  count and a reason, and *deleting the line is how the work gets scheduled*. This keeps
  `CLM-003/K5b` (the 49 blind excepts) visible rather than silently blessed.
- **R2 · CI failed on its first real run, and the cause was invisible locally.** 102 type
  errors across 22 files, all cascading from `Cannot find module
  '$lib/data/resource.svelte'`. `.gitignore` carried a bare `data/` for the root SQLite
  directory; unanchored, it also matched `frontend/src/lib/data/`, so four P5 commits
  landed the call sites while omitting the module they import. `git add -A` reported
  nothing wrong, because the path was *ignored*, not missed. Fixed by anchoring every
  root-only pattern (`/data/`, `/models/`, `/outputs/`, `/tmp/`, `/dist/`, `/build/`,
  `/venv/`, `/env/`, `/.specs/`); `__pycache__`, `.eggs` and `.pytest_cache` stay
  unanchored because they genuinely occur at any depth.
- **K8** [R2] ⇒ This is the strongest available evidence for `CLM-003/K4`, and it arrived
  by itself. Local verification had been thorough — type-check, build, a browser driving
  the real library — and every bit of it passed, because all of it ran against a working
  tree containing an untracked file. **Only a clean checkout could see the defect, and
  nothing in the project had ever performed one.** The gate found the bug on its first
  attempt, which is roughly the best return a day of work can have.
- **K9** [R2] ⇒ Corollary worth keeping: a gate that has never run is not a gate. P3 was
  "done" locally for several hours while shipping a frontend that could not build.

- **K10 · E9 is closed for the sequencing modules (2026-08-10).** `planner.py`,
  `filler.py` and `reorder.py` now have named test files — 43 invariant tests, which found
  a live artist-cooldown bug in `fill_set` on their first run. `cli.py` and `db/store.py`
  remain untested; `cli.py` is where `OBS-002/R1`'s broken `kiku search` hid.
- **K7 · E8 is unchanged and now cheap to close.** Coverage is still unmeasured; with a
  gate in place, adding `--cov-fail-under` is a one-line change whenever a number is wanted.

## Q — Open

- **Q1.** What is actual backend line coverage? Never measured (E8), so K2's "broad" is
  inferred from test-file topology, not from data.
- **Q2.** CI runs a single interpreter (3.13). `OBS-007/Q3` notes that the essentia pin is
  coupled to the interpreter by wheel tags — a matrix would surface that, at the cost of
  installing the audio stack in CI.
