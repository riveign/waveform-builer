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

### The key reuse: `score_replacement()` IS the best-gap scorer
- `score_replacement(candidate, prev_track, next_track, target_energy=0.5, weights=None, discovery_density=0.0, set_appearance_counts=None, target_vibe=None, vibe_strength=0.0) -> tuple[float, dict|None, dict|None]` (src/kiku/setbuilder/scoring.py:479-536) scores a candidate against BOTH neighbors (prev→candidate AND candidate→next), returning `(combined_score, incoming_breakdown, outgoing_breakdown)`. Breakdown dicts: `harmonic, energy_fit, bpm_compat, genre_coherence, track_quality, vibe, total`. This is exactly an insertion score — for inserting at gap `g` (between ordered[g-1] and ordered[g]): `prev=ordered[g-1].track` (or None at gap 0), `next=ordered[g].track` (or None at the tail gap). No new scorer needed.
- Underlying single-step: `transition_score(from_track, to_track, target_energy=0.5, ..., weights, discovery_density, target_vibe, vibe_strength) -> float` (scoring.py:443-477). Batch ranker `score_transitions(session, from_track, n=10, genre_filter, weights, exclude_ids, discovery_density, set_appearance_counts, target_energy) -> list[(Track, float)]` (scoring.py:538-601) — single-neighbor only, NOT used here (we need both-neighbor insertion via score_replacement).

### Set loading + per-position energy target (copy from existing endpoints)
- Ordered tracks + neighbors (routes/sets.py:954-961): `ordered = sorted(s.tracks, key=lambda st: st.position)`; `prev = ordered[i-1].track if i>0 else None`; `next = ordered[i+1].track if i<len-1 else None`.
- Energy target at a position (routes/sets.py:965-979, mirrors suggest-next tracks.py:328-337): parse `s.energy_profile` via `parse_energy_json()` then fallback `parse_energy_string()` (src/kiku/setbuilder/constraints.py); `elapsed = (position / max(total_tracks-1, 1)) * (s.duration_min or 120)`; `target = profile.target_energy_at(elapsed)`. For an insertion at gap `g`, use the gap's positional fraction `g / max(len(ordered), 1)` to derive elapsed → energy target.

### Artist data + querying owned tracks
- `Track.artist` is a plain string (models.py:42). Autocomplete: `autocomplete_artists(session, q, limit=20)` (src/kiku/db/store.py:23-33) — `Track.artist.ilike("%q%")`, distinct, ordered. Used by the typeahead.
- To get an artist's candidate pool: query `Track.artist.ilike("%name%")` to narrow at the DB level, THEN filter in Python with the new token matcher for precision (ilike is the coarse prefilter; token match is the exact gate). `search_tracks(session, artist=..., limit=...)` exists (store.py:49-138) but the direct ilike query is simpler here.

### Collaboration token matcher (new shared utility)
- Nothing parses collaborations today (confirmed: no `feat`/`&` splitting anywhere). New module (e.g. `src/kiku/artists.py`) with `artist_tokens(s: str) -> set[str]` (split on `,`, `&`, `feat.`, `ft.`, `x`, `vs`, `with`, `+`; lowercase; strip) and `artist_matches(requested: str, candidate_artist: str) -> bool` (requested token ∈ candidate tokens). Built standalone + tested so Phases B/C reuse it. Care: split on `x`/`vs`/`with` only as whole word-boundary tokens, not substrings (avoid splitting "Maxx" on "x").

### API & CLI patterns to mirror
- suggest-next route (routes/tracks.py:270-369): pool build + `exclude_ids` from set + target_energy block + `SuggestNextResponse{source_track_id, suggestions:[{track, score, breakdown}]}`. The new endpoint mirrors this shape but per-pick adds `position` + reason.
- CLI: `suggest_next` (cli.py:382-420) for the ranked rich Table; set resolution by id-or-name (cli.py:634-638): `try int(...) -> session.get(Set, id)` except `Set.name.ilike("%...%").first()`.

