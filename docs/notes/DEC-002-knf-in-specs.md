---
id: DEC-002
title: Specs are derivations that deposit notes — how KNF and /spec compose
type: DEC
date: 2026-08-09
depends-on: [OBS-009, DEC-001]
superseded-by: null
---

## C — Context

`DOC_SYSTEM.md`/R5 claimed "specs are process, notes are knowledge" and left the two
systems side by side. That is a truce, not a design: it leaves every spec re-deriving
facts that a note already holds, and every spec's findings dying with the branch.

## D — Definitions

- **D1 · Working.** In the exam sense: the derivation you write to get to an answer. Its
  value is mostly consumed at the moment of writing.
- **D2 · Deposit.** What survives the working and is worth citing later.

## E — Evidence

- **E1 · The spec template's real structure.** Human Section: HLO, MLO, Details, Scope,
  Design direction, Codebase anchors, Constraints, Testing, Behavior. AI Section: Research,
  Strategy, Plan (Files, Tasks), Validate, Plan Review, [Design], Implement, Results, Test
  Evidence, Updated Doc, Post-Implement Review, Backlog nits, Next steps, Feedback.
- **E2 · Stage goals, from the stage definitions.**
  RESEARCH: "RESEARCH affected files-lines and logic involved", then "STRATEGIZE HOW to
  ACHIEVE GOAL". PLAN: "a COMPLETE dry-run of the IMPLEMENT step". PLAN_REVIEW: "Validate
  PLAN robustness, consistency, accuracy" against "aligns with Research/Strategy".
  VALIDATE: "EVALUATE if AFTER implementing the Plan, the SPEC will successfully ACHIEVE
  Objectives, ALIGNED with Research". REVIEW: "Compare EACH Task with the actual
  implementation… DOCUMENT ANY deviations".
- **E3 · Specs are long and getting longer.** Spec 029 is 521 lines; spec 027 is ~950.
- **E4 · Reusable facts die inside them** — `OBS-009/E5`. Spec 029's Research section
  contains durable facts about the planner and the energy profile that nothing outside
  spec 029 can cite.
- **E5 · Codebase anchors are re-researched every spec.** The Human Section of specs 027,
  028 and 029 each carries a "Codebase anchors (verify in RESEARCH)" block covering
  overlapping ground.
- **E6 · Strategy is the least structured section.** In E1's list it is the only AI-Section
  heading with no stage agent of its own — it is produced as step 5 of RESEARCH and
  reviewed only indirectly, via PLAN_REVIEW's "aligns with Research/Strategy".

## A — Assumptions

- **A1.** The `/spec` stage workflow stays. It works, it has 29 specs of momentum, and the
  commit-per-stage discipline is genuinely useful.
  *Falsifier:* the author abandons staged specs for another workflow.
- **A2.** Adopting KNF inside specs must cost near-zero extra effort per spec, or it will
  be dropped under deadline like every other unenforced convention (`CLM-003/R3`).
  *Falsifier:* two consecutive specs written in the new shape that felt slower.

## R — Reasoning

- **R1** [E1, E2] ⇒ Read the stage list against `DOC_SYSTEM.md`/K1's sections. They are the
  same skeleton, in the same order, under different names:

  | `/spec` stage or section | KNF | What it actually is |
  |---|---|---|
  | HLO / MLO | *target* | the conclusion we are trying to reach — a **goal**, not yet a claim |
  | Details / Scope / Design direction | **D** | definitions and the shape of the problem |
  | Constraints | **A** | premises we are choosing to accept |
  | Codebase anchors | **E** (borrowed) | observations, mostly re-copied from prior specs |
  | RESEARCH | **E** | observations, with `file:line` |
  | Strategy | **R** | the derivation from evidence to approach |
  | PLAN (Files, Tasks) | **K**, made executable | conclusions expressed as ordered operations |
  | PLAN_REVIEW / VALIDATE | *proof check* | does every task trace back to an `R`, every `R` to an `E`/`A`? |
  | IMPLEMENT | — | execution; not part of the derivation |
  | Results / Test Evidence | **E′** | new observations, generated after the fact |
  | REVIEW | *falsification* | compare predicted `K` against observed `E′` |
  | Backlog nits / Next steps / Feedback | **Q** | what we could not close |

- **R2** [R1] ⇒ A spec is already a KNF derivation. Nothing needs to be added; the labels
  need to be made visible. This satisfies A2 directly — the work is renaming and numbering,
  not writing more.
