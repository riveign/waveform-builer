# Human Section
Critical: any text/subsection here cannot be modified by AI.

## High-Level Objective (HLO)
Let a DJ name artists they want featured while building a set, and have Kiku gently favor tracks from those artists (including collaborations) — without ever turning the set into an artist-filtered query. This is Phase B of the artist/track-intent line (Phase A shipped as spec 020 `artist-picks`). The bias must be a **visible soft nudge, not a hard filter**: preferred artists get a scoring boost that shows up in the breakdown, but the beam search can still reach past them when the music calls for it. This honors "Show the Why" and "The Story Comes First" (serving the DJ's intent) while protecting "Every Track Deserves a Chance" — naming an artist tilts the odds, it doesn't bar the rest of the library.

## Mid-Level Objectives (MLO)
- ADD a `preferred_artists` list and an `artist_intensity` strength knob to the build request and the `build_set()` planner, mirroring how `vibe_preset` / `vibe_intensity` already flow through
- APPLY a soft artist bonus during beam search: when a candidate's artist matches (via the existing `src/kiku/artists.py` token matcher) any preferred artist, add an `artist_intensity`-scaled bonus to its score — additive, never a filter; tracks from non-preferred artists remain fully eligible
- KEEP the existing 5-track artist cooldown intact, so a featured artist is spread across the set rather than clustered
- SURFACE the why: the score breakdown / teaching should be able to show that a track got a nudge because the DJ asked for that artist ("+ artist you asked for")
- BUILD the frontend: a "Featured artists" typeahead (reuse the artist autocomplete) plus an intensity control in the build dialog, defaulting to off so existing behavior is unchanged
- ENSURE unit tests for the artist-bonus scoring and planner integration, plus an API test for the build request carrying preferred artists

## Details (DT)

### Existing groundwork to reuse
- Artist matcher: `artist_tokens()` / `artist_matches()` (`src/kiku/artists.py`, from spec 020) — collaboration-aware, word-boundary safe. Reuse as-is; do not reimplement.
- Vibe precedent: `vibe_preset` + `vibe_intensity` on `SetBuildRequest` (schemas.py) and `preset_vibe` + `vibe_intensity` on `build_set()` (planner.py) — the artist knobs should flow the exact same way (request → CLI/API → planner → scoring term).
- Scoring: the beam search already blends additive terms (energy fit, the end-pull affinity, the optional vibe term). The artist bonus is another small additive term in the same place.
- Artist cooldown: `_violates_artist_cooldown()` / `ARTIST_COOLDOWN=5` (planner.py / config.py) — unchanged.

### Design constraints (the soft-bias contract)
- **Never a hard filter.** `preferred_artists` must not restrict the candidate pool. Every track stays eligible; preferred ones just score a bit higher. A set built with preferred artists set should differ from one without only by tilt, not by exclusion.
- **Intensity-controlled and visible.** `artist_intensity` (0 = ignore, 1 = strong nudge) scales the bonus, exactly like `vibe_intensity`. Default 0 so behavior is unchanged unless the DJ opts in. The DJ can see and reason about the strength.
- **Collaborations count.** "Tracks from that artist or that artist with others" — matching uses the token matcher, so a featured "Bicep" boosts "Bicep & Chroma" too.
- **Cooldown wins over bias.** The bonus never overrides the artist cooldown; featured artists are favored but still spaced out.
- Voice per BRANDING.md: "set" not "playlist", warm tone, the bonus is framed as honoring the DJ's intent, never as the tool overriding their ear.

### Out of scope
- Per-artist weighting (all preferred artists share one intensity) — keep it simple.
- Multi-anchor pins (that is Phase C).
- Negative preferences / artist avoidance.

### Testing
- Unit: artist-bonus term (matches preferred → bonus applied scaled by intensity; non-match → no bonus; intensity 0 → no effect; collaboration matches via token matcher); planner integration (a preferred artist's tracks rank higher with intensity > 0 but the pool is not filtered — a non-preferred track can still be chosen).
- API: build request accepts `preferred_artists` + `artist_intensity` and threads them through (smoke-level: request validates and a build runs).
- E2E (manual acceptance): in the build dialog, add a featured artist, build, and confirm more of that artist's tracks appear without the set becoming all-that-artist.

## Behavior
You are a senior engineer on Kiku. Honor the 7 product principles (BRANDING.md) — especially "Every Track Deserves a Chance" (this is the principle most at risk here: keep it a soft bias) and "Opinions You Can See Through" (intensity is visible and controllable). Mirror the vibe_intensity plumbing rather than inventing a new pathway. Reuse `src/kiku/artists.py`.

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
