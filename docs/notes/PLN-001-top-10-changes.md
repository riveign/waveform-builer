---
id: PLN-001
title: The ten changes, ranked
type: PLN
date: 2026-08-09
depends-on: [CLM-001, CLM-002, CLM-003, CLM-004]
superseded-by: null
---

## C — Context

The output of the status analysis: what to do, in order. Cost is in author-days at the
pace of `OBS-001/E7`.

## R — Reasoning (the ordering)

- **R1** [`CLM-004/K1,K2`] ⇒ P1–P2 relieve the binding constraint. They come first because
  they are cheap and because P3 is literally unimplementable without them (`CLM-004/R2`).
- **R2** [`CLM-004/R3`] ⇒ P3 (CI) is the multiplier. Every later item's value is partly
  "and it stays fixed", which only CI can provide.
- **R3** [`CLM-002/K4`] ⇒ P4 precedes P5–P6 and P8 because it creates the seams they need,
  and it is the only structural item with direct user-visible value.
- **R4** [`CLM-003/K2`] ⇒ P5–P7 are the three 5-edit boundaries from `CLM-003/E2`,
  collapsed. They are ordered by blast radius, smallest first.
- **R5** [`CLM-003/R6`] ⇒ P10 is last among the ten but is the only item that addresses
  *correctness of the product's core idea* rather than the cost of changing it. It is last
  only because it is not blocking anything; it is not last because it is optional.

## K — Conclusions

### The table

| # | Change | Derives from | Cost | Unblocks  |
|---|--------|--------------|-----------|---------------|
| **P1** ✅ | Make the schema reproducible — *done 2026-08-09* | `CLM-004/K1,K4`, `OBS-003/K2` | 1–2 d | P3, all deployment |
| **P2** ✅ | Pin the environment — *done 2026-08-09* | `OBS-007/K2,K3` | 1 d | P3 |
| **P3** ✅ | One CI workflow — *done 2026-08-09* | `OBS-002/K1`, `CLM-004/R3` | 1 d | P7, P8, everything's durability |
| **P4** ✅ | A real route table with URL state — *done 2026-08-09* | `OBS-004/K3,K4`, `CLM-002/K3` | 3–5 d | P6, P8; deep links |
| **P5** | `createResource` — one data-orchestration rune | `OBS-005/K1,K3` | 2–3 d | shrinks 26 components |
| **P6** | The four missing structural primitives | `OBS-008/K2,K3` | 3–4 d | collapses ~2,700 LOC |
| **P7** | Generate TS types from OpenAPI | `OBS-005/K4`, `CLM-003/E2` | 1 d | removes a 5-edit boundary |
| **P8** | Frontend test foundation | `OBS-002/K3`, `CLM-003/K3` | 3–4 d | frontend confidence |
| **P9** | Extract a service layer, starting with sets | `OBS-006/K2,K3`, `CLM-001/K5` | 4–6 d | Rust port; CLI/API parity |
| **P10** | Cover the sequencing modules | `CLM-003/R6`, `OBS-002/E9` | 2–3 d | correctness of set building |

Total ≈ 21–31 author-days. P1–P3 are ~4 days and carry a disproportionate share of the value.

---

### P1 — Make the schema reproducible ✅ **DONE 2026-08-09**

- Repair revision `b1c2d3e4f5a6` creates `hunt_sessions`/`hunt_tracks`, inserted before `c3d4e5f6a7b8`.
- `_init_schema()` runs `alembic upgrade head`; stamps head on a pre-Alembic DB.
- `KIKU_DB_PATH` env override — `config.py:37`, closes `OBS-003/E7`.
- `tests/test_migrations.py`: chain runs from base · every ORM table has a migration · no `compare_metadata` drift.
- **Found by the new test:** two index drifts + one FK drift, months old, invisible — `OBS-003/R1,R2`.
- **Also:** `tests/conftest.py` now redirects `KIKU_DB_PATH`; a bare `pytest` was migrating the real library.
- **Result:** 429 tests pass; real 4,328-track library upgraded, `integrity_check: ok`.

### P2 — Pin the environment ✅ **DONE 2026-08-09**

