# Human Section
Critical: any text/subsection here cannot be modified by AI.

## High-Level Objective (HLO)
The **final piece** of the set-role arc (after spec 027 tags + spec 028 opener/closer builder wiring):
wire the **break** role into the auto-builder so break-tagged tracks land at the right narrative
moment — completing "roles shape generated sets."

**The DJ's definition drives everything here:** *a break is the culmination of a "chapter" in the
story — after a high, the set releases, then starts building again.* So a break belongs at a **chapter
boundary**: an **interior valley** in the energy arc that (1) follows a peak/high (the release) and
(2) is followed by another build (the next chapter). It is **not** the final cooldown/outro — that
descends to the end and never rebuilds, so it is the *ending*, not a break.

## Mid-Level Objectives (MLO)
- **BIAS** break-tagged tracks toward interior energy **valleys** (chapter boundaries), as a soft
  preference — reusing the spec 028 soft-bias machinery.
- **SURFACE the WHY**: when a break-tagged track lands in a dip, explain it ("Gave the room a breather
  with 'X' before building back up").
- **ADD** a multi-chapter "story" energy preset so break placement has a home out of the box (no
  built-in preset currently has an interior valley).
- **ENSURE** the bias is soft and non-restrictive — never forces a weak transition, never filters the
  pool; a library with no break tags builds identically.

## Details (DT)

### Scope — spec 029 (the final role piece)
**IN:**
1. **break → chapter-boundary dip** — the builder soft-biases break-tagged tracks when the slot being
   filled sits in an interior energy **valley**: a local-minimum segment of the energy profile (target
   lower than BOTH adjacent segments), **excluding the first and last segments**. Reuse `_ROLE_SPAN`
   (0.15) + `has_role` in the `build_set` scoring loop, gated on "current position is in a valley
   segment" (instead of the closer's "final stretch").
2. **break teaching note** — when a break-tagged track lands in a dip, append a plain-language note,
   derived in `analyze_set` from the analyzed energy curve (a break-tagged track at a **local minimum**
   of `arc.energy_curve`), consistent with the opener/closer derivation.
3. **NEW multi-chapter "story" preset** — e.g. `build:0.6 → peak:0.9 → release:0.4 → build:0.7 →
   peak:0.95 → close:0.4` added to `DEFAULT_ENERGY_PRESETS`. **RATIONALE:** none of the current
   built-in presets (warmup / peak-time / journey) has an interior valley, so break placement would be
   **dormant** by default. This preset gives break tags a home and embodies the "chapters in the story"
   arc. **This is a product decision — the user may veto or reshape it at review.**

**OUT:** nothing deferred — this completes the set-role feature family (027 tags → 028 opener/closer →
029 break).

### Critical design direction (carried from spec 028)
- **SOFT BIAS, not hard placement.** Break is a small bounded **bonus**, never a filter, never
  overrides a clearly better key/energy/BPM fit, never removes a non-tagged track from eligibility
  (non-restrictive). A no-break-tag library builds identically (regression guard).
- **Reuse existing hooks; DO NOT OVERCOMPLICATE.** No new subsystem — a valley detector over
  `energy_profile.segments` + the existing scoring-loop bonus pattern.
- **Honest semantics:** break is a *preference* at valley slots, not a guaranteed placement (the beam
  search still decides).

### Codebase anchors (verify in RESEARCH)
- **EnergyProfile / segments / `target_energy_at` / `DEFAULT_ENERGY_PRESETS`:**
  `src/kiku/setbuilder/constraints.py` (presets ~L104-107; `parse_energy_string` ~L49). Add the new
  preset here.
- **Bias injection:** `src/kiku/setbuilder/planner.py` `build_set` scoring loop — the closer nudge is
  the pattern to mirror (`if end_ramp > 0 and has_role(cand,"closer"): score += end_ramp * _ROLE_SPAN`,
  ~L294). `_ROLE_SPAN` + `has_role` already imported (spec 028). Add a valley detector over
  `energy_profile.segments` and a check whether the current `elapsed` (or `target_e`) sits in a valley
  segment; when so, `score += _ROLE_SPAN` (or a ramped fraction) for break-tagged candidates.
- **Teaching:** `src/kiku/analysis/set_analyzer.py` `analyze_set` — opener/closer notes are appended to
  `set_patterns` after `detect_set_patterns` (spec 028, ~L100); `arc.energy_curve` is computed by
  `_compute_arc`. Add a break note from a break-tagged track at a local-min position of
  `arc.energy_curve`.
- **Reuse:** `src/kiku/set_roles.py` (`has_role`, `track_roles`); `_ROLE_SPAN` (planner.py, spec 028).

### Constraints
- Soft + non-restrictive (never a filter, never overrides a clear better fit).
- Valley = interior local-minimum segment ONLY (never the first/last segment).
- Minimal change; reuse the spec 028 bonus pattern; no new subsystem.
- Kiku voice — warm, storytelling ("released the tension, then built back up").

### Testing
- **Unit:** the valley detector flags interior local-minimum segments and NOT the first/last (e.g. the
  new "story" preset's `release` segment is a valley; `journey`'s `cooldown` is NOT); a break-tagged
  candidate gets the bonus only when the current slot is in a valley; a no-break-tag build is identical
  (regression). Teaching: `analyze_set` appends the break note when a break-tagged track sits at an
  energy-curve local minimum, and not otherwise.
- **E2E / integration:** build a set with break-tagged tracks on the "story" preset → a break tends to
  land in the release valley; the "why" note appears; the default `journey` preset produces no break
  placement (no interior valley) — confirming honest, non-dormant-only-with-chapters behaviour.

## Behavior
You are a senior engineer completing the set-role family with the smallest correct change. Reuse the
spec 028 soft-bias + teaching patterns; add only a valley detector and the "story" preset. SOFT bias
only. Break is a preference at chapter-boundary valleys, never forced.

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