- **R3** [R1, E6] ⇒ The mapping locates the template's weakest joint precisely. **Strategy
  is the `R` section**, and it is the only part of a spec with no stage agent, no numbered
  form, and no direct review (E6). That is exactly where unexamined jumps live — a spec can
  today go from a solid Research section to a detailed Plan with the reasoning between them
  stated in a paragraph. Numbering Strategy as `R<n> [inputs] ⇒ …` is the single
  highest-value change to the template, because it forces every Plan task to have a parent.
- **R4** [R1] ⇒ PLAN_REVIEW and VALIDATE currently ask fuzzy questions ("robustness",
  "consistency", "alignment"). Under R1 they get one sharp mechanical check that subsumes
  most of it: **every Task cites an `R`; every `R` cites an `E` or an `A`; every `A` has a
  falsifier.** A dangling task is an unjustified change; a dangling `R` is a leap.
- **R5** [R1, E2-REVIEW] ⇒ REVIEW is falsification and is already written that way
  ("compare each Task with the actual implementation… document any deviations"). Under KNF
  the comparison sharpens: the Plan **predicted** an outcome, Results/Test Evidence
  **observed** one, and a deviation is a failed prediction that should be traced back to
  which `R` step or `A` was wrong — not merely logged as a deviation.
- **R6** [D1, D2, E3, E4] ⇒ Now the second relationship, which R1 does not give. A spec is
  **working** (D1): 521 lines of it, most consumed at the moment of writing. But its
  Research `E` lines and its Design/Strategy choices are **deposit** (D2). Today the
  deposit is left inside the working, so it cannot be cited (E4) and gets re-derived (E5).
- **R7** [R6, `DEC-001`/R3] ⇒ Route the deposit by expiry mode. A spec's Research produces
  statements that expire when the world moves ⇒ `OBS`. A spec's Design/Strategy produces
  statements that expire when we change our minds ⇒ `DEC`. A spec's Backlog nits and Next
  steps expire when done ⇒ `PLN`. The spec keeps the rest.
- **R8** [R7, E5] ⇒ This inverts the "Codebase anchors" block. Instead of each spec
  re-copying anchors and marking them "verify in RESEARCH", a spec **cites** `OBS-006/E3`
  and RESEARCH's job becomes *confirm or re-measure the cited notes* — which is far cheaper
  than rediscovery, and which keeps the notes fresh as a side effect of normal work.
  Note the compounding: the more specs are written, the less each one costs.

## K — Conclusions

- **K1 · Decision: `/spec` and KNF are the same derivation at two lifetimes.** The spec is
  the working (D1); notes are the deposit (D2). They are not parallel systems and should
  not be maintained as such.
- **K2 · Adopt the labelled form inside the spec template**, per R1. Concretely, four
  changes and no new sections:
  1. **Constraints** → numbered `A1..An`, each with a falsifier.
  2. **Research** → numbered `E1..En`, each with its `file:line` or command.
  3. **Strategy** → numbered `R1..Rn` in the form `R<n> [inputs] ⇒ statement`. *(R3: the
     highest-value item in this list.)*
  4. **Plan tasks** → each opens with the `R` it discharges: `Task 4 [R2] — …`.
- **K3 · Upgrade PLAN_REVIEW and VALIDATE with R4's mechanical check.** It is
  greppable, it is not a matter of taste, and it catches the failure mode those stages
  exist for.
- **K4 · Add a deposit step, not a new stage.** At DOCUMENT (or REVIEW, whichever the
  author reaches), the spec emits its durable half per R7: Research `E` lines that outlive
  the branch become or update an `OBS`; design choices become a `DEC`; leftovers become
  `PLN` items. The spec then links to them instead of holding them. This is the concrete
  closure of `OBS-009/K5`.
- **K5 · RESEARCH's job changes from discovery to confirmation** (R8). A spec opens by
  citing the notes it depends on and re-checking them; it only researches what no note
  covers. Expect specs to get *shorter* as the note corpus grows — which is the falsifier
  for this whole decision: **if spec length does not trend down over the next five specs,
  the deposit step is not paying for itself.**
- **K6 · A spec that has deposited is disposable.** Once K4 has run, the spec's remaining
  value is historical. This is the answer to E3: specs may keep growing, because nobody
  will need to read an old one to learn something.
