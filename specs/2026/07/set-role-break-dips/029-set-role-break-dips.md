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

### Files
- `src/kiku/setbuilder/constraints.py` — `EnergyProfile.segment_index_at()` + `valley_segment_indices()`
  (after `target_energy_at`, ~L46); `"story"` in `DEFAULT_ENERGY_PRESETS` (L104-109).
- `src/kiku/setbuilder/planner.py` — `valley_idxs` before the beam loop (~L232); `in_valley` per beam
  (~L260); break bonus in the candidate loop (~L295).
- `src/kiku/analysis/set_analyzer.py` — break teaching note after the closer note (~L115).
- `frontend/src/lib/components/set/EnergyPresetPicker.svelte` — add the `story` card (~L33).
- `tests/test_set_role_builder.py` — valley/segment/preset/teaching + build tests.

### Tasks

#### Task 1 — constraints.py: valley helpers + "story" preset
Tools: editor. Two edits.

1a. `EnergyProfile` methods (after `target_energy_at`):
````diff
--- a/src/kiku/setbuilder/constraints.py
+++ b/src/kiku/setbuilder/constraints.py
@@
         # Past end — return last segment energy
         return self.segments[-1].target_energy if self.segments else 0.5
 
+    def segment_index_at(self, elapsed_min: float) -> int:
+        """Index of the segment covering elapsed_min (clamped to the last segment)."""
+        cumulative = 0.0
+        for i, seg in enumerate(self.segments):
+            cumulative += seg.duration_min
+            if elapsed_min <= cumulative:
+                return i
+        return len(self.segments) - 1 if self.segments else 0
+
+    def valley_segment_indices(self) -> set[int]:
+        """Interior local-minimum segments — chapter-boundary 'breather' valleys.
+
+        A segment qualifies when its target energy is lower than BOTH neighbours:
+        a release after a high, before the next build. The first and last segments
+        are never valleys, so a final cooldown/outro is excluded (spec 029).
+        """
+        segs = self.segments
+        return {
+            i
+            for i in range(1, len(segs) - 1)
+            if segs[i].target_energy < segs[i - 1].target_energy
+            and segs[i].target_energy < segs[i + 1].target_energy
+        }
 
 
 def parse_energy_string(s: str) -> EnergyProfile:
````
1b. Register the preset:
````diff
--- a/src/kiku/setbuilder/constraints.py
+++ b/src/kiku/setbuilder/constraints.py
@@ DEFAULT_ENERGY_PRESETS: dict[str, str] = {
     "afterhours": "deep:30:0.3,hypno:40:0.4,drift:30:0.25",
+    # Multi-chapter arc (spec 029): a release VALLEY between two builds gives
+    # break-tagged tracks a home — the culmination of a chapter, then a rebuild.
+    "story": "build:20:0.6,peak:30:0.9,release:12:0.4,rebuild:20:0.7,summit:30:0.95,close:12:0.4",
 }
````
Verification: Task 6 units.

#### Task 2 — planner.py: valley set + in_valley + break bonus
Tools: editor. Three edits in `build_set`.

2a. Compute the valley set once, before the beam loop:
````diff
--- a/src/kiku/setbuilder/planner.py
+++ b/src/kiku/setbuilder/planner.py
@@
     candidate_set = {t.id: t for t in candidates}
 
+    # Chapter-boundary energy valleys — break-tagged tracks are softly favoured here
+    # (spec 029). Empty for the default single-peak arcs, so break is a no-op there.
+    valley_idxs = energy_profile.valley_segment_indices()
+
     iteration = 0
````
2b. Per-beam: is this slot in a valley?
````diff
--- a/src/kiku/setbuilder/planner.py
+++ b/src/kiku/setbuilder/planner.py
@@
             end_ramp = _end_pull(progress)
             pull = end_ramp if end_track else 0.0
 
+            # Is this slot inside a chapter-boundary valley? (break-role bias below)
+            in_valley = energy_profile.segment_index_at(elapsed) in valley_idxs
+
             # Score all candidates not yet in sequence
