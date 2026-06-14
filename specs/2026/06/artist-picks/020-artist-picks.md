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

### Task Outline
1. New `src/kiku/artists.py` — artist-token matcher (`artist_tokens`, `artist_matches`)
2. New `src/kiku/setbuilder/artist_picks.py` — `ArtistPick` dataclass + `rank_artist_picks()` best-gap ranker
3. Schemas — `ArtistPickItem` + `ArtistPicksResponse` in `api/schemas.py`
4. API endpoint — `GET /api/sets/{set_id}/artist-picks` in `routes/sets.py`
5. CLI — `kiku artist-picks <set> <artist>` in `cli.py`
6. Frontend types — `ArtistPick`, `ArtistPicksResponse` in `types/index.ts`
7. Frontend API client — `getArtistPicks()` in `api/sets.ts`
8. Frontend component — `AddFromArtistPanel.svelte`
9. Frontend mount — wire panel into `SetView.svelte`
10. Unit test — `tests/test_artists.py` (token matcher)
11. Unit test — `tests/test_artist_picks.py` (best-gap ranker)
12. API test — `tests/api/test_artist_picks_api.py`
13. Lint / type-check (py_compile + svelte-check + pytest)
14. Commit changed files

### Files
- `src/kiku/artists.py` (NEW)
  - `artist_tokens(s)`, `artist_matches(requested, candidate_artist)`; word-boundary separators.
- `src/kiku/setbuilder/artist_picks.py` (NEW)
  - `ArtistPick` dataclass; `rank_artist_picks(session, set_id, artist, n, weights, discovery_density)`; reuses `score_replacement` (scoring.py:479) + `parse_energy_json/parse_energy_string` (constraints.py:49,65).
- `src/kiku/api/schemas.py`
  - Add `ArtistPickItem` + `ArtistPicksResponse` after `SuggestNextResponse` (L308).
- `src/kiku/api/routes/sets.py`
  - Import new schemas (L15 block); add `GET /{set_id}/artist-picks` endpoint at end (after L1046) reusing `_track_response` (L897).
- `src/kiku/cli.py`
  - Add `artist-picks` command after `suggest-next` (L420).
- `frontend/src/lib/types/index.ts`
  - Add `ArtistPick` + `ArtistPicksResponse` interfaces after `ReplacementSuggestionsResponse` (L540).
- `frontend/src/lib/api/sets.ts`
  - Add `ArtistPicksResponse` import (L1 block); add `getArtistPicks()` after `getReplacements` (L189).
- `frontend/src/lib/components/set/AddFromArtistPanel.svelte` (NEW)
  - Typeahead (single artist) + ranked pick cards + insert via `addTrackToSet`.
- `frontend/src/lib/components/set/SetView.svelte`
  - Import + state + "Add from an artist" button (L289 area) + panel mount (L402 area).
- `tests/test_artists.py` (NEW) — token matcher unit tests.
- `tests/test_artist_picks.py` (NEW) — best-gap ranker unit tests.
- `tests/api/test_artist_picks_api.py` (NEW) — endpoint integration tests.

### Tasks

#### Task 1 — artists.py: artist-token matcher
Tools: editor
Create `src/kiku/artists.py`.
Diff:
````diff
--- /dev/null
+++ b/src/kiku/artists.py
@@
+"""Artist-string token matcher.
+
+Splits a plain ``artist`` string into normalized whole-word tokens so a
+requested artist matches collaborations (e.g. "Bicep" matches
+"Bicep & Chroma" and "X feat. Bicep") but NOT substrings ("Bicepz", "Maxx").
+
+Shared utility: Phases B (build preferences) and C (multi-anchor pins) reuse it.
+"""
+
+from __future__ import annotations
+
+import re
+
+# Word-boundary separators. Punctuation separators are literal; word
+# separators (x / vs / with) match only as whole words so "Maxx"/"sixx"
+# are not split. ``feat.``/``ft.`` tolerate the optional trailing dot.
+_SEPARATOR_RE = re.compile(
+    r"\s*(?:,|&|\+|/|\bfeat\.?\b|\bft\.?\b|\bvs\.?\b|\bx\b|\bwith\b)\s*",
+    re.IGNORECASE,
+)
+
+
+def artist_tokens(s: str | None) -> set[str]:
+    """Split an artist string into normalized whole-name tokens.
+
+    Lowercased, whitespace-trimmed, empties dropped. Returns an empty set
+    for None/blank input.
+    """
+    if not s:
+        return set()
+    parts = _SEPARATOR_RE.split(s)
+    return {p.strip().lower() for p in parts if p and p.strip()}
+
+
+def artist_matches(requested: str | None, candidate_artist: str | None) -> bool:
+    """True when the requested artist is one of the candidate's tokens.
+
+    Both sides are tokenized; a match needs the (single) requested token to
+    be present among the candidate's tokens. Case- and whitespace-insensitive.
+    """
+    req = artist_tokens(requested)
+    if not req:
+        return False
+    cand = artist_tokens(candidate_artist)
+    return bool(req & cand)
````

Verification:
- `.venv/bin/python -c "from kiku.artists import artist_matches; assert artist_matches('Bicep','Bicep & Chroma'); assert artist_matches('Bicep','X feat. Bicep'); assert not artist_matches('Bicep','Bicepz'); assert not artist_matches('Maxx','Maxx'.replace('Maxx','Maxx')) is False"` — sanity (full cases in Task 10).

