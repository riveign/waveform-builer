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
| ~~**P1**~~ | ~~Make the schema reproducible and keep it that way~~ **DONE 2026-08-09** | `CLM-004/K1,K4`, `OBS-003/K2` | 1–2 d | P3, all deployment |
| **P2** | Pin the environment | `OBS-007/K2,K3` | 1 d | P3 |
| **P3** | One CI workflow | `OBS-002/K1`, `CLM-004/R3` | 1 d | P7, P8, everything's durability |
| **P4** | A real route table with URL state | `OBS-004/K3,K4`, `CLM-002/K3` | 3–5 d | P6, P8; deep links |
| **P5** | `createResource` — one data-orchestration rune | `OBS-005/K1,K3` | 2–3 d | shrinks 26 components |
| **P6** | The four missing structural primitives | `OBS-008/K2,K3` | 3–4 d | collapses ~2,700 LOC |
| **P7** | Generate TS types from OpenAPI | `OBS-005/K4`, `CLM-003/E2` | 1 d | removes a 5-edit boundary |
| **P8** | Frontend test foundation | `OBS-002/K3`, `CLM-003/K3` | 3–4 d | frontend confidence |
| **P9** | Extract a service layer, starting with sets | `OBS-006/K2,K3`, `CLM-001/K5` | 4–6 d | Rust port; CLI/API parity |
| **P10** | Cover the sequencing modules | `CLM-003/R6`, `OBS-002/E9` | 2–3 d | correctness of set building |

Total ≈ 21–31 author-days. P1–P3 are ~4 days and carry a disproportionate share of the value.

---

### P1 — Make the schema reproducible and keep it that way

**Do.** Add one repair revision creating `hunt_sessions` and `hunt_tracks` *before*
`c3d4e5f6a7b8` in the chain (or, if the chain proves easier to rebuild than to patch,
squash to a single new baseline generated from ORM metadata). Add a `KIKU_DB_PATH`
environment override in `src/kiku/config.py`, mirroring the existing `KIKU_MUSIC_ROOTS`.
Remove `Base.metadata.create_all()` from the normal startup path so Alembic is the sole
authority (`OBS-003/K1`). Then write the invariant test: build a fresh DB from base, and
assert `compare_metadata` between the migrated schema and `Base.metadata` yields no diff.

**Done-when.** `HOME=<tmp> alembic upgrade head` succeeds on an empty DB, and
`pytest tests/test_migrations.py` passes.

**Falsifier for the whole approach.** If the ORM/migration diff turns out to be large
enough that a repair revision is impractical, prefer the squashed-baseline route — the goal
is the invariant, not the history.

**DONE 2026-08-09** — `OBS-003/K6`. Repair revision `b1c2d3e4f5a6`, FK alignment
`c2d3e4f5a6b7`, `KIKU_DB_PATH`, `_init_schema()` on Alembic, `tests/test_migrations.py`.
The invariant test immediately found two further drifts nobody knew about
(`OBS-003/R1,R2`). 429 tests pass; the real library upgrades with integrity intact.
**Not committed** — the working tree is on `main`, which the project rules forbid
committing to. Needs a branch.

---

### P2 — Pin the environment

**Do.** Adopt `uv` (or `pip-tools`) and commit a lockfile. Correct
`requires-python` to `>=3.10` (`OBS-007/K2` — the declared 3.9 floor is contradicted by 523
annotations). Fix the `dev` extra so it includes `api`, `hunting`, and `analysis`-optional
test deps, so `pip install -e '.[dev]'` yields an environment the suite can run in
(`OBS-007/E5`). Add `.python-version`. The npm side already has a committed lockfile
(`OBS-007/E3`) — this item is Python-only.

**Done-when.** A scripted clean-clone install produces a passing `pytest` and a passing
`svelte-check`, with no manual step.

**Note.** Preserve `dev.sh` (`OBS-007/K5`); this changes what it installs, not how it runs.

---

### P3 — One CI workflow

**Do.** A single `.github/workflows/ci.yml` on push and PR, with five jobs:
`pytest` · `svelte-check` · `ruff check` + `ruff format --check` · the P1 migration test ·
`vite build`. Add `[tool.ruff]` to `pyproject.toml` — start with the default rule set and
`--fix` the result; do not hand-tune rules first, or this becomes a week.

**Done-when.** A PR with a deliberate type error is red.

**Why now and not later.** `CLM-003/R3`: without this, every fix below decays by default.
Fold in the `datetime.utcnow()` deprecations (`OBS-002/E10`) as the first thing the new
gate catches.

---

### P4 — A real route table with URL state

