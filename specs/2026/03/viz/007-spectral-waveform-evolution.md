# Human Section
Critical: any text/subsection here cannot be modified by AI.

## High-Level Objective (HLO)

Evolve the spectral waveform from a single-track display into a multi-track spectral comparison view that lets DJs visually identify where tracks overlap well sonically — seeing complementary frequencies, shared energy shapes, and natural mix points — so they can build better sets by understanding how tracks sound together before mixing them.

## Mid-Level Objectives (MLO)

1. **POLISH** the single-track spectral renderer (current MVP) — improve visual clarity, color contrast, and readability at small sizes
2. **CREATE** a compact spectral waveform component that renders cleanly at reduced heights (for multi-track stacking)
3. **BUILD** a multi-track spectral comparison view — stack multiple spectral waveforms vertically, time-aligned, so the DJ can scan for complementary frequency zones
4. **ADD** visual indicators for mix-friendly zones — where Track A's dominant frequencies complement Track B's (e.g., bass-heavy section meets a hi-hat-driven section)
5. **INTEGRATE** with set building — drag tracks from the comparison view into a set, informed by what the spectral view revealed

## Details (DT)

### Current State
- Spectral waveform MVP is live: 4-band stacked bars (bass=red, mid-low=orange, mid-high=green, high=blue) in `WavesurferPlayer.svelte`
- Band data exists for ~3,500+ tracks (4 float32 envelope arrays per track: low, midlow, midhigh, high)
- Backend API: `/api/waveforms/{id}/bands` returns band envelope data
- Toggle between Classic and Spectral view per player instance

### Vision
A DJ browsing their library can select 2-4 tracks and see their spectral waveforms stacked vertically on the same page. At a glance they can see:
- "Track A is bass-heavy in the first half, Track B has a bass drop at 2:00 — they'd layer well there"
- "These two tracks have almost identical frequency profiles — they'll clash"
- "Track C has a clean high-end intro that would sit perfectly over Track A's outro"

### Incremental Steps (phases)

**Phase 1: Compact spectral renderer**
- Visual-only spectral waveform component (no audio playback, no controls) for embedding in lists/grids
- Renders at 40-60px height with readable color bands
- Fetches band data, falls back to flat colored bar if unavailable

**Phase 2: Side-by-side comparison view**
- New view/panel where DJ can pin 2-4 tracks for spectral comparison
- Tracks stacked vertically, time-normalized (all same width regardless of duration)
- Time markers showing minutes/sections
- Click a track to hear it in the main player

**Phase 3: Mix-point indicators**
- Overlay showing "complementary zones" where two adjacent tracks' frequencies don't clash
- Highlight dominant-frequency shifts (bass drops, breakdowns, builds)
- Visual cue for where one track's energy fades and another's rises — natural transition points

**Phase 4: Set integration**
- In set view, show mini spectral waveforms for each track in the timeline
- At transition points, overlay both tracks' spectrals to preview the frequency blend
- Color-code transition quality based on spectral compatibility (not just harmonic/BPM)

### Constraints
- All rendering must use pre-computed band data (no real-time FFT)
- Compact renderer must be lightweight — potentially dozens on screen at once
- No new npm dependencies — Canvas 2D is sufficient
- Spectral comparison is read-only/visual — no audio mixing or processing

### Testing
- Visual verification: compact renderer at various heights (40px, 60px, 80px)
- Performance: render 20+ compact spectral waveforms without jank
- Fallback: tracks without band data show graceful placeholder
- E2E: pin tracks to comparison view, verify stacking and time alignment

## Behavior

You are a senior frontend engineer building a DJ visualization tool. Focus on visual clarity and performance. The spectral view should feel like looking at a mixing console's frequency analyzer — intuitive for DJs who already think in terms of lows, mids, and highs. Keep rendering fast and memory-light since many waveforms may be on screen simultaneously. Use Canvas 2D throughout — no WebGL complexity needed for bar rendering.

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
