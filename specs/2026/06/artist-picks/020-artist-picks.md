# Human Section
Critical: any text/subsection here cannot be modified by AI.

## High-Level Objective (HLO)
Let a DJ pull music from a specific artist into a set they're building. Given an open set, the DJ names an artist and Kiku returns that artist's top 5 owned tracks (including collaborations) **ranked by how well each fits the set** — and tells the DJ *where* each one belongs and *why*. This is library excavation, not external recommendation: every pick is a track the DJ already owns. It serves "Your Library Is the Lesson" (surface what you own by an artist you're forgetting) and "The Arc Over the Moment" (rank by best position in the whole set, not just the next slot). This is Phase A of a three-phase artist/track-intent feature line; Phases B (artist preferences during build) and C (multi-anchor pins) are out of scope here but share the artist-token matcher this spec introduces.

## Mid-Level Objectives (MLO)
- CREATE an artist-token matcher that splits an artist string on common separators (`,`, `&`, `feat.`, `ft.`, `x`, `vs`, `with`, `+`) into whole tokens, so "Bicep" matches "Bicep & Chroma" and "X feat. Bicep" but NOT "Bicepz" — case-insensitive, whitespace-trimmed
- ADD a "best fit anywhere in the set" ranker: for each owned track by the matched artist, find its ideal insertion slot in the set and the score there; exclude tracks already in the set
- EXPOSE via API: `GET /api/sets/{set_id}/artist-picks?artist=<name>&n=5` returning ranked picks, each with best position, the score breakdown at that position, and a teaching line ("fits at position 7 — 8A harmonic lock, lifts energy into the build")
- EXPOSE via CLI: `kiku artist-picks <set> <artist>` printing the ranked picks with placement + reasons
- BUILD a frontend "add from an artist" affordance in the set view: artist typeahead (reuse existing artist autocomplete), ranked pick cards showing placement + why, one-click insert at the suggested position
- ENSURE unit tests for the artist-token matcher and the best-fit ranker, plus an API test for the endpoint

## Details (DT)

### Existing groundwork to reuse
- Scoring: the 5-dimension `transition_score()` engine, position-aware energy targeting, and `set_id` exclusion already used by `suggest-next` (src/kiku/api/routes/tracks.py:270 `suggest_next`, src/kiku/setbuilder/scoring.py `score_transitions`)
- Artist data: `Track.artist` (plain string), `autocomplete_artists()` (src/kiku/db/store.py:23, case-insensitive substring) for the typeahead; frontend already calls `GET /autocomplete/artists`
- Energy/position: `EnergyProfile.target_energy_at()` (src/kiku/setbuilder/constraints.py) for the energy target at a candidate's position; the set's `energy_profile` JSON

### "Best fit anywhere" semantics
- The set is an ordered list of tracks. For a candidate track, evaluate every insertion gap (before track 0, between i and i+1, after the last track). Score the candidate at each gap against its neighbor(s) AND its position-derived energy target. The candidate's "fit" = its best gap's score; report that gap as the suggested position.
- Rank the artist's owned tracks by their best-gap score; return the top N (default 5).
- A candidate already in the set is excluded.
- Scoring at a gap should consider both the outgoing neighbor (track before the gap) and the incoming neighbor (track after the gap) where both exist — an insertion has two transitions, not one. At the ends, only one neighbor exists.

### Collaboration matching
- "Top songs from that artist (or that artist in collaboration with others)" — the token matcher is the mechanism. Match if the requested artist name equals one of the candidate's artist tokens.
- The matcher is a standalone, tested utility (new module, e.g. `src/kiku/artists.py` or similar) so Phases B/C reuse it. No change to how `artist` is stored.

### Constraints
- Library excavation only — never suggest tracks the DJ doesn't own (anti-principle #2). All picks come from the DJ's library.
- No new heavy dependencies; pure matching + existing scoring.
- "Show the Why": every pick must carry its placement reason and score breakdown — never a bare ranked list.
- Voice per BRANDING.md: "set" not "playlist", warm teaching tone on the cards/CLI, never blame.
- Empty/edge cases handled warmly: artist with no owned tracks, artist whose only tracks are already in the set, set too short to have meaningful gaps.

### Testing
- Unit: artist-token matcher (collabs match, near-misses don't, separators, case/whitespace); best-fit ranker (correct best gap chosen on synthetic sets, in-set exclusion, end-gap single-neighbor scoring)
- API: `artist-picks` endpoint (200 ranked with placements, empty-artist handling, n cap, 404 on missing set)
- E2E (manual acceptance): open a set, add a track from a named artist via the UI, confirm it lands at the suggested position

## Behavior
You are a senior engineer on Kiku. Honor the 7 product principles (BRANDING.md) — especially "Show the Why," "Your Library Is the Lesson," and "The Arc Over the Moment." Reuse the suggest-next / scoring machinery rather than building a parallel scorer. Build the artist-token matcher as a clean shared utility, because Phases B and C depend on it.

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