#### Task 2 — artist_picks.py: ArtistPick dataclass + best-gap ranker
Tools: editor
Create `src/kiku/setbuilder/artist_picks.py`. Uses `score_replacement` (scoring.py:479) for both-neighbor insertion scoring, mirrors energy-target logic from routes/sets.py:963-979.
Diff:
````diff
--- /dev/null
+++ b/src/kiku/setbuilder/artist_picks.py
@@
+"""Best-fit-anywhere artist pick ranker.
+
+Given an open set and an artist name, rank that artist's owned tracks
+(collaborations included) by the best insertion gap in the set. Reuses
+``score_replacement`` (two-neighbor insertion scoring) — no new scorer.
+"""
+
+from __future__ import annotations
+
+import json
+from dataclasses import dataclass
+
+from sqlalchemy.orm import Session
+
+from kiku.artists import artist_matches
+from kiku.db.models import Set, Track
+from kiku.setbuilder.constraints import parse_energy_json, parse_energy_string
+from kiku.setbuilder.scoring import score_replacement
+
+
+@dataclass
+class ArtistPick:
+    """One ranked artist pick with its best insertion slot."""
+
+    track: Track
+    position: int  # suggested insertion gap (0..len(set))
+    score: float  # best-gap combined score
+    breakdown: dict  # breakdown dict at the chosen gap (score_replacement shape)
+    reason: str  # mentor-voice teaching line
+
+
+def _energy_target_at_gap(profile, gap: int, gap_count: int, duration_min: float) -> float:
+    """Energy target for an insertion at ``gap`` from its positional fraction."""
+    if profile is None:
+        return 0.5
+    fraction = gap / max(gap_count, 1)
+    elapsed = fraction * (duration_min or 120)
+    return profile.target_energy_at(elapsed)
+
+
+def _reason_for(breakdown: dict, position: int) -> str:
+    """Build a warm teaching line from the dominant breakdown dimension.
+
+    Mirrors the phrasing style of analysis/teaching.py. Never blames.
+    """
+    pos_label = f"fits at position {position + 1}"
+    if not breakdown:
+        return f"{pos_label} — a fresh face for this stretch of the set."
+    dims = {
+        "harmonic": breakdown.get("harmonic", 0.0),
+        "energy_fit": breakdown.get("energy_fit", 0.0),
+        "bpm_compat": breakdown.get("bpm_compat", 0.0),
+        "genre_coherence": breakdown.get("genre_coherence", 0.0),
+    }
+    dominant = max(dims, key=lambda k: dims[k])
+    phrases = {
+        "harmonic": "the keys lock in cleanly here",
+        "energy_fit": "it sits right on the energy you're shaping",
+        "bpm_compat": "the tempo glues straight in",
+        "genre_coherence": "it keeps the genre thread running",
+    }
+    return f"{pos_label} — {phrases[dominant]}."
+
+
+def rank_artist_picks(
+    session: Session,
+    set_id: int,
+    artist: str,
+    n: int = 5,
+    weights: dict[str, float] | None = None,
+    discovery_density: float = 0.0,
+) -> list[ArtistPick]:
+    """Rank an artist's owned tracks by their best insertion gap in the set.
+
+    Returns up to ``n`` picks ordered by best-gap score (descending). Returns
+    an empty list when the set is missing or the artist owns nothing new.
+    """
+    s = session.get(Set, set_id)
+    if not s:
+        return []
+
+    ordered = sorted(s.tracks, key=lambda st: st.position)
+    set_track_ids = {st.track_id for st in ordered}
+    ordered_tracks = [st.track for st in ordered]
+
+    # Parse energy profile (JSON first, then string fallback).
+    profile = None
+    if s.energy_profile:
+        try:
+            try:
+                profile = parse_energy_json(s.energy_profile)
+            except (json.JSONDecodeError, KeyError):
+                profile = parse_energy_string(s.energy_profile)
+        except Exception:
+            profile = None
+
+    duration_min = s.duration_min or 120
+    gap_count = len(ordered_tracks)
+
+    # Candidate pool: ilike prefilter at the DB, then exact token gate.
+    prefilter = (
+        session.query(Track)
+        .filter(Track.artist.isnot(None), Track.artist.ilike(f"%{artist}%"))
+        .all()
+    )
+    candidates = [
+        t
+        for t in prefilter
+        if t.id not in set_track_ids and artist_matches(artist, t.artist)
+    ]
+
+    picks: list[ArtistPick] = []
+    for cand in candidates:
+        best_score = float("-inf")
+        best_gap = 0
+        best_breakdown: dict = {}
+        # Gaps 0..gap_count: before first track, between, after last.
+        for gap in range(gap_count + 1):
+            prev_track = ordered_tracks[gap - 1] if gap > 0 else None
+            next_track = ordered_tracks[gap] if gap < gap_count else None
+            target_energy = _energy_target_at_gap(profile, gap, gap_count, duration_min)
+            combined, incoming, outgoing = score_replacement(
+                cand, prev_track, next_track, target_energy=target_energy,
+                weights=weights, discovery_density=discovery_density,
+            )
+            if combined > best_score:
+                best_score = combined
+                best_gap = gap
+                # Prefer the incoming (prev→cand) breakdown; fall back to outgoing.
+                best_breakdown = incoming or outgoing or {}
+        picks.append(ArtistPick(
+            track=cand,
+            position=best_gap,
+            score=round(best_score, 3),
+            breakdown=best_breakdown,
+            reason=_reason_for(best_breakdown, best_gap),
+        ))
+
+    picks.sort(key=lambda p: p.score, reverse=True)
+    return picks[:n]
````

Verification:
- `.venv/bin/python -m py_compile src/kiku/setbuilder/artist_picks.py` (full behavior in Task 11).

#### Task 3 — schemas.py: ArtistPickItem + ArtistPicksResponse
Tools: editor
Reuses existing `TrackResponse` (L25) and `TransitionScoreBreakdown` (L199). `breakdown` is optional because end-gap single-neighbor breakdowns may be empty.
Diff:
````diff
--- a/src/kiku/api/schemas.py
+++ b/src/kiku/api/schemas.py
@@
 class SuggestNextResponse(BaseModel):
     source_track_id: int
     suggestions: list[SuggestNextItem]
+
+
+class ArtistPickItem(BaseModel):
+    track: TrackResponse
+    position: int
+    score: float
+    breakdown: TransitionScoreBreakdown | None = None
+    reason: str
+
+
+class ArtistPicksResponse(BaseModel):
+    set_id: int
+    artist: str
+    picks: list[ArtistPickItem]
````

