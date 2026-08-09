---
id: CLM-001
title: The tech stack is a correct set of choices operated without a supporting apparatus
type: CLM
date: 2026-08-09
depends-on: [OBS-001, OBS-002, OBS-004, OBS-006, OBS-007]
superseded-by: null
---

## C — Context

Kiku's technology choices, benchmarked against what a competent product team would run in
2026 — specifically, the practices that keep a two-year-old codebase pleasant to change.

## D — Definitions

- **D1 · Choice.** Which technologies are used.
- **D2 · Apparatus.** The machinery that keeps a choice honest over time: locks, gates,
  contract generation, migrations, observability, reproducible environments.
- **D3 · Benchmark.** The 2026 baseline for a product web application: CI on every PR;
  linted and type-checked in the gate; a lockfile; a container or equivalent manifest;
  migrations as the sole schema authority; generated client types from an API contract;
  component and E2E tests; error and performance telemetry; structured logs.

## E — Evidence

Inherited: `OBS-001/K1`, `OBS-002/K1`, `OBS-004/K1-K2`, `OBS-006/K1-K2`, `OBS-007/K1-K3`.

- **E1 · Benchmark scorecard.**

  | Benchmark practice (D3) | Kiku | Source |
  |---|---|---|
  | Modern frontend framework, current major | ✅ Svelte 5 / Kit 2 / Vite 7 | `OBS-004/E1` |
  | Typed end to end | ✅ TS strict-clean, Pydantic schemas | `OBS-002/E3` |
  | Lean dependency graph | ✅ 3 FE runtime deps, extras-isolated BE | `OBS-007/K1` |
  | Domain logic separable from transport | 🟡 core clean, rind thick | `OBS-006/K1,K2` |
  | Backend test suite | ✅ 426 tests, 11s | `OBS-002/E1` |
  | Frontend tests | ❌ zero | `OBS-002/E2` |
  | CI on every push | ❌ no `.github/` | `OBS-002/E4` |
  | Linter / formatter in a gate | ❌ none configured | `OBS-002/E6,E7` |
  | Lockfile | 🟡 npm yes, Python no | `OBS-007/E3` |
  | Container / env manifest | ❌ none | `OBS-007/E7` |
  | Migrations as schema authority | ❌ broken from base | `OBS-003/K2` |
  | Generated API client types | ❌ 699 LOC hand-mirrored | `OBS-005/E4` |
  | Route-level code splitting | ❌ one 540 KB chunk | `OBS-004/E6` |
  | Error telemetry / boundaries | ❌ none | `OBS-004/E7` |
  | Structured logging / tracing | ❌ none | `OBS-006/E8` |

  Score: **4 of 15 fully met, 2 partial, 9 absent.**

- **E2 · The absences cluster.** All nine absent rows are D2 (apparatus). All four fully
  met rows are D1 (choice).

## A — Assumptions

- **A1.** Kiku is intended to outlive its current single-machine, single-author phase — the
  personal-server arc and the Rust migration plan both presuppose this.
  *Falsifier:* the author decides Kiku is permanently a personal laptop tool, in which
  case roughly half of the absent rows in E1 are correctly absent.

## R — Reasoning

- **R1** [E1, E2] ⇒ The scorecard does not describe a project that picked badly. Every
  technology selection is one a strong team would also make in 2026, and two of them —
  the three-dependency frontend and the extras-isolated backend — are *better* than the
  median commercial codebase, which accretes dependencies as a substitute for decisions.
- **R2** [E2] ⇒ The deficit is uniform in kind. This matters: nine unrelated-looking gaps
  that all fall in one category are usually one cause, not nine problems. The cause is that
  the project has never had a reader other than its author, so every check that exists to
  inform *someone else* has been skipped as redundant.
- **R3** [R2, A1] ⇒ Under A1, "someone else" arrives. The someone else is the second
  machine (`OBS-007/K3`), the deployed instance (`OBS-003/K5`), the Rust port reading the
  Python as a spec (`OBS-006/K3`), and the author in eighteen months. Each of these is a
  reader who cannot ask the author what is true.
- **R4** [`OBS-003/K2`, `OBS-007/K3`] ⇒ Two absent rows are qualitatively different from the
  other seven. No lockfile is a risk; no CI is a risk; but a schema that cannot be built
  from scratch *plus* an environment that cannot be reproduced is not a risk — it is a
  present-tense inability. Every other item on the list can be added later at roughly the
  same cost. These two get more expensive every week, because every new column and every
  new dependency widens the gap between the running system and the described one.
- **R5** [R1, R4] ⇒ Therefore the correct posture is **not** a stack change. Any effort
  spent re-choosing technologies is spent on the one dimension where Kiku is already
  correct, and not spent on the nine where it is not.

## K — Conclusions

- **K1 · The stack is right. Keep it.** Svelte 5 + SvelteKit 2 + Vite 7 + FastAPI +
  SQLAlchemy 2 + SQLite is a defensible 2026 stack for this product, and the restraint
  shown in dependency count is a genuine competitive advantage in maintenance cost.
- **K2 · Kiku scores 4/15 (plus 2 partial) on the 2026 apparatus benchmark, and every failure is apparatus,
  not choice.** This is the good version of a bad score: apparatus is addable, taste is not.
- **K3 · Two failures are load-bearing and dated.** `OBS-003/K2` (Alembic cannot run from
  base) and `OBS-007/K3` (no Python lockfile, no manifest, false interpreter floor) jointly mean the repository cannot
  stand up a working copy of itself. They should be fixed before anything on the feature
  roadmap, because they are the precondition for CI, which is the precondition for
  everything else on the scorecard.
- **K4 · SQLite is not on the list of problems.** For a single-DJ library of ~4,300 tracks
  it is the right call, and the personal-server arc does not change that. Do not let a
  general-purpose "modernisation" instinct migrate this to Postgres; nothing in the
  evidence justifies it.
- **K5 · The Rust migration plan is premature by exactly one step.** `OBS-006/K2` — the
  service boundary does not exist yet — means a strangler-fig port would today be porting
  route handlers, i.e. the transport rind, rather than the domain core. Extract services
  first; the port becomes a mechanical exercise afterwards, and may prove unnecessary.
