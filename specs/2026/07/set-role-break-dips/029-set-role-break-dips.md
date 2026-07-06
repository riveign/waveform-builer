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

Verified against current source. Everything reuses the spec 028 machinery; the only genuinely new
logic is a small valley detector.

### 1. Energy profile shape (valley detection input)
- **`src/kiku/setbuilder/constraints.py`:** `EnergySegment(name, duration_min, target_energy)` (L9-15);
  `EnergyProfile.segments: list[EnergySegment]` (L18-22); `target_energy_at(elapsed_min)` interpolates
  between segment boundaries (L28-46).
- **Valley = interior local-minimum segment.** Segment `i` is a valley iff `1 <= i <= len-2` AND
  `segs[i].target_energy < segs[i-1].target_energy` AND `segs[i].target_energy < segs[i+1].target_energy`.
  First/last excluded by construction, so the final cooldown/outro is never a valley (matches the DJ's
  "not the ending" rule).
- **Confirmed: NO built-in preset has an interior valley** (`DEFAULT_ENERGY_PRESETS`, L104-109):
  `warmup` (0.3→0.5→0.6, rising), `peak-time` (0.7→0.9→0.8, last drops), `journey` (0.3→0.6→0.9→0.4,
  last drops = the *ending*), `afterhours` (0.3→0.4→0.25, last drops). So without the new "story"
  preset, break placement is dormant — the preset is justified.

### 2. Bias injection (planner)
- **`build_set` scoring loop** (`planner.py`): the per-beam loop exposes `elapsed` (L226) and computes
  `target_e = energy_profile.target_energy_at(elapsed)` (L233); the closer nudge is at ~L294. `_ROLE_SPAN`
  (0.15) + `has_role` are already imported (spec 028).
- **Plan:** add two tiny helpers (planner-local or constraints.py):
  `_valley_segment_indices(profile) -> set[int]` and `_segment_index_at(profile, elapsed) -> int`.
  Compute `valley_idxs = _valley_segment_indices(energy_profile)` ONCE before the beam loop; per beam
  compute `in_valley = _segment_index_at(energy_profile, elapsed) in valley_idxs`; then in the candidate
  loop, mirroring the closer nudge:
  `if in_valley and has_role(cand, "break"): score += _ROLE_SPAN`.
- **Bonus magnitude — flat `_ROLE_SPAN` (0.15), NOT ramped.** The closer uses `end_ramp * _ROLE_SPAN`
  (≈0.0375 max) because proximity-to-end is continuous; a valley is a discrete region, so a flat 0.15
  is the right, effective-yet-soft nudge (still below vibe 0.3 / artist 0.2 spans and far below the
  base harmonic/energy weights — it breaks close calls, never steamrolls). Document this intentional
  difference.
- Short-circuit `in_valley and has_role(...)` means `has_role` (a JSON parse) runs only inside a valley
  region — negligible overhead, and zero when no valleys exist (journey/default).

### 3. Teaching (analyze_set)
- **`arc.energy_curve` is 1:1 with track positions** (`_compute_arc`, L295-298: one entry per track,
  `energy_curve[i]` = energy of `tracks[i]`).
- **Plan:** after the opener/closer notes (spec 028, ~L100), scan interior positions for a break-tagged
  track at a local minimum: for `1 <= i <= len-2`, if `has_role(tracks[i], "break")` AND
  `energy_curve[i] < energy_curve[i-1]` AND `energy_curve[i] < energy_curve[i+1]` → append
  *"Gave the room a breather with '{tracks[i].title}' before building back up."* (guard null title like
  the spec 028 review fix). Cap at the first such note to avoid spam. No build-time provenance — derived
  from the final set + roles + curve, exactly like opener/closer.

### 4. New "story" preset
- Add to `DEFAULT_ENERGY_PRESETS` (constraints.py L104-109), e.g.
  `"story": "build:20:0.6,peak:30:0.9,release:12:0.4,rebuild:20:0.7,summit:30:0.95,close:12:0.4"`
  (~124 min). `release` (0.4) is an interior valley (0.9 before, 0.7 after) → break's home; `close`
  (0.4) is last → correctly NOT a valley. Exposed automatically via `get_energy_presets()` +
  `resolve_energy()`; the frontend build UI lists presets from the API (verify the preset dropdown
  picks it up — likely a `GET` of energy presets).

### 5. Reuse / no-change confirmations
- Reuse `set_roles.has_role`, planner `_ROLE_SPAN`. No `transition_score`/`track_quality`/`suggest_next`
  change; no `SetBuildRequest` field (break bias is automatic, reads roles off tracks).
- **Regression:** no break tags → bonus 0; the valley helpers don't affect non-break scoring; the
  `journey`/default presets have no valley → no break placement → identical builds.

### 6. Tests
- **Unit** (extend `tests/test_set_role_builder.py`): `_valley_segment_indices` flags the "story"
  `release` segment and NOT `journey`'s `cooldown`, and excludes first/last; `_segment_index_at` maps
  elapsed→segment; a break-tagged candidate gets +`_ROLE_SPAN` only when the slot is in a valley;
  no-break-tag build unchanged. Teaching: `analyze_set` appends the breather note for a break-tagged
  local-min track, not otherwise.
- **E2E:** build on "story" with break-tagged tracks → a break tends to land in the release valley +
  note appears; build on "journey" → no break placement (no valley).

### Strategy

**Build order (each independently verifiable):**
1. **Valley helpers** — `_valley_segment_indices` + `_segment_index_at` (planner-local). Unit-test on
   the story vs journey profiles (valley present/absent; first/last excluded).
2. **"story" preset** — add to `DEFAULT_ENERGY_PRESETS`; assert it parses and its `release` is a valley.
3. **Break bias** — compute `valley_idxs` once + `in_valley` per beam + the candidate bonus in the
   scoring loop. Unit: bonus applied only in a valley; no-break build identical.
4. **Teaching** — break-at-local-min note in `analyze_set` (null-title-guarded, first-only). Unit:
   present when a tagged break sits in a curve valley.

**Testing strategy:** extend `tests/test_set_role_builder.py` (valley detector + break bonus + teaching
units) with in-memory sessions; a build-level regression asserting a no-break-tag "story" build equals
the pre-029 sequence. E2E on story vs journey. Frontend: only if the preset dropdown needs a label —
otherwise no FE change.

**Voice/principle checks:** "The Arc Over the Moment" (P3 — break serves chapter structure); teaching in
Kiku storytelling voice ("released the tension, then built back up"); soft/non-restrictive (P6).

**Explicit non-goals:** no ramped break bonus (flat, by design), no `transition_score`/`suggest_next`/
`SetBuildRequest` change, no hard placement.

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
