---
id: CLM-002
title: The frontend should not be rebuilt — three surgical changes recover most of the benefit
type: CLM
date: 2026-08-09
depends-on: [OBS-001, OBS-002, OBS-004, OBS-005, OBS-008]
superseded-by: null
---

## C — Context

The author has explicitly opened the door to a complete frontend rebuild. Should they, and
if not, what is the minimum set of changes that captures what a rebuild would have bought?

> **Re-check 2026-08-09 — K1 held.** All three changes named in K3 shipped incrementally,
> in the order K4 required: the route table (P4), `createResource` (P5), and the structural
> primitives (P6). No rebuild was needed and none of the 29,600 lines was re-typed.
> **K5's falsifier came out mixed**: the largest files did shrink, but by ~10% rather than
> the implied 40% — see `PLN-001`/P6 for why that reads as an optimistic estimate rather
> than a wrong abstraction.

## D — Definitions

- **D1 · Rebuild.** Starting a new frontend application and re-implementing the six
  surfaces, retaining at most the token files and visual design.
- **D2 · Rebuild dividend.** The set of improvements a rebuild would deliver *that
  incremental work could not*.

## E — Evidence

Inherited: `OBS-004/K1-K5`, `OBS-005/K1-K5`, `OBS-008/K1-K5`, `OBS-002/E2,E3`,
`OBS-001/E4,E5`.

- **E1 · Asset inventory at risk in a rebuild.** 92 components / ~29,600 LOC; a 250-token
  three-tier design system with 2,033 call sites; 6 working surfaces including two
  non-trivial ones (dual-deck playback state machine, 465 LOC; wavesurfer track view,
  1,246 LOC); focus-trap and roving-focus a11y actions; five shipped UI specs (023–029) of
  accumulated design decisions.
- **E2 · The frontend type-checks clean.** 0 errors, 0 warnings across 133 files
  (`OBS-002/E3`). The existing code is not in a state of decay.
- **E3 · Every identified frontend defect is local.** Enumerated: single route
  (`OBS-004/E2`), no URL state (`OBS-004/E4`), 540 KB chunk (`OBS-004/E6`), no error
  boundary (`OBS-004/E7`), D2-orchestration duplicated 44× (`OBS-005/K1`), missing
  structural primitives (`OBS-008/K2`), zero tests (`OBS-002/E2`), no virtualization
  (`OBS-005/E8`), 123 stray hex literals (`OBS-008/E2`).
- **E4 · None of the defects in E3 are framework-level.** No item in E3 would be *solved*
  by choosing a different framework; each is a missing module or a missing file within the
  current one.

## A — Assumptions

- **A1.** A faithful rebuild of six surfaces at ~29,600 LOC of accumulated behaviour costs
  at least 2–3 months of the author's evenings, and lands with fewer features than today.
  *Falsifier:* a spike reproducing Set View + Track View to current fidelity in under two
  weeks.
- **A2.** The design decisions embedded in specs 023–029 are worth keeping — they encode
  taste developed against the real library, not arbitrary layout.
  *Falsifier:* the author reports being dissatisfied with the current visual/interaction
  design as such, rather than with its implementation.

## R — Reasoning

- **R1** [E3, E4] ⇒ Compute the rebuild dividend (D2). Take each defect and ask whether a
  greenfield app solves it *inherently*:

  | Defect | Solved inherently by a rebuild? |
  |---|---|
  | Single route / no URL state | No — you must still design the route table. |
  | 540 KB chunk | Follows from routing, not from newness. |
  | No error boundary | One file, either way. |
  | Orchestration duplicated 44× | No — you must still build the data layer. |
  | Missing structural primitives | No — you must still write `Modal`, `Input`, `EmptyState`. |
  | Zero tests | No — a rebuild starts with zero tests too. |
  | No virtualization | No. |
  | 123 hex literals | Yes, trivially (but so does one day of cleanup). |

  ⇒ **The rebuild dividend is one row: colour literals.**
- **R2** [R1] ⇒ A rebuild is not a way of *getting* the improvements. It is a way of being
  *forced* to make them, at the price of re-typing 29,600 lines of working behaviour. The
  discipline can be bought directly and far more cheaply.
- **R3** [E1, A1, A2] ⇒ The cost side is large and the discarded assets are the ones that
  took longest to earn — the playback state machine, the a11y actions, and five specs of
  design decisions. Note that the *token system*, the one thing usually cited as
  "we'd keep the design", is also the one part with no implementation problem
  (`OBS-008/K1`).
- **R4** [R1, R2, R3] ⇒ Rebuild is dominated: strictly higher cost, strictly lower or equal
  benefit. Reject.
- **R5** [E3, `OBS-005/K1`, `OBS-008/K2`] ⇒ Now find the minimum set. Observe that the E3
  defects are not independent. `OBS-004/K4` shows the bundle is downstream of routing.
  `OBS-008/K3` and `OBS-005/K2` jointly show that the oversized components
  (`OBS-001/K3`) are large *because* each re-implements the missing data-orchestration
  primitive and the missing structural primitives. So:
  - Route table ⇒ fixes URL state, deep links, back button, code splitting, error
    boundaries (per-route `+error.svelte`), and gives tests something to target.
  - `createResource` rune ⇒ fixes 26 duplicated load/error pairs, adds abort and dedup
    (`OBS-005/K3` a–c), and shrinks the largest components.
  - Structural primitives (`Modal`, `Input`, `EmptyState`, `Skeleton`) ⇒ collapses ~2,700
    LOC of bespoke dialog (`OBS-008/E5`) into composition.
- **R6** [R5] ⇒ These three changes touch every one of the ten oversized files
  (`OBS-001/K3`) without rewriting any of their domain logic, because in each case the
  removed code is the boilerplate, not the behaviour.

## K — Conclusions

- **K1 · Do not rebuild the frontend.** The rebuild dividend is one trivial row (R1); the
  cost is 29,600 LOC of working behaviour and five specs of design decisions (R3).
  The verdict is not close.
- **K2 · The instinct behind the question is nonetheless correct.** The frontend *is* the
  weaker half — 54% of the code and 0% of the tests (`OBS-002/K3`), with composability
  deficits that are real (`OBS-008/K5`). The right response is three targeted changes,
  not a restart.
- **K3 · The three changes, in dependency order:** (1) a real route table with URL-encoded
  selection state; (2) a first-party `createResource` rune owning load/error/abort/
  invalidate; (3) the four missing structural primitives. Each is independently shippable
  and independently valuable.
- **K4 · Sequence matters.** (1) must come first: it creates the seams that make (2) and
  (3) testable, and it is the only one of the three with direct user-visible value —
  deep-linkable transitions serve the teaching mission (`OBS-004/K3`).
- **K5 · Expect the codebase to shrink.** R6 predicts a net LOC *reduction* in the ten
  largest files. If a proposed implementation of K3 grows them instead, the abstraction is
  wrong and should be reconsidered — this is the falsifier for the whole plan.
