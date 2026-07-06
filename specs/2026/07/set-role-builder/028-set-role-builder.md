# Human Section
Critical: any text/subsection here cannot be modified by AI.

## High-Level Objective (HLO)
Wire the **set-role tags** (opener / closer / break) shipped in spec 027 into the **auto-builder**, so
a DJ's curation actually shapes **generated** sets — not just manual tagging + filtering. When you've
told Kiku which tracks are great openers or closers, the builder should *listen*: favour an opener for
the first slot and a closer for the last — and **tell you why it did**.

This is the v2 follow-up to spec 027 (merged to main via PR #37). It is deliberately **phased**: this
spec covers opener→first, closer→last, and multi-role filtering; break→dips is the next spec (029).

## Mid-Level Objectives (MLO)
- **BIAS** seed selection toward **opener**-tagged tracks (opener → first slot), as a soft preference.
- **BIAS** the final/trailing slot toward **closer**-tagged tracks (closer → last slot), as a soft
  preference.
- **UPGRADE** the library role filter from single-active to **multi-role OR-filtering** (accept several
  active roles at once, OR-matched) — backend list param + frontend multi-active chip-toggles.
- **SURFACE the WHY**: whenever a role influenced a build choice, the set explains it in plain,
  teaching language ("Opened with X — you marked it a great opener"). MANDATORY.
- **ENSURE** the bias never forces a musically weak transition and never removes a non-tagged track
  from eligibility (soft, non-restrictive — carried over from spec 027).

## Details (DT)

### Scope — spec 028 (phased, confirmed with user)
**IN:**
1. **opener → first slot** — soft-bias seed selection toward opener-tagged tracks.
2. **closer → last slot** — soft-bias the final/trailing slot toward closer-tagged tracks.
3. **multi-role OR-filter** — the library filter accepts multiple active roles, OR-matched (upgrades
   the v1 single-active scalar filter).
4. **"Show the Why" teaching** — plain-language explanation wherever a role shaped a build decision.

**OUT (deferred to a FAST FOLLOW-UP, spec 029 — document as the next step, do NOT build here):**
- **break → energy dips**: favour break-tagged tracks when filling a slot whose target energy is a
  local low point in the curve. Break is the least-defined and riskiest piece.

### Critical design direction (confirmed with user)
- **SOFT BIAS, not hard placement.** Roles are a **preference/bonus, never a rule.** An opener-tagged
  track is *favoured* for the first slot, but a clearly better-scoring untagged track can still win.
  This preserves the Kiku anti-principle **"Not a DJ autopilot"** and Principle 6 **"Every Track
  Deserves a Chance"**: a role must NEVER force a musically weak transition just to honour a tag, and
  must NEVER remove a non-tagged track from eligibility (non-restrictive, carried from spec 027).
- The bias is a **small additive bonus** in the existing scoring/selection path, **not a filter.**
  Prefer folding a position-conditional role-fit bonus into the current selection (e.g. the seed/tail
  hook or `track_quality()`) over new machinery. **DO NOT OVERCOMPLICATE.**
- The bonus magnitude should be tunable/defensible and small enough that key/energy/BPM fit still
  dominate — a role breaks ties and nudges close calls; it does not steamroll the score.

### Codebase anchors (from spec 027 RESEARCH — verify in this spec's RESEARCH)
- **Seed (opener):** `src/kiku/setbuilder/planner.py` `_pick_seed()` (~L99-122) — currently picks the
  DJ-specified seed or the track closest to the first segment's target energy. Inject an opener
  preference here.
- **Tail (closer):** no dedicated closer-picker today; the last slot emerges from the beam search +
  `src/kiku/setbuilder/filler.py` (~L93-101) targeting `energy_profile.target_energy_at(last_elapsed)`.
  Add a closer-preference hook at the final position.
- **Scoring:** `src/kiku/setbuilder/scoring.py` `track_quality()` (~L318-371) is the curation-signal
  dimension; `score_candidate()` / `score_transitions()` (~L497+) already accept context params
  (e.g. `target_vibe`, `vibe_strength`) — a role/position context param follows that pattern.
- **Teaching:** `src/kiku/analysis/set_analyzer.py` `analyze_set()` + its teaching-moments pattern is
  where the "why" should surface.
- **Multi-role filter:** backend `search_tracks` `set_role` scalar (spec 027) → accept a list
  (OR-match); route `set_role` Query param → list; frontend `SearchFilters.svelte` role chip-toggles
  (built single-active in spec 027) → make multi-active; `SearchParams.set_role` → `set_roles` /
  repeatable param.
- **Reuse from spec 027:** `set_roles` column, `SET_ROLES`, `normalize_roles` (`src/kiku/set_roles.py`).

### Constraints
- Non-restrictive: role bias never filters a track out of any candidate pool.
- Soft: a role bonus never overrides a clearly better key/energy/BPM fit.
- Minimal change; reuse existing scoring/selection hooks; no new subsystems.
- All user-facing copy in Kiku voice (warm, teaching; set = "set", DJ = "you").

### Testing
- **Unit:** seed selection prefers an opener when scores are close but does NOT when a non-opener is
  clearly better; tail selection prefers a closer under the same rule; role bonus is additive and
  bounded; a set with no role-tagged tracks builds identically to pre-028 (no regression). Multi-role
  filter OR-matches (a track with ANY selected role is returned) and empty selection = no filter.
- **E2E / integration:** build a set from a library with opener/closer-tagged tracks → the opener
  leads and a closer trails when musically reasonable; the "why" note appears; multiple filter
  toggles return the union.

## Behavior
You are a senior engineer implementing the smallest correct change that makes curation shape
generation. Reuse the established scoring/selection + teaching-moment patterns; do not invent new
subsystems. SOFT bias only. Do not touch break→dips — record it as the documented spec 029 follow-up.

# AI Section
Critical: AI can ONLY modify this section.

## Research
<!-- Filled by /spec RESEARCH -->

## Plan
<!-- Filled by /spec PLAN -->

## Plan Review
<!-- Filled if required to validate plan -->

## Implement
<!-- Filled by /spec IMPLEMENT -->

## Test Evidence & Outputs
<!-- Filled by explicit testing after /spec IMPLEMENT -->

## Updated Doc
<!-- Filled by explicit documentation udpates after /spec IMPLEMENT -->

## Post-Implement Review
<!-- Filled by /spec REVIEW -->