Verification:
- `.venv/bin/python -c "from kiku.api.schemas import ArtistPicksResponse, ArtistPickItem"`.

#### Task 4 — sets.py: GET /{set_id}/artist-picks endpoint
Tools: editor
Two edits. Edit 4a adds the schema imports; Edit 4b appends the endpoint. `breakdown` from `score_replacement` carries `discovery_label`/`set_appearances` extras that `TransitionScoreBreakdown` ignores (model is non-strict) — only the matching keys are read.

Edit 4a — imports:
````diff
--- a/src/kiku/api/routes/sets.py
+++ b/src/kiku/api/routes/sets.py
@@
 from kiku.api.schemas import (
     CueCreateRequest,
     CueResponse,
+    ArtistPickItem,
+    ArtistPicksResponse,
     ImportResultResponse,
     SetAnalysisResponse,
     ReplaceTrackRequest,
````

Edit 4b — append endpoint at end of file (after L1046, the final `return [_set_track_response(st) for st in tracks]` of `replace_track`):
````diff
--- a/src/kiku/api/routes/sets.py
+++ b/src/kiku/api/routes/sets.py
@@
     return [_set_track_response(st) for st in tracks]
+
+
+@router.get("/{set_id}/artist-picks", response_model=ArtistPicksResponse)
+def get_artist_picks(
+    set_id: int,
+    artist: str,
+    n: int = 5,
+    discovery_density: float = 0.0,
+    db: Session = Depends(get_db),
+):
+    """Rank an artist's owned tracks by their best fit anywhere in the set.
+
+    Library excavation only — every pick is a track the DJ already owns.
+    Returns an empty pick list (200) when the artist owns nothing new here.
+    """
+    from kiku.setbuilder.artist_picks import rank_artist_picks
+
+    s = db.get(Set, set_id)
+    if not s:
+        raise HTTPException(status_code=404, detail="Set not found")
+
+    ranked = rank_artist_picks(
+        db, set_id, artist, n=n, discovery_density=discovery_density,
+    )
+
+    picks = [
+        ArtistPickItem(
+            track=_track_response(p.track),
+            position=p.position,
+            score=p.score,
+            breakdown=TransitionScoreBreakdown(**p.breakdown) if p.breakdown else None,
+            reason=p.reason,
+        )
+        for p in ranked
+    ]
+    return ArtistPicksResponse(set_id=set_id, artist=artist, picks=picks)
````

Verification:
- `.venv/bin/python -m py_compile src/kiku/api/routes/sets.py`.
- Note: `TransitionScoreBreakdown(**p.breakdown)` — `p.breakdown` keys (`harmonic, energy_fit, bpm_compat, genre_coherence, track_quality, total, discovery_label, set_appearances`) are a superset of the model fields; pydantic ignores `vibe` only if present, but `score_replacement` breakdown also includes `vibe` key. Guard: pass only known keys — see Edit 4c.

Edit 4c — filter breakdown keys to the model's fields (the `score_replacement` breakdown includes `vibe` which `TransitionScoreBreakdown` does not declare and would reject under pydantic's default `extra='ignore'` — pydantic v2 ignores extras by default, but be explicit and safe):
````diff
--- a/src/kiku/api/routes/sets.py
+++ b/src/kiku/api/routes/sets.py
@@
+    _BD_FIELDS = {
+        "harmonic", "energy_fit", "bpm_compat", "genre_coherence",
+        "track_quality", "total", "discovery_label", "set_appearances",
+    }
     picks = [
         ArtistPickItem(
             track=_track_response(p.track),
             position=p.position,
             score=p.score,
-            breakdown=TransitionScoreBreakdown(**p.breakdown) if p.breakdown else None,
+            breakdown=(
+                TransitionScoreBreakdown(
+                    **{k: v for k, v in p.breakdown.items() if k in _BD_FIELDS}
+                )
+                if p.breakdown
+                else None
+            ),
             reason=p.reason,
         )
         for p in ranked
     ]
````

Verification:
- Hit endpoint in Task 12; confirm 200 with picks, 404 missing set, empty list when no new tracks.

#### Task 5 — cli.py: kiku artist-picks command
Tools: editor
Append after `suggest_next` (ends L420). Set id-or-name resolution per cli.py:634-638. Warm, never-blame copy.
Diff:
````diff
--- a/src/kiku/cli.py
+++ b/src/kiku/cli.py
@@
     console.print(table)
+
+
+@cli.command("artist-picks")
+@click.argument("set_name_or_id")
+@click.argument("artist")
+@click.option("-n", "--num", default=5, help="Number of picks")
+def artist_picks_cmd(set_name_or_id: str, artist: str, num: int):
+    """Pull an artist's best-fitting owned tracks into a set you're building.
+
+    Ranks tracks you already own by that artist (collaborations included)
+    by where they fit best across the whole set.
+    """
+    from kiku.db.models import Set, get_session
+    from kiku.setbuilder.artist_picks import rank_artist_picks
+
+    session = get_session()
+
+    # Resolve set by ID or name
+    try:
+        set_id = int(set_name_or_id)
+        s = session.get(Set, set_id)
+    except ValueError:
+        s = session.query(Set).filter(Set.name.ilike(f"%{set_name_or_id}%")).first()
+
+    if not s:
+        console.print(f"[yellow]Couldn't find set '{set_name_or_id}'.[/]")
+        return
+
+    picks = rank_artist_picks(session, s.id, artist, n=num)
+    if not picks:
+        console.print(
+            f"[yellow]Nothing new from '{artist}' to add to '{s.name}' — "
+            f"either you don't own tracks by them, or they're all already in the set.[/]"
+        )
+        return
+
+    table = Table(title=f"{artist} — best fits in '{s.name}'")
+    table.add_column("#", justify="right", style="dim")
+    table.add_column("Title", style="cyan")
+    table.add_column("Artist")
+    table.add_column("Placement", style="magenta")
+    table.add_column("Score", justify="right", style="green")
+    table.add_column("Why", style="dim")
+
+    for i, p in enumerate(picks, 1):
+        table.add_row(
+            str(i),
+            p.track.title or "?",
+            p.track.artist or "?",
+            f"→ pos {p.position + 1}",
+            f"{p.score:.3f}",
+            p.reason,
+        )
+
+    console.print(table)
````

