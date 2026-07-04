# Human Section
Critical: any text/subsection here cannot be modified by AI.

## High-Level Objective (HLO)
Redesign the track rows and transition strips in Kiku's set-builder view so the set reads as one continuous, legible journey — where each transition explains the move it makes and the run-level story is told once instead of repeating as wallpaper. Today every transition strip renders the same cryptic line (`BUILD 0.62 / 0.89 CTX EXCELLENT — Both tracks in Cm — perfect harmonic match. Your ear picked this.`), which fails four product principles: two opaque scores with no hint of which drives the verdict (#5 Opinions You Can See Through); an identical teaching sentence repeated on every row of a key-locked run so it teaches nothing (#1 Show the Why); a decorative red energy bar with no scale or target (#5 again); and inverted space that leaves a dead gap in the middle while the connective story — the key move, the energy direction — is crammed or missing (#3 The Arc Over the Moment). This spec turns an already-approved interactive mockup into an implementation plan. Its organizing insight: the pairwise builder score (BUILD) and the arc-aware set-analysis score (CTX) often diverge — tracks that are modest as a pair (~0.6–0.7) can be excellent in the arc (~0.9) because the run is key-locked — and that divergence IS the lesson. Surface it; don't hide it.

Approved mockup (the reference for copy and layout): https://claude.ai/code/artifact/17b5bc19-6899-4dc6-b793-bc46bae91176

## Mid-Level Objectives (MLO)
- REDESIGN `frontend/src/lib/components/set/TransitionIndicator.svelte` to replace the cryptic `BUILD x / y CTX` line with plain-language two-score copy — "On their own {build} · In your arc {ctx}" — a verdict pill driven by the CTX score (Excellent ≥0.8 / Good ≥0.6 / Fair ≥0.4 / else Poor, reusing the existing `scoreLabel()`/`scoreColor()` thresholds and `--score-*` tokens), and an expandable full 5-dimension weighted breakdown (Harmonic 25%, Energy fit 20%, BPM 20%, Genre 15%, Quality 20%) lazily fetched via the existing `getTransition(setId, transitionIndex)` → `TransitionScoreBreakdown`.
- ADD compact per-transition mechanics to the strip — a harmonic-relationship word (hold / lift / switch), a BPM delta, and an energy direction (↑ / → / ↓) — replacing the repeated teaching sentence. Show the written teaching NOTE ONLY when noteworthy: gated on a key/mode change OR a significant build-vs-ctx divergence OR an energy inflection.
- ADD a small Camelot-relationship helper (near `frontend/src/lib/utils/camelot.ts`) that maps two keys to hold / lift / switch — same key = hold; ±1 on the wheel or relative major/minor = lift/switch; else clash — reusing `toCamelot()` and the `CAMELOT_COLORS` wheel.
- ADD a run-level insight banner: when consecutive tracks share a key (a key-locked run), show ONE insight ("The story here is energy, not key") instead of repeating the same teaching sentence per transition.
- REDESIGN the energy bar in `frontend/src/lib/components/set/SetTrackCard.svelte` to show fit-to-arc, not just loudness — the in-palette energy ramp (navy → lilac → magenta per CERCETA `--energy-low/mid/high`) with a target tick (the `energy-target-marker` that already exists) — and thread a faint "spine" down the row gutter (a gradient of the energy ramp) so the set reads as one continuous flow.
- ADD a compact card grid view plus a list/grid toggle: a `SegmentedControl` (list default) in `SetTimeline.svelte`/`SetView.svelte` switches between the existing row list and a card grid for scanning the whole set's key/energy field at a glance. Each grid card shows position (a badge on the LEFT of the header — NOT absolute top-right, which collided with the score), incoming-transition color as a top stripe, a "from {key} · {relation}" caption + ctx score, title/artist, Camelot-colored key, BPM, a genre Chip, and an energy mini-bar with target tick.
- ENSURE all user-facing copy follows BRANDING.md (warm DJ-friend, "set" not "playlist", "flow" not "sequence", teach the why); the mockup copy ("The story here is energy, not key", "On their own · In your arc") is the approved reference.
- ENSURE the frontend type-check passes: `cd frontend && npx svelte-check --tsconfig ./tsconfig.json`.

## Details (DT)

### The problem, and why it fits the mission
The set view is where a DJ should *see* their flow and learn from it. Instead, the transition strips are noise: two unlabeled numbers, a verdict word, and a teaching sentence that repeats verbatim down a key-locked run. That is the opposite of Kiku's job. The redesign is a direct answer to four principles — #1 (Show the Why: teach, don't wallpaper), #3 (The Arc Over the Moment: give the connective story the space, not the dead gap), #5 (Opinions You Can See Through: name which score drives the verdict and let the DJ open the math), and voice (BRANDING.md: warm, plain, no cryptic labels). This is a UI/teaching redesign, not a scoring-engine change — but it may need a small server-side adjustment so the analysis stops emitting repetitive sentences (see the backend question below).