**Do.** Replace the `{#if}` ladder in `Workspace.svelte` (`OBS-004/E3`) with routes:
`/track/[id]`, `/set/[id]`, `/dna`, `/tinder`, `/hunt`, `/albums`. Move `selectedTrack`,
`selectedSetId`, `selectedTrackInSet`, `setViewMode` out of `ui.svelte.ts` into route params
and query strings. Add `+error.svelte` (`OBS-004/E7`). Keep `ssr = false` — the SPA
decision is fine (`OBS-004/Q1`); this is about routing, not rendering.

**Done-when.** A URL for a specific transition can be pasted into a fresh tab and lands on
it; browser back works; the largest client chunk drops well below 540 KB
(`OBS-004/E6`, and `OBS-004/K4` says this comes free).

**Product argument, not just an engineering one.** `OBS-004/K3` — a teaching tool whose
lessons cannot be bookmarked or shared is fighting its own mission.

---

### P5 — `createResource` — one data-orchestration rune

**Do.** A ~100-LOC first-party rune in `lib/data/` owning: fire-on-dependency-change,
`loading`/`error`/`data`, `AbortController` on re-fire and unmount (`OBS-005/E6`),
in-flight dedup, and explicit `invalidate(key)` after mutations. Migrate the 26
hand-rolled load/error pairs (`OBS-005/E3`) onto it.

**Done-when.** `grep -rc 'let loading = \$state' src/lib/components` returns 0, and the
three bug classes in `OBS-005/K3` are structurally unreachable.

**Falsifier.** Answers `OBS-005/Q1` — if the rune exceeds ~200 LOC or starts growing a
cache-eviction policy, stop and take TanStack Query instead; the point was to avoid a
dependency, not to reimplement one.

---

### P6 — The four missing structural primitives

**Do.** `Modal` (backdrop, focus trap via the existing `focusTrap` action, escape, scroll
lock), `Input`, `EmptyState`, `Skeleton`. Migrate the six bespoke dialogs
(`OBS-008/E5`) onto `Modal`. This is the deferred spec-026 shared-modal item.

**Done-when.** Total LOC across the six dialog files drops by ≥40%, and the design-system
gallery renders each new primitive.

**Falsifier.** `CLM-002/K5` — if the dialog files do not shrink, the primitive's API is
wrong.

---

### P7 — Generate TS types from OpenAPI

**Do.** `openapi-typescript` against the FastAPI schema, wired as an npm script and a CI
check that the committed output is current. Delete the hand-written half of
`lib/types/index.ts` (699 LOC, `OBS-005/E4`); keep only genuinely client-side types.

**Done-when.** Renaming a Pydantic field turns CI red without a human noticing anything.

**Sequencing.** After P3 — the value is the *check*, and the check needs a gate.

---

### P8 — Frontend test foundation

**Do.** Vitest + `@testing-library/svelte` for the 12+4 primitives and the two real state
machines (`playback.svelte.ts` 465 LOC, `player.svelte.ts` 371 LOC — the highest-risk
untested code in the repo). Playwright smoke test per route from P4: loads, renders, no
console errors. Do **not** chase coverage percentage; cover primitives and state machines.

**Done-when.** CI runs both; a broken `Modal` fails a test rather than a browser session.

**Sequencing.** After P4 — `CLM-002/K4`: routes are what a smoke test can address.

---

### P9 — Extract a service layer, starting with sets

**Do.** Create `src/kiku/services/`. Move the set use-cases out of
`api/routes/sets.py` (1,340 LOC) — including its domain-flavoured private helpers
(`OBS-006/E3`) — into `services/sets.py`, taking a `Session` and returning domain objects.
Point both `cli.py` and the route at it, killing the duplication in `OBS-006/E6`. Leave the
two SSE endpoints for last (`OBS-006/K6`).

**Done-when.** `api/routes/sets.py` is routing, validation, and serialization only; a
grep for `session.query` in it returns 0; the same use-case function backs both entry points.

**Strategic note.** `CLM-001/K5` — this is the actual prerequisite for the Rust migration,
and it may reveal the migration to be unnecessary. Do this before committing to that plan.

---

### P10 — Cover the sequencing modules

**Do.** Tests for `planner.py`, `filler.py`, `reorder.py` — the untested modules
(`OBS-002/E9`). Property-style assertions on invariants that must hold for any input:
artist cooldown respected; energy curve monotone within a segment; no track appears twice;
role bias never becomes a hard filter (the explicit design constraint of specs 028–029).
Add golden-set regression tests over a small fixture library.

**Done-when.** The three modules have named test files, and each invariant above has an
assertion.

**Why this matters more than its position suggests.** `CLM-003/R6` — these modules'
bugs produce sets that *look* plausible. They are the only defects in this document that
the author cannot catch by looking.

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
