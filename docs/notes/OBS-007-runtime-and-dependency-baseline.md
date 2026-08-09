---
id: OBS-007
title: Runtime targets, dependency currency, and reproducibility
type: OBS
date: 2026-08-09
depends-on: []
superseded-by: null
---

## C — Context

Whether the declared environment matches the actual one, and whether a second machine
could reproduce it.

## E — Evidence

- **E1 · Declared Python floor is 3.9; actual interpreter is 3.13.12.**
  `pyproject.toml` → `requires-python = ">=3.9"`; `.venv/bin/python -V` → `Python 3.13.12`.
- **E2 · The 3.9 claim is false.** 523 PEP 604 union annotations (`X | None`) appear across
  `src/kiku`, and only 80 of 97 files carry `from __future__ import annotations`. On 3.9,
  any un-shielded module raises `TypeError` at import.
- **E3 · The Python side has no lockfile; the frontend does.** No `requirements.lock`,
  `uv.lock`, `poetry.lock`, or `pdm.lock` exists, and all Python deps are floor-pinned
  (`>=`) with no upper bounds. `frontend/package-lock.json` **is** present and tracked
  (`git ls-files`), so the npm side is reproducible.
- **E4 · Dependencies are few and current.** Core: SQLAlchemy 2.0+, Click 8, Rich 13,
  numpy, mutagen, alembic, httpx, thefuzz. Optional extras keep heavy things out of the
  core: `analysis` (essentia, librosa), `api` (fastapi, uvicorn), `hunting`, `rekordbox`,
  `visualizer` (dash, plotly). Frontend runtime deps: three (`OBS-004/E1`).
- **E5 · Extras are load-bearing but undeclared as such.** `kiku serve` requires the `api`
  extra; the README's quick start installs `.[api]`, but `pyproject.toml`'s `dev` extra
  pulls only `rekordbox`, `pytest`, `pytest-cov` — so `pip install -e '.[dev]'` yields an
  environment where the API tests cannot run.
- **E6 · Configuration is file-only, with one exception.** `src/kiku/config.py` reads
  `~/.kiku/config.toml`. The single environment override is `KIKU_MUSIC_ROOTS`
  (`config.py:48`). The database path has none (`OBS-003/E7`).
- **E7 · There is no container or environment manifest.** No `Dockerfile`, no
  `compose.yaml`, no `.tool-versions`, no `.python-version`.
- **E8 · Local orchestration is one good script.** `dev.sh` starts backend and frontend
  together, preflight-checks `.venv/` and `node_modules/`, colour-prefixes both log
  streams, and traps for clean shutdown.
- **E9 · Development happens on many branches.** 15+ local and remote branches, plus a
  `trees/` worktree directory and `.claude/worktrees/`.

## K — Conclusions

- **K1 · The dependency posture is genuinely good.** E4: few dependencies, current
  versions, heavy optional work correctly isolated behind extras. This is a real strength
  and should be preserved by any change proposed elsewhere.
- **K2 · The stated runtime contract is wrong.** E1+E2: `>=3.9` is not merely optimistic,
  it is contradicted by 523 annotations. The true floor is 3.10.
- **K3 · The Python environment is not reproducible.** E3+E7: floor-only pins with no lock
  and no pinned interpreter means "it works here" carries no information about anywhere
  else. The asymmetry is instructive — npm gave the author a lockfile by default and it is
  committed; Python did not, and so there is none. Combined with
  `OBS-003/K2` (schema cannot be built from scratch), **the repository currently cannot
  provision a working instance of itself on a clean machine.** This is the single
  strongest statement in the whole analysis, and it is a conjunction of two independent
  defects, either of which alone would be survivable.
- **K4 · E6 compounds K3.** Even a correctly built environment cannot be pointed at a
  different database without editing a file in `$HOME`, which rules out per-test and
  per-container isolation.
- **K5 · E8 shows the author's instincts are right.** `dev.sh` is exactly the ergonomics
  that E7 is missing at the next level up; the gap is scope, not care.

## Q — Open

- **Q1.** Is `uv` acceptable as the pin/lock tool, given `dev.sh` currently assumes a plain
  `.venv`? Changing this touches the one script that works well.
