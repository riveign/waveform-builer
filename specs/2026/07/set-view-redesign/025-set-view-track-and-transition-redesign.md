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

_All claims below verified by reading the actual code. Type-check gate: `cd frontend && npx svelte-check --tsconfig ./tsconfig.json`._

### Verified current state (props / markup / data paths)

**`TransitionIndicator.svelte`** (`frontend/src/lib/components/set/`, 205 lines)
- Props (l.5-17): `fromTrackId`, `toTrackId`, `score?`, `analysisScore?`, `teachingMoment?`, `setId`, `transitionIndex`, `active=false`, `onclick?`.
- `builderScore = breakdown?.total ?? score ?? null`; `displayScore = analysisScore ?? builderScore`; `hasDualScores` when both present (l.22-24).
- Owns `scoreColor()` (l.26-31: 0.8/0.6/0.4 → `--score-excellent/good/fair/poor`) and `scoreLabel()` (l.33-38: Excellent/Good/Fair/Poor) — the exact thresholds the spec reuses.
- Lazy breakdown via `getTransition(setId, transitionIndex)` → `detail.score_breakdown` (l.40-52), triggered by `$effect` only when `score == null` (l.59-63). Breakdown currently shown only as a hover `title` string (l.65-75, 83).
- Markup (l.78-109): renders `build x / y ctx` dual score (l.90-100), `scoreLabel(displayScore)` verdict word (l.101), and `teachingMoment` inline (l.102-104). This is the strip to rebuild.

**`SetTrackCard.svelte`** (326 lines)
- Props (l.12-28): `track: SetTrack`, `position`, `isSelected`, `isPlaying`, `energyTarget?: number`, `energyConflict?`, `onplay?`. **`energyTarget` prop CONFIRMED present.**
- Energy cell (l.131-147): `.energy-bar-bg` → `.energy-bar-fill` (width `energyNorm*100%`, `background: energyColorVal` from `energyColor()`), and **`.energy-target-marker` CONFIRMED** (l.137-142) rendered at `left: {energyTarget*100}%` when `energyTarget !== undefined`. Styles l.286-324 (`.energy-target-marker` is a 2×10px `--text-dim` tick).
- `energyNorm = getTrackEnergyNumeric(track.energy_value, track.energy)` (l.48). `energyFitIndicator()` (l.39-46) uses a ±0.12 deadband already.
- Position badge is `<span class="position">` (l.91), a flex sibling on the LEFT — the row already has no top-right collision (the collision the spec designs out is the GRID card's, which doesn't exist yet).

**`SetTimeline.svelte`** (555 lines) — the row container
- Props l.11-29: `tracks: SetWaveformTrack[]`, `setId`, `energyProfile?`, `activeTransitionIndex=-1`, `analysis?: SetAnalysis`, `onTransitionClick?`, `onTracksChanged?`, `onTrackPlay?`.
- `computeEnergyTargets(profile, count)` (l.51-75): regex `/(\w+)\(([0-9.]+)\)/g` parses a `warmup(0.3)->build(0.6)->…` string then **linearly interpolates a target per position** → `energyTargets` (l.77). Passed to card as `energyTarget={typeof energyTargets[i]==='number' ? energyTargets[i] : undefined}` (l.251). **Energy-target data path VERIFIED end-to-end.**
- `analysisMap = Map<position,{score,teaching}>` built from `analysis.transitions` keyed by `t.position` (l.80-87). `t.position` = transition index `i` (0-based; see `_score_transitions` `position=i` below), and the timeline reads `analysisMap.get(i)` (l.289-290) — indices line up.
- `TransitionIndicator` instantiated l.285-295 with `score`, `analysisScore=analysisMap.get(i)?.score`, `teachingMoment=analysisMap.get(i)?.teaching`. **The two adjacent tracks' keys/bpm/energy are all in `items[i]` / `items[i+1]`** (SetWaveformTrack) — available to thread as new props with no fetch.
- Left "energy sidebar" (l.183-208) is a separate mini energy column; the row-gutter "spine" the spec wants is new.

**`SetView.svelte`** (parent) — renders `SetTimeline` at l.597-606 with `energyProfile={setDetail?.energy_profile}` (l.600). Toolbar band `.timeline-controls` (l.385-515) is the natural home for a list/grid toggle. `analysis.set_patterns`/`arc` already rendered in the `.analysis-bar` (l.557-578).

**`SegmentedControl.svelte`** primitive API (verified): props `options: SegmentOption<T>[]` (`{value,label,shortcut?}`), `value: T`, `onchange:(value:T)=>void`, `ariaLabel: string`, `dense=false`. Roving-tablist keyboard model built in. Perfect for a `list`/`grid` toggle.

**CERCETA tokens** (verified): energy ramp `--energy-low`(navy-400) / `--energy-mid`(lilac-400) / `--energy-high`(magenta-400) in `tokens.semantic.css` l.47-49. Score ramp `--score-excellent`(teal-400) / `--score-good`(lilac-400) / `--score-fair`(magenta-400) / `--score-poor`(magenta-300) l.70-73. `--bpm-delta-warn` (l.78) exists for BPM emphasis. `energyColor()` in `utils/energy.ts` maps <0.4/<0.65/else → low/mid/high.

**Types** (`types/index.ts`): `SetTrack` l.110-128 (has `key`, `bpm`, `genre`, `energy`, `energy_value`, `energy_conflict`). `TransitionScoreBreakdown` l.150-159 (harmonic/energy_fit/bpm_compat/genre_coherence/track_quality/total + optional discovery_label/set_appearances). `TransitionAnalysis` l.176-183 (`position`, `track_a_id`, `track_b_id`, `scores`, `teaching_moment`, `suggestion`). `ArcAnalysis` l.185-194 (`energy_curve`, `energy_shape`, `key_journey`, `key_style`, `bpm_range`, `bpm_drift`, `bpm_style`, `genre_segments`). `SetAnalysis` l.196-205 (`transitions[]`, `arc`, `overall_score`, `set_patterns: string[]`).

### Resolved open questions

**Q1 — Teaching-moment repetition: frontend-suppress or fix at source? → FRONTEND (no `set_analyzer.py` change).**
- (a) **Identical sentences ARE emitted per transition — CONFIRMED.** `_score_transitions()` (set_analyzer.py l.254-260) calls `transition_teaching_moment()` per adjacent pair. For a same-key run where `total≥0.8` and `harmonic≥0.85`, `_explain_strength()` (teaching.py l.56-59, 67) returns the **literal constant** `f"Both tracks in {key_a} — perfect harmonic match. Your ear picked this."` — byte-identical for every transition in a Cm-locked run. This is exactly the wallpaper string in the HLO.
- (b) **The frontend can fully derive run-grouping and duplication** from data already in hand: each `analysis.transitions[i]` carries `teaching_moment` + `track_a_id/track_b_id`, and adjacent track keys live in `items[i].key`/`items[i+1].key`. Duplicate detection (`teaching[i] === teaching[i-1]`) and same-key runs (`toCamelot(items[i].key) === toCamelot(items[i+1].key)`) are both trivially computable client-side.
- **Recommendation:** do NOT touch `set_analyzer.py` or `teaching.py`. The redesign *replaces* the sentence with a mechanics row and only surfaces the note when a gate fires (Q4) — so the string is naturally dropped on flat runs, not "papered over". Keeping the raw string intact preserves `TransitionDetail.svelte`'s expanded view (which still renders `teaching_moment`) and the `analysis-bar` patterns. This holds the change to the frontend two-components + helper + grid, per the spec's "not a scoring-engine change". The run-banner copy ("The story here is energy, not key") is new view-authored copy, not a backend field. _(BRANDING.md note: the retained `teaching_moment` strings and the new banner copy already read in-voice — "your ear picked this", "set"/"flow" — no copy that violates the banned-word list is introduced.)_

