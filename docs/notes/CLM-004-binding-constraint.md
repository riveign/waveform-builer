---
id: CLM-004
title: The binding constraint is that Kiku cannot reproduce itself
type: CLM
date: 2026-08-09
depends-on: [CLM-001, CLM-002, CLM-003, OBS-003, OBS-007]
superseded-by: null
---

## C — Context

Three verdict notes each end with a priority list. Reconciling them into one statement of
what is actually limiting the project, so [[PLN-001]] has an ordering principle.

## D — Definitions

- **D1 · Binding constraint.** The one limitation such that relieving it raises the ceiling
  on everything else, and such that improving anything else while it holds yields little.

## E — Evidence

- **E1.** `OBS-003/K2` — `alembic upgrade head` raises on an empty database. The schema
  cannot be constructed from the repository.
- **E2.** `OBS-007/K3` — no Python lockfile, no manifest, no pinned interpreter, and a
  declared interpreter floor that is false. The environment cannot be constructed from the
  repository.
- **E3.** `OBS-002/K1` — zero automated gates.
- **E4.** `CLM-001/K2` — 4/15 (+2 partial) on the apparatus benchmark; all nine failures are apparatus.
- **E5.** `CLM-003/K4` — the cost curve is rising, cause is the absent immune system.
- **E6.** `CLM-002/K1` — the frontend does not need rebuilding; three local changes suffice.

## R — Reasoning

- **R1** [E1, E2] ⇒ Conjunction: a clean machine can obtain neither a working schema nor a
  working environment from this repository. Kiku currently exists as a *running instance*
  on one laptop, of which the git repository is an incomplete description.
- **R2** [R1, E3] ⇒ CI is not merely absent; it is currently **unimplementable**. A CI job
  is by definition a clean machine. Any attempt to add one halts at E1 or E2. This
  dependency is why E3 has stayed unfixed despite being obviously worth fixing.
- **R3** [R2, E4, E5] ⇒ Nearly every remaining apparatus gap — linting, coverage, frontend
  tests, type generation, visual regression, a11y checks — derives its value from running
  automatically, i.e. from CI. So R1 gates R2 gates most of E4.
- **R4** [R1, `OBS-003/K5`, `OBS-006/K5`] ⇒ R1 also independently blocks every deployment
  story in the project's stated direction: the personal server, the PWA over Tailscale, and
  any second machine.
- **R5** [R3, R4] ⇒ R1 sits upstream of both the engineering-quality track and the product
  roadmap track. By D1, it is the binding constraint.
- **R6** [E6, R5] ⇒ Note what this displaces. The frontend is the more *visible* weakness
  and the one the author asked about first, but per E6 it needs no restart, and per R3 its
  most valuable fix (tests) is itself gated on R1. Frontend work is correctly sequenced
  *after* reproducibility, not before it.
- **R7** [R1] ⇒ Scope check. Relieving R1 is small: one repair migration plus a test that
  runs the chain from base; a lockfile; a pinned interpreter; a `KIKU_DB_PATH` env
  override. This is days, not weeks — which is the strongest argument for doing it first.

## K — Conclusions

> **Re-check 2026-08-09 — K1 no longer holds.** `PLN-001`/P1 and P2 both shipped, and a
> clean clone now goes from `git clone` to a passing suite and a self-building database
> with one command (`OBS-003/K6`, `OBS-007/K6`). R2's blocker is gone: **CI is now
> implementable**, which makes P3 the next thing rather than the impossible thing.
> R4's deployment stories are likewise unblocked. K2's prediction held — relieving the
> constraint took two days and surfaced five latent defects on the way (`OBS-003/R1,R2`,
> `OBS-007/R2`), each of which had been invisible precisely because nothing ever built
> the project from scratch.

- **K1 · The binding constraint: the repository cannot produce a running Kiku on a clean
  machine.** Schema (E1) and environment (E2) are both underspecified.
- **K2 · It is cheap to relieve (R7) and it gates the two most valuable things available**
  — CI, and therefore the entire quality apparatus (R3); and deployment, and therefore the
  entire product roadmap beyond this laptop (R4).
- **K3 · Everything else is "important, and second"** — including the frontend work the
  author asked about (R6).
- **K4 · A single test is the durable fix, not the migration repair.** A CI job that builds
  a fresh database from base and asserts the ORM metadata matches converts K1 from a state
  into an invariant. Without that test, the repair regresses the next time a table is added
  via `create_all`.