### Frontend
- `addTrackToSet(setId, trackId, position?)` (src/lib/api/sets.ts:154-164) → `POST /api/sets/{id}/tracks` body `{track_id, position}`; position optional (defaults to end). Pass the suggested gap index to insert in place. Adding a track recomputes transition scores + invalidates analysis (and now comparison cache) server-side.
- Artist typeahead exists: `Typeahead.svelte` (src/lib/components/library/Typeahead.svelte) props `placeholder`, bindable `selected`, `fetchSuggestions(q)=>Promise<string[]>`; wire to `autocompleteArtists(q, limit)` (src/lib/api/tracks.ts:38-40). Used in SearchFilters.svelte.
- Mount point: SetView.svelte alongside the existing panels (it already hosts SetEnergyReview, FillReorderDialog, etc.). New component `AddFromArtistPanel.svelte` (or a dialog like ReplaceTrackModal) shows typeahead → ranked pick cards (placement + breakdown + why) → one-click insert at suggested position. After insert, call the existing `onTracksChanged` reload path.

### Test landscape
- Unit: tests/test_scoring.py exists for scoring; new tests/test_artists.py for the token matcher (MagicMock not needed — pure strings); best-gap ranker testable with MagicMock tracks like tests/test_set_analysis.py `_mock_track()`.
- API: tests/api/conftest.py `db_session` seeds 20 tracks + a 5-track set (id=1); `client` fixture. New tests/api/test_artist_picks_api.py follows test_sets_api.py patterns.

### Strategy

**Pure utility → ranker → API → CLI → UI, reusing score_replacement throughout.**
1. **Artist-token matcher** — new `src/kiku/artists.py`: `artist_tokens()` + `artist_matches()`. Word-boundary aware separators. Fully unit-tested first (it gates everything and Phases B/C depend on it).
2. **Best-gap ranker** — new `src/kiku/setbuilder/artist_picks.py` (or function in scoring.py): `rank_artist_picks(session, set_id, artist, n=5, weights=None, discovery_density=0.0) -> list[ArtistPick]`. Steps: load ordered set tracks + set's energy profile; build candidate pool (ilike prefilter → `artist_matches` gate → exclude track IDs already in set); for each candidate, iterate all gaps `g in 0..len`, compute per-gap target_energy, call `score_replacement(cand, prev, next, target_energy, ...)`, keep the best gap; rank candidates by best-gap combined score; return top n with `{track, best_position, score, breakdown_at_gap, reason}`. `reason` built in mentor voice from the dominant breakdown dimension at the chosen gap (harmonic lock / energy lift / bpm glue), reusing the phrasing approach in teaching.py.
3. **Schemas** (api/schemas.py): `ArtistPickItem{track: TrackResponse, position: int, score: float, breakdown: TransitionScoreBreakdown, reason: str}` + `ArtistPicksResponse{set_id, artist, picks: list[ArtistPickItem]}`.
4. **API** (routes/sets.py): `GET /api/sets/{set_id}/artist-picks?artist=<str>&n=5&discovery_density=...` → 404 missing set, 200 with picks (empty list + warm message when artist owns nothing new). Reuse weight-override query params optionally (defer unless trivial).
5. **CLI** (cli.py): `kiku artist-picks <set> <artist>` — set id-or-name resolution, rich Table of picks with `→ pos N`, score, and reason.
6. **Frontend**: API client `getArtistPicks(setId, artist, n)` + types; `AddFromArtistPanel.svelte` (Typeahead + ranked cards with placement/why + insert button calling `addTrackToSet(setId, trackId, position)`); mount in SetView with an "Add from an artist" entry near the existing set actions; reload via `onTracksChanged`.

**Testing strategy**
- Unit `tests/test_artists.py`: token matcher — "Bicep" matches "Bicep & Chroma", "X feat. Bicep", "Bicep, Other"; does NOT match "Bicepz"/"Maxx" (word-boundary); case/whitespace; empty/None.
- Unit `tests/test_artist_picks.py`: best-gap ranker on synthetic sets — correct best gap chosen (harmonic/energy planted), in-set exclusion, end-gap single-neighbor (prev or next None), n cap, empty pool.
- API `tests/api/test_artist_picks_api.py`: 200 ranked with positions + reasons; 404 missing set; artist with no new owned tracks → 200 empty + message; n cap.
- E2E (manual): open a set → "Add from an artist" → type artist → pick a card → it inserts at the suggested position.
- Coverage: matcher + ranker fully unit-tested; endpoint covered; frontend type-checked via svelte-check (no FE test harness).

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
