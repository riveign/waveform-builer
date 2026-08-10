# Note index

Format: [KNF](../DOC_SYSTEM.md). Dependency direction is one-way: `OBS → CLM → DEC → PLN`.
Cite statements, not documents — `OBS-003/K2`, never "see OBS-003".

**Status 2026-08-10 — [[PLN-001]] is complete: all ten changes shipped and merged.** Six of the nine
`OBS` notes below have been overtaken by that work. They are kept, not rewritten: the
original evidence is what `CLM-001`–`CLM-004` derive from, so each note carries a dated
re-check at the top saying which of its conclusions no longer hold. The **Now** column here
is the short version.

## OBS — what is true right now

| ID | Title | Originally | Now |
|----|-------|-----------|-----|
| [OBS-001](OBS-001-codebase-inventory.md) | Codebase inventory | ~55k LOC, 46/54 backend/frontend | 🟡 ~63k LOC; the 10 oversized files are smaller but still oversized |
| [OBS-002](OBS-002-quality-gates.md) | Quality gates | **0 gates, no CI** | ✅ **7 gates on every PR** · 501 backend + 65 frontend tests |
| [OBS-003](OBS-003-schema-management-split.md) | Alembic vs `create_all` | `upgrade head` raised on an empty DB | ✅ Alembic is sole authority, invariant test in CI |
| [OBS-004](OBS-004-frontend-architecture.md) | Frontend architecture | one route, no URL state, 540 KB chunk | ✅ 7 routes, URL-addressable, landing route 292 KB |
| [OBS-005](OBS-005-frontend-data-layer.md) | Frontend data layer | orchestration hand-rolled 44× | ✅ `createResource` (22/26) · types generated · **K3(b) still open** |
| [OBS-006](OBS-006-backend-layering.md) | Backend layering | clean core, thick transport rind | 🟡 service layer exists; `sets.py` 1,261 lines, 0 `db.query`. Other route modules still query directly |
| [OBS-007](OBS-007-runtime-and-dependency-baseline.md) | Runtime + dependencies | no lock, false interpreter floor | ✅ `uv.lock`, `>=3.11` pinned, one-command setup |
| [OBS-008](OBS-008-design-system-state.md) | Design system | structural primitives missing | ✅ 15 primitives, one dialog shell; 123 hex literals remain |
| [OBS-009](OBS-009-documentation-corpus.md) | The written record | nothing addressable below file level | 🟡 KNF exists and is used; **5 design docs still untracked** |

## CLM — what it means

| ID | Title | Verdict | Now |
|----|-------|---------|-----|
| [CLM-001](CLM-001-tech-stack-verdict.md) | Tech stack | Choices right, apparatus absent — **4/15** | 🟡 **11/15 met, 3 partial** — observability is the main gap left |
| [CLM-002](CLM-002-frontend-rebuild-verdict.md) | Frontend rebuild | **Do not rebuild** | ✅ held — all three named changes shipped incrementally |
| [CLM-003](CLM-003-maintainability-verdict.md) | Maintainability | Good bones, no immune system | 🟡 immune system exists; the 5-edit boundaries are half-closed |
| [CLM-004](CLM-004-binding-constraint.md) | The binding constraint | repo can't build itself on a clean machine | ✅ **relieved** — clean clone → passing suite in one command |

## PLN — what to do

| ID | Title | Progress |
|----|-------|----------|
| [PLN-001](PLN-001-top-10-changes.md) | The ten changes, ranked | ✅ **All ten done and merged.** |

## DEC — what we chose

| ID | Title | Decision |
|----|-------|----------|
| [DEC-001](DEC-001-note-taxonomy.md) | Why four note types, and why OBS/CLM/DEC/PLN | Sort by **expiry mode**, not topic — that's what makes "is this still true?" cheap |
| [DEC-002](DEC-002-knf-in-specs.md) | Specs are derivations that deposit notes | A spec is the *working*, notes are the *deposit* — same skeleton, two lifetimes |
| [DEC-003](DEC-003-resource-boundary.md) | Where `createResource` stops | It owns the fetch lifecycle; **accumulation stays with the caller** |

## The spec ↔ KNF map

From [[DEC-002]]/R1. A spec is already a KNF derivation; the labels were just invisible.

| `/spec` | KNF | |
|---|---|---|
| HLO / MLO | *target* | the conclusion we're trying to reach |
| Details / Scope | **D** | definitions |
| Constraints | **A** | premises — give each a falsifier |
| Research | **E** | observations, with `file:line` |
| **Strategy** | **R** | **the derivation — the template's weakest joint (`DEC-002`/R3)** |
| Plan tasks | **K** | conclusions made executable — each cites its `R` |
| PLAN_REVIEW / VALIDATE | *proof check* | every task → an `R`; every `R` → an `E`/`A` |
| Results / Test Evidence | **E′** | post-hoc observations |
| Review | *falsification* | predicted `K` vs observed `E′` |
| Nits / Next steps | **Q** | what we couldn't close |

At DOCUMENT, the spec **deposits**: Research `E` → `OBS`, design choices → `DEC`,
leftovers → `PLN` (`DEC-002`/K4). Then it links to them instead of holding them.

## Reading paths

- **"Where are we?"** → the Now column above, then [PLN-001](PLN-001-top-10-changes.md).
- **"What's left to do"** → [PLN-001](PLN-001-top-10-changes.md), items P8–P10.
- **"Why that order?"** → [CLM-004](CLM-004-binding-constraint.md).
- **"Should I rebuild the frontend?"** → [CLM-002](CLM-002-frontend-rebuild-verdict.md).
- **"How does Kiku compare to how good teams build things?"** → [CLM-001](CLM-001-tech-stack-verdict.md)/E1.
- **"How do I write one of these?"** → [DOC_SYSTEM.md](../DOC_SYSTEM.md)/K1.
- **"Why these type names?"** → [DEC-001](DEC-001-note-taxonomy.md)/R3, R6.
- **"How do I write my next spec?"** → [DEC-002](DEC-002-knf-in-specs.md)/K2, and the map above.