Verification:
- `.venv/bin/python -m py_compile src/kiku/cli.py`.
- `source .venv/bin/activate && kiku artist-picks <set> <artist>` prints a ranked Table or a warm empty message.

#### Task 6 — types/index.ts: ArtistPick + ArtistPicksResponse
Tools: editor
Add after `ReplacementSuggestionsResponse` (L537-540). Reuses `Track` (L7) + `TransitionScoreBreakdown` (L147).
Diff:
````diff
--- a/frontend/src/lib/types/index.ts
+++ b/frontend/src/lib/types/index.ts
@@
 export interface ReplacementSuggestionsResponse {
 	context: ReplacementContext;
 	candidates: ReplacementCandidate[];
 }
+
+export interface ArtistPick {
+	track: Track;
+	position: number;
+	score: number;
+	breakdown: TransitionScoreBreakdown | null;
+	reason: string;
+}
+
+export interface ArtistPicksResponse {
+	set_id: number;
+	artist: string;
+	picks: ArtistPick[];
+}
````

Verification:
- Covered by svelte-check (Task 13).

#### Task 7 — api/sets.ts: getArtistPicks client
Tools: editor
Two edits: import the type, add the function after `getReplacements` (ends L189).

Edit 7a — import:
````diff
--- a/frontend/src/lib/api/sets.ts
+++ b/frontend/src/lib/api/sets.ts
@@
 import type {
+	ArtistPicksResponse,
 	Cue,
 	DJSet,
 	ImportResult,
````

Edit 7b — function:
````diff
--- a/frontend/src/lib/api/sets.ts
+++ b/frontend/src/lib/api/sets.ts
@@
 	return fetchJson<ReplacementSuggestionsResponse>(
 		`/api/sets/${setId}/tracks/${position}/replacements?${qs}`
 	);
 }
+
+export async function getArtistPicks(
+	setId: number,
+	artist: string,
+	n = 5
+): Promise<ArtistPicksResponse> {
+	const qs = new URLSearchParams({ artist, n: String(n) });
+	return fetchJson<ArtistPicksResponse>(`/api/sets/${setId}/artist-picks?${qs}`);
+}
````

Verification:
- Covered by svelte-check (Task 13).

