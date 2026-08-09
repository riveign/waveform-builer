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

> **Re-check 2026-08-09 — resolved by [[PLN-001]]/P2.** E1–E9 record the state that
> motivated the fix; `CLM-001` and `CLM-004` derive from them. What changed is in **K6**,
> and **K2 was wrong** — see R1.

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

- **R1 · K2 understated the floor.** K2 said the true minimum was 3.10, reasoning only from
  PEP 604 unions. `config.py:8` imports `tomllib` at module level, which is stdlib from
  **3.11**. No `match` statements and no 3.12+ syntax exist, so 3.11 is exact. Declared as
  `>=3.11`; `.python-version` pins 3.13 to match the working interpreter.
- **R2 · Two dependencies were undeclared and only a clean install could reveal them.**
  Both were present in the author's `.venv` by accident and absent from `pyproject.toml`:
  - `python-multipart` — `sets.py:110` takes an `UploadFile`, and FastAPI raises at import
    time without it. Every API test errored at collection in a clean clone.
  - `scikit-learn` + `joblib` — `analysis/autotag.py:281,412` train and persist the energy
    model. `kiku autotag` would have failed on any fresh install, on any machine.
- **K6 · Resolved 2026-08-09.**
  - `requires-python = ">=3.11"` (R1); `.python-version` → 3.13.
  - `uv.lock` committed: 100 packages, all extras including `analysis`.
  - `dev` extra now pulls `api` + `hunting` + `ml` + `rekordbox`, so `pytest` runs from a
    single install — closes E5.
  - New `ml` extra (scikit-learn, joblib), separate from `analysis` because model training
    reads DB features rather than audio.
  - `scripts/setup.sh`: `uv sync --extra dev --extra analysis` + `npm ci`; `--lean` drops
    the audio stack. README and `dev.sh` preflight both point at it.
  - `.venv` converged onto the lock — one environment, no parallel pip-installed set.
  - Verified from a clean clone: setup → **429 tests pass**, `svelte-check` 0/0 across 341
    files, and `kiku stats` builds its own database and reports an empty library.
- **K7** [R2] ⇒ The two undeclared dependencies are the same failure as `OBS-003/R1,R2`:
  a divergence between the described system and the running one, invisible from inside the
  author's machine, surfaced immediately once something built the project from scratch. The
  general form of `CLM-003/K4`.

- **R3 · The `analysis` extra was uninstallable, and floor-pins were the cause.** Neither
  problem was visible before a lockfile forced resolution to be explicit:
  - `essentia>=2.1b6.dev1110` resolved to `dev1438`, which ships **cp314 wheels only** and
    cannot install on the pinned 3.13. Essentia publishes only dev builds and each carries
    a single interpreter tag, so `>=` is meaningless for it. Pinned to `==2.1b6.dev1389`,
    the newest with cp313 wheels.
  - With essentia pinned, `librosa` → `numba` escaped *backwards* to `numba 0.53.1`
    (2021), whose `llvmlite 0.36.0` supports Python <3.10 and fails to build. Every modern
    numba caps numpy below what essentia pulls in, so the resolver preferred an ancient
    numba over an older numpy. Fixed by flooring `numba>=0.60` in the extra, which settles
    on numba 0.66 / llvmlite 0.48 / numpy 2.4.6.
- **K8** [R3] ⇒ `OBS-007/K1` ("the dependency posture is genuinely good") was right about
  *count* and wrong about *health*. A small dependency graph pinned only by floors is not a
  pinned graph; two of six extras could not be installed at all. Fewness is not safety.

## Q — Open

- ~~**Q1.** Is `uv` acceptable as the pin/lock tool?~~ Yes — adopted, and `dev.sh` keeps its
  shape; only its preflight message changed.
- ~~**Q2.** `uv sync` strips extras not requested, so `setup.sh` could remove
  essentia/librosa.~~ Closed by making the full environment the default and `--lean` the
  opt-out, rather than documenting around the footgun.
- **Q3.** The essentia pin must be revisited deliberately whenever the interpreter moves —
  `.python-version` 3.13 and `essentia==2.1b6.dev1389` are coupled by wheel tags (R3). A CI
  matrix would surface this; a comment in `pyproject.toml` is the interim guard.
