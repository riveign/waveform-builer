# 017 — Vibe-Aware Set Building

> Status: DONE (CREATE → IMPLEMENT → TEST → FIX → DOCUMENT)
> Branch: `vibe-aware-sets`
> Created: 2026-06-07

## Outcome

Shipped end-to-end and verified live. Vibe backfilled on all 4,254 analyzed tracks
(`kiku autotag vibe`). Steering proven: a "dark & deep" preset at 0.9 intensity pulled
a set seeded with a bright track (Ghetto Bang, brightness 0.90) from average brightness
0.70 → **0.21**; "euphoric" held it at 0.70; "melodic" landed mid at 0.65. 27 new tests
(22 unit + 5 API) plus a features-endpoint regression test; full suite 274 passed (the
5 failing `test_energy` cases pre-date this work — on-disk energy calibration shifts the
zone boundaries away from those tests' hardcoded expectations). Frontend type-checks clean.

---

## Human Section

I want to build a new system to improve how we build sets where we can also share
some feelings or indications of what we want the mood to be. Right now we get sets
with songs that on paper make sense (BPM, energy) but the *style* can be off — one
track is dark and deep, the next is very happy. We should look at this too when
building sets.

It should be possible to set a starting and ending song of the set, base the
analysis on those, determine the starting and ending moods, and consider those
transitions as well.

---

## AI Section

### Problem

Tracks are scored on five dimensions — harmonic, energy, BPM, genre, quality — but
none of them capture *vibe*. Two tracks can share a key, BPM and energy zone yet
feel opposite: one dark and hypnotic, one bright and euphoric. The set "works on
paper" and clashes on the floor.

The database already has `mood_happy/sad/aggressive/relaxed` columns, but they are
**0% populated** — the Essentia mood models were never installed and the extraction
code is dead. So there is no vibe signal feeding the scorer today.

### Decisions (confirmed with DJ)

1. **Mood signal — derive a transparent vibe** from features we already extract.
   No new dependencies, no black-box ML, works on the ~4,254 already-analyzed
   tracks immediately. Fits *Opinions You Can See Through* / *Don't Hide the Math*.
2. **Input — vibe presets + intensity.** DJ picks a descriptor ("dark & deep",
   "hypnotic", "driving", "melodic", "euphoric", …) and an intensity knob for how
   strongly vibe should steer selection.
3. **Anchoring — soft.** A start and an end track bias selection and define the
   endpoints of a *vibe arc*; they are not force-pinned into position.

### The Vibe Model (transparent)

Two explainable axes in `[0, 1]`, derived per track from existing data:

- **Brightness** (dark ↔ bright) — the "dark/deep vs happy" axis the DJ described.
  - `0.45 ·` key mode (major = 1.0, minor = 0.0 — from Camelot letter)
  - `0.40 ·` normalized `spectral_centroid` (brighter timbre → higher)
  - `0.15 ·` high-band ratio (`midhigh + high` band energy / total band energy)
  - Falls back to `0.55 / 0.45` mode/centroid split when band data is absent.
- **Density** (spacious/hypnotic ↔ busy/driving)
  - `0.55 ·` normalized `spectral_complexity`
  - `0.45 ·` `danceability`

Normalization uses library-wide robust percentiles (5th/95th) stored in
`data/vibe_calibration.json`, mirroring the energy-calibration pattern. When no
calibration exists, fixed fallback ranges are used. Every coefficient is documented
so a DJ can read exactly why a track reads "dark".

Stored as two new `audio_features` columns: `vibe_brightness`, `vibe_density`.
Backfilled from data already in the DB — no audio re-decoding.

### Vibe Presets

`VIBE_PRESETS: dict[str, (brightness, density)]` — descriptors that match how DJs
talk, each a target point in vibe space:

| Preset       | brightness | density |
|--------------|-----------:|--------:|
| dark & deep  | 0.15 | 0.35 |
| hypnotic     | 0.30 | 0.25 |
| rolling      | 0.50 | 0.65 |
| driving      | 0.50 | 0.80 |
| melodic      | 0.70 | 0.45 |
| euphoric     | 0.90 | 0.60 |
| raw / peak   | 0.45 | 0.90 |

`vibe_intensity ∈ [0, 1]` scales how much the vibe term shifts ranking.

### Scoring Integration

Vibe enters as a **bounded additive term**, like the existing genre-momentum and
BPM-progression bonuses — so the five normalized weights, their validation, and the
weights UI are untouched.

- `vibe_target_fit(track, target_vibe) → [0,1]` — `1 − dist` to the target vibe.
- `vibe_continuity(from, to) → [0,1]` — `1 − dist` between adjacent tracks' vibes;
  penalizes the jarring dark→happy jump unless the arc intends it.
- Contribution: `vibe_intensity · 0.3 · ((0.6·fit + 0.4·continuity) − 0.5) · 2`,
  i.e. roughly `[−0.3, +0.3]` at full intensity. Exposed in score breakdowns.

### Anchors & Vibe Arc

- Start anchor = existing seed (`seed_track_id`).
- End anchor = new `end_track_id`.
- `VibeProfile` interpolates the target vibe across the set:
  - both anchors → linear arc from the seed's vibe to the end track's vibe;
  - preset only → flat target at the preset vibe;
  - both → preset biases the middle, anchors fix the endpoints.
- **Soft landing:** in the final stretch (`progress > 0.8`) when an end anchor
  exists, candidates get a bonus for harmonic/BPM/vibe compatibility with the end
  track, so the set lands near it without forcing it as the literal last track.

### Teaching (Show the Why)

Transition analysis surfaces each track's vibe (brightness/density + label) and
flags vibe clashes between neighbours with a teaching moment, e.g. *"This jump
brightens hard — dark to euphoric. Intentional lift, or a clash?"*

### Surface Area

- `src/kiku/vibe.py` — derivation, calibration, presets, labels.
- `alembic/versions/…_add_vibe_columns.py` — `vibe_brightness`, `vibe_density`.
- `kiku autotag vibe` — calibration + backfill.
- `src/kiku/setbuilder/scoring.py` — vibe functions + transition/breakdown terms.
- `src/kiku/setbuilder/planner.py` — `VibeProfile`, end-anchor soft pull.
- `src/kiku/api/schemas.py` + `routes/sets.py` — `end_track_id`, `vibe_preset`,
  `vibe_intensity`; vibe presets endpoint; vibe fields on responses.
- Frontend — vibe preset picker + intensity slider + start/end anchor pickers in
  `BuildSetDialog`; vibe + clash surfacing in transition analysis.

### Test Plan

Unit: vibe derivation (mode/centroid/band math, fallbacks), preset lookup,
`vibe_target_fit` / `vibe_continuity`, `VibeProfile` interpolation, soft-anchor
pull. API: build with vibe params returns a set and emits vibe data.