**Q2 — View-mode state: repurpose dead enum vs. fresh state? → REPURPOSE.**
- `grep` confirms `TimelineViewMode`/`timelineViewMode` are referenced **only inside `ui.svelte.ts`** (l.4,10,26-27) — read by nothing. (MEMORY also lists dead view enums as a known removal target.)
- **Recommendation:** rename in place — `export type SetViewMode = 'list' | 'grid'`; `let setViewMode = $state<SetViewMode>('list')`; getter/setter `setViewMode`. Default `'list'` per spec.
- **Persistence:** No state in this store persists to localStorage (activeTab, selectedSetId, etc. are all in-memory session state). To match the store's convention, keep `setViewMode` in-memory — do NOT add localStorage. (If PLAN wants persistence later it would be a new pattern for this store; out of scope for a minimal change.)

**Q3 — Harmonic hold/lift/switch/clash helper: already partly present.**
- `camelot.ts` ALREADY has `parseCamelot()`, `harmonicRelationship()` (l.221-252 → `same/adjacent/modeSwitch/adjacentMode/twoAway/clash` with score+label+description) and `keyMoveLabel()` (l.194-209 → `same key/energy up/energy down/mood switch/distant keys`). Neither uses the mockup's exact `hold/lift/switch/clash` vocabulary.
- Backend `scores.harmonic` is a **number** (`harmonic_score()`), not a move-word, so the label must be classified frontend-side from the two Camelot codes.
- **Recommendation:** add one small pure helper in `camelot.ts` reusing `parseCamelot()` + the existing `wrap()` idiom (l.175/202): `harmonicMove(a,b): 'hold'|'lift'|'switch'|'clash'` — same number+letter → `hold`; same letter & `±1` on the wheel (with 12↔1 wrap) → `lift`; same number & different letter (relative major/minor) → `switch`; else → `clash`. ~12 lines, unit-testable. (Do not fork `harmonicRelationship`; the new helper is a thin vocabulary map for the strip/grid.)

