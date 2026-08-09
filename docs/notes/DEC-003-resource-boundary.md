---
id: DEC-003
title: createResource owns the fetch lifecycle and nothing else — paging stays with the caller
type: DEC
date: 2026-08-09
depends-on: [OBS-005, PLN-001]
superseded-by: null
---

## C — Context

`AlbumGrid` combines debounced search with offset pagination that appends to a list. It is
the one shape `createResource` does not serve, and it forces the question of where the
rune's boundary sits before the remaining 18 components are migrated against it.

## D — Definitions

- **D1 · Fetch lifecycle.** When to fire, cancellation, which response is allowed to write,
  loading and error status, invalidation after a write.
- **D2 · Accumulation.** Deciding that page 3's results are *appended* to pages 1–2 rather
  than replacing them, and what the current offset is.

## E — Evidence

- **E1.** The rune is 165 LOC and covers D1 for 8 migrated components without a special
  case (`PLN-001`/P5).
- **E2.** Exactly one of 26 components needs D2: `AlbumGrid`, which appends pages under a
  debounced `search` and a `sort`, with a `GROUPED_LIMIT` of 5000 for grouped modes.
- **E3.** `PLN-001`/P5 set a falsifier before any code existed: if the rune passes ~200 LOC
  or grows a cache-eviction policy, take TanStack Query instead.
- **E4.** D2 and D1 disagree about what a new response *means*. D1's correct default is
  "the newest response replaces the previous one"; accumulation needs the opposite, and
  needs to know when to reset — a filter change resets, a page change does not.

## A — Assumptions

- **A1.** No second component will need accumulation soon. Every other list in Kiku either
  loads whole or is served by the existing `PaginatedTracks` limit/offset without appending.
  *Falsifier:* a second accumulating list appears, at which point extract a shared
  `createPagedResource` rather than widening this one.

## R — Reasoning

- **R1** [E4] ⇒ Supporting D2 inside the rune means a mode flag that inverts its central
  rule about which response wins, plus reset semantics keyed to which arg changed. That is
  not a parameter; it is a second component living inside the first.
- **R2** [E2, A1] ⇒ The cost is paid by all 26 call sites to serve 1. Generalising from a
  single instance is how a 165-line helper becomes an unowned framework.
- **R3** [R1, E3] ⇒ Widening the rune moves it toward the falsifier the plan set in advance.
  If accumulation is genuinely needed everywhere later, the honest answer is a real query
  library, not a home-grown one that grew into a worse copy of it.
- **R4** [E1] ⇒ Keeping D2 out costs `AlbumGrid` its existing local offset/append state,
  which already works. Nothing is lost; one component stays as it is.

## K — Conclusions

- **K1 · Decision: `createResource` owns D1 only. Accumulation stays with the caller.**
- **K2 · `AlbumGrid` keeps its own offset and append logic.** Its *fetch* still moves onto
  the rune where that is clean; the list-building around it does not.
- **K3 · The migration metric follows from K1:** a component is done when it no longer
  hand-rolls a fetch lifecycle — not when it holds no state at all. Paging state, mutation
  flags, and derived view state are all legitimately local (`PLN-001`/P5).
- **K4 · Revisit on a second instance, not on a first inconvenience** (A1). The next
  accumulating list means extracting `createPagedResource` beside this one; a third means
  reconsidering E3's falsifier in earnest.
