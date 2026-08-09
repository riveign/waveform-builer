---
id: CLM-003
title: Maintainability — good bones, no immune system
type: CLM
date: 2026-08-09
depends-on: [OBS-001, OBS-002, OBS-003, OBS-005, OBS-006, OBS-007, OBS-008]
superseded-by: null
---

## C — Context

The engineering-quality verdict: can this codebase absorb another year of features without
the cost per feature rising? Covers composability, testing, and structural growth.

## D — Definitions

- **D1 · Composability.** The number of places you must edit to make one conceptual change.
  Lower is better; the ideal is one.
- **D2 · Immune system.** The set of mechanisms that reject a bad change *without a human
  choosing to look* — `OBS-002/D1`'s gates, plus type generation, plus migrations as
  authority.
- **D3 · Cost curve.** How effort-per-feature trends over time. Flat is healthy; rising is
  the definition of accumulating debt.

> **Re-check 2026-08-09.** K4's diagnosis stands but its premise is being dismantled:
> [[PLN-001]] P1–P3 shipped, so **D2 is no longer empty** — four gates now run on every
> push (`OBS-002/K5`). E3's inventory is stale in three rows: gates, migrations-as-
> authority, and lock/manifest are all now yes. E2's edit-counts are unchanged, so K2
> still holds and P5–P7 are still the work. E4b was fixed only in part: the 49 blind
> excepts are deferred *visibly*, in `pyproject.toml`'s ignore list (`OBS-002/K6`).

## E — Evidence

Inherited across `OBS-001` … `OBS-008`. Consolidated:

- **E1 · Structural strengths.**
  (a) A genuine domain layer that expresses the product's ideas and is independently
      testable — `OBS-006/K1`.
  (b) 426 backend tests running in 11 seconds — `OBS-002/E1`. Fast enough to be run
      constantly, which is the property that makes a suite actually used.
  (c) A clean transport boundary on the client: zero raw `fetch` in components —
      `OBS-005/E1`.
  (d) A consistently applied token system, 2,033 call sites — `OBS-008/K1`.
  (e) A lean, current, extras-isolated dependency graph — `OBS-007/K1`.
- **E2 · Composability deficits, with their edit-count.**

  | Conceptual change | Places to edit | Source |
  |---|---|---|
  | Add a field to a track | ORM + migration + Pydantic schema + TS type + component | `OBS-003`, `OBS-005/E4` |
  | Change how a set is built | `cli.py` **and** `api/routes/sets.py` | `OBS-006/E6` |
  | Change dialog chrome | 6 bespoke dialog components | `OBS-008/E5` |
  | Change loading-state presentation | 26 components | `OBS-005/E3`, `OBS-008/E6` |
  | Add a queryable filter | route + ORM query + schema + TS type + filter component | `OBS-006/E4` |

- **E3 · Immune-system inventory.** Gates: **0** (`OBS-002/K1`). Type generation: none
  (`OBS-005/E4`). Migrations as authority: no (`OBS-003/K1`). Lock/manifest: none
  (`OBS-007/E3,E7`). Observability: none (`OBS-006/E8`). Frontend tests: none
  (`OBS-002/E2`).
- **E4 · Carried dead weight.** ~2,045 LOC Dash visualizer reachable from one lazy CLI
  import; two mood components rendering never-populated columns — `OBS-001/E8`.
  (`TrackAffinity` was checked and is *not* dead: `scoring.py:643` loads affinities and
  applies a ±10/20% modifier in `suggest_next`.)
- **E4b · Errors are swallowed at scale.** 63 `except Exception` blocks in `src/kiku`.
  At least one is load-bearing in the wrong direction: `_load_affinities`
  (`scoring.py:659–685`) catches every exception and returns `{}` with the comment
  "table may not exist yet if migration hasn't run". This directly contradicts the
  project's own "Always re-raise" principle, and it is a purpose-built blindfold over
  exactly the failure mode `OBS-003/K3` describes.
- **E5 · Untested domain modules.** `planner.py`, `filler.py`, `reorder.py`, `store.py`,
  `cli.py` have no test file bearing their name — `OBS-002/E9`.
- **E6 · Velocity is currently high.** 223 commits in 90 days, single author —
  `OBS-001/E7`.

## A — Assumptions

- **A1.** The author will continue shipping at roughly E6's pace for at least another
  6 months.
  *Falsifier:* commit rate over the next 90 days drops below ~1/day.
- **A2.** Nobody else is going to run the checks. Any process requiring a human to remember
  a command will be skipped under time pressure.
  *Falsifier:* three months of history showing lint/tests run manually before every merge.

## R — Reasoning

