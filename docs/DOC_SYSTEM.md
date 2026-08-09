# Kiku Note Format (KNF)

**Status:** active · **Since:** 2026-08-09 · **Applies to:** everything under `docs/notes/`

A document should read like a proof, not like a report. This file defines how we write
them. It is itself written in the format, so it doubles as the worked example.

---

## C — Context

Kiku's written record is currently split across twelve root-level `.md` files and
thirty-one spec documents. Those documents are *narrative*: they explain by accumulation.
Narrative documents have three failure modes we keep hitting.

1. A claim and the reason for the claim drift apart, so a later reader cannot tell whether
   a decision is still load-bearing.
2. Assumptions get stated once, in prose, and are never revisited when they expire.
3. Nothing is reusable. To cite one fact you must re-read the document that contains it.

We want the opposite: **small, addressable, individually falsifiable chunks that compose.**

---

## D — Definitions

- **D1 · Note.** One file. One conclusion. If a file needs two conclusions, it is two files.
- **D2 · Chunk address.** `TYPE-NNN`. Stable forever. Notes are never renumbered; a wrong
  note is marked `superseded-by:` and left in place, because the derivations that cited it
  must remain readable.
- **D3 · Line label.** A single-letter-prefixed, numbered statement: `E4`, `A2`, `R7`.
  Labels are local to their note. Cross-note references are qualified: `OBS-003/K1`.
- **D4 · Derivation step.** A line of the form
  `R<n> [inputs] ⇒ statement`, where every input is a label defined *earlier* —
  in this note or in a cited note. A step with no inputs is not a step; it is either
  evidence (`E`) or an assumption (`A`), and must be relabelled as such.
- **D5 · Assumption.** A statement used as an input that is *not* backed by evidence.
  Every assumption carries a **falsifier**: the concrete observation that would kill it.
  An assumption with no falsifier is an opinion and does not belong in the derivation.

---

## E — Evidence

- **E1.** The repository has 31 spec documents (`find specs -name '*.md' | wc -l`) and 12
  root-level `.md` files, with no `docs/` directory prior to this note.
- **E2.** `ROADMAP.md` is dated 2026-04-04 and describes Q2 2026 as the current timeframe;
  today is 2026-08-09.
- **E3.** The `/spec` template already separates a Human Section from an AI Section, and
  already has distinct `Research` / `Plan` / `Implement` / `Review` stages — i.e. the
  *staging* discipline exists; the *statement* discipline does not.

---

## A — Assumptions

- **A1.** The primary reader of these notes is either the author six months later or an
  agent loading a subset of them as context.
  *Falsifier:* the notes get read mainly by a third party who needs onboarding prose.
- **A2.** Retrieval will be partial — a reader pulls three notes, not the whole corpus.
  *Falsifier:* notes are only ever read front-to-back as one document.

---

## R — Reasoning

- **R1** [A2] ⇒ Every note must be self-contained enough to survive being read alone.
  Therefore each note restates the definitions it uses rather than assuming a preamble.
- **R2** [A2, D2] ⇒ Cross-note references must point at a *statement*, not a document.
  `OBS-003` is not a citation; `OBS-003/K1` is. This is why labels are mandatory.
- **R3** [E1, E2] ⇒ Documents without an explicit expiry mechanism rot silently. Therefore
  evidence lines carry their source command or `file:line`, so any reader can re-run the
  check and detect rot in seconds rather than trusting the prose.
- **R4** [D5, R3] ⇒ The falsifier field is what makes a note *maintainable*: it converts
  "is this still true?" from a research question into a one-line check.
- **R5** [E3, R1] ⇒ KNF does not replace `/spec`. A spec is the *working*; notes are the
  *deposit*. The full mapping — every spec stage to its KNF section, and the deposit step
  that drains reusable findings out of specs — is derived in [[DEC-002]]. Summary:
  Research is `E`, Strategy is `R`, Plan is `K` made executable, PLAN_REVIEW is a proof
  check, and REVIEW is falsification.

