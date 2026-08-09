# Note index

Format: [KNF](../DOC_SYSTEM.md). Dependency direction is one-way: `OBS → CLM → DEC → PLN`.
Cite statements, not documents — `OBS-003/K2`, never "see OBS-003".

## OBS — what is true right now

| ID | Title | Headline |
|----|-------|----------|
| [OBS-001](OBS-001-codebase-inventory.md) | Codebase inventory and mass distribution | ~55k LOC, 46/54 backend/frontend; 10 files hold 21% of it |
| [OBS-002](OBS-002-quality-gates.md) | Test coverage and automated quality gates | 426 backend tests pass; **0 frontend tests, 0 gates, no CI** |
| [OBS-003](OBS-003-schema-management-split.md) | Alembic vs `create_all` | **`alembic upgrade head` raises on an empty DB** — reproduced |
| [OBS-004](OBS-004-frontend-architecture.md) | Frontend architecture and delivery shape | Current stack, one route, no URL state, one 540 KB chunk |
| [OBS-005](OBS-005-frontend-data-layer.md) | Frontend data layer | Transport centralised and clean; orchestration hand-rolled 44× |
| [OBS-006](OBS-006-backend-layering.md) | Backend layering | Clean domain core, ~6,400 LOC transport rind doing service work |
| [OBS-007](OBS-007-runtime-and-dependency-baseline.md) | Runtime and dependency baseline | Lean deps; **no Python lock, no manifest, declared floor is false** |
| [OBS-008](OBS-008-design-system-state.md) | Design system maturity | Tokens excellent (2,033 uses); structural primitives missing |
| [OBS-009](OBS-009-documentation-corpus.md) | State of the written record | 43 documents, none addressable below file level; 5 untracked |

## CLM — what it means

| ID | Title | Verdict |
|----|-------|---------|
| [CLM-001](CLM-001-tech-stack-verdict.md) | Tech stack verdict | Choices right, apparatus absent — **4/15 (+2 partial) on the 2026 benchmark** |
| [CLM-002](CLM-002-frontend-rebuild-verdict.md) | Frontend rebuild verdict | **Do not rebuild.** Rebuild dividend is one trivial row |
| [CLM-003](CLM-003-maintainability-verdict.md) | Maintainability verdict | Good bones, no immune system; cost curve is rising |
| [CLM-004](CLM-004-binding-constraint.md) | The binding constraint | **The repo cannot produce a running Kiku on a clean machine** |

## PLN — what to do

| ID | Title | Shape |
|----|-------|-------|
| [PLN-001](PLN-001-top-10-changes.md) | The ten changes, ranked | ≈21–31 author-days; P1–P3 are ~4 of them |

## DEC — what we chose

| ID | Title | Decision |
|----|-------|----------|
| [DEC-001](DEC-001-note-taxonomy.md) | Why four note types, and why OBS/CLM/DEC/PLN | Sort by **expiry mode**, not topic — that's what makes "is this still true?" cheap |
| [DEC-002](DEC-002-knf-in-specs.md) | Specs are derivations that deposit notes | A spec is the *working*, notes are the *deposit* — same skeleton, two lifetimes |

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

- **"Just tell me what to do"** → [PLN-001](PLN-001-top-10-changes.md), the table.
- **"Why that order?"** → [CLM-004](CLM-004-binding-constraint.md).
- **"Should I rebuild the frontend?"** → [CLM-002](CLM-002-frontend-rebuild-verdict.md).
- **"How does Kiku compare to how good teams build things?"** → [CLM-001](CLM-001-tech-stack-verdict.md)/E1.
- **"How do I write one of these?"** → [DOC_SYSTEM.md](../DOC_SYSTEM.md)/K1.
- **"Why these type names?"** → [DEC-001](DEC-001-note-taxonomy.md)/R3, R6.
- **"How do I write my next spec?"** → [DEC-002](DEC-002-knf-in-specs.md)/K2, and the map above.
