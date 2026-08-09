---
id: OBS-001
title: Codebase inventory and mass distribution
type: OBS
date: 2026-08-09
depends-on: []
superseded-by: null
---

## C — Context

Baseline measurement of where the code actually lives, so later claims about
maintainability have a denominator.

## E — Evidence

Measured on `main` at commit `12dc127`, 2026-08-09.

- **E1 · Total mass.** Python: 140 files / 25,596 LOC (`src` + `tests`). Frontend:
  133 files / 29,579 LOC (`.svelte` + `.ts` under `frontend/src`). Roughly a 46 / 54 split.
- **E2 · Backend shape.** `src/kiku/` is 97 files / 20,465 LOC across 15 subpackages
  (`analysis`, `api`, `artwork`, `db`, `export`, `hunting`, `import_playlist`, `metadata`,
  `musicbrainz`, `parsing`, `setbuilder`, `soundcloud`, `visualization`).
- **E3 · Backend top-5 by size.**

  | File | LOC |
  |------|-----|
  | `src/kiku/cli.py` | 1,631 |
  | `src/kiku/api/routes/sets.py` | 1,340 |
  | `src/kiku/visualization/figures.py` | 1,157 |
  | `src/kiku/api/schemas.py` | 976 |
  | `src/kiku/visualization/callbacks.py` | 888 |

- **E4 · Frontend shape.** 92 `.svelte` components + 7 stores + 10 API modules +
  1 types file (699 LOC) + 4 utils + 2 actions + 4 style files.
- **E5 · Frontend top-5 by size.**

  | File | LOC |
  |------|-----|
  | `frontend/src/routes/design-system/+page.svelte` | 1,488 |
  | `frontend/src/lib/components/waveform/TrackView.svelte` | 1,246 |
  | `frontend/src/lib/components/library/TrackCard.svelte` | 1,119 |
  | `frontend/src/lib/components/library/SearchFilters.svelte` | 955 |
  | `frontend/src/lib/components/set/SetView.svelte` | 909 |

- **E6 · API surface.** 86 endpoints across 11 route modules
  (`grep -rhoE '@router\.(get|post|put|patch|delete)' src/kiku/api/routes/ | wc -l`).
- **E7 · History.** 319 commits total, first on 2026-03-14; 223 of them in the last
  90 days. Single contributor.
- **E8 · Dead-weight candidates.** `src/kiku/visualization/` is 2,045+ LOC (a Dash app)
  reachable from exactly one place: a lazy import at `src/kiku/cli.py:954`. The frontend
  contains `dna/MoodScatter.svelte` and `tinder/MoodRadar.svelte`, which render mood
  columns that the DB has never populated.

## K — Conclusions

- **K1.** The project is ~55k LOC built by one person in five months at ~2.5 commits/day —
  a *sustained* pace, not a spike. Velocity is not the problem to solve.
- **K2.** Mass is evenly split backend/frontend, so neither side can be treated as the
  "small" one when planning structural work.
- **K3.** Five backend files and five frontend files each exceed 900 LOC. These ten files
  are ~11,700 LOC — 21% of the codebase in 10 of 273 files.
- **K4.** At least 2,045 backend LOC (`visualization/`, the Dash app) and two frontend
  components are plausibly dead. This is ~4% of the codebase carried as pure maintenance
  tax. See [[CLM-003]].

## Q — Open

- **Q1.** Is `kiku viz` (the Dash app) still used by the author, or has the SvelteKit
  frontend fully subsumed it? Answer determines whether E8 is deletion or documentation.
