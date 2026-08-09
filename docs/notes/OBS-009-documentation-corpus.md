---
id: OBS-009
title: State of the written record
type: OBS
date: 2026-08-09
depends-on: []
superseded-by: null
---

## C — Context

Baseline for the documentation half of this effort: what exists, what it is for, and where
it has rotted. Motivates [[DOC_SYSTEM]].

## E — Evidence

- **E1 · Root-level markdown: 12 files.** `AGENTS.md`, `BACKEND_MIGRATION.md`,
  `BRANDING.md`, `CLAUDE.md`, `GEMINI.md`, `PERSONAL_SERVER.md`,
  `PERSONAL_SERVER_ALIGNMENT.md`, `PROJECT_AGENTS.md`, `README.md`, `ROADMAP.md`,
  `SOUNDCLOUD_EXPORT.md`, `TRACKLIST_EXPORT.md`.
- **E2 · Five of those twelve are untracked.** `git status` shows `BACKEND_MIGRATION.md`,
  `PERSONAL_SERVER.md`, `PERSONAL_SERVER_ALIGNMENT.md`, `SOUNDCLOUD_EXPORT.md`,
  `TRACKLIST_EXPORT.md` as `??`. Substantial design work exists only on one disk.
- **E3 · Spec corpus: 31 documents** under `specs/2026/{03,04,06,07}/<branch>/`, numbered
  001–029. Recent specs are long — spec 029 is 521 lines.
- **E4 · Specs are staged, not chunked.** Spec 029's headings run Human Section (HLO / MLO
  / Details / Constraints / Testing / Behavior) then AI Section (Research / Strategy / Plan
  / Tasks 1–9 / Validate / Plan Review / Implement / Results / Test Evidence / Updated Doc
  / Post-Implement Review / Backlog nits / Next steps / Feedback).
- **E5 · Findings are trapped inside specs.** Spec 029's Research section contains reusable
  facts about the planner and energy profiles. Nothing outside spec 029 can cite them; a
  later spec must re-derive or re-read.
- **E6 · `ROADMAP.md` is stale.** Version 2.0, dated 2026-04-04, framing "Q2 2026 (April –
  June)" as upcoming. Today is 2026-08-09; specs 016–029 have shipped since.
- **E7 · `README.md` is accurate but thin.** Correct feature list and install steps. No
  architecture section, no diagram, no contribution or testing instructions.
- **E8 · There is no architecture document.** Nothing describes the request path, the
  module boundaries, or the CLI-vs-API split.
- **E9 · Three parallel agent instruction files** — `CLAUDE.md`, `AGENTS.md`, `GEMINI.md`
  — plus a `PROJECT_AGENTS.md`, with overlapping content.
- **E10 · The one durable convention is good.** `BRANDING.md` and the CLAUDE.md condensation
  of it (7 "even over" principles, voice table, anti-principles) is genuinely load-bearing
  and consistently applied in shipped copy.

## K — Conclusions

- **K1 · Volume is not the problem; addressability is.** 43 documents exist. The corpus is
  large enough that the binding constraint is retrieval, and nothing in it is addressable
  below file granularity (E5).
- **K2 · Specs are optimised for the act of building, not for the state of knowing.** E4's
  stage sequence is a workflow log. It is the right shape while a feature is in flight and
  the wrong shape six months later, when the reader wants one fact, not one history.
- **K3 · Knowledge decays because nothing declares its own expiry.** E6 is the visible
  instance; E7/E8 are the invisible ones. No document in the corpus states the observation
  that would prove it stale.
- **K4 · E2 is a live risk, independent of format.** Five design documents — including the
  backend-migration and personal-server plans — are one `rm -rf` from gone.
- **K5 · The gap KNF fills is precisely E5+K3:** facts extracted from specs into
  individually citable, individually falsifiable chunks. It does not replace specs (E4 is
  fine at what it does); it drains the reusable parts out of them.
- **K6 · E10 is the proof the author can sustain a written convention.** The branding
  guide has held across 29 specs. A documentation format has a realistic chance of
  sticking here.

## Q — Open

- **Q1.** Do `AGENTS.md` and `GEMINI.md` still serve distinct readers, or can E9 collapse
  to one file plus symlinks?
