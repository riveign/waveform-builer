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

**Status 2026-08-09: P1–P7 done and merged to `main`, CI green. P8–P10 open.**

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
| **P5** ✅ | `createResource` — one data-orchestration rune — *done 2026-08-09* | `OBS-005/K1,K3` | 2–3 d | shrinks 26 components |
| **P6** ✅ | The four missing structural primitives — *done 2026-08-09* | `OBS-008/K2,K3` | 3–4 d | collapses ~2,700 LOC |
| **P7** ✅ | Generate TS types from OpenAPI — *done 2026-08-09* | `OBS-005/K4`, `CLM-003/E2` | 1 d | removes a 5-edit boundary |
| **P8** | Frontend test foundation | `OBS-002/K3`, `CLM-003/K3` | 3–4 d | frontend confidence |
| **P9** | Extract a service layer, starting with sets | `OBS-006/K2,K3`, `CLM-001/K5` | 4–6 d | Rust port; CLI/API parity |
| **P10** | Cover the sequencing modules | `CLM-003/R6`, `OBS-002/E9` | 2–3 d | correctness of set building |

Total ≈ 21–31 author-days. **P1–P7 are done and merged**; P8–P10 remain (~9–13 days).

P1–P3 carried the disproportionate share, as predicted: they relieved the binding
constraint and put six gates on every PR. Those gates have since caught two bugs that no
local check could see (`OBS-002/R2`, and the eager `pyrekordbox` import in P7).

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
- **First real run caught a live bug** (`OBS-002/R2`): an unanchored `data/` in `.gitignore` had kept `frontend/src/lib/data/resource.svelte.ts` — the whole P5 rune — out of every commit. Green locally, unbuildable on a clean checkout. Fixed in `2e54793`; CI green on run 2.

### P4 — A real route table with URL state ✅ **DONE 2026-08-09**

- Six routes under an `(app)` group (so `/design-system` stays outside the shell): `/track/[[id]]` · `/set/[[id]]` · `/dna` · `/tinder` · `/hunt` · `/albums`; `/` redirects to `/track`.
- `?t=` focused track, `?view=` list/grid — written with `replaceState`, so Back leaves the set instead of walking every row you clicked.
- Navigation state left `ui.svelte.ts` entirely; what stays is ambient (last-viewed track for the build seed, playing track, two hand-off channels). `Workspace.svelte` deleted.
- `+error.svelte` added — a bad id renders a page, not a blank app.
- **Fixed a dead-state bug:** `ui.selectedSetId` had two writers and no reader, so jumping to a set from a track or a finished build silently did nothing (`OBS-004/K7`).
- **Initial JS: 700 KB on every route → 253–612 KB by route; `/track` is 292 KB (−58%).** The 1,488-line design-system gallery left the app path.
- **Verified in Chromium** against the real library: cold `/set/12?t=3891` loads the set with the row selected · `?view=grid` restores the grid · Back/Forward walk surfaces · number keys navigate · refresh preserves set + row · bad id → error page · no console errors.

### P5 — `createResource`, one data-orchestration rune ✅ **DONE 2026-08-09**

- `lib/data/resource.svelte.ts` (165 LOC): deps-driven refetch · `loading`/`error`/`data` · `AbortController` on re-fire and unmount · in-flight dedup · `invalidate(prefix)` · null source = idle.
- Optional `AbortSignal` threaded through the reads in `stats.ts`, `tracks.ts`, `sets.ts`, `albums.ts`, `tinder.ts`, `waveforms.ts`.
- **22 of 26 components migrated.** The other 4 are decisions, not gaps: `FixMetadataModal`, `MusicBrainzMatchModal`, `ImportPlaylistDialog` are user-driven wizards holding *action* state with no reactive source; `AlbumGrid` is the accumulation exception ([[DEC-003]]).
- **Boundary:** [[DEC-003]] — the rune owns the fetch lifecycle, accumulation stays with the caller.

**Three corrections this item produced, all from measuring rather than reasoning:**

- **Dedup does not close `OBS-005/K3`(b).** It merges only requests in flight *at the same moment*; on `/dna` a parent gating its children makes them sequential, so `/api/stats/library` is still fetched 3×. Closing (b) needs a cache with a lifetime — the line P5 agreed not to cross. (a) and (c) *are* closed.
- **The done-when metric was wrong.** `grep 'let loading = $state' → 0` conflates read state with mutation state. Restated: **no component hand-rolls a *fetch* lifecycle.** Five components turned out to share one `error` between a read and a write beside it; each now has its own channel.
- **`TrackView` had a latent bug the split exposed:** waveform and features loaded behind one error flag, so a missing feature row blanked the waveform. Two resources now; only a missing waveform is reported.

