---
id: DEC-001
title: Why four note types, and why OBS / CLM / DEC / PLN
type: DEC
date: 2026-08-09
depends-on: [OBS-009]
superseded-by: null
---

## C — Context

`DOC_SYSTEM.md`/K2 asserted four note types and named them, with no derivation — which
breaks the format's own rule (`DOC_SYSTEM.md`/K5: no unlabelled claim). The derivation, and
the naming decision.

## D — Definitions

- **D1 · Taxonomy axis.** The property by which notes are sorted into types. Every
  classification scheme picks one; most pick it implicitly and badly.
- **D2 · Expiry.** The event after which a note's content is no longer true.

## E — Evidence

- **E1 · The corpus rots silently** — `OBS-009/K3`. `ROADMAP.md` was four months stale
  before anyone noticed, and nothing in it declared what would make it stale.
- **E2 · Findings are trapped and un-citable** — `OBS-009/E5,K1`. Granularity, not volume,
  is the binding problem.
- **E3 · Different documents in the corpus expire for completely different reasons.**
  `ROADMAP.md` expired because the plan was executed. `README.md`'s architecture gap will
  expire when the architecture changes. `BRANDING.md` has not expired in five months
  because it records a choice, and choices do not decay — they are only reversed.
- **E4 · Prior art surveyed.** ADR (Nygard), Zettelkasten (fleeting / literature /
  permanent), Diátaxis (tutorial / how-to / reference / explanation), and plain
  topic-folders (`architecture/`, `api/`, `ui/`).

## A — Assumptions

- **A1.** The dominant maintenance question for this corpus is *"is this still true?"*,
  asked by a reader who was not present when it was written.
  *Falsifier:* notes are consulted mainly while being written, and discarded after.

## R — Reasoning

- **R1** [A1] ⇒ The taxonomy axis (D1) should be chosen to make the dominant question
  cheap to answer. So sort notes by **how they expire (D2)**, not by what they are about.
- **R2** [R1] ⇒ Topic-based schemes (`architecture/`, `api/`, `ui/` — part of E4) are
  therefore rejected outright. A topic folder tells you where a note lives and nothing
  about when to distrust it. This is the scheme most repositories use and the reason most
  repository documentation is stale.
- **R3** [R1, E3] ⇒ Enumerate the ways a written engineering statement can stop being
  true. There are exactly four, and they are mutually exclusive:

  | # | Expiry event | Example | Type |
  |---|---|---|---|
  | 1 | **The world moved.** The statement described reality; reality changed. | "426 tests pass" | `OBS` |
  | 2 | **An input moved.** The statement was derived; a premise it rested on expired. | "the stack is fine, the apparatus is not" | `CLM` |
  | 3 | **We changed our minds.** | "SQLite, not Postgres" | `DEC` |
  | 4 | **We did it — or stopped wanting to.** | "add CI" | `PLN` |

- **R4** [R3] ⇒ Four types, and the count is derived rather than chosen. Each type gets a
  distinct maintenance protocol, which is the whole payoff:

  | Type | Re-check by | On expiry |
  |------|-------------|-----------|
  | `OBS` | re-running the command in its `E` lines | re-measure in place, dated |
  | `CLM` | checking whether its `depends-on` notes changed | supersede |
  | `DEC` | never — a past choice is a fact about history | reverse with a new `DEC` |
  | `PLN` | checking the done-when | check off |

- **R5** [E4, R3] ⇒ Evaluate the prior art against R1's axis:
  - **ADR** sorts by expiry correctly, but covers only row 3. Its known failure mode —
    every ADR restating its own context — is exactly the absence of rows 1 and 2 to cite.
    `DEC` is deliberately ADR-compatible; it is ADR *with somewhere to put the evidence*.
  - **Zettelkasten** sorts by *provenance* (where a note came from). Wrong axis under R1:
    provenance does not predict expiry.
  - **Diátaxis** sorts by *reader need*. Correct and excellent for user-facing
    documentation; inapplicable here, because it says nothing about truth over time.
- **R6** [R3] ⇒ Naming. Constraints: three letters uppercase, so that `OBS-003/K2` parses
  as an address at a glance, greps unambiguously, and aligns in index tables.
  - **`OBS` (observation), not `FACT` / `MEAS` / `EVD`.** "Observation" carries an implicit
    observer and an implicit timestamp — *this is what was seen, then*. "Fact" invites
    permanent belief, which is precisely the error row 1 exists to prevent. `EVD` is
    rejected on a category error: evidence is a **role a statement plays in an argument**,
    not a kind of statement. The same observation is evidence in three different `CLM`s.
    Roles are the `E`-labels *inside* a note; types are the notes.
  - **`CLM` (claim), not `CONC` / `THM` / `ANL`.** These derivations run on assumptions
    with falsifiers, so they are arguments, not proofs — `THM` over-promises and `CONC`
    sounds settled. "Claim" is the word that invites the reader to argue back, which is
    also the product's own fifth principle applied to its documentation.
  - **`DEC` (decision), not `ADR` / `CHO`.** `ADR` is the better-known term but bakes
    "architecture" into a type that also records product, process, and naming choices.
  - **`PLN` (plan), not `TODO` / `RFC`.** `TODO` already means something lighter in source
    code; `RFC` implies a review process that a solo project does not run.
- **R7** [R3] ⇒ Closure check — are four enough? Two candidate fifth types were considered
  and rejected because neither introduces a new expiry mode:
  - `DEF` (glossary). Definitions expire when the thing defined changes, i.e. row 1 or 3.
    They live in `D` sections; a standalone glossary is an index, not a note.
  - `QST` (open question). Expires when answered, i.e. it is a `PLN` item with no owner.
    Lives in `Q` sections and graduates into a real note.

## K — Conclusions

- **K1 · Decision: four note types, sorted by expiry mode (R3), named `OBS` / `CLM` /
  `DEC` / `PLN` (R6).**
- **K2 · The axis is the decision; the names are secondary.** If the names are ever
  changed, the constraint to preserve is R1: a reader must be able to tell, from the type
  alone, what would make the note wrong and how much it costs to check.
- **K3 · The one-way dependency `OBS → CLM → DEC → PLN` is not stylistic — it falls out of
  R3.** Each row can only rest on rows above it: a decision rests on claims, a claim rests
  on observations, and an observation rests on the world. A `CLM` citing a `PLN` would mean
  a belief justified by an intention, which is how projects talk themselves into things.
- **K4 · This scheme's own falsifier.** If, after ~50 notes, a substantial number cannot be
  typed without argument, then R3's enumeration is incomplete and the taxonomy needs a
  fifth row — not a judgement call about where to file things.
- **K5 · Consequence for `DOC_SYSTEM.md`.** Its K2 table should cite this note rather than
  assert the taxonomy, and its "`DEC` evidence is cited `CLM`" rule is too narrow: this
  note is a `DEC` resting directly on `OBS-009`. A `DEC` may cite any note above it in K3.