**Q4 — "Noteworthy" gating (all frontend-derivable). Show the written note when ANY of:**
1. **Key/mode change:** `harmonicMove(a,b) !== 'hold'` (i.e. lift/switch/clash). On a flat key-locked run every move is `hold` → no note. Directly kills the repetition.
2. **Build-vs-CTX divergence:** `Math.abs(analysisScore - builderScore) >= 0.15`. Grounded in the `scoreLabel` bands (0.4/0.6/0.8 → 0.2-wide); 0.15 ≈ crossing most of a band. The spec's canonical case (pairwise ~0.6–0.7 vs ctx ~0.9) is a 0.2–0.3 gap, comfortably over the line. Guard for `null` scores.
3. **Energy inflection:** with `Δᵢ = energyNorm[i+1] − energyNorm[i]` on the 0..1 scale — direction arrow = `↑` if `Δ > 0.05`, `↓` if `Δ < −0.05`, else `→` (small deadband, consistent with the card's ±0.12 fit band); noteworthy when `|Δ| >= 0.15` OR the sign of `Δᵢ` differs from `Δᵢ₋₁` (an actual inflection point in the arc).
- When a gate fires, the note text = the retained `teaching_moment` (already appropriate for a noteworthy moment); otherwise show only the mechanics row.

**Q5 — Energy target tick: CONFIRMED and wired.** `SetTrackCard` already declares `energyTarget?` and renders `.energy-target-marker` (see above). Source: `SetTimeline.computeEnergyTargets(energyProfile, count)` interpolates per-slot targets from the profile string, and `energyProfile` flows from `SetView` → `setDetail.energy_profile`. The tick already reflects the real per-slot arc target; the redesign only restyles the bar to the `--energy-low→mid→high` ramp and keeps the existing tick. _(Note: `computeEnergyTargets` parses the `name(0.3)->…` string form; the marker renders today, so that string form is what currently flows — do NOT change the parser in this spec.)_

**Q6 — Run-level insight banner: frontend grouping (backend fields are set-level only).**
- Backend offers `arc.key_style` (set_analyzer l.338-348 → `home-key` when unique/total ≤0.3) and `set_patterns` ("You stay close to home key…", teaching.py l.203) — but both are **whole-set** signals, not a specific consecutive run, and can't place a banner over the right stretch.
- **Recommendation:** the frontend groups **maximal runs of ≥3 consecutive tracks sharing a Camelot code** (via `toCamelot(items[i].key)`), and shows ONE banner per run ("The story here is energy, not key") at the top of `SetTimeline` (or above the run). `arc.key_style === 'home-key'` can serve as a cheap coarse gate for whether to bother, but run-grouping drives placement. Copy is view-authored per the mockup.

### Verified file-change inventory (for IMPLEMENT)

1. **`frontend/src/lib/stores/ui.svelte.ts`** (l.4, 10, 26-27) — rename `TimelineViewMode`→`SetViewMode`, values `'list'|'grid'`, default `'list'`, getter/setter `setViewMode`. In-memory (no localStorage).
2. **`frontend/src/lib/utils/camelot.ts`** (after l.209) — add pure `harmonicMove(a,b): 'hold'|'lift'|'switch'|'clash'` reusing `parseCamelot` + `wrap`.
3. **`frontend/src/lib/components/set/TransitionIndicator.svelte`** (largest change; l.5-17 props, l.78-109 markup, styles) — accept new props (adjacent `keyA/keyB`, `bpmA/bpmB`, `energyA/energyB`, `prevEnergyDelta`); render plain-language two-score copy ("On their own {build} · In your arc {ctx}"), a CTX-driven verdict pill (`scoreColor/scoreLabel` on `analysisScore ?? builderScore`), an expandable 5-dim weighted breakdown from the already-fetched `getTransition` `score_breakdown`, a mechanics row (`harmonicMove` word + BPM delta + energy direction), and the gated note (Q4).
4. **`frontend/src/lib/components/set/SetTrackCard.svelte`** (l.131-147 markup, l.286-324 styles) — restyle energy bar to the `--energy-low→mid→high` ramp (keep the existing `.energy-target-marker`); add the faint row-gutter "spine" gradient.
5. **`frontend/src/lib/components/set/SetTimeline.svelte`** (l.283-295 TransitionIndicator call; new: run-grouping, banner, spine gutter, list/grid host + grid render) — thread `items[i]`/`items[i+1]` key/bpm/energy + `prevEnergyDelta` into `TransitionIndicator`; compute same-key runs; render the run-level banner; read `ui.setViewMode` to switch between the row list and the new grid.
6. **`frontend/src/lib/components/set/SetCardGrid.svelte`** (NEW) — compact card grid: LEFT position badge, incoming-transition color top stripe, "from {key} · {relation}" (via `harmonicMove`) + ctx score, title/artist, Camelot-colored key (`getCamelotColor`/`formatKey`), BPM, genre `Chip variant="genre"`, energy mini-bar with target tick.
7. **`frontend/src/lib/components/set/SetView.svelte`** (`.timeline-controls` toolbar l.385-515, and/or pass-through) — host the `SegmentedControl` list/grid toggle bound to `ui.setViewMode` (decision for PLAN: toolbar in SetView vs. a header row inside SetTimeline — recommend SetView toolbar for consistency with the other view controls, since `ui.setViewMode` is global).

### Test landscape
- **Zero frontend test infrastructure** — `grep` finds no `*.test.*`/`*.spec.*` files, no `vitest.config.*`, no `test` script in `package.json` (matches MEMORY: "zero frontend tests"). The only pure-unit-testable new code is `harmonicMove()` in `camelot.ts`.
- Backend teaching/analyzer tests exist under `tests/` (backend, ~373 tests). Since RESEARCH recommends **no** backend change, no backend test work is required.

### Risks / notes for PLAN
- **No frontend test harness.** Deciding whether to stand up Vitest + `@testing-library/svelte` + jsdom for the component tests the Human Section lists, or to cover `harmonicMove` with a minimal Vitest unit test and treat component/E2E as manual acceptance. Recommend the smaller path (unit-test the pure helper; manual E2E for components) unless PLAN wants the harness — flag it explicitly.
- **Prop surface growth on `TransitionIndicator`** — must thread keys/bpm/energy + prev delta from `SetTimeline`; keep types strict (no `as`/`!`), use `SetWaveformTrack` fields already in `items`.
- **Verdict fallback** — spec says verdict is CTX-driven; when `analysisScore` is null (pre-analysis) fall back to `builderScore` to preserve today's behavior.
- **`energy_profile` string form** — `computeEnergyTargets` expects `name(0.3)->…`; the tick renders today, so leave the parser untouched (format change is out of scope).
- **Grid "from {key} · {relation}" per card** needs the previous track's key + `harmonicMove` — same helper, computed per card index.
- **Placement of the toggle** (SetView toolbar vs SetTimeline header) is the one genuine layout decision left for PLAN; both are viable since `setViewMode` is global store state.

### Strategy

**Approach (minimal, frontend-only):**
1. **Store** — repurpose the dead enum to `SetViewMode='list'|'grid'` (in-memory).
2. **Helper** — add pure `harmonicMove()` to `camelot.ts`; this is the unit-test anchor.
3. **`TransitionIndicator`** — rebuild the strip: two-score plain copy, CTX-driven verdict pill (reuse `scoreLabel`/`scoreColor` + `--score-*`), expandable 5-dim breakdown from the existing lazy `getTransition`, mechanics row (`harmonicMove` + BPM delta + energy arrow), Q4-gated note. New props threaded from `SetTimeline`'s `items`.
4. **`SetTrackCard`** — restyle energy bar to the `--energy-*` ramp, keep the existing target tick, add the row-gutter spine gradient.
5. **`SetTimeline`** — thread adjacent-track props + prev-energy delta; group consecutive same-key runs; render the one-per-run insight banner; switch list↔grid on `ui.setViewMode`.
6. **`SetCardGrid`** (new) — the scannable grid with LEFT position badge (design out the top-right collision).
7. **`SetView`** — host the `SegmentedControl` toggle bound to `ui.setViewMode`.

**Testing strategy:**
- **Unit (add minimal Vitest):** `harmonicMove()` — `same → hold`, `±1 same-letter → lift` (incl. 12A↔1A wrap), `same-number diff-letter (relative maj/min) → switch`, `else → clash`, and null/unparseable → `clash`/no-move. This is the highest-value, lowest-cost coverage and the only pure function introduced.
- **Component (decision for PLAN):** if a harness is stood up — `TransitionIndicator` renders the two-score copy + CTX-driven verdict + expands to the 5-dim breakdown; mechanics row shows correct `hold/lift/switch` word, BPM-delta sign, and `↑/→/↓`; note present ONLY when a gate fires and absent on a flat key-locked run; run-banner appears once per run; `SetTrackCard` renders the target tick + ramp; grid card shows the LEFT badge with no score overlap. Otherwise these become manual E2E acceptance checks (below).
- **Manual E2E acceptance:** open a set → transitions read in plain language with a verdict pill and expandable math; a key-locked run shows ONE banner (not repeated sentences); the list/grid toggle switches views and the grid is scannable at a glance.
- **Type-check gate (mandatory):** `cd frontend && npx svelte-check --tsconfig ./tsconfig.json` must be clean — no `as`/`!` assertions per the TypeScript guidelines.

**Expected coverage:** `harmonicMove` fully unit-covered; components covered by manual acceptance (or Vitest component tests if PLAN elects the harness); type-check green. No backend change → no backend test delta.

## Plan

_All diffs are anchored to the verified current-state line numbers in Research. Whitespace inside Svelte `{#if}`/`{#each}` control blocks is illustrative (Svelte is whitespace-insensitive there); indentation inside `<script>`/`<style>` uses tabs to match each file. Two files (TransitionIndicator, SetCardGrid) are given as COMPLETE file contents because the change is a rewrite / new file — write the whole file. The rest are targeted diffs. No `as`/`!` assertions anywhere (TypeScript guideline). Type-check gate: `cd frontend && npx svelte-check --tsconfig ./tsconfig.json`._

### Files
- `frontend/src/lib/stores/ui.svelte.ts`
  - l.4: rename type `TimelineViewMode`→`SetViewMode`, values `'list'|'grid'`.
  - l.10: rename state `timelineViewMode`→`setViewMode`, default `'list'`.
  - l.26-27: rename getter/setter to `setViewMode`.
- `frontend/src/lib/utils/camelot.ts`
  - after l.209 (`keyMoveLabel`): add pure `harmonicMove(a,b)` reusing `parseCamelot` + `wrap`.
- `frontend/src/lib/components/set/TransitionIndicator.svelte`
  - Full rewrite: add adjacent-track props; two-score copy; CTX-driven verdict pill; mechanics row (`harmonicMove` word + BPM delta + energy arrow); Q4-gated note; expandable 5-dim breakdown from the existing lazy `getTransition`.
- `frontend/src/lib/components/set/SetTrackCard.svelte`
  - l.294-317 styles: restyle `.energy-bar-bg` to the `--energy-low→mid→high` ramp; keep `.energy-target-marker` (bump contrast). Markup unchanged.
- `frontend/src/lib/components/set/SetCardGrid.svelte` (NEW)
  - Compact card grid: LEFT position badge, incoming-transition color stripe, "from {key} · {relation}" + ctx score, title/artist, Camelot-colored key, BPM, genre `Chip`, energy mini-bar with tick.
- `frontend/src/lib/components/set/SetTimeline.svelte`
  - l.4 area: import `parseCamelot`; l.7 area: import `SetCardGrid`.
  - after l.77: add `energyNorms`, `deltaOf()`, `runStartIndices` derived.
  - l.181-301 markup: wrap in list/grid switch on `ui.setViewMode`; render run banner; thread adjacent-track props into `TransitionIndicator`.
  - styles: `.track-list` gutter spine + `.run-banner`.
- `frontend/src/lib/components/set/SetView.svelte`
  - l.17 area: import `SegmentedControl` + `SetViewMode`; after l.22: add `viewOptions`.
  - after l.426: add the list/grid `SegmentedControl` tool-group.

### Tasks

#### Task 1 — ui.svelte.ts: repurpose dead enum to SetViewMode
File: `frontend/src/lib/stores/ui.svelte.ts`
Tools: editor
Description: Rename the unused `TimelineViewMode` enum + state + accessor to `SetViewMode='list'|'grid'`, default `'list'`, in-memory (no localStorage). Nothing reads the old names (Research Q2).
Diff:
````diff
--- a/frontend/src/lib/stores/ui.svelte.ts
+++ b/frontend/src/lib/stores/ui.svelte.ts
@@
 export type Tab = 'track' | 'set' | 'dna' | 'tinder' | 'hunt' | 'albums';
-export type TimelineViewMode = 'linear' | 'staircase';
+export type SetViewMode = 'list' | 'grid';
@@
 let selectedTrackInSet = $state<number | null>(null);
-let timelineViewMode = $state<TimelineViewMode>('linear');
+let setViewMode = $state<SetViewMode>('list');
 let playingTrackId = $state<number | null>(null);
@@
 		get selectedTrackInSet() { return selectedTrackInSet; },
 		set selectedTrackInSet(v: number | null) { selectedTrackInSet = v; },
-		get timelineViewMode() { return timelineViewMode; },
-		set timelineViewMode(v: TimelineViewMode) { timelineViewMode = v; },
+		get setViewMode() { return setViewMode; },
+		set setViewMode(v: SetViewMode) { setViewMode = v; },
 		get playingTrackId() { return playingTrackId; },
````
Verification: `grep -rn "timelineViewMode\|TimelineViewMode" frontend/src` returns nothing; `grep -rn "setViewMode" frontend/src/lib/stores/ui.svelte.ts` shows the new names.

#### Task 2 — camelot.ts: add pure harmonicMove() helper
File: `frontend/src/lib/utils/camelot.ts`
Tools: editor
Description: Add a ~12-line pure classifier reusing `parseCamelot` + the `wrap` idiom. Classification table:
| Condition (a→b) | Result |
|---|---|
| same number AND same letter | `hold` |
| same letter AND b is ±1 wheel hour of a (12↔1 wraps) | `lift` |
| same number AND different letter (relative major/minor) | `switch` |
| either key unparseable, OR anything else | `clash` |
Diff (insert immediately after `keyMoveLabel` closes at l.209):
````diff
--- a/frontend/src/lib/utils/camelot.ts
+++ b/frontend/src/lib/utils/camelot.ts
@@
 	if (a.number === b.number) return { label: 'mood switch', score: 0.8 };
 	return { label: 'distant keys', score: 0.3 };
 }