**Verified in Chromium throughout:** DNA charts, track view (waveform + features + related + set appearances), albums grid and detail, set view (52 rows ↔ 7 rows on switch), tinder, hunt. Rapid switching — tracks and sets alike — produces no stale write and no console error.

### P6 — The four missing structural primitives ✅ **DONE 2026-08-09**

- `Modal` · `Input` · `EmptyState` · `Skeleton`, all four documented and interactive in the design-system gallery.
- `Modal` standardises on native `<dialog>` + `showModal()` — backdrop, Escape, focus trapping, `inert` background and top-layer stacking, all correct and free. Kiku had **two competing idioms**: four dialogs on native `<dialog>`, two hand-rolling a div overlay with `use:focusTrap`. The div ones also shed their JS focus traps, which native `inert` does better.
- All six bespoke dialogs migrated. Every migration was a mechanical swap — no escape hatches, no special-case props.
- **Latent bug fixed:** `app.css` resets `* { margin: 0 }`, clobbering the UA's `dialog { margin: auto }`, so every plain native `<dialog>` pinned itself to the **top-left instead of centring**. Surfaced by a Playwright backdrop-click assertion failing — the click at (20,20) landed *inside* the dialog. Fixed once, for all six.

**Correction — the ≥40% target was wrong; they shrank 10%.**

| dialog | before | after | |
|---|---|---|---|
| BuildSetDialog | 781 | 690 | −12% |
| FillReorderDialog | 493 | 432 | −12% |
| ImportPlaylistDialog | 478 | 452 | −5% |
| ReplaceTrackModal | 541 | 492 | −9% |
| FixMetadataModal | 435 | 399 | −8% |
| MusicBrainzMatchModal | 315 | 267 | −15% |
| **total** | **3,043** | **2,732** | **−10%** |

`CLM-002/K5` reads a failure to shrink as a wrong API. That is not the reading here: the 40% assumed most of those 2,700 lines were chrome, and they are not — chrome was ~50 lines per dialog and it is gone. What remains is domain content (30-odd form fields, candidate cards, a four-stage wizard) that no `Modal` could remove. Reaching 40% needs field-row and card primitives, which is separate work. **The API stands; the estimate was optimistic** — the same shape of error as P5's done-when.

- **Adoption is partial and not overclaimed:** `Input` in two `FillReorderDialog` fields and the set-name field; `EmptyState` on `/track`. `Skeleton` is documented but not yet adopted. Broader rollout is follow-on.

### P7 — Generate TS types from OpenAPI ✅ **DONE 2026-08-09**

- `scripts/gen_openapi.py` dumps the schema straight from the FastAPI app — **no running server**, so CI regenerates deterministically. Sorted keys, stable diff.
- `npm run gen:api` regenerates; **`npm run check:api` gates it in CI**.
- `lib/types/index.ts`: **699 → 164 lines**; 58 of 71 types are aliases onto the generated schema, so call sites still import `Track`.
- **34 real mismatches surfaced** — every one a field the client assumed but the API doesn't guarantee. Mostly `T | null | undefined` hitting a `T | null` signature; fixed by widening the few outlier helpers rather than 25 × `?? null`.
- **One fixed at the source:** `scores: dict` in `TransitionAnalysisResponse` reached the client as `{[key: string]: unknown}`, so `scores.total` was untyped. It has always held exactly `TransitionScoreBreakdown`'s shape (`set_analyzer.py:272`). Typing it killed three client errors at once and made the contract real.
- **Request bodies need care:** openapi-typescript marks defaulted fields required — correct for a response, wrong for a request. `SetBuildParams` and friends are `Partial<>` with only the genuinely required keys picked.
- **Gate verified:** renaming `teaching_moment` in `schemas.py` turns `check:api` red with *"Generated types are not up-to-date!"*.
- **Still hand-written (13):** responses from endpoints declared with no `response_model` — the gaps/enhanced-stats family, `VibePreset`, `SetBuildComplete`. Each is a small hole in the contract, and a natural follow-on.

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