### The organizing insight — BUILD vs CTX divergence IS the lesson
- **BUILD** = the pairwise builder score (how well two adjacent tracks mix on their own).
- **CTX** = the arc-aware set-analysis score (how well the track serves the whole flow at that point).
They diverge often and meaningfully: a run of 7 tracks all in Cm can be modest pair-by-pair (~0.6–0.7) yet excellent in context (~0.9) because the key-lock carries the arc. The old UI hid this behind `BUILD 0.62 / 0.89 CTX`. The redesign makes the divergence readable ("On their own {build} · In your arc {ctx}") and treats a significant gap between the two as one of the triggers that earns a written teaching note.

### Approved design (what to implement)
1. **Run-level insight banner** — when a run shares a key, show ONE insight ("The story here is energy, not key") instead of repeating the same teaching sentence per transition.
2. **Plain-language two-score display** — replace `BUILD x / y CTX` with "On their own {build} · In your arc {ctx}", expandable to the full 5-dimension weighted breakdown (Harmonic 25%, Energy fit 20%, BPM 20%, Genre 15%, Quality 20%). The verdict pill (Excellent / Good / Fair / Poor) is driven by the CTX score.
3. **Live transition mechanics** — replace the repeated sentence with compact per-transition mechanics: the harmonic-relationship word (hold / lift / switch), the BPM delta, and the energy direction (↑ / → / ↓). The written teaching NOTE appears ONLY when noteworthy — gated on a key/mode change OR a significant build-vs-ctx divergence OR an energy inflection.
4. **Energy bar with a target tick** on the in-palette energy ramp (navy → lilac → magenta per CERCETA tokens), showing fit-to-arc, not just loudness.
5. **A faint "spine"** threading the row gutter (a gradient of the energy ramp) — the set as one continuous journey.
6. **Grid view + list/grid toggle** — a compact card grid for scanning the whole set's key/energy field at a glance. Each card shows position (a badge on the LEFT of the header — NOT absolute top-right, which collided with the score), incoming-transition color as a top stripe, "from {key} · {relation}" caption + ctx score, title/artist, Camelot-colored key, BPM, genre, and an energy mini-bar with target tick. Toggle via a `SegmentedControl` (list default).

### Components in scope (all under `frontend/src/lib/components/set/`)
- `SetTrackCard.svelte` — the track row: position, play button, title + genre `Chip`, artist, key-badge via `formatKey`/`getCamelotColor`, BPM, and the energy bar via `getTrackEnergyNumeric`/`energyColor` (the `energy-target-marker` already exists). Redesign the energy bar (target tick, palette ramp) and add the row-gutter spine.
- `TransitionIndicator.svelte` — the between-rows strip: currently renders `builderScore` ("build"), `analysisScore` ("ctx"), the `scoreLabel()` verdict thresholds (≥0.8 Excellent, ≥0.6 Good, ≥0.4 Fair, else Poor), `scoreColor()` → `--score-excellent/good/fair/poor`, the `teachingMoment` text, and lazily fetches the breakdown via `getTransition(setId, transitionIndex)` → `TransitionScoreBreakdown`. This is the largest change: two-score copy, verdict pill, expandable breakdown, mechanics row, gated note.
- `SetTimeline.svelte` — the row container: owns the drag handle + DnD reorder, places `SetTrackCard` + `TransitionIndicator`, and builds a `Map<position, {score, teaching}>` from `analysis.transitions`. Host the list/grid toggle and render the grid view.
- `SetView.svelte` — the parent: renders `SetTimeline` when a set is selected (`getSetWaveforms` + `getSetAnalysis`/`analyzeSet`). (It also renders `SetGrid`, the grid of *sets*, when none is selected — that is unrelated and out of scope.)

### Primitives, state, and helpers to reuse
- `SegmentedControl.svelte` (`frontend/src/lib/components/primitives/`) already exists — reuse for the list/grid toggle.
- `Chip.svelte` with `variant="genre"` — reuse for the genre chip.
- A DEAD/UNUSED view-mode enum exists to repurpose: `frontend/src/lib/stores/ui.svelte.ts` has `export type TimelineViewMode = 'linear' | 'staircase'` with `timelineViewMode` state + getter/setter, currently read by NOTHING. Either repurpose it to `'list' | 'grid'` or add fresh view-mode state — this is an open question (below).
- Camelot: `frontend/src/lib/utils/camelot.ts` — `formatKey()`, `getCamelotColor()` (Cm = 5A = `#cddc39`, full `CAMELOT_COLORS` wheel), `toCamelot()`. The hold / lift / switch relationship needs a small new helper (same code = hold; ±1 on the wheel or relative major/minor = lift/switch; else clash).

### Types (`frontend/src/lib/types/index.ts`)
- `SetTrack` — position, track_id, title, artist, bpm, key, genre, energy, energy_value (0..1), energy_source, energy_conflict, ...
- `TransitionScoreBreakdown` — harmonic, energy_fit, bpm_compat, genre_coherence, track_quality, total, discovery_label?, set_appearances?
- `TransitionAnalysis` — position, track_a_id, track_b_id, scores, teaching_moment, suggestion.
- `SetAnalysis` — transitions[], overall_score, arc, set_patterns.