+
+/**
+ * Classify the harmonic move between two keys in the strip/grid vocabulary:
+ * hold (same key), lift (±1 on the wheel, same mode), switch (relative
+ * major/minor), clash (distant or unparseable). Pure — classified client-side
+ * because the backend only gives a numeric harmonic score. Reuses parseCamelot.
+ */
+export function harmonicMove(
+	a: string | null | undefined,
+	b: string | null | undefined,
+): 'hold' | 'lift' | 'switch' | 'clash' {
+	const ka = parseCamelot(a);
+	const kb = parseCamelot(b);
+	if (!ka || !kb) return 'clash';
+	if (ka.number === kb.number && ka.letter === kb.letter) return 'hold';
+	const wrap = (n: number) => ((n - 1 + 12) % 12) + 1;
+	if (ka.letter === kb.letter && (kb.number === wrap(ka.number + 1) || kb.number === wrap(ka.number - 1))) return 'lift';
+	if (ka.number === kb.number && ka.letter !== kb.letter) return 'switch';
+	return 'clash';
+}
````
Verification: desk-check against Task 9 truth table; type-check passes.

#### Task 3 — TransitionIndicator.svelte: full rebuild
File: `frontend/src/lib/components/set/TransitionIndicator.svelte`
Tools: editor (Write — replace ENTIRE file)
Description: Replace the cryptic `BUILD x / y CTX` line. New surface: CTX-driven verdict pill (`scoreLabel`/`scoreColor` on `analysisScore ?? builderScore`), plain-language two-score copy ("On their own {build} · In your arc {ctx}"), a mechanics row (`harmonicMove` word + signed BPM delta + energy arrow ↑/→/↓ with ±0.05 deadband), a Q4-gated teaching note, and an expandable 5-dimension weighted breakdown reusing the existing lazy `getTransition`. New props threaded from `SetTimeline`: `keyA/keyB`, `bpmA/bpmB`, `energyA/energyB` (normalized 0..1), `prevEnergyDelta`. Verdict falls back to `builderScore` when `analysisScore` is null. No `as`/`!`.
Replace the whole file with:
````svelte
<script lang="ts">
	import type { TransitionScoreBreakdown } from '$lib/types';
	import { getTransition } from '$lib/api/sets';
	import { harmonicMove } from '$lib/utils/camelot';

	interface Props {
		fromTrackId: number;
		toTrackId: number;
		score?: number;
		analysisScore?: number;
		teachingMoment?: string;
		setId: number;
		transitionIndex: number;
		active?: boolean;
		onclick?: (index: number) => void;
		keyA?: string | null;
		keyB?: string | null;
		bpmA?: number | null;
		bpmB?: number | null;
		energyA?: number | null;
		energyB?: number | null;
		prevEnergyDelta?: number | null;
	}

	let {
		fromTrackId,
		toTrackId,
		score,
		analysisScore,
		teachingMoment,
		setId,
		transitionIndex,
		active = false,
		onclick,
		keyA = null,
		keyB = null,
		bpmA = null,
		bpmB = null,
		energyA = null,
		energyB = null,
		prevEnergyDelta = null,
	}: Props = $props();

	let loading = $state(false);
	let breakdown = $state<TransitionScoreBreakdown | null>(null);
	let error = $state<string | null>(null);
	let expanded = $state(false);

	let builderScore = $derived(breakdown?.total ?? score ?? null);
	let ctxScore = $derived(analysisScore ?? builderScore);
	let hasDualScores = $derived(analysisScore != null && builderScore != null);

	function scoreColor(s: number): string {
		if (s >= 0.8) return 'var(--score-excellent)';
		if (s >= 0.6) return 'var(--score-good)';
		if (s >= 0.4) return 'var(--score-fair)';
		return 'var(--score-poor)';
	}

	function scoreLabel(s: number): string {
		if (s >= 0.8) return 'Excellent';
		if (s >= 0.6) return 'Good';
		if (s >= 0.4) return 'Fair';
		return 'Poor';
	}

	// ── Mechanics ──
	let move = $derived(harmonicMove(keyA, keyB));
	let bpmDelta = $derived(bpmA != null && bpmB != null ? Math.round(bpmB - bpmA) : null);
	let energyDelta = $derived(energyA != null && energyB != null ? energyB - energyA : null);
	let energyArrow = $derived(
		energyDelta == null ? '→' : energyDelta > 0.05 ? '↑' : energyDelta < -0.05 ? '↓' : '→',
	);

	// Two-score copy — narrowed inside the closure so no non-null assertions are needed.
	let dualCopy = $derived.by(() => {
		if (analysisScore != null && builderScore != null) {
			return `On their own ${builderScore.toFixed(2)} · In your arc ${analysisScore.toFixed(2)}`;
		}
		return null;
	});

	// ── Noteworthy gate (Research Q4) ──
	let divergence = $derived(
		analysisScore != null && builderScore != null ? Math.abs(analysisScore - builderScore) : 0,
	);
	let energyInflection = $derived(
		energyDelta != null &&
			(Math.abs(energyDelta) >= 0.15 ||
				(prevEnergyDelta != null &&
					prevEnergyDelta !== 0 &&
					energyDelta !== 0 &&
					Math.sign(energyDelta) !== Math.sign(prevEnergyDelta))),
	);
	let noteworthy = $derived(move !== 'hold' || divergence >= 0.15 || energyInflection);
	let showNote = $derived(noteworthy && !!teachingMoment);

	async function fetchBreakdown() {
		if (breakdown || loading) return;
		loading = true;
		error = null;
		try {
			const detail = await getTransition(setId, transitionIndex);
			breakdown = detail.score_breakdown;
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load transition';
		} finally {
			loading = false;
		}
	}

	function handleClick() {
		onclick?.(transitionIndex);
	}

	function toggleExpanded(e: MouseEvent) {
		e.stopPropagation();
		expanded = !expanded;
		if (expanded) fetchBreakdown();
	}

	// Preserve prior behavior: lazy-fetch the breakdown when no pre-computed score exists.
	$effect(() => {
		if (score == null && !breakdown && !loading && !error) {
			fetchBreakdown();
		}
	});

	type NumDim = 'harmonic' | 'energy_fit' | 'bpm_compat' | 'genre_coherence' | 'track_quality';
	const DIMS: { key: NumDim; label: string; weight: string }[] = [
		{ key: 'harmonic', label: 'Harmonic', weight: '25%' },
		{ key: 'energy_fit', label: 'Energy fit', weight: '20%' },
		{ key: 'bpm_compat', label: 'BPM', weight: '20%' },
		{ key: 'genre_coherence', label: 'Genre', weight: '15%' },
		{ key: 'track_quality', label: 'Quality', weight: '20%' },
	];