- `uv.lock` committed — 100 packages, all extras.
- `requires-python` → `>=3.11`, not the `>=3.10` planned here: `tomllib` at `config.py:8` is the real floor (`OBS-007/R1`). `.python-version` → 3.13.
- `dev` extra now pulls `api` + `hunting` + `ml` + `rekordbox` (`OBS-007/E5` closed).
- New `ml` extra — scikit-learn + joblib, kept out of `analysis`.
- `scripts/setup.sh` = `uv sync --extra dev --extra analysis` + `npm ci` (`--lean` to skip audio); README and `dev.sh` point at it.
- **Found by building from scratch:** `python-multipart` and `scikit-learn`/`joblib` were undeclared — `kiku autotag` and every API test fail on a clean install (`OBS-007/R2`).
- **Also found:** the `analysis` extra was uninstallable — essentia floor-resolved to a cp314-only wheel, then numba escaped back to a 2021 build needing Python <3.10 (`OBS-007/R3`). Both pinned.
- **`.venv` converged onto the lock** — one environment, not a lock plus a hand-built venv beside it.
- **Verified:** clean clone → setup → 429 tests, `svelte-check` 0/0 over 341 files, `kiku stats` builds its own DB; essentia/librosa import and the real library still reports 4,328 tracks.

### P3 — One CI workflow ✅ **DONE 2026-08-09**

- Two jobs, push-to-main + every PR, superseded runs cancelled. **backend:** `uv sync --frozen` · `ruff check` · `ruff format --check` · `pytest`. **frontend:** `npm ci` · `svelte-check` · `vite build`.
- All 479 ruff findings cleared — 98 autofixed, rest by hand. Real ones: 6 `F821`, 3 dead assignments, a `subprocess.run` without `check=` (`OBS-002/R1`).
- The 4 `datetime.utcnow()` deprecations fixed; suite warnings 11 → 1.
- Codebase `ruff format`ted in its own commit, with `.git-blame-ignore-revs` so blame still names whoever changed a line's *meaning*.
- **Deferred, not blessed:** `BLE001` (49) · `S110` · `DTZ005` · `C408` · `RUF059` sit in `lint.ignore` with counts and reasons. Deleting an entry is how the backlog gets scheduled (`OBS-002/K6`).
- **Verified by breaking each gate:** unused import → lint red · reformatted function → format red · ORM column with no migration → `Detected added column 'tracks.ci_canary'`, test red · `$state<Tab>(42)` → svelte-check red.

### P4 — A real route table with URL state ✅ **DONE 2026-08-09**

- Six routes under an `(app)` group (so `/design-system` stays outside the shell): `/track/[[id]]` · `/set/[[id]]` · `/dna` · `/tinder` · `/hunt` · `/albums`; `/` redirects to `/track`.
- `?t=` focused track, `?view=` list/grid — written with `replaceState`, so Back leaves the set instead of walking every row you clicked.
- Navigation state left `ui.svelte.ts` entirely; what stays is ambient (last-viewed track for the build seed, playing track, two hand-off channels). `Workspace.svelte` deleted.
- `+error.svelte` added — a bad id renders a page, not a blank app.
- **Fixed a dead-state bug:** `ui.selectedSetId` had two writers and no reader, so jumping to a set from a track or a finished build silently did nothing (`OBS-004/K7`).
- **Initial JS: 700 KB on every route → 253–612 KB by route; `/track` is 292 KB (−58%).** The 1,488-line design-system gallery left the app path.
- **Verified in Chromium** against the real library: cold `/set/12?t=3891` loads the set with the row selected · `?view=grid` restores the grid · Back/Forward walk surfaces · number keys navigate · refresh preserves set + row · bad id → error page · no console errors.

### P5 — `createResource`, one data-orchestration rune

- ~100 LOC in `lib/data/`: fire-on-dependency-change · `loading`/`error`/`data` · `AbortController` on re-fire and unmount · in-flight dedup · `invalidate(key)`.
- Migrate the 26 hand-rolled load/error components (`OBS-005/E3`) onto it.
- **Done when:** `grep -rc 'let loading = \$state' src/lib/components` → 0, and `OBS-005/K3`'s three bug classes are unreachable.
- **Falsifier:** if it passes ~200 LOC or grows a cache-eviction policy, take TanStack Query instead (`OBS-005/Q1`).