#### Task 8 — AddFromArtistPanel.svelte (NEW)
Tools: editor
Reuses `Typeahead` (single artist via local 1-element binding), `autocompleteArtists`, `getArtistPicks`, `addTrackToSet`. On insert, calls `onInserted` so SetView reloads. Voice: "set", warm, never blame; no smart/powerful/seamless/magic.
Diff:
````diff
--- /dev/null
+++ b/frontend/src/lib/components/set/AddFromArtistPanel.svelte
@@
+<script lang="ts">
+	import type { ArtistPick } from '$lib/types';
+	import { getArtistPicks, addTrackToSet } from '$lib/api/sets';
+	import { autocompleteArtists } from '$lib/api/tracks';
+	import Typeahead from '$lib/components/library/Typeahead.svelte';
+
+	let {
+		setId,
+		onInserted,
+		onclose,
+	}: {
+		setId: number;
+		onInserted: () => void;
+		onclose: () => void;
+	} = $props();
+
+	let selectedArtists = $state<string[]>([]);
+	let artist = $derived(selectedArtists[0] ?? '');
+	let picks = $state<ArtistPick[]>([]);
+	let loading = $state(false);
+	let searched = $state(false);
+	let error = $state<string | null>(null);
+	let insertingId = $state<number | null>(null);
+
+	async function loadPicks() {
+		if (!artist) return;
+		loading = true;
+		searched = true;
+		error = null;
+		try {
+			const res = await getArtistPicks(setId, artist, 5);
+			picks = res.picks;
+		} catch (e) {
+			error = e instanceof Error ? e.message : 'Something went wrong reading your library.';
+			picks = [];
+		} finally {
+			loading = false;
+		}
+	}
+
+	// Re-run when the chosen artist changes.
+	$effect(() => {
+		if (artist) loadPicks();
+	});
+
+	async function insertPick(pick: ArtistPick) {
+		insertingId = pick.track.id;
+		try {
+			await addTrackToSet(setId, pick.track.id, pick.position);
+			onInserted();
+			onclose();
+		} catch (e) {
+			error = e instanceof Error ? e.message : "Couldn't add that track.";
+		} finally {
+			insertingId = null;
+		}
+	}
+</script>
+
+<div class="artist-panel">
+	<div class="panel-header">
+		<h3>Add from an artist</h3>
+		<button class="close-btn" onclick={onclose} aria-label="Close">×</button>
+	</div>
+	<p class="hint">Pull a track you already own — ranked by where it fits this set.</p>
+
+	<Typeahead
+		placeholder="Name an artist…"
+		bind:selected={selectedArtists}
+		fetchSuggestions={(q) => autocompleteArtists(q, 10)}
+	/>
+
+	{#if loading}
+		<div class="status">Reading your library…</div>
+	{:else if error}
+		<div class="status error">{error}</div>
+	{:else if searched && artist && picks.length === 0}
+		<div class="status">
+			Nothing new from {artist} here — you may already have their tracks in this set.
+		</div>
+	{:else}
+		<ul class="picks">
+			{#each picks as pick (pick.track.id)}
+				<li class="pick-card">
+					<div class="pick-main">
+						<div class="pick-title">{pick.track.title ?? 'Untitled'}</div>
+						<div class="pick-artist">{pick.track.artist ?? ''}</div>
+						<div class="pick-reason">{pick.reason}</div>
+						{#if pick.breakdown}
+							<div class="pick-breakdown">
+								<span>key {Math.round(pick.breakdown.harmonic * 100)}</span>
+								<span>energy {Math.round(pick.breakdown.energy_fit * 100)}</span>
+								<span>bpm {Math.round(pick.breakdown.bpm_compat * 100)}</span>
+								<span>genre {Math.round(pick.breakdown.genre_coherence * 100)}</span>
+							</div>
+						{/if}
+					</div>
+					<div class="pick-side">
+						<div class="pick-score">{Math.round(pick.score * 100)}</div>
+						<button
+							class="insert-btn"
+							onclick={() => insertPick(pick)}
+							disabled={insertingId === pick.track.id}
+						>
+							{insertingId === pick.track.id ? 'Adding…' : `Add at pos ${pick.position + 1}`}
+						</button>
+					</div>
+				</li>
+			{/each}
+		</ul>
+	{/if}
+</div>
+
+<style>
+	.artist-panel {
+		position: absolute;
+		top: 56px;
+		right: 16px;
+		z-index: 30;
+		width: 380px;
+		max-height: 70vh;
+		overflow-y: auto;
+		background: var(--surface, #1b1c20);
+		border: 1px solid var(--border, #2a2b30);
+		border-radius: 10px;
+		padding: 14px;
+		box-shadow: 0 8px 28px rgba(0, 0, 0, 0.4);
+	}
+	.panel-header {
+		display: flex;
+		align-items: center;
+		justify-content: space-between;
+	}
+	.panel-header h3 {
+		margin: 0;
+		font-size: 15px;
+	}
+	.close-btn {
+		background: none;
+		border: none;
+		color: var(--text-secondary, #9a9b9f);
+		font-size: 20px;
+		cursor: pointer;
+		line-height: 1;
+	}
+	.hint {
+		margin: 4px 0 10px;
+		font-size: 12px;
+		color: var(--text-secondary, #9a9b9f);
+	}
+	.status {
+		margin-top: 12px;
+		font-size: 13px;
+		color: var(--text-secondary, #9a9b9f);
+	}
+	.status.error {
+		color: var(--danger, #e06c75);
+	}
+	.picks {
+		list-style: none;
+		margin: 12px 0 0;
+		padding: 0;
+		display: flex;
+		flex-direction: column;
+		gap: 8px;
+	}
+	.pick-card {
+		display: flex;
+		justify-content: space-between;
+		gap: 10px;
+		padding: 10px;
+		border: 1px solid var(--border, #2a2b30);
+		border-radius: 8px;
+	}
+	.pick-title {
+		font-weight: 600;
+		font-size: 13px;
+	}
+	.pick-artist {
+		font-size: 12px;
+		color: var(--text-secondary, #9a9b9f);
+	}
+	.pick-reason {
+		margin-top: 4px;
+		font-size: 12px;
+		color: var(--text-tertiary, #7a7b82);
+	}
+	.pick-breakdown {
+		margin-top: 6px;
+		display: flex;
+		flex-wrap: wrap;
+		gap: 6px;
+		font-size: 11px;
+		color: var(--text-tertiary, #7a7b82);
+	}
+	.pick-side {
+		display: flex;
+		flex-direction: column;
+		align-items: flex-end;
+		gap: 8px;
+	}
+	.pick-score {
+		font-size: 18px;
+		font-weight: 700;
+		color: var(--accent, #7aa2f7);
+	}
+	.insert-btn {
+		font-size: 12px;
+		padding: 5px 9px;
+		border: 1px solid var(--accent, #7aa2f7);
+		border-radius: 6px;
+		background: transparent;
+		color: var(--accent, #7aa2f7);
+		cursor: pointer;
+		white-space: nowrap;
+	}
+	.insert-btn:disabled {
+		opacity: 0.5;
+		cursor: default;
+	}
+</style>
````

Verification:
- Covered by svelte-check (Task 13).

#### Task 9 — SetView.svelte: mount AddFromArtistPanel
Tools: editor
Three edits: import, state flag + button, panel mount.

Edit 9a — import (after FillReorderDialog import, L10):
````diff
--- a/frontend/src/lib/components/set/SetView.svelte
+++ b/frontend/src/lib/components/set/SetView.svelte
@@
 	import FillReorderDialog from './FillReorderDialog.svelte';
+	import AddFromArtistPanel from './AddFromArtistPanel.svelte';
````

Edit 9b — state flag (after `let showAssist = $state(false);`, L76):
````diff
--- a/frontend/src/lib/components/set/SetView.svelte
+++ b/frontend/src/lib/components/set/SetView.svelte
@@
 	let showAssist = $state(false);
+	let showArtistPicks = $state(false);
````

Edit 9c — toggle button (after the Assist button block, L289-293):
````diff
--- a/frontend/src/lib/components/set/SetView.svelte
+++ b/frontend/src/lib/components/set/SetView.svelte
@@
 			{#if waveformTracks.length >= 3}
 				<button class="assist-btn" onclick={() => { showAssist = true; }}>
 					Assist
 				</button>
 			{/if}
+			<button class="assist-btn" onclick={() => { showArtistPicks = !showArtistPicks; }}>
+				Add from an artist
+			</button>
````

Edit 9d — panel mount (after the `{#if showEnergyReview}` block, before the closing `</div>` at L413):
````diff
--- a/frontend/src/lib/components/set/SetView.svelte
+++ b/frontend/src/lib/components/set/SetView.svelte
@@
 			}}
 		/>
 	{/if}
+
+	{#if showArtistPicks && selectedSet}
+		<AddFromArtistPanel
+			setId={selectedSet.id}
+			onInserted={handleTracksChanged}
+			onclose={() => { showArtistPicks = false; }}
+		/>
+	{/if}
 </div>
````

Verification:
- Covered by svelte-check (Task 13). Manual E2E: button opens panel, type artist, pick card → inserts at suggested position, timeline reloads.

#### Task 10 — tests/test_artists.py (NEW): token matcher
Tools: editor
Diff:
````diff
--- /dev/null
+++ b/tests/test_artists.py
@@
+"""Unit tests for the artist-token matcher."""
+
+from __future__ import annotations
+
+from kiku.artists import artist_matches, artist_tokens
+
+
+def test_tokens_basic():
+    assert artist_tokens("Bicep & Chroma") == {"bicep", "chroma"}
+    assert artist_tokens("X feat. Bicep") == {"x", "bicep"}
+    assert artist_tokens("Bicep, Other") == {"bicep", "other"}
+    assert artist_tokens("A vs B") == {"a", "b"}
+    assert artist_tokens("A with B") == {"a", "b"}
+    assert artist_tokens("A ft. B") == {"a", "b"}
+    assert artist_tokens("A + B") == {"a", "b"}
+
+
+def test_tokens_word_boundary():
+    # "x"/"with"/"vs" only split as whole words, not substrings.
+    assert artist_tokens("Maxx") == {"maxx"}
+    assert artist_tokens("Sixx") == {"sixx"}
+
+
+def test_tokens_case_whitespace():
+    assert artist_tokens("  BICEP  &  chroma ") == {"bicep", "chroma"}
+
+
+def test_tokens_empty_none():
+    assert artist_tokens(None) == set()
+    assert artist_tokens("") == set()
+    assert artist_tokens("   ") == set()
+
+
+def test_matches_collaborations():
+    assert artist_matches("Bicep", "Bicep & Chroma")
+    assert artist_matches("Bicep", "X feat. Bicep")
+    assert artist_matches("Bicep", "Bicep, Other")
+    assert artist_matches("Chroma", "Bicep & Chroma")
+
+
+def test_matches_near_miss():
+    assert not artist_matches("Bicep", "Bicepz")
+    assert not artist_matches("Maxx", "Max")
+    assert not artist_matches("Bicep", "Other Artist")
+
+
+def test_matches_case_whitespace():
+    assert artist_matches("  bicep ", "Bicep & Chroma")
+
+
+def test_matches_empty_none():
+    assert not artist_matches(None, "Bicep")
+    assert not artist_matches("", "Bicep")
+    assert not artist_matches("Bicep", None)
+    assert not artist_matches("Bicep", "")
````

Verification:
- `source .venv/bin/activate && python -m pytest tests/test_artists.py -q`.

#### Task 11 — tests/test_artist_picks.py (NEW): best-gap ranker
Tools: editor
Uses MagicMock tracks (style of tests/test_set_analysis.py `_mock_track`) + a fake session. The ranker queries `session.query(Track).filter(...).all()` for the candidate pool and `session.get(Set, set_id)` for the set — both stubbed. Plants the best gap via a harmonic-friendly key at one slot.
Diff:
````diff
--- /dev/null
+++ b/tests/test_artist_picks.py
@@
+"""Unit tests for the best-gap artist pick ranker."""
+
+from __future__ import annotations
+
+from unittest.mock import MagicMock
+
+from kiku.setbuilder.artist_picks import rank_artist_picks
+
+
+def _track(track_id, artist, key="8A", bpm=124.0, genre="techno"):
+    t = MagicMock()
+    t.id = track_id
+    t.artist = artist
+    t.title = f"Track {track_id}"
+    t.key = key
+    t.bpm = bpm
+    t.dir_genre = genre
+    t.rb_genre = genre
+    t.dir_energy = "mid"
+    t.energy_predicted = None
+    t.rating = 3
+    t.play_count = 0
+    t.kiku_play_count = 0
+    return t
+
+
+def _set_track(track, position):
+    st = MagicMock()
+    st.track = track
+    st.track_id = track.id
+    st.position = position
+    return st
+
+
+def _make_session(set_obj, pool):
+    """Fake session: .get(Set, id) -> set_obj; query(Track)...all() -> pool."""
+    session = MagicMock()
+    session.get.return_value = set_obj
+    query = MagicMock()
+    query.filter.return_value = query
+    query.all.return_value = pool
+    session.query.return_value = query
+    return session
+
+
+def _make_set(set_tracks, energy_profile=None, duration_min=60):
+    s = MagicMock()
+    s.tracks = set_tracks
+    s.energy_profile = energy_profile
+    s.duration_min = duration_min
+    return s
+
+
+def test_ranks_and_caps_n():
+    in_set = [_track(1, "Resident"), _track(2, "Resident"), _track(3, "Resident")]
+    set_tracks = [_set_track(t, i) for i, t in enumerate(in_set)]
+    s = _make_set(set_tracks)
+    pool = [_track(10 + i, "Bicep") for i in range(8)]
+    session = _make_session(s, pool)
+    picks = rank_artist_picks(session, 1, "Bicep", n=3)
+    assert len(picks) == 3
+    # Sorted descending by score.
+    assert picks[0].score >= picks[1].score >= picks[2].score
+    # Each pick reports a valid gap (0..len(set)).
+    for p in picks:
+        assert 0 <= p.position <= len(in_set)
+        assert p.reason
+
+
+def test_excludes_in_set_tracks():
+    shared = _track(5, "Bicep")
+    in_set = [_track(1, "Resident"), shared, _track(3, "Resident")]
+    set_tracks = [_set_track(t, i) for i, t in enumerate(in_set)]
+    s = _make_set(set_tracks)
+    # Pool returns the in-set Bicep track plus a new one.
+    pool = [shared, _track(20, "Bicep")]
+    session = _make_session(s, pool)
+    picks = rank_artist_picks(session, 1, "Bicep")
+    ids = {p.track.id for p in picks}
+    assert 5 not in ids
+    assert 20 in ids
+
+
+def test_empty_pool_returns_empty():
+    in_set = [_track(1, "Resident"), _track(2, "Resident")]
+    set_tracks = [_set_track(t, i) for i, t in enumerate(in_set)]
+    s = _make_set(set_tracks)
+    session = _make_session(s, [])
+    assert rank_artist_picks(session, 1, "Bicep") == []
+
+
+def test_missing_set_returns_empty():
+    session = _make_session(None, [])
+    assert rank_artist_picks(session, 999, "Bicep") == []
+
+
+def test_end_gap_single_neighbor():
+    # Single-track set → gaps 0 (before) and 1 (after), each one-neighbor.
+    in_set = [_track(1, "Resident")]
+    set_tracks = [_set_track(in_set[0], 0)]
+    s = _make_set(set_tracks)
+    pool = [_track(10, "Bicep")]
+    session = _make_session(s, pool)
+    picks = rank_artist_picks(session, 1, "Bicep")
+    assert len(picks) == 1
+    assert picks[0].position in (0, 1)
+
+
+def test_token_gate_filters_pool():
+    # ilike prefilter could return a near-miss; token gate must drop it.
+    in_set = [_track(1, "Resident")]
+    set_tracks = [_set_track(in_set[0], 0)]
+    s = _make_set(set_tracks)
+    pool = [_track(10, "Bicepz"), _track(11, "Bicep & Chroma")]
+    session = _make_session(s, pool)
+    picks = rank_artist_picks(session, 1, "Bicep")
+    ids = {p.track.id for p in picks}
+    assert ids == {11}
````

Verification:
- `source .venv/bin/activate && python -m pytest tests/test_artist_picks.py -q`.

#### Task 12 — tests/api/test_artist_picks_api.py (NEW): endpoint
Tools: editor
Uses `db_session` + `client` from tests/api/conftest.py. Seed set id=1 holds track ids 1-5; artists are `"Artist {(i%5)+1}"`. "Artist 2" owns tracks 1,6,11,16 — track 1 is in the set, so 6/11/16 are new.
Diff:
````diff
--- /dev/null
+++ b/tests/api/test_artist_picks_api.py
@@
+"""Integration tests for GET /api/sets/{set_id}/artist-picks."""
+
+from __future__ import annotations
+
+
+def test_artist_picks_ranked(client):
+    # "Artist 2" owns tracks 1,6,11,16; track 1 is in set 1, so 6/11/16 are new.
+    resp = client.get("/api/sets/1/artist-picks", params={"artist": "Artist 2"})
+    assert resp.status_code == 200
+    body = resp.json()
+    assert body["set_id"] == 1
+    assert body["artist"] == "Artist 2"
+    picks = body["picks"]
+    assert len(picks) >= 1
+    # No in-set track leaks in (track 1 belongs to Artist 2 but is in the set).
+    ids = {p["track"]["id"] for p in picks}
+    assert 1 not in ids
+    # Every pick carries a placement + reason (Show the Why).
+    for p in picks:
+        assert isinstance(p["position"], int)
+        assert p["reason"]
+    # Ranked descending.
+    scores = [p["score"] for p in picks]
+    assert scores == sorted(scores, reverse=True)
+
+
+def test_artist_picks_n_cap(client):
+    resp = client.get(
+        "/api/sets/1/artist-picks", params={"artist": "Artist 2", "n": 2}
+    )
+    assert resp.status_code == 200
+    assert len(resp.json()["picks"]) <= 2
+
+
+def test_artist_picks_missing_set_404(client):
+    resp = client.get("/api/sets/9999/artist-picks", params={"artist": "Artist 2"})
+    assert resp.status_code == 404
+
+
+def test_artist_picks_no_new_tracks_empty(client):
+    # Unknown artist owns nothing → 200 with empty picks (warm, not an error).
+    resp = client.get(
+        "/api/sets/1/artist-picks", params={"artist": "Nonexistent Artist"}
+    )
+    assert resp.status_code == 200
+    assert resp.json()["picks"] == []
````

Verification:
- `source .venv/bin/activate && python -m pytest tests/api/test_artist_picks_api.py -q`.

#### Task 13 — Lint / type-check (changed files)
Tools: shell
ruff is NOT installed — use `py_compile` for Python. Capture svelte-check baseline (currently 0 errors, 4 warnings) — only NEW errors are failures.
Commands:
- `source .venv/bin/activate && python -m py_compile src/kiku/artists.py src/kiku/setbuilder/artist_picks.py src/kiku/api/schemas.py src/kiku/api/routes/sets.py src/kiku/cli.py tests/test_artists.py tests/test_artist_picks.py tests/api/test_artist_picks_api.py`
- `cd /home/mantis/Development/mantis-dev/waveform-builer/frontend && npx svelte-check --tsconfig ./tsconfig.json 2>&1 | tail -3` (expect `0 ERRORS`; warnings unchanged from baseline of 4)
- `source .venv/bin/activate && python -m pytest tests/ -x -q` (full backend suite green)

Expectations:
- All `py_compile` succeed; svelte-check 0 errors; pytest all pass.

#### Task 14 — Commit changed files
Tools: git
Commit ONLY the files created/modified in Tasks 1-12 (leave untracked `trees/`). Never commit to main.
Commands:
- `cd /home/mantis/Development/mantis-dev/waveform-builer && git branch --show-current` (expect `artist-picks`; abort if `main`)
- `git add src/kiku/artists.py src/kiku/setbuilder/artist_picks.py src/kiku/api/schemas.py src/kiku/api/routes/sets.py src/kiku/cli.py frontend/src/lib/types/index.ts frontend/src/lib/api/sets.ts frontend/src/lib/components/set/AddFromArtistPanel.svelte frontend/src/lib/components/set/SetView.svelte tests/test_artists.py tests/test_artist_picks.py tests/api/test_artist_picks_api.py`
- Commit message:
  ```
  spec(020): IMPLEMENT - artist-picks best-fit excavation (matcher, ranker, API, CLI, UI)

  Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
  ```

### Validate

Each Human Section requirement → compliance note with line refs.

- **HLO: top 5 owned tracks ranked by fit, with where + why** (L7): `rank_artist_picks` ranks owned tracks by best-gap score, default `n=5`, each pick carries `position` + `reason` (Task 2); exposed via API/CLI/UI (Tasks 4,5,8).
- **HLO: collaborations included; library excavation only** (L7): candidate pool is `Track.artist.ilike` → `artist_matches` token gate over the DJ's own library — never external (Task 2, L? candidates block).
- **MLO: artist-token matcher, separators `,&feat.ft.x vs with +`, "Bicep"≠"Bicepz", case/ws** (L12): `_SEPARATOR_RE` covers all separators with word-boundaries for `x`/`vs`/`with`; lowercased+trimmed (Task 1); proven in Task 10.
- **MLO: best-fit-anywhere ranker, exclude in-set** (L13): per-gap loop 0..len calling `score_replacement`, keep best; `set_track_ids` exclusion (Task 2); proven Task 11.
- **MLO: API `GET /sets/{id}/artist-picks?artist=&n=5` with position+breakdown+teaching line** (L14): Task 4 endpoint returns `ArtistPicksResponse{picks:[{track,position,score,breakdown,reason}]}`.
- **MLO: CLI `kiku artist-picks <set> <artist>` with placement+reasons** (L15): Task 5 command, rich Table with `→ pos N` + Why column.
- **MLO: frontend artist typeahead + ranked cards + one-click insert at position** (L16): Task 8 `AddFromArtistPanel` reuses `Typeahead`+`autocompleteArtists`, cards show placement/why/breakdown, insert calls `addTrackToSet(setId, id, position)`; mounted Task 9.
- **MLO: unit tests for matcher + ranker, API test** (L17): Tasks 10,11,12.
- **DT: reuse suggest-next/scoring engine, position-aware energy, set_id exclusion** (L21-24): reuses `score_replacement` + `parse_energy_*` + `target_energy_at`; gap-fraction energy target (Task 2).
- **DT: both-neighbor insertion scoring, one neighbor at ends** (L33-39): gap loop passes `prev=ordered[g-1] or None`, `next=ordered[g] or None`; `score_replacement` already handles single-neighbor (Task 2).
- **DT: rank by best gap, top N default 5, exclude in-set** (L35-37): `picks.sort(... reverse=True)[:n]`, default `n=5`, exclusion set (Task 2).
- **DT: collaboration via token equality; standalone tested utility** (L42-45): `artist_matches` = requested token ∈ candidate tokens; `src/kiku/artists.py` standalone (Tasks 1,10).
- **DT: library-only, no new heavy deps** (L48-50): pool from local DB; only stdlib `re`/`dataclasses` added (Tasks 1,2).
- **DT: Show the Why — every pick carries reason + breakdown** (L51): `breakdown` + `reason` on every `ArtistPickItem`/card/Table row (Tasks 2,4,5,8).
- **DT: voice — "set" not "playlist", warm, never blame** (L52): CLI/UI copy uses "set", warm empty/error messages, no blame (Tasks 5,8); no banned words.
- **DT: empty/edge cases handled warmly** (L53): empty pool → 200 empty list + warm CLI/UI message; missing set → 404; short set still has end gaps (Tasks 2,4,5,8,11,12).
- **DT testing: matcher, ranker, endpoint** (L56-58): Tasks 10,11,12 cover collabs/near-miss/separators/case, best-gap/exclusion/end-gap/n-cap/empty, 200/404/empty/n-cap.
- **DT E2E manual acceptance** (L59): Task 9 verification notes the manual open-set → add-from-artist → lands-at-position flow.
- **Behavior: reuse machinery, build matcher as shared utility for Phases B/C** (L62-64): `score_replacement` reused (no new scorer); `artists.py` is standalone shared (Tasks 1,2).

## Plan Review
<!-- Filled if required to validate plan -->

## Implement

### TODO
1. New `src/kiku/artists.py` — artist-token matcher — Status: Done (adapted `_SEPARATOR_RE`: plan's `\bfeat\.?\b` left a stray ". " on tokens and `\bx\b` dropped a leading bare "X" artist; reworked to flush punctuation `,&+/` + whitespace-flanked word separators `feat/ft/vs/x/with` — all spec Task 10 cases pass)
2. New `src/kiku/setbuilder/artist_picks.py` — ArtistPick + ranker — Status: Done
3. Schemas — `ArtistPickItem` + `ArtistPicksResponse` — Status: Done
4. API endpoint — `GET /{set_id}/artist-picks` in `routes/sets.py` — Status: Done
5. CLI — `kiku artist-picks <set> <artist>` — Status: Done
6. Frontend types — `ArtistPick`, `ArtistPicksResponse` — Status: Done
7. Frontend API client — `getArtistPicks()` — Status: Done
8. Frontend component — `AddFromArtistPanel.svelte` — Status: Done
9. Frontend mount — wire panel into `SetView.svelte` — Status: Done
10. Unit test — `tests/test_artists.py` — Status: Done (8 passed)
11. Unit test — `tests/test_artist_picks.py` — Status: Done (6 passed; adapted `_track` mock to set `audio_features=None` + real `resolved_energy_zone` tuple + `playlist_tags=None` so the real scoring internals run against mocks)
12. API test — `tests/api/test_artist_picks_api.py` — Status: Done (4 passed)
13. Lint / type-check (py_compile + svelte-check + pytest) — Status: Done (py_compile OK; svelte-check 0 errors / 4 warnings = baseline; pytest 312 passed, 5 pre-existing test_energy.py failures unrelated to this spec)
14. Commit changed files — Status: Done

### Result
- Code + tests committed: `806029d` (12 files, +787).
- Tests: 8 matcher + 6 ranker + 4 API = 18 new, all green. Full suite 312 passed (5 pre-existing test_energy.py failures unrelated).
- svelte-check: 0 errors / 4 warnings (= baseline).
- Manual E2E pending: open a set → "Add from an artist" → type artist → pick a card → confirm it inserts at the suggested position and the timeline reloads.

## Test Evidence & Outputs
<!-- Filled by explicit testing after /spec IMPLEMENT -->

## Updated Doc
<!-- Filled by explicit documentation udpates after /spec IMPLEMENT -->

## Post-Implement Review
<!-- Filled by /spec REVIEW -->