### Design tokens (CERCETA)
`frontend/src/lib/styles/tokens.semantic.css` + `tokens.primitives.css`. Energy ramp: `--energy-low` (navy `#5FABE2`), `--energy-mid` (lilac `#BA94BA`), `--energy-high` (magenta `#F969A3`). Score ramp: `--score-excellent/good/fair/poor`. Accent teal `#008A84`. Stay in-palette — the energy bar and spine use the energy ramp, the verdict pill uses the score ramp.

### Backend question RESEARCH must resolve
The run-level insight (detecting a key-locked run) and the "noteworthy" gating for teaching notes may need backend support in `analyze_set()` (`src/kiku/analysis/set_analyzer.py`) if the frontend cannot derive them from existing analysis fields alone. Resolve: can the frontend derive run-grouping + noteworthiness purely from `analysis.transitions[]` + track keys/energy, OR does `teaching_moment` generation need to change server-side to stop emitting the repetitive sentence in the first place? Prefer the smaller change; if the repetition is baked into the analysis output, fixing it at the source is cleaner than suppressing it in the view.

### Constraints
- Reuse what exists: `SegmentedControl`, `Chip`, the `energy-target-marker`, the `scoreLabel()`/`scoreColor()` thresholds and `--score-*` tokens, `getTransition()` for the lazy breakdown, and the `camelot.ts` helpers. Do NOT fork the scoring or the analysis fetch.
- Stay in-palette (CERCETA energy + score ramps); no new decorative colors.
- Voice per BRANDING.md: "set" not "playlist", "flow" not "sequence", warm mentor tone, never blame the DJ, never use the banned words (smart, powerful, seamless, magic, leverage, …). The teaching NOTE must earn its place — it appears only when it teaches something the mechanics row doesn't already show.
- The position badge lives on the LEFT of the grid-card header (the top-right collision with the score is the specific bug being designed out).
- DO NOT OVERCOMPLICATE: this is a redesign of two components plus a grid view and a toggle — not a new data model. EFFICIENCY: the breakdown stays lazily fetched; the grid renders from analysis already in hand.

### Scope
- IN: redesign of `SetTrackCard` + `TransitionIndicator`; the run-level insight banner; the grid view + list/grid toggle wired through `SetTimeline`/`SetView`; the Camelot relationship helper.
- OUT: `SetGrid` (the sets picker) is untouched. The directional-slot work (spec 024) is separate. No change to the 5-dimension scoring math itself.

### Open questions (for RESEARCH)
- Repurpose the dead `TimelineViewMode` enum vs. add fresh `'list' | 'grid'` state?
- Exact thresholds for a "noteworthy" teaching note — key/mode change (any?) + build-vs-ctx divergence (what delta?) + energy inflection (what delta?).
- Should repetitive `teaching_moment` sentences be suppressed frontend-side or fixed at the source in `set_analyzer.py`?
- Is the grid a strong enough second view, or does a future energy-arc timeline serve the "whole set at a glance" need better? (User flagged as a possible alternative.)

### Testing
- Component: `TransitionIndicator` renders two-score copy ("On their own … · In your arc …"), a verdict pill matching the CTX-driven threshold, and expands to the 5-dimension breakdown on demand (fetched via `getTransition`).
- Component: the mechanics row shows the correct hold / lift / switch word, BPM delta sign, and energy direction (↑ / → / ↓); the written note is present ONLY when a gate fires (key/mode change, build-vs-ctx divergence, or energy inflection) and absent on a flat key-locked run.
- Unit: the Camelot relationship helper — same key → hold, ±1 on the wheel → lift, relative major/minor → switch, wheel wrap (`12A`/`1A`), clash otherwise.
- Component: the run-level insight banner appears once for a key-locked run and not per transition.
- Component: `SetTrackCard` energy bar renders the target tick and the palette ramp; the grid card shows the position badge on the LEFT with no overlap with the score.
- Type-check: `cd frontend && npx svelte-check --tsconfig ./tsconfig.json` is clean.
- E2E (manual acceptance): open a set, confirm transitions read in plain language with a verdict pill and expandable math, a key-locked run shows one insight banner (not repeated sentences), and the list/grid toggle switches views with the grid scannable at a glance.

## Behavior
You are a senior frontend engineer on Kiku working in Svelte 5 runes + TypeScript. Honor the 7 product principles (BRANDING.md) — especially "Show the Why," "The Arc Over the Moment," and "Opinions You Can See Through." Implement the approved mockup, not a reinterpretation: match its copy ("The story here is energy, not key", "On their own · In your arc") and its layout decisions (position badge on the LEFT, verdict driven by CTX, note only when noteworthy). Reuse the existing primitives, tokens, camelot helpers, and the lazy `getTransition` breakdown rather than building parallel machinery. Treat the BUILD-vs-CTX divergence as the teaching payload — make it readable. Keep the change minimal and efficient: two components, a grid view, a toggle, and one small helper. Where the run-level insight or note-gating needs data the frontend can't derive, name the smallest server-side change in `set_analyzer.py` rather than papering over it in the view.

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