</script>

<div class="transition-indicator" class:active>
	<div class="strip-row">
		<button
			class="strip"
			style="--score-color: {ctxScore != null ? scoreColor(ctxScore) : 'var(--border)'}"
			onclick={handleClick}
		>
			<span class="score-fill"></span>
			{#if ctxScore != null}
				<span class="verdict" style="color: {scoreColor(ctxScore)}; border-color: {scoreColor(ctxScore)}">
					{scoreLabel(ctxScore)}
				</span>
				<span class="scores">
					{#if dualCopy}{dualCopy}{:else}{ctxScore.toFixed(2)}{/if}
				</span>
			{:else if loading}
				<span class="scores">...</span>
			{:else}
				<span class="scores">--</span>
			{/if}

			<span class="mechanics">
				<span class="mech mech-move" data-move={move}>{move}</span>
				{#if bpmDelta != null}
					<span class="mech mech-bpm">{bpmDelta > 0 ? '+' : bpmDelta < 0 ? '−' : ''}{Math.abs(bpmDelta)} BPM</span>
				{/if}
				<span class="mech mech-energy">{energyArrow}</span>
			</span>
		</button>
		<button
			class="expand-btn"
			onclick={toggleExpanded}
			aria-expanded={expanded}
			aria-label={expanded ? 'Hide the math' : 'Show the math'}
		>
			{expanded ? '▴' : '▾'}
		</button>
	</div>

	{#if showNote}
		<div class="note">{teachingMoment}</div>
	{/if}

	{#if expanded}
		<div class="breakdown">
			{#if loading}
				<span class="breakdown-status">Reading the math...</span>
			{:else if error}
				<span class="breakdown-status">Couldn't load the breakdown — try again.</span>
			{:else if breakdown}
				{#each DIMS as dim (dim.key)}
					{@const v = breakdown[dim.key]}
					<div class="dim-row">
						<span class="dim-label">{dim.label}</span>
						<span class="dim-weight">{dim.weight}</span>
						<span class="dim-bar"><span class="dim-fill" style="width: {v * 100}%; background: {scoreColor(v)}"></span></span>
						<span class="dim-val">{v.toFixed(2)}</span>
					</div>
				{/each}
			{/if}
		</div>
	{/if}
</div>

<style>
	.transition-indicator {
		padding: 2px 0;
		display: flex;
		flex-direction: column;
		align-items: stretch;
		gap: 3px;
	}

	.strip-row {
		display: flex;
		align-items: stretch;
		gap: 4px;
	}

	.strip {
		flex: 1;
		display: flex;
		align-items: center;
		gap: 8px;
		position: relative;
		height: 26px;
		padding: 0 10px;
		border: none;
		border-radius: 13px;
		background: var(--bg-tertiary);
		cursor: pointer;
		overflow: hidden;
		transition: box-shadow 0.15s;
	}

	.strip:hover {
		box-shadow: 0 0 0 1px var(--score-color);
	}

	.active .strip {
		box-shadow: 0 0 0 2px var(--accent, var(--score-color));
	}

	.score-fill {
		position: absolute;
		inset: 0;
		background: var(--score-color);
		opacity: 0.12;
		pointer-events: none;
	}

	.verdict {
		position: relative;
		z-index: 1;
		font-size: 9px;
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0.4px;
		padding: 1px 6px;
		border: 1px solid;
		border-radius: 8px;
		flex-shrink: 0;
	}

	.scores {
		position: relative;
		z-index: 1;
		font-size: 11px;
		font-weight: 500;
		color: var(--text-secondary);
		font-variant-numeric: tabular-nums;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.mechanics {
		position: relative;
		z-index: 1;
		margin-left: auto;
		display: flex;
		align-items: center;
		gap: 8px;
		flex-shrink: 0;
	}

	.mech {
		font-size: 10px;
		font-weight: 600;
		color: var(--text-secondary);
		font-variant-numeric: tabular-nums;
	}

	.mech-move {
		text-transform: uppercase;
		letter-spacing: 0.3px;
	}

	.mech-move[data-move='lift'] { color: var(--energy-mid); }
	.mech-move[data-move='switch'] { color: var(--energy-high); }
	.mech-move[data-move='clash'] { color: var(--score-poor); }

	.mech-energy {
		font-size: 12px;
	}

	.expand-btn {
		flex-shrink: 0;
		width: 22px;
		border: none;
		background: var(--bg-tertiary);
		color: var(--text-dim);
		border-radius: 11px;
		cursor: pointer;
		font-size: 10px;
	}

	.expand-btn:hover {
		color: var(--text-primary);
		background: var(--bg-hover);
	}

	.note {
		font-size: 11px;
		line-height: 1.35;
		color: var(--text-secondary);
		padding: 2px 10px;
	}

	.breakdown {
		display: flex;
		flex-direction: column;
		gap: 4px;
		padding: 6px 10px;
		background: var(--bg-secondary);
		border-radius: 8px;
	}

	.breakdown-status {
		font-size: 11px;
		color: var(--text-dim);
	}

	.dim-row {
		display: grid;
		grid-template-columns: 72px 34px 1fr 34px;
		align-items: center;
		gap: 6px;
	}

	.dim-label {
		font-size: 11px;
		color: var(--text-secondary);
	}

	.dim-weight {
		font-size: 9px;
		color: var(--text-dim);
		text-align: right;
	}

	.dim-bar {
		height: 5px;
		background: var(--bg-tertiary);
		border-radius: 3px;
		overflow: hidden;
	}

	.dim-fill {
		display: block;
		height: 100%;
		border-radius: 3px;
	}

	.dim-val {
		font-size: 11px;
		font-weight: 600;
		text-align: right;
		font-variant-numeric: tabular-nums;
		color: var(--text-primary);
	}
</style>
````
Verification: type-check clean; visually a key-locked run shows the mechanics row with `hold`/`→` and NO note; a lift/switch/clash or a ≥0.15 build-vs-ctx gap shows the note; the ▾ toggle reveals five weighted dimension rows.

#### Task 4 — SetTrackCard.svelte: restyle energy bar to the CERCETA ramp
File: `frontend/src/lib/components/set/SetTrackCard.svelte`
Tools: editor
Description: Show fit-to-arc not just loudness — paint the bar track with the faint `--energy-low→mid→high` ramp and bump the existing target tick to `--text-secondary` for legibility. Markup and the `.energy-target-marker` element are unchanged (Research Q5: keep the tick as-is).
Diff:
````diff
--- a/frontend/src/lib/components/set/SetTrackCard.svelte
+++ b/frontend/src/lib/components/set/SetTrackCard.svelte
@@
 	.energy-bar-bg {
 		position: relative;
 		flex: 1;
 		height: 6px;
-		background: var(--bg-tertiary);
+		background: linear-gradient(
+			90deg,
+			color-mix(in srgb, var(--energy-low) 22%, var(--bg-tertiary)),
+			color-mix(in srgb, var(--energy-mid) 22%, var(--bg-tertiary)),
+			color-mix(in srgb, var(--energy-high) 22%, var(--bg-tertiary))
+		);
 		border-radius: 3px;
 		overflow: visible;
 	}
@@
 	.energy-target-marker {
 		position: absolute;
 		top: -2px;
 		width: 2px;
 		height: 10px;
-		background: var(--text-dim);
+		background: var(--text-secondary);
 		border-radius: 1px;
 		transform: translateX(-1px);
 	}
````
Verification: the row energy bar shows the navy→lilac→magenta ramp behind the fill; the target tick renders and is clearly visible.

#### Task 5 — SetCardGrid.svelte: NEW scannable grid view
File: `frontend/src/lib/components/set/SetCardGrid.svelte`
Tools: editor (Write — new file)
Description: A compact card grid for scanning the whole set's key/energy field at a glance. Each card: position badge on the LEFT of the header (designs out the top-right/score collision), an incoming-transition color stripe (top), a "from {key} · {relation}" caption (via `harmonicMove`) + ctx score, title/artist, Camelot-colored key, BPM, a genre `Chip variant="genre"`, and an energy mini-bar with the target tick. Read-only (click selects the track in the set; no DnD). No `setId` needed (breakdown is not fetched here). No `as`/`!`.
Prop contract:
| Prop | Type | Purpose |
|---|---|---|
| `tracks` | `SetWaveformTrack[]` | ordered set tracks (pass `items` from SetTimeline) |
| `energyTargets` | `(number \| undefined)[]` | per-slot arc targets (from `computeEnergyTargets`), default `[]` |
| `analysis` | `SetAnalysis \| null` | source of the CTX score per incoming transition, default `null` |
Create the file with:
````svelte
<script lang="ts">
	import type { SetWaveformTrack, SetAnalysis } from '$lib/types';
	import { formatKey, getCamelotColor, harmonicMove } from '$lib/utils/camelot';
	import { getTrackEnergyNumeric, energyColor } from '$lib/utils/energy';
	import { getUiStore } from '$lib/stores/ui.svelte';
	import Chip from '$lib/components/primitives/Chip.svelte';

	let {
		tracks,
		energyTargets = [],
		analysis = null,
	}: {
		tracks: SetWaveformTrack[];
		energyTargets?: (number | undefined)[];
		analysis?: SetAnalysis | null;
	} = $props();

	const ui = getUiStore();

	// Incoming-transition CTX score keyed by transition position (i-1 lands on card i).
	let ctxMap = $derived.by(() => {
		const map = new Map<number, number>();
		if (analysis) for (const t of analysis.transitions) map.set(t.position, t.scores.total);
		return map;
	});

	function scoreColor(s: number): string {
		if (s >= 0.8) return 'var(--score-excellent)';
		if (s >= 0.6) return 'var(--score-good)';
		if (s >= 0.4) return 'var(--score-fair)';
		return 'var(--score-poor)';
	}

	function selectTrack(trackId: number) {
		ui.selectedTrackInSet = trackId;
	}
</script>

<div class="card-grid" role="list" aria-label="Set at a glance">
	{#each tracks as track, i (track.position ?? i)}
		{@const prevKey = i > 0 ? tracks[i - 1].key : null}
		{@const move = i > 0 ? harmonicMove(prevKey, track.key) : null}
		{@const ctx = ctxMap.get(i - 1)}
		{@const stripe = ctx != null ? scoreColor(ctx) : getCamelotColor(track.key)}
		{@const energyNorm = getTrackEnergyNumeric(track.energy_value, track.energy)}
		{@const target = energyTargets[i]}
		<div
			class="grid-card"
			class:selected={ui.selectedTrackInSet === track.track_id}
			role="listitem"
			tabindex="0"
			onclick={() => selectTrack(track.track_id)}
			onkeydown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); selectTrack(track.track_id); } }}
		>
			<div class="stripe" style="background: {stripe}" aria-hidden="true"></div>
			<div class="card-header">
				<span class="pos-badge">{i + 1}</span>
				{#if move}
					<span class="from-caption">from {formatKey(prevKey) || '?'} · {move}</span>
				{:else}
					<span class="from-caption from-start">set opener</span>
				{/if}
				{#if ctx != null}
					<span class="ctx" style="color: {scoreColor(ctx)}">{ctx.toFixed(2)}</span>
				{/if}
			</div>
			<span class="title" title={track.title ?? ''}>{track.title ?? 'Untitled'}</span>
			<span class="artist" title={track.artist ?? ''}>{track.artist ?? 'Unknown'}</span>
			<div class="meta">
				<span class="key-badge" style="color: {getCamelotColor(track.key)}">{formatKey(track.key) || '?'}</span>
				<span class="bpm">{track.bpm ? Math.round(track.bpm) : '?'}</span>
				{#if track.genre}
					<Chip variant="genre" value={track.genre} size="sm" title={track.genre} />
				{/if}
			</div>
			<div class="energy-bar-bg">
				<div
					class="energy-bar-fill"
					style="width: {energyNorm !== null ? energyNorm * 100 : 0}%; background: {energyNorm !== null ? energyColor(energyNorm) : 'transparent'}"
				></div>
				{#if target !== undefined}
					<div class="energy-target-marker" style="left: {target * 100}%"></div>
				{/if}
			</div>
		</div>
	{/each}
</div>

<style>
	.card-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
		gap: 8px;
		padding: 8px 12px;
	}

	.grid-card {
		position: relative;
		display: flex;
		flex-direction: column;
		gap: 3px;
		padding: 8px 10px 10px;
		background: var(--bg-secondary);
		border: 1px solid transparent;
		border-radius: 6px;
		cursor: pointer;
		overflow: hidden;
		transition: background 0.1s, border-color 0.15s;
	}

	.grid-card:hover {
		background: var(--bg-hover);
	}

	.grid-card.selected {
		background: var(--bg-active);
		border-color: var(--accent);
	}

	.stripe {
		position: absolute;
		top: 0;
		left: 0;
		right: 0;
		height: 3px;
	}

	.card-header {
		display: flex;
		align-items: center;
		gap: 6px;
		margin-top: 2px;
	}

	.pos-badge {
		flex-shrink: 0;
		min-width: 18px;
		height: 18px;
		padding: 0 5px;
		display: inline-flex;
		align-items: center;
		justify-content: center;
		font-size: 10px;
		font-weight: 700;
		font-variant-numeric: tabular-nums;
		color: var(--text-secondary);
		background: var(--bg-tertiary);
		border-radius: 9px;
	}

	.from-caption {
		font-size: 10px;
		color: var(--text-dim);
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.from-start {
		font-style: italic;
	}

	.ctx {
		margin-left: auto;
		font-size: 11px;
		font-weight: 600;
		font-variant-numeric: tabular-nums;
	}

	.title {
		font-size: 12px;
		font-weight: 500;
		color: var(--text-primary);
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.artist {
		font-size: 11px;
		color: var(--text-secondary);
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.meta {
		display: flex;
		align-items: center;
		gap: 8px;
		margin-top: 2px;
	}

	.key-badge {
		font-weight: 600;
		font-size: 11px;
	}

	.bpm {
		font-size: 11px;
		color: var(--text-secondary);
		font-variant-numeric: tabular-nums;
	}

	.energy-bar-bg {
		position: relative;
		height: 6px;
		margin-top: 4px;
		background: linear-gradient(
			90deg,
			color-mix(in srgb, var(--energy-low) 22%, var(--bg-tertiary)),
			color-mix(in srgb, var(--energy-mid) 22%, var(--bg-tertiary)),
			color-mix(in srgb, var(--energy-high) 22%, var(--bg-tertiary))
		);
		border-radius: 3px;
		overflow: visible;
	}

	.energy-bar-fill {
		height: 100%;
		border-radius: 3px;
	}

	.energy-target-marker {
		position: absolute;
		top: -2px;
		width: 2px;
		height: 10px;
		background: var(--text-secondary);
		border-radius: 1px;
		transform: translateX(-1px);
	}
</style>
````
Verification: type-check clean; in grid mode each card shows the LEFT position badge with no overlap on the ctx score, the top stripe, the "from {key} · {relation}" caption, and the energy mini-bar with tick.

#### Task 6 — SetTimeline.svelte: thread props, run banner, spine, list/grid switch
File: `frontend/src/lib/components/set/SetTimeline.svelte`
Tools: editor
Description: (a) import `parseCamelot` + `SetCardGrid`; (b) add `energyNorms`, `deltaOf()`, and `runStartIndices` (maximal runs of ≥3 consecutive same-Camelot-key tracks); (c) switch the rendered body on `ui.setViewMode` — grid renders `SetCardGrid`, list keeps the existing DnD timeline; (d) render one run banner ("The story here is energy, not key") above the first track of each qualifying run; (e) thread adjacent-track key/bpm/energy + `prevEnergyDelta` into `TransitionIndicator`; (f) add the faint energy-ramp gutter spine + `.run-banner` styles.
Diff (imports):
````diff
--- a/frontend/src/lib/components/set/SetTimeline.svelte
+++ b/frontend/src/lib/components/set/SetTimeline.svelte
@@
 	import { getUiStore } from '$lib/stores/ui.svelte';
+	import { parseCamelot } from '$lib/utils/camelot';
 	import { reorderSetTracks, removeTrackFromSet, addTrackToSet } from '$lib/api/sets';
 	import SetTrackCard from './SetTrackCard.svelte';
 	import TransitionIndicator from './TransitionIndicator.svelte';
+	import SetCardGrid from './SetCardGrid.svelte';
 	import ReplaceTrackModal from './ReplaceTrackModal.svelte';
 	import InSetTrackSearch from './InSetTrackSearch.svelte';
````
Diff (derived helpers — insert after the `energyTargets` derived at l.77):
````diff
--- a/frontend/src/lib/components/set/SetTimeline.svelte
+++ b/frontend/src/lib/components/set/SetTimeline.svelte
@@
 	let energyTargets = $derived(computeEnergyTargets(energyProfile, items.length));
+
+	// Normalized energy per position — feeds the transition energy arrow + inflection gate.
+	let energyNorms = $derived(items.map((it) => getTrackEnergyNumeric(it.energy_value, it.energy)));
+
+	function deltaOf(a: number | null, b: number | null): number | null {
+		return a != null && b != null ? a - b : null;
+	}
+
+	/** Start indices of maximal runs of ≥3 consecutive tracks sharing a Camelot key. */
+	let runStartIndices = $derived.by(() => {
+		const starts = new Set<number>();
+		let start = 0;
+		for (let i = 1; i <= items.length; i++) {
+			const a = parseCamelot(items[i - 1]?.key);
+			const b = i < items.length ? parseCamelot(items[i]?.key) : null;
+			const same = !!a && !!b && a.number === b.number && a.letter === b.letter;
+			if (!same) {
+				if (i - start >= 3) starts.add(start);
+				start = i;
+			}
+		}
+		return starts;
+	});
````
Note: `getTrackEnergyNumeric` is already imported at the existing mid-`<script>` line (`import { getTrackEnergyNumeric } from '$lib/utils/energy';`); ESM imports hoist, so using it above is valid — do NOT add a duplicate import.
Diff (list/grid switch open — wrap the existing `.timeline-content`):
````diff
--- a/frontend/src/lib/components/set/SetTimeline.svelte
+++ b/frontend/src/lib/components/set/SetTimeline.svelte
@@
 		{:else}
+			{#if ui.setViewMode === 'grid'}
+				<SetCardGrid tracks={items} {energyTargets} {analysis} />
+			{:else}
 			<div class="timeline-content">
````
Diff (run banner + threaded props — inside the `{#each items ...}` list loop):
````diff
--- a/frontend/src/lib/components/set/SetTimeline.svelte
+++ b/frontend/src/lib/components/set/SetTimeline.svelte
@@
 				{#each items as item, i (item.id)}
+					{#if runStartIndices.has(i)}
+						<div class="run-banner">The story here is energy, not key</div>
+					{/if}
 					<div class="track-slot">
@@
 								<TransitionIndicator
 									fromTrackId={item.track_id}
 									toTrackId={items[i + 1].track_id}
 									score={items[i + 1].transition_score ?? undefined}
 									analysisScore={analysisMap.get(i)?.score}
 									teachingMoment={analysisMap.get(i)?.teaching}
+									keyA={item.key}
+									keyB={items[i + 1].key}
+									bpmA={item.bpm}
+									bpmB={items[i + 1].bpm}
+									energyA={energyNorms[i]}
+									energyB={energyNorms[i + 1]}
+									prevEnergyDelta={i > 0 ? deltaOf(energyNorms[i], energyNorms[i - 1]) : null}
 									{setId}
 									transitionIndex={i}
 								active={activeTransitionIndex === i}
 									onclick={handleTransitionClickInternal}
 								/>
````
Diff (list/grid switch close — after the `.timeline-content` closing `</div>` at l.301):
````diff
--- a/frontend/src/lib/components/set/SetTimeline.svelte
+++ b/frontend/src/lib/components/set/SetTimeline.svelte
@@
 				</div>
 			</div>
+			{/if}
 
 		{#if dropActive || dropAdding}
````
Diff (styles — spine + run banner; extend the existing `.track-list` rule):
````diff
--- a/frontend/src/lib/components/set/SetTimeline.svelte
+++ b/frontend/src/lib/components/set/SetTimeline.svelte
@@
 	.track-list {
 		flex: 1;
 		min-width: 0;
 		display: flex;
 		flex-direction: column;
+		position: relative;
 	}
+
+	/* Faint energy-ramp spine down the row gutter — the set as one continuous flow. */
+	.track-list::before {
+		content: '';
+		position: absolute;
+		left: -11px;
+		top: 4px;
+		bottom: 4px;
+		width: 2px;
+		border-radius: 1px;
+		background: linear-gradient(var(--energy-low), var(--energy-mid), var(--energy-high));
+		opacity: 0.18;
+		pointer-events: none;
+	}
+
+	.run-banner {
+		margin: 4px 0 6px;
+		padding: 4px 10px;
+		font-size: 11px;
+		font-weight: 500;
+		color: var(--text-secondary);
+		background: color-mix(in srgb, var(--energy-mid) 10%, transparent);
+		border-left: 2px solid var(--energy-mid);
+		border-radius: 3px;
+	}
````
Verification: list view unchanged except the gutter spine + one banner per key-locked run of ≥3; toggling to grid renders `SetCardGrid`; transitions now receive keys/bpm/energy (mechanics + gated note populate).

#### Task 7 — SetView.svelte: host the list/grid SegmentedControl toggle
File: `frontend/src/lib/components/set/SetView.svelte`
Tools: editor
Description: Add a `SegmentedControl` (list default) in the toolbar, bound to the global `ui.setViewMode`, shown once the set has tracks. `getUiStore()`/`ui` already exist (l.4, l.22).
Diff (imports — after the `MenuSeparator` import at l.17):
````diff
--- a/frontend/src/lib/components/set/SetView.svelte
+++ b/frontend/src/lib/components/set/SetView.svelte
@@
 	import MenuSeparator from '$lib/components/primitives/MenuSeparator.svelte';
+	import SegmentedControl, { type SegmentOption } from '$lib/components/primitives/SegmentedControl.svelte';
+	import type { SetViewMode } from '$lib/stores/ui.svelte';
````
Diff (view options — after `const ui = getUiStore();` at l.22):
````diff
--- a/frontend/src/lib/components/set/SetView.svelte
+++ b/frontend/src/lib/components/set/SetView.svelte
@@
 	const ui = getUiStore();
+
+	const viewOptions: SegmentOption<SetViewMode>[] = [
+		{ value: 'list', label: 'List' },
+		{ value: 'grid', label: 'Grid' },
+	];
````
Diff (toolbar control — after the Build/arrange group `{/if}` at l.426):
````diff
--- a/frontend/src/lib/components/set/SetView.svelte
+++ b/frontend/src/lib/components/set/SetView.svelte
@@
 						</Button>
 					</div>
 				{/if}
+
+				<!-- View: list vs grid — scan the whole set's key/energy field at a glance -->
+				{#if waveformTracks.length >= 1}
+					<div class="tool-divider" role="separator" aria-orientation="vertical"></div>
+					<div class="tool-group">
+						<SegmentedControl
+							options={viewOptions}
+							value={ui.setViewMode}
+							onchange={(v) => (ui.setViewMode = v)}
+							ariaLabel="Set view"
+							dense
+						/>
+					</div>
+				{/if}
 
 				<!-- 3 · Analyze — keep the energy-review count CTA prominent -->
````
Verification: a List/Grid toggle appears in the set toolbar; switching to Grid re-renders the timeline body as the card grid, back to List restores the row list; default is List.

#### Task 8 — Type-check gate (svelte-check)
Tools: shell
Description: Project norm is svelte-check as the only frontend static gate (zero test infra — Research). Must be clean (no `as`/`!` per TypeScript guideline).
Commands:
- `cd /home/mantis/Development/mantis-dev/waveform-builer/frontend && npx svelte-check --tsconfig ./tsconfig.json`
Expectation: 0 errors. Resolve any error before proceeding (common risks: a stray non-null assertion, a mistyped prop, an unused import).

#### Task 9 — Testing: harmonicMove desk-check + manual E2E acceptance
Tools: manual / shell
Description: Per Research (zero frontend test harness) and DO NOT OVERCOMPLICATE, do not stand up Vitest. Cover the one pure function by desk-checking `harmonicMove` against the truth table below, and cover the components by the manual browser acceptance checklist.
harmonicMove truth table (verify each by reading Task 2's logic; each row must hold):
| a | b | expected | why |
|---|---|---|---|
| `8A` | `8A` | `hold` | same number+letter |
| `Am` | `Am` | `hold` | parses to 8A both sides |
| `8A` | `9A` | `lift` | +1 wheel, same letter |
| `8A` | `7A` | `lift` | −1 wheel, same letter |
| `12A` | `1A` | `lift` | wheel wrap 12→1 |
| `1A` | `12A` | `lift` | wheel wrap 1→12 |
| `8A` | `8B` | `switch` | same number, relative major/minor |
| `8A` | `10A` | `clash` | two steps apart |
| `8A` | `3B` | `clash` | distant |
| `null` | `8A` | `clash` | unparseable input |
| `xyz` | `8A` | `clash` | unparseable input |
Manual E2E acceptance (run the app: `source .venv/bin/activate && kiku api` + `cd frontend && npm run dev`; open a set with ≥3 tracks and a Cm-locked run):
1. Each transition strip reads in plain language — a verdict pill (CTX-driven) + "On their own {build} · In your arc {ctx}" — not the old `BUILD x / y CTX`.
2. The mechanics row shows the correct `hold`/`lift`/`switch`/`clash` word, a signed BPM delta, and an energy arrow ↑/→/↓.
3. On a flat key-locked run the written note is ABSENT (every move is `hold`, no divergence, no inflection); it APPEARS on a key/mode change, a ≥0.15 build-vs-ctx gap, or an energy inflection.
4. Expanding a transition (▾) reveals the five weighted dimensions (Harmonic 25 / Energy 20 / BPM 20 / Genre 15 / Quality 20) fetched via `getTransition`.
5. A key-locked run of ≥3 shows ONE banner ("The story here is energy, not key"), not a repeated sentence per row.
6. The energy bar shows the navy→lilac→magenta ramp with a visible target tick; the row gutter shows the faint spine.
7. The List/Grid toggle switches views; in Grid each card has the position badge on the LEFT (no overlap with the ctx score), the incoming stripe, the "from {key} · {relation}" caption, key/BPM/genre, and an energy mini-bar with tick.

#### Task 10 — Commit (code files only)
Tools: git
Description: Stage ONLY the seven files this spec touches. DO NOT stage the unrelated `SimilarTrackCard→RelatedTrackCard` rename or any other working-tree change. Never `git add -A`/`git add .`.
Commands:
- `cd /home/mantis/Development/mantis-dev/waveform-builer && git branch --show-current` → must print `set-view-redesign`
- `git add -- frontend/src/lib/stores/ui.svelte.ts frontend/src/lib/utils/camelot.ts frontend/src/lib/components/set/TransitionIndicator.svelte frontend/src/lib/components/set/SetTrackCard.svelte frontend/src/lib/components/set/SetCardGrid.svelte frontend/src/lib/components/set/SetTimeline.svelte frontend/src/lib/components/set/SetView.svelte`
- `git commit -m "spec(025): IMPLEMENT - set-view track and transition redesign"`

### Validate

Each Human-Section requirement mapped to the task that satisfies it:
- **MLO — Redesign `TransitionIndicator`: two-score copy, CTX verdict pill, expandable 5-dim breakdown (L10).** → Task 3 (dualCopy, `scoreLabel`/`scoreColor` on `analysisScore ?? builderScore`, breakdown via lazy `getTransition`).
- **MLO — Compact mechanics (hold/lift/switch, BPM delta, energy ↑/→/↓) replacing the repeated sentence; note only when noteworthy (L11).** → Task 3 (mechanics row + `showNote` gate) using Task 2's helper.
- **MLO — Camelot relationship helper hold/lift/switch/clash (L12).** → Task 2 (`harmonicMove`), reusing `parseCamelot` + `wrap`.
- **MLO — Run-level insight banner once per key-locked run (L13).** → Task 6 (`runStartIndices` + `.run-banner`, copy "The story here is energy, not key").
- **MLO — Energy bar fit-to-arc on the `--energy-*` ramp with target tick + gutter spine (L14).** → Task 4 (ramp + tick) and Task 6 (spine).
- **MLO — Grid view + list/grid `SegmentedControl` toggle (list default); LEFT position badge (L15).** → Task 5 (grid, LEFT badge), Task 6 (switch on `ui.setViewMode`), Task 7 (toggle), Task 1 (store).
- **MLO — Copy per BRANDING.md; approved mockup strings (L16).** → Tasks 3/6 use exactly "On their own · In your arc" and "The story here is energy, not key"; no banned words introduced.
- **MLO — Type-check passes (L17).** → Task 8.
- **DT — Reuse `SegmentedControl`, `Chip`, `energy-target-marker`, `scoreLabel/scoreColor` + `--score-*`, `getTransition`, camelot helpers; no scoring/analysis fork (L62).** → Tasks 3/5/7 reuse primitives + lazy fetch; Task 2 reuses `parseCamelot`; no backend change (Research Q1).
- **DT — Stay in-palette (energy + score ramps), no new colors (L63).** → Tasks 3/4/5/6 use only `--energy-*`/`--score-*` tokens + `color-mix`.
- **DT — Position badge on the LEFT of the grid card (L65).** → Task 5 (`.pos-badge` first in `.card-header`).
- **DT — Efficiency: breakdown stays lazily fetched; grid renders from analysis in hand (L66).** → Task 3 (unchanged lazy `getTransition`), Task 5 (renders from `analysis`/`items`, no fetch).
- **Testing — component behaviors, Camelot unit cases, banner, energy tick, grid badge, type-check, manual E2E (L79-85).** → Task 9 (truth table + acceptance checklist) + Task 8 (type-check).
- **Scope — `SetGrid` untouched, no scoring-math change (L69-70).** → No task touches `SetGrid` or scoring; unrelated working-tree files explicitly excluded in Task 10.

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