````
2c. Break bonus in the candidate loop (after the closer nudge):
````diff
--- a/src/kiku/setbuilder/planner.py
+++ b/src/kiku/setbuilder/planner.py
@@
                 if end_ramp > 0 and has_role(cand, "closer"):
                     score += end_ramp * _ROLE_SPAN
 
+                # Break role: favour break-tagged tracks in a chapter-boundary energy
+                # valley — the release after a high, before the next build (spec 029).
+                # Flat (not ramped): a valley is a discrete region. Soft, never forced.
+                if in_valley and has_role(cand, "break"):
+                    score += _ROLE_SPAN
+
                 scored_candidates.append((cand, score))
````
Verification: Task 6.

#### Task 3 — set_analyzer.py: break teaching note
Tools: editor. After the closer note:
````diff
--- a/src/kiku/analysis/set_analyzer.py
+++ b/src/kiku/analysis/set_analyzer.py
@@
     if has_role(tracks[-1], "closer"):
         closer_name = tracks[-1].title or "the last track"
         set_patterns.append(
             f"Closed on “{closer_name}” — one of your go-to closers."
         )
 
+    # Break role: a break-tagged track sitting in an energy VALLEY (a local minimum
+    # of the curve) is the release between chapters — say so (spec 029). First only.
+    curve = arc.energy_curve
+    for i in range(1, len(tracks) - 1):
+        if has_role(tracks[i], "break") and curve[i] < curve[i - 1] and curve[i] < curve[i + 1]:
+            break_name = tracks[i].title or "a track"
+            set_patterns.append(
+                f"Gave the room a breather with “{break_name}” before building back up."
+            )
+            break
+
     # 5. Overall score
````
Verification: Task 6 teaching test.

#### Task 4 — EnergyPresetPicker.svelte: add the "story" card
Tools: editor. Add a fifth preset (its sparkline shows the double-peak + release valley):
````diff
--- a/frontend/src/lib/components/set/EnergyPresetPicker.svelte
+++ b/frontend/src/lib/components/set/EnergyPresetPicker.svelte
@@
 		{
 			name: 'afterhours',
 			label: 'After Hours',
 			description: 'Late night vibes',
 			points: [0, 0.5, 0.25, 0.5, 0.5, 0.45, 0.75, 0.4, 1, 0.3],
 		},
+		{
+			name: 'story',
+			label: 'Story',
+			description: 'Two chapters, one breather',
+			points: [0, 0.6, 0.2, 0.9, 0.4, 0.4, 0.6, 0.7, 0.8, 0.95, 1, 0.4],
+		},
 	];
````
Verification: svelte-check; the card renders with a W-shaped sparkline and is selectable.

#### Task 5 — (no other frontend change) — the preset flows via `energy_preset` already.

#### Task 6 — tests/test_set_role_builder.py: extend
Tools: editor. Append (reuses the existing `session` fixture + `_t` helper):
````python
from kiku.setbuilder.constraints import (
    DEFAULT_ENERGY_PRESETS,
    parse_energy_string,
    resolve_energy,
)


def test_valley_segment_indices():
    assert resolve_energy("story").valley_segment_indices() == {2}   # 'release'
    assert resolve_energy("journey").valley_segment_indices() == set()  # cooldown is last
    w = parse_energy_string("a:10:0.9,b:10:0.3,c:10:0.9,d:10:0.4,e:10:0.9")
    assert w.valley_segment_indices() == {1, 3}                      # two valleys
    ends = parse_energy_string("a:10:0.1,b:10:0.9,c:10:0.1")
    assert ends.valley_segment_indices() == set()                   # first/last never


def test_segment_index_at():
    p = parse_energy_string("a:10:0.5,b:10:0.6,c:10:0.7")
    assert [p.segment_index_at(x) for x in (5, 10, 15, 25, 999)] == [0, 0, 1, 2, 2]


