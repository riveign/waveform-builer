# Human Section
Critical: any text/subsection here cannot be modified by AI.

## High-Level Objective (HLO)
A Tinder-style swipe UI for reviewing energy and mood predictions — the DJ listens to each track playing in the browser, sees the model's prediction, and swipes to confirm, correct, or skip. Every decision feeds back into the training set, closing the human-in-the-loop retraining cycle from spec 001-autotag-energy.

## Mid-Level Objectives (MLO)
- BUILD a card-based UI in the existing Dash/SvelteKit app that shows one track at a time with: waveform player, predicted energy zone, confidence score, and current audio features
- PLAY the track audio directly in the browser (HTML5 audio element) so the DJ can listen before deciding
- PRESENT swipe actions: confirm prediction (right/green), override with correct zone (left/choose), skip (up/gray)
- DISPLAY the prediction alongside mood indicators (aggressive/relaxed, happy/sad axes) so the DJ builds intuition about what the model sees vs. what they feel
- STORE every decision (confirm, override, skip) in the DB — confirmed and overridden predictions become `energy_source = "approved"` training data
- SUPPORT batch sessions: DJ opens the tinder, reviews N tracks, closes — progress is saved, next session starts where they left off
- TRACK session stats: reviewed count, confirmed %, overridden %, skip rate, and how the model's accuracy evolves over sessions
- ENABLE one-click retrain after a review session: "You reviewed 50 tracks. Retrain model now?" which triggers `train_energy_model()` with the new approved data

## Details (DT)

### Track Queue
- Queue = all tracks with `energy_predicted IS NOT NULL AND energy_source = "auto"` (not yet reviewed)
- Order by confidence ascending (show uncertain predictions first — that's where human input is most valuable)
- DJ can filter queue by genre family or BPM range

### Card Layout
- Large waveform with playback controls (play/pause, seek) — reuse existing waveform visualization
- Track metadata: title, artist, genre, BPM, key
- Prediction display: predicted zone (warmup/build/peak) with confidence bar
- Mood radar: show mood_happy, mood_sad, mood_aggressive, mood_relaxed as a small 4-axis spider/radar
- Action buttons: Confirm (keeps prediction), Override (dropdown to pick correct zone), Skip

### Audio Playback
- Use HTML5 `<audio>` element pointing to the track's `file_path`
- Auto-play when card appears, pause when swiping
- Consider serving audio through a local endpoint if file paths are on external drives

### Decision Storage
- On confirm: set `energy_source = "approved"`, keep `energy_predicted` as-is
- On override: set `energy_source = "approved"`, update `energy_predicted` to DJ's choice, store `energy_confidence = 1.0`
- On skip: leave `energy_source = "auto"`, don't include in training data
- All decisions logged with timestamp for session tracking

### Retraining Integration
- After review session ends, show summary: "Reviewed 47 tracks: 38 confirmed, 6 overridden, 3 skipped"
- Button: "Retrain model with new data" → calls `train_energy_model(include_approved=True)`
- Show before/after accuracy comparison

### Teaching Moment
- When the DJ overrides a prediction, briefly show which features confused the model (e.g., "Model predicted build because loudness was high, but you said warmup — this teaches the model that loudness alone doesn't mean energy")
- This is the Miyagi moment: learning through correcting

## Behavior
You are a senior AI engineer building an interactive music review tool. The UI must feel fast and fun — like swiping through tracks, not filling out forms. Prioritize audio playback latency and smooth transitions between cards. The teaching moments should be concise (one sentence) and appear non-intrusively.

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