- **R1** [E1] ⇒ The bones are good. (a) and (b) together are
  the two properties that most often *don't* exist in a codebase this age, and they are the
  two that most determine whether a rewrite eventually becomes necessary. Kiku's domain
  logic is legible and covered. That is the hard part, and it is done.
- **R2** [E2] ⇒ But D1 is poor at the seams. Every row in E2 has an edit-count of 2 or
  more, and the two most common changes in this project — adding a track field, and adding
  a filter — are 5-place edits. Composability is not bad *inside* modules; it is bad
  *across* the layer boundaries, because each boundary is crossed by hand-maintained
  duplication rather than by generation or a shared abstraction.
- **R3** [E3, A2] ⇒ D2 is empty. Under A2, "0 gates" does not mean "quality depends on
  discipline" — it means quality depends on discipline *at the exact moments discipline is
  most expensive*, which is when a fix is urgent. This is why `OBS-002/E10` (ten
  deprecation warnings) and `OBS-008/E2` (123 hex literals) exist: neither is a decision
  anyone made, both are what happens by default.
- **R4** [R2, R3, A1] ⇒ Project the cost curve (D3). Cost per feature ≈ (edit-count from
  R2) × (probability a missed edit ships, from R3) × (cost to find it, which with no
  observability and no frontend tests means "in the browser, by hand"). All three factors
  grow with the number of surfaces. Under A1, the curve is **rising**, and it is rising
  multiplicatively rather than additively.
- **R5** [E4] ⇒ Dead weight is a second-order term but not zero: ~4% of the codebase,
  and — more importantly — it is *indistinguishable from live code* to any future reader,
  including the Rust port (`CLM-001/K5`) and any agent loading context.
- **R5b** [E4b, R3, `OBS-003/K3`] ⇒ E4b is the sharpest single illustration of R3. Faced
  with a schema that might not match the code, the response was a `try/except` that returns
  a plausible empty result. The system therefore does not fail on drift; it silently
  degrades — suggestions quietly stop honouring the DJ's own good/bad affinity marks, with
  no error anywhere. A missing immune system does not merely fail to catch problems; it
  creates pressure to write code that hides them.
- **R6** [E5, `OBS-002/K2`] ⇒ The test suite's shape has a specific hole: the modules that
  are untested are the *sequencing* ones (planner, filler, reorder), which are precisely
  the ones whose bugs are hardest to see, because a badly ordered set looks plausible.
  Scoring is well covered because scoring is easy to assert on. The suite is strong where
  assertions are easy and absent where they are hard.
- **R7** [R1, R4] ⇒ The two findings are not in tension, and the combination is the actual
  diagnosis: a healthy organism with no immune system. It is not sick yet — E6's velocity
  proves that — and the intervention is cheap *now*, precisely because the bones are good
  enough that the apparatus has something solid to attach to.

## K — Conclusions

- **K1 · Structural verdict: better than average, and specifically strong where it counts.**
  A separable domain layer with a fast 426-test suite (R1) puts Kiku ahead of most
  solo-authored codebases of this size and age.
- **K2 · Composability verdict: poor at layer boundaries, fine within layers.** The two
  most frequent changes in this project cost five edits each (R2). This is the mechanism by
  which features get slower to ship.
- **K3 · Testing verdict: strong but lopsided in two dimensions.** By layer: 426 backend
  tests, 0 frontend tests, over a 46/54 code split (`OBS-002/K3`). By difficulty: covered
  where assertions are easy, absent where they are hard (R6). The second lopsidedness is
  the more dangerous one.
- **K4 · The cost curve is rising, and the cause is the empty immune system (R3, R4), not
  the code.** This is good news: the fix is additive and does not require touching working
  logic.
- **K5 · Priority ordering follows directly.** Restore reproducibility (`CLM-001/K3`) →
  add gates (R3) → collapse the 5-edit boundaries by generation and shared abstraction
  (R2) → close the sequencing-test hole (R6) → delete dead weight (R5). Note this ordering
  is forced, not chosen: gates require a reproducible environment to run in, and generation
  is only safe once a gate can catch its failures.
- **K5b · Audit the 63 `except Exception` blocks as part of K5's gate step.** R5b shows at
  least one is actively concealing the binding constraint. The project already has the
  right rule written down ("Always re-raise"); it has no mechanism enforcing it, which is
  K4 in miniature. `ruff`'s `BLE`/`TRY` rule families make this a lint, not an audit.
- **K6 · Do this now rather than later, for a non-obvious reason.** The intervention is
  cheapest at the current size and while the author still holds the whole system in memory.
  Every month of A1-rate shipping adds surfaces that the eventual apparatus must
  retroactively cover.