def test_story_preset_registered():
    assert "story" in DEFAULT_ENERGY_PRESETS
    assert resolve_energy("story").valley_segment_indices()          # has a breather


def test_break_teaching_note_at_energy_valley(session):
    from kiku.analysis.set_analyzer import analyze_set
    hi = _t(session, 1, "peak")                       # high
    br = _t(session, 2, "warmup", roles=["break"])    # low → curve valley + break tag
    hi2 = _t(session, 3, "peak")                      # high again
    st = Set(id=1, name="S", duration_min=30)
    session.add(st)
    session.flush()
    for pos, tr in enumerate([hi, br, hi2]):
        session.add(SetTrack(set_id=1, position=pos, track_id=tr.id))
    session.commit()
    assert any("breather" in p for p in analyze_set(session, 1).set_patterns)


def test_break_placed_in_valley_on_story(session):
    from kiku.setbuilder.planner import build_set
    for i in range(1, 8):
        _t(session, i, "peak", bpm=126.0, key="8A")           # high-energy pool
    _t(session, 99, "warmup", roles=["break"], bpm=126.0, key="8A")  # the breather
    session.commit()
    s = build_set(session, duration_min=40, energy_profile=resolve_energy("story"), set_name="s")
    ids = [st.track_id for st in sorted(s.tracks, key=lambda x: x.position)]
    assert 99 in ids and 0 < ids.index(99) < len(ids) - 1   # placed, interior
````
Note: `test_break_placed_in_valley_on_story` is the one most likely to need value tuning if the beam
ends early — keep the pool all-`peak` except the single `warmup` break track so the release valley
strongly prefers it. Verification: Task 7.

#### Task 7 — Lint + tests + type-check
Tools: shell.
- `source .venv/bin/activate && python -m pytest tests/test_set_role_builder.py -q`
- `source .venv/bin/activate && python -m pytest tests/ -q`   (full suite — regression guard)
- `cd frontend && npx svelte-check --tsconfig ./tsconfig.json`
Expectation: all green; svelte-check 0 errors.

#### Task 8 — E2E (manual)
Tools: browser. Build a set on the **Story** preset with a couple of break-tagged mid/low-energy
tracks → a break tends to land in the release valley; the set view shows "Gave the room a breather…".
Build on **Journey** → no break placement (no interior valley), no breather note. Confirm a no-break
library builds normally.

#### Task 9 — Commit
Tools: git.
- `git add -- src/kiku/setbuilder/constraints.py src/kiku/setbuilder/planner.py src/kiku/analysis/set_analyzer.py frontend/src/lib/components/set/EnergyPresetPicker.svelte tests/test_set_role_builder.py`
- `BRANCH=$(git rev-parse --abbrev-ref HEAD); [ "$BRANCH" != "main" ] || { echo 'ERROR: on main' >&2; exit 2; }`
- `git commit -m "spec(029): IMPLEMENT - set-role-break-dips"`

### Validate
- **MLO break→valley** (L… MLO): Task 2 — flat `_ROLE_SPAN` when the slot is in an interior valley.
  Satisfied.
- **MLO Show the Why** (L… MLO): Task 3 — breather note derived from an energy-curve local min.
  Satisfied.
- **MLO "story" preset** (L… MLO): Tasks 1b, 4. Satisfied (flagged for user veto in Details).
- **DT soft, non-restrictive** (L… Details): bounded +0.15 bonus, no filter, short-circuit behind
  `in_valley and has_role`. Satisfied.
- **DT no-regression when no break tags / no valley** (L… Testing): full suite + `journey` has no
  valley + bonus 0 for untagged. Satisfied.
- **DT valley excludes first/last** (L… Details): `range(1, len-2)`; `test_valley_segment_indices`
  proves the outro is never a valley. Satisfied.
- **DT reuse hooks, no new subsystem** (L… Details): two `EnergyProfile` methods + the existing bonus
  pattern; no `transition_score`/`suggest_next`/`SetBuildRequest` change. Satisfied.

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