### P6 — The four missing structural primitives

- `Modal` (backdrop, `focusTrap`, escape, scroll lock) · `Input` · `EmptyState` · `Skeleton`.
- Migrate the six bespoke dialogs (`OBS-008/E5`) onto `Modal`. This is the deferred spec-026 item.
- Fold in the 123 stray hex literals (`OBS-008/E2`) while touching these files.
- **Done when:** the six dialog files shrink ≥40% and the gallery renders each primitive.
- **Falsifier:** if they don't shrink, the primitive's API is wrong (`CLM-002/K5`).

### P7 — Generate TS types from OpenAPI

- `openapi-typescript` against the FastAPI schema, as an npm script + a CI check that the committed output is current.
- Delete the hand-written half of `lib/types/index.ts` (699 LOC); keep only client-side types.
- **Done when:** renaming a Pydantic field turns CI red with nobody watching.
- **After P3** — the value is the check, and the check needs a gate.

### P8 — Frontend test foundation

- Vitest + `@testing-library/svelte` on the 16 primitives.
- Cover the two real state machines: `playback.svelte.ts` (465 LOC), `player.svelte.ts` (371 LOC) — the highest-risk untested code in the repo.
- Playwright smoke per P4 route: loads, renders, no console errors.
- Do **not** chase a coverage number. Primitives and state machines only.
- **After P4** — routes are what a smoke test can address.

### P9 — Extract a service layer, starting with sets

- Create `src/kiku/services/`; move set use-cases out of `api/routes/sets.py` (1,340 LOC), including its domain-flavoured private helpers (`OBS-006/E3`).
- Point both `cli.py` and the route at it, killing the duplication in `OBS-006/E6`.
- Leave the two SSE endpoints for last (`OBS-006/K6`).
- **Done when:** `sets.py` is routing/validation/serialization only; `grep session.query` in it → 0; one use-case backs both entry points.
- **Strategic:** this is the real prerequisite for the Rust migration, and may show it to be unnecessary (`CLM-001/K5`).

### P10 — Cover the sequencing modules

- Tests for `planner.py`, `filler.py`, `reorder.py` (`OBS-002/E9`).
- Property-style invariants: artist cooldown respected · energy curve monotone within a segment · no track twice · role bias never becomes a hard filter (the explicit constraint of specs 028–029).
- Golden-set regression over a small fixture library.
- **Done when:** three named test files, one assertion per invariant above.
- **Why it matters more than its rank:** these bugs produce sets that *look* plausible — the only defects here the author cannot catch by looking (`CLM-003/R6`).

---

## Q — Below the line

Considered and deliberately excluded from the ten, with reasons:

- **Delete the dead weight** (~2,045 LOC Dash visualizer, `MoodScatter`, `MoodRadar` —
  `CLM-003/E4`). Real, cheap, but blocked on `OBS-001/Q1`. Do it opportunistically, not as
  a project. Note `TrackAffinity` is **not** dead and must not be swept up with it.
- **The 63 `except Exception` blocks** (`CLM-003/E4b`). Not a separate item: enable ruff's
  `BLE`/`TRY` families in P3 and fix what it flags, starting with `_load_affinities`,
  which is currently hiding P1's defect from the DJ.
- **Structured logging, request IDs, telemetry** (`OBS-006/E8`). Correctly absent for a
  laptop tool. Becomes P1-urgent the day the personal server runs unattended.
- **List virtualization** (`OBS-005/K5`). Latent, not acute at ~4,300 tracks with
  server-side paging. Revisit if a view drops paging or the library grows several-fold.
- **The 123 stray hex literals** (`OBS-008/E2`). A day of work; fold into P6 rather than
  scheduling separately.
- **Rewrite `ROADMAP.md`** (`OBS-009/E6`). Not engineering. Should become `DEC` notes plus
  a short living roadmap once KNF has bedded in.
- **Postgres migration.** Explicitly rejected — `CLM-001/K4`.
- **Frontend rebuild.** Explicitly rejected — `CLM-002/K1`.
