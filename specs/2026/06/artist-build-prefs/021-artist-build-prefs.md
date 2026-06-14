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

### Vibe is the exact template — mirror it field-for-field
- **Request** (src/kiku/api/schemas.py:260-275): `SetBuildRequest` has `vibe_preset: str | None = None` + `vibe_intensity: float = 0.0`. Add `preferred_artists: list[str] | None = None` + `artist_intensity: float = 0.0` alongside.
- **API route** (src/kiku/api/routes/sets.py:302-365): `POST /build` resolves `vibe_preset`→tuple via `resolve_preset()` (338-342) then passes `preset_vibe=...`, `vibe_intensity=body.vibe_intensity` into `build_set(...)` (350-365). Artists need NO resolve step — pass the strings straight through: `preferred_artists=body.preferred_artists, artist_intensity=body.artist_intensity`.
- **Planner** (src/kiku/setbuilder/planner.py:133-148): `build_set()` signature ends with `preset_vibe: tuple|None = None, vibe_intensity: float = 0.0`. Add `preferred_artists: list[str] | None = None, artist_intensity: float = 0.0` the same way. Vibe arc is set up at 192-202 (only when `vibe_intensity > 0`); the per-candidate scoring call is at planner.py:257.

### Where the bonus attaches (scoring.py)
- `transition_score(from_track, to_track, target_energy=0.5, prefer_playlists=None, weights=None, discovery_density=0.0, set_appearance_counts=None, target_vibe=None, vibe_strength=0.0) -> float` (scoring.py:443-453). Body (473-476): `base = Σ weighted dims`; `vibe_contribution, _ = vibe_term(...)`; `return base + vibe_contribution`.
- `vibe_term(from_track, to_track, target_vibe, vibe_strength) -> (contribution, breakdown)` (scoring.py:417-441): returns `0.0, None` when off; else maps a [0,1] fit to ±`_VIBE_SPAN` (`_VIBE_SPAN=0.3`, line 398) scaled by strength. This is the precedent for a bounded additive term **with a breakdown for transparency**.
- `score_replacement(...)` (scoring.py:479-489) returns `(combined, incoming_bd, outgoing_bd)` and already folds the vibe sub-dict into its breakdowns (`"vibe": vibe_bd`, ~517).
- Planner loop (planner.py:220-287): `_violates_artist_cooldown(seq, cand)` skips at 246-247 (`continue`) — **runs before scoring, so the cooldown already wins over any bonus**. `transition_score(...)` called at 257 with vibe params; BPM-progression bonus added right after (260).

### Artist matcher (reuse as-is, src/kiku/artists.py:26-48)
- `artist_tokens(s) -> set[str]` (collab/word-boundary aware) and `artist_matches(requested, candidate_artist) -> bool` (token-set intersection). For a list, a tiny helper `artist_matches_any(candidate_artist, preferred) = any(artist_matches(p, candidate_artist) for p in preferred)`.

### Frontend (mirror vibe in the build dialog)
- BuildSetDialog.svelte: vibe rendered via `<VibePresetPicker bind:preset bind:intensity />` (~287-290); params assembled (144-182) and only set when present: `if (vibePreset) { params.vibe_preset=...; params.vibe_intensity = vibeIntensity/100; }`. Add a "Featured artists" field: a Typeahead (multi-select) + an intensity slider, and `if (preferredArtists.length) { params.preferred_artists = preferredArtists; params.artist_intensity = artistIntensity/100; }`.
- Typeahead reuse: `AddFromArtistPanel.svelte` already uses `<Typeahead bind:selected fetchSuggestions={(q)=>autocompleteArtists(q,10)} />` (autocompleteArtists from src/lib/api/tracks.ts:38). Typeahead supports a multi-select `selected: string[]` binding.
- Types: `SetBuildParams` (src/lib/types/index.ts:326-341) — add `preferred_artists?: string[] | null; artist_intensity?: number;`. `buildSet()` (src/lib/api/sets.ts) serializes params as-is, no change needed.

### CLI
- `build` command (src/kiku/cli.py:140-150) is minimal and does NOT expose vibe — so it need not expose artists either. Keep CLI parity (skip), interactive surface is the API/dialog. (Note in PLAN; no CLI work.)

### Strategy

**Mirror vibe exactly, with a bounded additive `artist_term` carrying a breakdown for transparency.**
1. **schemas.py**: add `preferred_artists` + `artist_intensity` to `SetBuildRequest` (defaults None/0.0 → zero behavior change when unused).
2. **scoring.py**: add `artist_term(to_track, preferred_artists, artist_intensity) -> (contribution, breakdown|None)` — `0.0, None` when intensity ≤ 0 or no preferred list; else `contribution = artist_intensity * _ARTIST_SPAN` when `artist_matches_any(to_track.artist, preferred)` (positive-only nudge, no penalty), breakdown `{matched: True, contribution}`. Pick `_ARTIST_SPAN ≈ 0.2` (strong enough to tilt the ~[0,1] base, smaller than vibe's 0.3 so it never dominates harmony/energy). Thread `preferred_artists` + `artist_intensity` params (defaulting off) through `transition_score()` (add the contribution to the return) and into `score_replacement()` (fold `"artist": artist_bd` into its breakdowns) so suggest-next / artist-picks / transition-detail can show "+ artist you asked for".
3. **planner.py**: add the two params to `build_set()`, pass them into the `transition_score(...)` call at 257. Cooldown is untouched (it already gates before scoring).
4. **routes/sets.py**: thread `preferred_artists` + `artist_intensity` from the request into `build_set()` (no resolve step).
5. **Frontend**: BuildSetDialog "Featured artists" Typeahead (multi-select) + intensity slider (default 0 → off); add fields to `SetBuildParams`; only attach when a list is present.
6. **Voice/transparency**: the breakdown label and any teaching string read as honoring the DJ's ask ("+ artist you asked for"), never the tool overriding the ear.

**Testing**
- Unit (tests/test_scoring.py or new tests/test_artist_bias.py): `artist_term` — match → positive bonus scaled by intensity; non-match → 0; intensity 0 → 0; collaboration matches via the token matcher; bonus bounded by `_ARTIST_SPAN`. `transition_score` returns higher with a matching preferred artist at intensity>0, identical to baseline at intensity 0.
- Unit (planner): with `artist_intensity>0` a preferred artist's tracks are favored but the candidate pool is NOT filtered — a non-preferred track is still selectable (assert pool size unchanged / a non-preferred track can win when it scores higher).
- API (tests/api/test_sets_api.py or build test): `POST /build` accepts `preferred_artists` + `artist_intensity` and completes a build (smoke).
- E2E (manual): build dialog → add a featured artist + intensity → build → more of that artist appears, set is not all-that-artist.
- Coverage: scoring term + matcher integration fully unit-tested; build request threading covered; frontend type-checked via svelte-check.

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
