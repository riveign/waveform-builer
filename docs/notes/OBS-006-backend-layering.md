---
id: OBS-006
title: Backend layering — a clean domain core behind a thick transport rind
type: OBS
date: 2026-08-09
depends-on: []
superseded-by: null
---

## C — Context

Whether the backend has a reusable domain layer, or whether logic lives in the places that
happen to receive requests.

> **Re-check 2026-08-10 — [[PLN-001]]/P9 shipped.** `src/kiku/services/` exists; **K2 is
> half-discharged**. `sets.py` is 1,261 lines with **zero** `db.query`, and `E6`'s
> duplication is gone for set resolution — one use-case now backs both transports.
> **K3 stands for the other route modules** (albums, tracks, tinder still query the ORM
> directly), and **K6 stands**: the two SSE endpoints were deliberately left. **K5's
> consequence for `CLM-001/K5` is the interesting one — with a service boundary in place,
> a Rust port would now be porting the domain rather than the rind, which is the question
> that was premature before.**
>
> **Superseded — the note below described the state before P9:**
>
> **Re-checked 2026-08-09 — unchanged, and that is the point.** [[PLN-001]] P1–P7 were all
> either infrastructure or frontend; nothing touched the layering. `api/routes/sets.py` is
> **1,410 lines** (up from 1,340). Every conclusion K1–K6 stands as written, and K3's
> ceiling is now the binding one: this is P9, the last structural item before the Rust
> question can be answered honestly.
## D — Definitions

- **D1 · Domain layer.** Code that expresses Kiku's actual ideas — scoring, planning,
  energy, analysis — and that could be called from a CLI, an HTTP route, a test, or a
  future Rust port without change.
- **D2 · Transport layer.** HTTP routing, CLI argument parsing, serialization.

## E — Evidence

- **E1 · A real domain layer exists.** `src/kiku/setbuilder/` holds `scoring.py` (686),
  `planner.py` (377), `constraints.py`, `filler.py`, `reorder.py`, `camelot.py`,
  `slot_picks.py`, `artist_picks.py`. `src/kiku/analysis/` holds `set_analyzer.py` (408),
  `autotag.py` (480), `teaching.py` (324), `insights.py` (324), `set_compare.py` (296).
  These are testable pure-ish modules and are what the 426 tests mostly exercise.
- **E2 · Transport is disproportionately large.** `api/routes/` totals 3,764 LOC across 11
  modules plus a 976-LOC `schemas.py`; `cli.py` is a single 1,631-LOC file. Combined,
  D2 is ~6,400 LOC — roughly 31% of `src/kiku`.
- **E3 · `sets.py` is a route module doing service work.** 1,340 LOC, ~30 endpoints, and it
  defines private helpers with domain semantics inside the route file:
  `_set_track_response`, `_clear_comparison_caches`, `_purge_expired_sets`,
  `_track_summary`, `_track_response`, `_sse_event`.
- **E4 · Routes talk to the ORM directly.** `session.query(...)` / `db.query(...)` appears
  in 6 of 11 route modules (albums 8, tracks 5, sets 5, tinder 3, export 1, soundcloud 1).
  There is no repository layer; `db/store.py` (767 LOC) exists but is not the sole gateway.
- **E5 · No service layer between routes and domain.** There is no `services/` package.
  The call shape is route → (ORM + domain functions) → response model.
- **E6 · Business rules are duplicated across transports.** Both `cli.py` and
  `api/routes/` construct planner/scoring invocations; there is no shared use-case object,
  so a change to how a set is built must be made in both entry points.
- **E7 · Two long-lived streaming endpoints.** `POST /sets/build` and `POST /sets/{id}/fill`
  are SSE generators defined inline in `sets.py` (lines 305–433 and 648–686), holding a
  request-scoped `Session` for the duration of the stream.
- **E8 · No observability.** No structured logging configuration, no request IDs, no
  metrics, no tracing. `api/main.py` is 47 lines.

## K — Conclusions

- **K1 · The valuable part of the backend is in good shape.** E1 is the codebase's real
  asset: Kiku's ideas are expressed in modules that are independently testable, and the
  test suite proves it (`OBS-002/K2`). This is the opposite of the common failure mode.
- **K2 · The rind is where the rot is.** E2–E5: ~6,400 LOC of transport that has quietly
  absorbed service responsibilities. `sets.py` is not "a big router"; it is an undeclared
  set-service with HTTP decorators on it.
- **K3 · E6 sets the ceiling on the number of clients.** Today there are two entry points
  (CLI, HTTP) and the duplication is annoying. The personal-server/PWA arc adds a third and
  the Rust migration adds a fourth; at that point E6 stops being annoying and starts being
  the reason features ship inconsistently.
- **K4 · E4 is the mechanism by which `OBS-003/K3` (schema drift) reaches users as 500s.**
  With queries spread across 6 route modules, a column that exists in the ORM but not in
  the deployed database fails at request time, in whichever route touches it first.
- **K5 · E8 means production diagnosis is currently impossible.** For a laptop-only tool
  this is fine. It becomes a blocker the same moment `OBS-003/K5` does — when Kiku runs
  somewhere the author is not watching.
- **K6 · E7 is the highest-risk code to port.** Streaming + a held session + inline
  generators is exactly the shape that resists a strangler-fig migration; it should be the
  *last* thing moved, and it needs a service boundary (K2) first.

## Q — Open

- **Q1.** Does `db/store.py` (767 LOC) already want to be the repository layer, or is it a
  grab-bag? Reading it decides whether the service extraction has a head start.