---

## K — Conclusions

**K1 · The note skeleton.** Every note under `docs/notes/` has these sections, in this
order. Empty sections are omitted, except `E` and `K`, which are mandatory.

| § | Name | Contains | Rule |
|---|------|----------|------|
| **C** | Context | Why this note exists | ≤ 1 paragraph. No claims. |
| **D** | Definitions | Terms and symbols used below | Only terms that are actually used. |
| **E** | Evidence | Observations | Each carries its source: command, `file:line`, or metric. |
| **A** | Assumptions | Unbacked inputs | Each carries a falsifier. |
| **R** | Reasoning | Derivation | Each step is `R<n> [inputs] ⇒ statement`. |
| **K** | Conclusions | What we now know | Each traces to `R` steps. |
| **Q** | Open | What we could not close | Optional. Becomes future notes. |

**K2 · The four note types.** Types are sorted by **how a note expires**, not by what it is
about — so the type alone tells you what would make the note wrong and what it costs to
check. The derivation of the axis, the count, and the names is in [[DEC-001]]; do not
change this table without reading `DEC-001`/K2.

| Type | Answers | Expires when… | Rests on | Maintenance |
|------|---------|---------------|----------|-------------|
| `OBS` | "What is true right now?" | the world moves | the world | Re-run the command in its `E` lines. Re-measure in place, dated. |
| `CLM` | "What does that mean?" | an input moves | `OBS` | Check its `depends-on`. Supersede. |
| `DEC` | "What did we choose, and why?" | we change our minds | `OBS`, `CLM` | Never re-checked — a past choice is a fact about history. Reversed by a new `DEC`. |
| `PLN` | "What do we do about it?" | we do it, or stop wanting to | `CLM`, `DEC` | Check the done-when. Items check off. |

The dependency direction is one-way: `OBS → CLM → DEC → PLN`, and it falls out of the
expiry ordering rather than being a style rule (`DEC-001`/K3). A `CLM` that cites no `OBS`
is an opinion. A `PLN` item that cites no `CLM` is a whim. A `CLM` citing a `PLN` is a
belief justified by an intention.

**K3 · Frontmatter.** Six fields, no more:

```yaml
---
id: OBS-004
title: Frontend architecture and delivery shape
type: OBS
date: 2026-08-09
depends-on: []          # note IDs this derivation consumes
superseded-by: null     # note ID, once wrong
---
```

**K4 · Size budget.** A note that exceeds ~120 lines is doing two jobs. Split it. The point
of the format is that a reader can hold one whole note in their head at once.

**K5 · The one hard rule.** *No unlabelled claim.* If a sentence asserts something the
reader is expected to carry forward, it is an `E`, an `A`, an `R`, or a `K`, and it has a
number. Prose that is not numbered is context, and context is not citable.

**K6 · Two kinds of noise, banned.**

*Self-description* — sentences about the document instead of about the subject. "Nothing
here is a preference; every item cites a note." "This note establishes…". "As we will
see…". The format's guarantees live in this spec; a note that restates them is spending
the reader's attention to praise itself. Write the subject; the structure is visible.

*Vacuous definitions* — a `D` entry that restates a term's ordinary meaning, or that just
names a table column. `**D2 · Done-when.** A check that can be run, not a feeling.` defines
nothing; it is a style instruction wearing a definition's clothes. Define a term only when
the derivation turns on a meaning the reader would not otherwise assume — `D` earns its
place by being *cited* in an `R` step. If no `R` cites it, delete it.

---

## Q — Open

- ~~**Q1.** Should `DEC` notes replace the existing ADR skill output?~~ Closed by
  [[DEC-001]]/R5: `DEC` **is** ADR, with somewhere to put the evidence. Use `DEC`.
- **Q2.** At what corpus size does `INDEX.md` stop being adequate and need real search?
- **Q3.** Does the spec template change in [[DEC-002]]/K2 survive contact with a real
  spec? Falsifier stated in `DEC-002`/K5: spec length should trend down over five specs.
