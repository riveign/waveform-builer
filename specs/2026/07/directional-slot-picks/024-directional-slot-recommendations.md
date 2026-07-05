# Human Section
Critical: any text/subsection here cannot be modified by AI.

## High-Level Objective (HLO)
Let a DJ ask for intentional dynamism at a specific point in a set — "between track 7 and 8, give me something that lifts the mood" — and have Kiku answer with owned tracks that make that move while still mixing cleanly out of the track before AND into the track after. This is directional, both-neighbor-aware slot excavation: the DJ names a slot and a *direction* (push higher, brighten, cool down, or hold), and Kiku ranks tracks from their own library that fit — each one reporting the harmonic MOVE it makes and why. It serves "The Arc Over the Moment" (a slot is judged against the whole flow, not one adjacent mix), "Grow the Ear" (the DJ learns the harmonic move — same-letter step up, mode flip — not just receives a track), and "Opinions You Can See Through" (every pick shows the move, the energy shift, and any caveat). Library excavation only — never a track the DJ doesn't own.

## Mid-Level Objectives (MLO)
- ADD Camelot move helpers to `src/kiku/setbuilder/camelot.py`: enumerate the target key(s) for a named move relative to a neighbor's key (e.g. energy step +1 same letter `8A→9A`, brighten mode flip `8A→8B`, cool down `−1` on the wheel or `B→A`), and map a named intent to an `allowed_keys` set plus an energy-target shift. Unit-tested standalone.
- ADD a slot-recommendation ranker (new module, e.g. `src/kiku/setbuilder/slot_picks.py`) supporting `mode` (`insert` | `replace`), a named `intent`, and optional `allowed_keys` / `energy_delta` overrides. It reuses `score_replacement` against BOTH neighbors, hard-filters candidates by allowed keys when a key constraint is present, scores against the direction-shifted energy target, and returns ranked owned tracks — each carrying its harmonic-move description and a caveat when the slot resists the requested move.
- EXPOSE via API: `GET /api/sets/{set_id}/slots/{position}/suggestions?mode=&intent=&allowed_keys=&energy_delta=&n=` — mirroring the existing replacements endpoint's response shape plus per-candidate `move` and `caveat` fields.
- EXPOSE via CLI: `kiku slot-suggest <set> <position> --mode --intent [--allowed-keys --energy-delta]` — a warm ranked table showing each pick's move, why, and any caveat.
- BUILD a frontend slot affordance in the set view: from a slot, choose `insert`/`replace` and a direction (named-move buttons — Push higher / Brighten / Cool down), see ranked cards with the move + caveat, one-click apply (insert via `addTrackToSet(setId, trackId, position)` or replace via the existing replace endpoint).
- ENSURE tests: unit for the Camelot move helper, unit for the ranker (both modes, allowed-keys hard filter, energy shift, the honesty/caveat path), and an API test for the endpoint.

## Details (DT)

### The problem, and why it fits the mission
DJs get stuck in same-key monotony. They want to add an intentional lift or a darkening at a chosen point — but a slot has two fixed neighbors, so the move that lifts *out of* the previous track can fight the move *into* the next one. Kiku's job is not to hand over a track; it's to teach the harmonic move that the slot allows and to be honest when the requested move isn't cleanly available. This is Principle #3 (judge the slot against the whole flow), #4 (teach the move, grow the ear), and #5 (show the math — the move, the energy shift, the caveat).

### Core capability
Given (a) a set, (b) a slot position, and (c) a desired direction, recommend owned tracks that fit the slot while satisfying BOTH neighbors — mixing out of the predecessor and into the successor. Library excavation only; never external tracks (anti-principle #2).

### Two modes
- `insert` — add a NEW track between position N and N+1 (the set grows). Neighbors are tracks N and N+1.
- `replace` — swap the track currently at the slot. Neighbors are N−1 and N+1.

### Direction — named intent plus optional explicit override
Kiku translates a named intent into a concrete harmonic move plus an energy-target shift. Advanced DJs can also override the harmonic constraint and/or the energy shift explicitly.

- `push_higher` (energy boost) → `+1` on the Camelot wheel, same letter (e.g. `8A→9A`); raises the energy target above the smooth baseline.
- `brighten` (mood lift) → mode flip, same number `A→B` (e.g. `8A→8B`); minor→major, feels brighter.
- `cool_down` (energy drop / darken) → `−1` on the wheel, or `B→A`.
- `hold` → stay compatible, no directional shift (the current smoothness-seeking behavior).

Optional overrides:
- `allowed_keys` — an explicit list that becomes a HARD filter on the candidate's key (bypasses the intent's derived key set).
- `energy_delta` — an explicit shift that overrides the intent's energy shift.

### The honesty constraint (the teaching soul of the feature)
Because both neighbors are FIXED anchors, a large directional move is not always available without a harsh transition on the OTHER side. Kiku must be transparent when the slot resists the requested move — for example: "Track 8 pulls you back toward 8A, so the cleanest lift here is 8B (a brighten), not a full energy boost." Never silently return a bad transition; explain the ceiling. Every candidate must report the harmonic MOVE it makes (e.g. "8A → 9A energy boost, +0.15 energy, mixes out to 8A clean") — show the why, don't hide the math.

### Existing groundwork to reuse (established by prior codebase exploration — state as given, do not re-verify exhaustively)
- `score_replacement(candidate, prev_track, next_track, target_energy, weights, discovery_density, set_appearance_counts, target_vibe, vibe_strength, ...)` in `src/kiku/setbuilder/scoring.py:532` already scores a candidate against BOTH neighbors and returns `(combined, incoming_breakdown, outgoing_breakdown)`. This is the engine — no new scorer.
- `src/kiku/setbuilder/camelot.py`: `parse_camelot(key)` (`:43`, accepts "8A" and "Am"/"F#"), `harmonic_score(a, b)` (`:68`). A NEW helper is needed here to *enumerate* the target Camelot key(s) for a named move relative to a neighbor (energy boost `8A→9A`, brighten `8A→8B`, etc.) and to derive an `allowed_keys` set + energy shift from an intent.
- Existing endpoint `GET /sets/{set_id}/tracks/{position}/replacements` → `get_replacements` (`src/kiku/api/routes/sets.py:1091`) is the pattern to mirror/extend: it already computes a per-position energy target, BPM pre-filters, excludes in-set tracks, and returns per-candidate incoming/outgoing breakdowns.
- Energy target: `EnergyProfile.target_energy_at(elapsed)` (`src/kiku/setbuilder/constraints.py:28`) plus the position→elapsed mapping used in `get_replacements` (`:1122-1137`). The directional intent SHIFTS this baseline target.
- Sibling patterns for shape/structure: `filler.py` `fill_set` (gap detection) and `artist_picks.py` `rank_artist_picks` (best-gap ranking).

### Constraints
- Library excavation only — every pick is a track the DJ already owns (anti-principle #2). Candidate pool comes from their own library.
- Reuse `score_replacement` as the both-neighbor scorer — do NOT build a parallel scorer.
- `allowed_keys`, when present (from an explicit override or derived from a directional intent that names concrete keys), is a HARD filter on the candidate's key. `hold` applies no key filter.
- Honesty over silence: never return a harsh transition dressed as a match. When the requested move degrades the outgoing (or incoming) transition, surface a caveat explaining the ceiling — the achievable move given the anchor that resists.
- Show the Why: every candidate carries its harmonic-move description (from-key → to-key, the move name, the energy shift) and its score breakdown. Never a bare ranked list.
- Voice per BRANDING.md: "set" not "playlist", "flow" not "sequence", warm mentor tone, never blame the DJ. Never use the banned words (smart, powerful, seamless, magic, leverage, …). Empty/edge cases handled warmly: no owned candidates for the constraint, a slot too tight for any clean move, an out-of-range position.
- DO NOT OVERCOMPLICATE: minimal helper + ranker + endpoint + CLI + one UI affordance; reuse the replacements machinery rather than forking it.

### Testing
- Unit: Camelot move helper — target-key enumeration per move (`push_higher` `8A→9A`, `brighten` `8A→8B`, `cool_down` `8B→8A` / wheel `−1`, wheel wrap `12A→1A` / `1A→12A`), and intent→(allowed_keys, energy shift) mapping including `hold` (no key filter, no shift).
- Unit: ranker — both modes (`insert` neighbors N/N+1, `replace` neighbors N−1/N+1), allowed-keys hard filter drops non-matching candidates, energy shift moves the scored target, and the honesty/caveat path (a candidate that makes the requested move but degrades the opposite-side transition surfaces a caveat).
- API: `slots/{position}/suggestions` endpoint — 200 ranked with `move` + `caveat` fields, mode/intent parsing, `allowed_keys` / `energy_delta` overrides honored, in-set exclusion for `insert`, 404 on missing set, out-of-range position handled warmly.
- E2E (manual acceptance): open a set, pick a slot, choose insert/replace + a direction, confirm ranked cards show the move + caveat and one-click apply inserts/replaces at the slot.

## Behavior
You are a senior engineer on Kiku. Honor the 7 product principles (BRANDING.md) — especially "The Arc Over the Moment," "Grow the Ear," and "Opinions You Can See Through." Reuse `score_replacement` (the both-neighbor scorer) and the existing replacements endpoint machinery rather than building a parallel path. Build the Camelot move helper as clean, tested functions in `camelot.py` so the directional vocabulary is reusable. Make the honesty constraint real: when a slot resists the requested move, say so and name the achievable move — that caveat is the teaching, not an afterthought.

# AI Section
Critical: AI can ONLY modify this section.

## Research

### The key reuse: `score_replacement()` IS the both-neighbor engine (verified)
- `score_replacement(candidate, prev_track, next_track, target_energy=0.5, weights=None, discovery_density=0.0, set_appearance_counts=None, target_vibe=None, vibe_strength=0.0, preferred_artists=None, artist_intensity=0.0) -> tuple[float, dict|None, dict|None]` lives at **`src/kiku/setbuilder/scoring.py:532-592`** (the def is at :532; the Human Section's "~:532" is exact for the `def`, though spec 020's stale ":479" ref is from before the artist-bias params landed). It returns `(round(combined, 3), incoming_breakdown, outgoing_breakdown)`.
- **Breakdown dict keys (verified :567-578)**: `harmonic, energy_fit, bpm_compat, genre_coherence, track_quality, vibe, artist, total, discovery_label, set_appearances`. NOTE vs the assumed map: current breakdowns carry TWO extra keys the earlier map omits — `vibe` and `artist` (the artist-bias soft-nudge feature landed after spec 020). `vibe`/`artist` are `None` when those features are off. The API's `ReplacementBreakdown`/`TransitionScoreBreakdown` pydantic models (schemas.py:512, :202) declare only `harmonic, energy_fit, bpm_compat, genre_coherence, track_quality, total, discovery_label, set_appearances` — extras (`vibe`, `artist`) are silently dropped by pydantic v2's default `extra='ignore'` (confirmed live: `get_replacements` does `ReplacementBreakdown(**incoming)` directly at :1177 with no key filtering). The new `slot_picks` endpoint can mirror this and pass `**breakdown` straight through.
- **None-neighbor behavior (verified :580-592)** — THE crux for insert-at-ends and single-track sets:
  - `incoming = _breakdown(prev_track, candidate) if prev_track else None`
  - `outgoing = _breakdown(candidate, next_track) if next_track else None`
  - both present → `combined = (incoming["total"] + outgoing["total"]) / 2`
  - only one present → `combined` = that side's `total`
  - **both None** → `combined, _ = track_quality(candidate, discovery_density=...)` and BOTH breakdowns are `None` (a bare quality score; no harmonic signal). The caveat logic must guard for `None` sides.
- Single-step `transition_score()` (scoring.py:491-529) and batch `score_transitions()` (scoring.py:595-657) are single-neighbor only — NOT used here; the both-neighbor `score_replacement` is the whole engine.

### Camelot module — verified in full (`src/kiku/setbuilder/camelot.py`, 110 lines)
- **Internal representation**: `(number: int 1-12, letter: str 'A'|'B')`. `A` = minor, `B` = major.
- `parse_camelot(key: str | None) -> tuple[int, str] | None` (**:43**): matches Camelot notation via `_CAMELOT_RE = ^(\d{1,2})([AB])$` (case-insensitive, so "8a"→(8,"A")), else looks up standard notation in `_KEY_TO_CAMELOT` (**:13-40**, e.g. `"Am"→"8A"`, `"F#"→"2B"`, `"Ebm"→"2A"`, `"F#m"→"11A"`). Returns `None` for out-of-range (`13A`, `0A`) or unknown strings. Verified against `tests/test_camelot.py:6-12`.
- `harmonic_score(key_a, key_b) -> float` (**:68-109**) — the exact ladder the caveat threshold must be grounded in (verified against `tests/test_camelot.py`):

  | Relationship | Score | Source line |
  |---|---|---|
  | same key (`8A`/`8A`) | **1.0** | :88-89 |
  | same number, mode flip (`8A`/`8B`) | **0.8** | :92-93 |
  | adjacent on wheel, same letter (`8A`/`9A`, wrap `12A`/`1A`) | **0.85** | :99-100 |
  | two steps, same letter (`8A`/`10A`) | **0.5** | :102-103 |
  | adjacent + mode flip (`8A`/`9B`) | **0.6** | :106-107 |
  | anything else (clash) | **0.2** | :109 |
  | either key unparseable/None | **0.5** (neutral) | :81-82 |

  Wheel wrap is handled by `wheel_diff = min(diff, 12 - diff)` (:96-97) — so `12→1` is distance 1. Confirms the Human Section's `push_higher` wrap (`12A→1A`) and `cool_down` wrap (`1A→12A`) land as adjacent (0.85).

- **NEW helpers to ADD to `camelot.py`** (clean, standalone, unit-tested — the reusable directional vocabulary the Behavior section asks for):

  ```python
  def camelot_str(key: tuple[int, str]) -> str:            # (9, "A") -> "9A"
  def step_wheel(key: tuple[int,str], delta: int) -> tuple[int,str]  # +1/-1 same letter, mod-12 wrap (1..12)
  def flip_mode(key: tuple[int,str]) -> tuple[int,str]     # A<->B, same number
  def move_targets(neighbor_key: str, intent: str) -> list[tuple[int,str]]
      # push_higher -> [step_wheel(k, +1)]                       (8A -> 9A)
      # brighten    -> [flip_mode(k)]                            (8A -> 8B)
      # cool_down   -> [step_wheel(k, -1)] + ([flip_mode(k)] if letter=='B' else [])
      #                                                          (8A -> 7A ; 8B -> 7B and 8A)
      # hold        -> []   (no key constraint)
  def intent_allowed_keys(neighbor_key: str, intent: str) -> set[str] | None
      # returns {camelot_str(t) for t in move_targets(...)} or None for `hold`
  def intent_energy_delta(intent: str) -> float
      # push_higher -> +0.15 ; brighten -> +0.05 ; cool_down -> -0.15 ; hold -> 0.0
  ```

  Anchor semantics: for **insert/replace the directional move is measured against the PREVIOUS neighbor** (mixing OUT of the predecessor is where the "lift"/"darken" reads); the NEXT neighbor is the fixed anchor the honesty check tests against. Wrap math must keep numbers in `1..12` (use `((n - 1 + delta) % 12) + 1`, NOT `n % 12 + 1`, so `12 + (-1)` → `11` and `1 + (-1)` → `12`). `cool_down` returning a 2-element set (wheel `-1` OR mode `B→A`) means `allowed_keys` is a set, and a candidate matches if its parsed key is in that set.

### `get_replacements` endpoint — the shape to mirror + extend (`src/kiku/api/routes/sets.py:1091-1188`, verified)
- Loads set: `s = db.get(Set, set_id)` → 404 "Set not found" (:1109-1111). Orders: `ordered = sorted(s.tracks, key=lambda st: st.position)` (:1113). Position guard `0 <= position < len(ordered)` else 404 "Invalid position" (:1114-1115).
- **REPLACE indexing (:1117-1120)**: `current = ordered[position]`, `prev = ordered[position-1].track if position>0 else None`, `next = ordered[position+1].track if position<len-1 else None`. The current track at `position` is dropped from candidacy because ALL set track ids are excluded (below).
- **Per-position energy target (:1122-1137)**: parse `s.energy_profile` via `parse_energy_json()` then fallback `parse_energy_string()`; `elapsed = (position / max(total_tracks-1, 1)) * (s.duration_min or 120)`; `energy_target = profile.target_energy_at(elapsed)`; defaults to `0.5` on any failure.
- **In-set exclusion + candidate pool (:1140, :1146)**: `set_track_ids = {st.track_id for st in ordered}`; `q = db.query(Track).filter(Track.id.notin_(set_track_ids))`.
- **BPM pre-filter (:1142-1150)**: `ref_bpm = mean([prev.bpm, next.bpm] present)` (falls back to `current.bpm`); `q.filter(Track.bpm.between(ref_bpm*(1-2·BPM_TOLERANCE), ref_bpm*(1+2·BPM_TOLERANCE)))` — a ±12% window around the neighbor average. `genre_filter` optional ilike (:1152-1155).
- **Scoring loop (:1160-1169)**: `score_replacement(cand, prev, next, target_energy=energy_target, discovery_density=...)`, sort desc, take top `n`.
- **Response (verified schemas.py:512-548)**: `ReplacementSuggestionsResponse{ context: ReplacementContext, candidates: list[ReplacementCandidate] }` where `ReplacementCandidate{ track: TrackResponse, combined_score: float, incoming_breakdown: ReplacementBreakdown|None, outgoing_breakdown: ReplacementBreakdown|None }` and `ReplacementContext{ prev_track: TrackSummary|None, next_track: TrackSummary|None, energy_target: float, position: int }`.
- **New endpoint extends this**: add per-candidate `move: str` (e.g. `"8A → 9A energy boost"`) and `caveat: str | None`, plus the requested `intent`/`mode` and resolved `allowed_keys`/`energy_delta` echoed into the context. `_track_response` (:1067) and `_track_summary` are the reusable serializers.

### Energy target + how the intent shifts it (verified)
- `EnergyProfile.target_energy_at(elapsed_min)` (`src/kiku/setbuilder/constraints.py:28-46`): linear interpolation between segment boundaries; past-end returns the last segment's energy; empty profile → `0.5`.
- `parse_energy_json` (:65-80) parses `[{"name","duration_min","target_energy"}, ...]`; `parse_energy_string` (:49-62) parses `"warmup:30:0.3,..."`.
- `energy_fit(track, target_energy)` (scoring.py:298-315): reads `audio_features.energy` (numeric) else `resolved_energy_zone → zone_to_numeric`, else `0.5`; returns `max(0.0, 1.0 - abs(track_energy - target) * 2.0)`. **This is why a shifted target directly re-ranks candidates**: adding `energy_delta` to the baseline moves the optimal track-energy by exactly `energy_delta` (a `+0.15` shift makes hotter tracks score `energy_fit` higher and cooler tracks lower). The ranker computes `baseline = target_energy_at(elapsed)` then `shifted = clamp(baseline + energy_delta, 0, 1)` and passes `shifted` into `score_replacement(..., target_energy=shifted)`.

### Resolved design questions + recommendations

**(1) New module `slot_picks.py` — RECOMMENDED (not extending `get_replacements`).**
The sibling `src/kiku/setbuilder/artist_picks.py` (verified, 141 lines) is the exact precedent: a small standalone module = one `@dataclass` (`ArtistPick`) + one `rank_*` function that (a) loads the ordered set + energy profile with the same JSON→string fallback (:86-95), (b) builds a candidate pool, (c) loops gaps calling `score_replacement`, (d) returns ranked dataclasses with a mentor-voice `reason`. It is fully unit-testable with mock sessions (no endpoint coupling). `filler.py` (`fill_set`, verified :26+) is heavier (SSE generator, planner coupling) — the wrong template. `get_replacements` is endpoint-bound (FastAPI `Depends`, `HTTPException`) and NOT reusable as a library function. **Recommendation: new `src/kiku/setbuilder/slot_picks.py` mirroring `artist_picks.py` — `@dataclass SlotPick{track, move, from_key, to_key, energy_shift, score, incoming_breakdown, outgoing_breakdown, caveat}` + `rank_slot_picks(session, set_id, position, mode, intent, allowed_keys=None, energy_delta=None, n=10, weights=None, discovery_density=0.0) -> list[SlotPick]`.** The Camelot move helpers go in `camelot.py` (reusable vocabulary). The endpoint stays thin, mirroring `get_artist_picks` (:1208-1251). Lowest duplication, consistent with the codebase.

**(2) Insert vs replace mechanics — indexing confirmed against `get_replacements` + `artist_picks`.**
  - **replace at slot N**: `prev = ordered[N-1]`, `next = ordered[N+1]`, exclude `ordered[N].track_id` (and all in-set ids) — identical to `get_replacements` (:1117-1120, :1140). The track at N is removed and re-scored against its two flanks.
  - **insert at slot N** (set grows, nothing removed): per the Human Section, neighbors are tracks **N and N+1** → `prev = ordered[N]`, `next = ordered[N+1]` (mixing out of the current track-N into what follows). This equals `artist_picks`' gap `g = N+1` (its gap `g` uses `prev=ordered[g-1]`, `next=ordered[g]`, verified :118-120). Insert must exclude in-set ids too. Edge cases: insert after the last track (`next=None`, `prev=ordered[N]`), and insert before the first (`N=-1`/gap 0 → `prev=None`). The ranker takes `mode` and resolves the `(prev, next)` pair once, then scores the single slot (unlike `artist_picks` which scans ALL gaps — here the DJ has NAMED the slot).
  - **Apply — both endpoints verified to exist**:
    - insert → `add_track` at **`routes/sets.py:546`** (`POST /{set_id}/tracks`, body `SetAddTrackRequest{track_id, position}`) via frontend `addTrackToSet(setId, trackId, position)` (**`frontend/src/lib/api/sets.ts:166-176`**).
    - replace → `replace_track` at **`routes/sets.py:1191`** (`POST /{set_id}/tracks/{position}/replace`, body `ReplaceTrackRequest{new_track_id}`) via `replaceTrackInSet(setId, position, newTrackId)` (**sets.ts:212-222**).

**(3) The caveat / honesty algorithm — concrete, grounded in `harmonic_score`.**
  Per candidate that satisfies the requested move (its key ∈ `allowed_keys`), compute the two harmonic sides:
  - `h_in  = harmonic_score(prev.key, cand.key)`  (mixing OUT of the predecessor — the move side)
  - `h_out = harmonic_score(cand.key, next.key)`  (mixing INTO the fixed successor — the anchor side)

  **Clean threshold `T = 0.8`** — grounded in the verified ladder: `1.0` (same), `0.85` (adjacent), `0.8` (mode flip) are all musically clean mixes; the drop-off to `0.5` (two-step) and `0.2` (clash) is where a transition turns harsh. So `>= 0.8` = clean, `< 0.8` = the slot resists.

  **Detection**: a candidate `resists` when `min(h_in, h_out) < T` while the move side is clean (`h_in >= T`) — i.e. the requested move mixes cleanly out of the predecessor but the FIXED successor drags harmonic below clean. (Unknown keys score `0.5` < T, so a keyless anchor also trips the caveat — correct: we can't promise a clean mix we can't see.)

  **Achievable alternative**: enumerate the other intents' `move_targets(prev.key, alt_intent)`; pick the `alt` whose target key maximizes `min(h_in', h_out')` and keeps BOTH sides `>= T`. If `hold` (compatible, no constraint) is the only both-clean option, name it.

  **Caveat wording pattern** (BRANDING voice — teach, never blame, no banned words), echoing the Human Section's example:
  > `"Track {N+1} pulls back toward {next.key}, so the cleanest lift here is a {alt_move_name} ({from}→{alt_to}), not a full {requested_move_name}."`

  When both sides are already `>= T`, `caveat = None` and the `move` string states the clean move: `"{prev.key} → {cand.key} {move_name}, +{energy_shift} energy, mixes into {next.key} clean."`

  ```mermaid
  flowchart TD
    A[candidate key ∈ allowed_keys] --> B[h_in = harmonic prev→cand<br/>h_out = harmonic cand→next]
    B --> C{min h_in,h_out ≥ 0.8?}
    C -->|yes| D[caveat = None<br/>move string states clean move]
    C -->|no| E[enumerate alt intents' targets<br/>pick alt maximizing min both sides ≥ 0.8]
    E --> F[caveat names the achievable move<br/>+ the anchor that resists]
  ```

### CLI + frontend landing points (verified)
- **CLI**: add `kiku slot-suggest <set> <position> --mode --intent [--allowed-keys --energy-delta -n]` in `src/kiku/cli.py` right after `artist_picks_cmd` (ends **cli.py:475-476**). Reuse the id-or-name set resolution (`try int(...) → session.get(Set, id)` except `Set.name.ilike(...).first()`, verified cli.py:439-447) and the rich `Table` pattern (cli.py:457-475) — columns: `#, Title, Artist, Move, Energy, Score, Caveat`.
- **Frontend types** (`frontend/src/lib/types/index.ts`): add `SlotPick` + `SlotSuggestionsResponse` after `ReplacementSuggestionsResponse` (interfaces at :510-548 area; `Track` :7, `TransitionScoreBreakdown`/`ReplacementBreakdown` :150/:510). `ArtistPick`/`ArtistPicksResponse` already exist as precedent.
- **Frontend API client** (`frontend/src/lib/api/sets.ts`): add `getSlotSuggestions(setId, position, {mode, intent, allowedKeys?, energyDelta?, n?})` after `getArtistPicks` (:203-210), mirroring its `URLSearchParams` shape.
- **Frontend mount** (`frontend/src/lib/components/set/SetView.svelte`): two live precedents — (a) the `AddFromArtistPanel` floating panel toggled by a `MenuItem` at **:496** with `showArtistPicks` state (:90) and mount at **:640-646** (`onInserted={handleTracksChanged}`); (b) `ReplaceTrackModal` (`SetTimeline.svelte:326`, opened from a per-slot action, using `getReplacements`+`replaceTrackInSet`). The slot affordance fits best as a per-slot control in `SetTimeline` (it already knows `position` and mounts `ReplaceTrackModal`) OR a `SetView` panel like `AddFromArtistPanel`. Apply via `addTrackToSet` (insert) / `replaceTrackInSet` (replace), then `handleTracksChanged()` (SetView:355-357) reloads. `Typeahead` reuse is NOT needed (no artist input) — the direction is chosen via named-move buttons.

### Test landscape (verified)
- `tests/test_camelot.py` (44 lines) — the home for the move-helper unit tests (`move_targets`, `step_wheel`, `flip_mode`, wrap `12A→1A`/`1A→12A`, `intent_allowed_keys`, `intent_energy_delta`, `hold`→no filter/no shift). Same import style (`from kiku.setbuilder.camelot import ...`).
- `tests/test_scoring.py` exists for scoring internals.
- **Ranker unit** — new `tests/test_slot_picks.py` follows `tests/test_artist_picks.py` (already in-repo, the exact mock-session pattern: `session.get(Set,id)` + `session.query(Track).filter(...).all()` stubbed) and `tests/test_set_analysis.py:204-226` `_energy_track` mock recipe — a MMock track MUST set `audio_features=None` (or a MagicMock with `.energy`), `resolved_energy_zone=(None,"none",0.0)`, `playlist_tags=None`, numeric `rating`/`play_count`/`kiku_play_count`, and `.key`/`.bpm`/`.dir_genre`/`.rb_genre` so the real scoring internals run against mocks without choking. Cover: both modes (insert N/N+1, replace N-1/N+1), `allowed_keys` hard filter drops non-matching keys, energy shift moves the scored target, and the honesty/caveat path (candidate makes the move but the fixed anchor drops harmonic < 0.8 → caveat + achievable alt).
- **API** — new `tests/api/test_slot_picks_api.py` uses `tests/api/conftest.py` (verified): `db_session` seeds 20 tracks (`artist="Artist {(i%5)+1}"`, `key="8A" if i%2==0 else "8B"`, `bpm=120+i`, genre techno/house) + set `id=1` holding track ids 1-5 at positions 0-4; `client` overrides `get_db`. **RISK/surprise for PLAN**: seeded keys are only `8A`/`8B`, so `brighten` (8A→8B) and `hold` are directly testable, but `push_higher` (needs a `9A` candidate) and `cool_down` (needs `7A`) have NO matching candidate in the default seed — the API test must add a couple of purpose-keyed tracks in-test (session insert) or assert the warm empty-result path. Mirror `test_artist_picks_api.py` for 200/404/empty/n-cap shape.

### Strategy

**Camelot helpers → ranker → schemas → API → CLI → frontend → tests, reusing `score_replacement` as the sole scorer throughout.**

1. **Camelot move helpers** (`src/kiku/setbuilder/camelot.py`) — `camelot_str`, `step_wheel` (mod-12 wrap via `((n-1+delta)%12)+1`), `flip_mode`, `move_targets(neighbor_key, intent)`, `intent_allowed_keys` (→ `set[str] | None`, `None` for `hold`), `intent_energy_delta`. Pure, no DB. Unit-tested FIRST (they gate the whole feature and are the reusable directional vocabulary the Behavior section asks for).
2. **Ranker** (new `src/kiku/setbuilder/slot_picks.py`, mirrors `artist_picks.py`) — `@dataclass SlotPick{track, from_key, to_key, move, energy_shift, score, incoming_breakdown, outgoing_breakdown, caveat}` + `rank_slot_picks(session, set_id, position, mode, intent, allowed_keys=None, energy_delta=None, n=10, weights=None, discovery_density=0.0)`. Steps: load ordered set + energy profile (JSON→string fallback per artist_picks:86-95); resolve `(prev, next)` by `mode` (replace: N-1/N+1 excluding N; insert: N/N+1); resolve `allowed_keys` (explicit override else `intent_allowed_keys(prev.key, intent)`) and `energy_shift` (explicit `energy_delta` else `intent_energy_delta(intent)`); compute `shifted_target = clamp(target_energy_at(elapsed) + energy_shift, 0, 1)`; build candidate pool (in-set exclusion + BPM prefilter mirroring get_replacements:1140-1150); HARD-filter by `parse_camelot(cand.key) in allowed_keys` when a key constraint is present (drop keyless/off-key); `score_replacement(cand, prev, next, target_energy=shifted_target, ...)`; run the caveat detection (T=0.8) + achievable-alt; build the `move` string; sort desc; return top `n`.
3. **Schemas** (`src/kiku/api/schemas.py`) — `SlotPickItem{track: TrackResponse, from_key, to_key, move: str, energy_shift: float, score: float, incoming_breakdown: ReplacementBreakdown|None, outgoing_breakdown: ReplacementBreakdown|None, caveat: str|None}` + `SlotSuggestionsResponse{set_id, position, mode, intent, allowed_keys: list[str]|None, energy_delta: float, picks: list[SlotPickItem]}`. Reuse `ReplacementBreakdown` (extras dropped by pydantic).
4. **API** (`src/kiku/api/routes/sets.py`) — `GET /{set_id}/slots/{position}/suggestions?mode=&intent=&allowed_keys=&energy_delta=&n=`, mounted after `get_artist_picks` (:1251). 404 missing set, out-of-range position handled warmly, 200 with ranked picks (empty list + resolved context when the slot is too tight for any clean move). Thin — delegates to `rank_slot_picks`, serializes with `_track_response`.
5. **CLI** (`src/kiku/cli.py`) — `kiku slot-suggest <set> <position> --mode --intent [--allowed-keys --energy-delta -n]` after `artist_picks_cmd` (:476); id-or-name resolution; rich Table (`#, Title, Artist, Move, Energy, Score, Caveat`); warm empty/edge messaging (no banned words).
6. **Frontend** — types (`SlotPick`, `SlotSuggestionsResponse`) + `getSlotSuggestions()` client + a slot affordance (named-move buttons Push higher / Brighten / Cool down + insert/replace toggle) either as a `SetView` panel (mirror `AddFromArtistPanel`, SetView:640) or a `SetTimeline` per-slot modal (mirror `ReplaceTrackModal`, SetTimeline:326); ranked cards show `move` + `caveat`; apply via `addTrackToSet`/`replaceTrackInSet` then `handleTracksChanged()`.

**Testing strategy**
- Unit `tests/test_camelot.py` (extend): `move_targets`/`step_wheel`/`flip_mode` per move — `push_higher 8A→9A`, `brighten 8A→8B`, `cool_down 8B→{7B,8A}` & `8A→7A`, wrap `12A→1A` / `1A→12A`; `intent_allowed_keys` (`hold`→`None`) and `intent_energy_delta`.
- Unit `tests/test_slot_picks.py` (new, mock-session + `_energy_track`-style mocks): both modes' neighbor resolution, `allowed_keys` hard filter drops off-key candidates, energy shift moves the scored target, caveat path (candidate makes the requested move but the fixed anchor's harmonic < 0.8 → non-null caveat naming the achievable alt), and the both-clean path (caveat None).
- API `tests/api/test_slot_picks_api.py` (new, `client` + seeded set id=1): 200 ranked with `move`+`caveat`, `mode`/`intent` parsing, `allowed_keys`/`energy_delta` overrides honored, in-set exclusion for insert, 404 missing set, out-of-range position warm-handled. Because the seed only has `8A`/`8B` keys, insert purpose-keyed tracks in-test for `push_higher`/`cool_down` coverage (or assert the warm empty path).
- Coverage: Camelot helpers + ranker fully unit-tested; endpoint covered; frontend type-checked via `svelte-check` (no FE test harness). Lint via `py_compile` (ruff not installed); full backend suite `python -m pytest tests/ -x -q` green.

## Plan

### Task Outline
1. Camelot move helpers in `src/kiku/setbuilder/camelot.py` — `camelot_str`, `step_wheel`, `flip_mode`, `move_targets`, `intent_allowed_keys`, `intent_energy_delta`
2. New `src/kiku/setbuilder/slot_picks.py` — `SlotPick` dataclass + `rank_slot_picks()` (both-neighbor, direction-aware, caveat)
3. Schemas — `SlotSuggestionItem` + `SlotSuggestionsResponse` in `api/schemas.py`
4. API endpoint — `GET /{set_id}/slots/{position}/suggestions` in `routes/sets.py`
5. CLI — `kiku slot-suggest <set> <position> --mode --intent [--keys --energy-delta]` in `cli.py`
6. Frontend types — `SlotSuggestion`, `SlotSuggestionsResponse` in `types/index.ts`
7. Frontend API client — `getSlotSuggestions()` in `api/sets.ts`
8. Frontend component — `AddSlotPicksPanel.svelte` (NEW)
9. Frontend mount — wire panel into `SetView.svelte`
10. Unit test — `tests/test_camelot.py` additions (move helpers, wrap, intent maps)
11. Unit test — `tests/test_slot_picks.py` (NEW — both modes, filter, shift, caveat)
12. API test — `tests/api/test_slot_suggestions_api.py` (NEW)
13. Lint / type-check (py_compile + svelte-check + pytest)
14. Commit changed files

### Files
- `src/kiku/setbuilder/camelot.py`
  - Append the directional vocabulary after `harmonic_score` (:109): `camelot_str`, `step_wheel` (mod-12 wrap `((n-1+δ)%12)+1`), `flip_mode`, `move_targets`, `intent_allowed_keys`, `intent_energy_delta`. Pure, no DB. Reuses the existing `parse_camelot` (:43).
- `src/kiku/setbuilder/slot_picks.py` (NEW)
  - `SlotPick` dataclass; `rank_slot_picks(session, set_id, position, mode, intent, allowed_keys, energy_delta, n, weights, discovery_density)`; reuses `score_replacement` (scoring.py:532), `parse_energy_json/parse_energy_string` (constraints.py:65,49), `harmonic_score` + the new camelot helpers. Mirrors `artist_picks.py` shape (energy-profile parse block :86-95; in-set exclusion :83; sort/top-n :139-140).
- `src/kiku/api/schemas.py`
  - Add `SlotSuggestionItem` + `SlotSuggestionsResponse` after `ReplaceTrackRequest` (:552). Reuse `TrackResponse` (:25) + `ReplacementBreakdown` (:512).
- `src/kiku/api/routes/sets.py`
  - Add `SlotSuggestionItem, SlotSuggestionsResponse` to the schema import block (:16-44); append `GET /{set_id}/slots/{position}/suggestions` after `get_artist_picks` (ends :1251), reusing `_track_response` (:1067) and the `_BD_FIELDS` filter idiom (:1231-1234).
- `src/kiku/cli.py`
  - Add `slot-suggest` command after `artist_picks_cmd` (ends :475); id-or-name set resolution (:439-443); rich `Table` (mirror :457-475).
- `frontend/src/lib/types/index.ts`
  - Add `SlotSuggestion` + `SlotSuggestionsResponse` after `ArtistPicksResponse` (:561). Reuse `Track` (:7) + `ReplacementBreakdown` (:510).
- `frontend/src/lib/api/sets.ts`
  - Add `SlotSuggestionsResponse` to the type import block (:1-17); add `getSlotSuggestions()` after `getArtistPicks` (:210).
- `frontend/src/lib/components/set/AddSlotPicksPanel.svelte` (NEW)
  - Insert/replace toggle + named-move buttons (Push higher / Brighten / Cool down / Hold) + slot number input; ranked cards with move + caveat; apply via `addTrackToSet` (insert) / `replaceTrackInSet` (replace). Mirrors `AddFromArtistPanel.svelte`.
- `frontend/src/lib/components/set/SetView.svelte`
  - Import (after :13); `showSlotPicks` state (after :90); `MenuItem` toggle (after :496); panel mount (after the `AddFromArtistPanel` block :640-646).
- `tests/test_camelot.py` — append move-helper unit tests.
- `tests/test_slot_picks.py` (NEW) — ranker unit tests.
- `tests/api/test_slot_suggestions_api.py` (NEW) — endpoint integration tests.

### Tasks

#### Task 1 — camelot.py: directional move helpers
Tools: editor
Append after `harmonic_score` (ends :109). Pure functions, no DB. `step_wheel` uses `((n - 1 + delta) % 12) + 1` so `12 + (+1)` → `1` and `1 + (-1)` → `12` (the wheel-wrap gotcha). The directional move is measured against the PREVIOUS neighbor's key; `cool_down` on a `B` key yields two targets (wheel `-1` OR mode `B→A`).
Diff:
````diff
--- a/src/kiku/setbuilder/camelot.py
+++ b/src/kiku/setbuilder/camelot.py
@@
     if wheel_diff == 1 and let_a != let_b:
         return 0.6
 
     return 0.2
+
+
+# ── Directional move vocabulary (reused by slot_picks + the API/CLI) ──
+
+_INTENT_ENERGY_DELTA = {
+    "push_higher": 0.15,
+    "brighten": 0.05,
+    "cool_down": -0.15,
+    "hold": 0.0,
+}
+
+
+def camelot_str(key: tuple[int, str]) -> str:
+    """Format a ``(number, letter)`` Camelot key as its canonical string.
+
+    ``(9, "A") -> "9A"``.
+    """
+    num, letter = key
+    return f"{num}{letter}"
+
+
+def step_wheel(key: tuple[int, str], delta: int) -> tuple[int, str]:
+    """Step ``delta`` positions around the 12-slot wheel, same letter.
+
+    Wraps ``12 -> 1`` (up) and ``1 -> 12`` (down) so the number stays in 1..12.
+    """
+    num, letter = key
+    stepped = ((num - 1 + delta) % 12) + 1
+    return (stepped, letter)
+
+
+def flip_mode(key: tuple[int, str]) -> tuple[int, str]:
+    """Flip the mode ``A<->B`` at the same wheel number (minor<->major)."""
+    num, letter = key
+    return (num, "B" if letter == "A" else "A")
+
+
+def move_targets(neighbor_key: str | None, intent: str) -> list[tuple[int, str]]:
+    """Enumerate the target Camelot key(s) for a named move, relative to a neighbor.
+
+    ``push_higher`` -> ``[+1 same letter]``            (8A -> 9A)
+    ``brighten``    -> ``[mode flip]``                 (8A -> 8B)
+    ``cool_down``   -> ``[-1 same letter]`` (+ B->A)   (8A -> 7A ; 8B -> 7B and 8A)
+    ``hold``        -> ``[]``  (no key constraint)
+
+    Returns ``[]`` for an unparseable neighbor or an unknown intent.
+    """
+    base = parse_camelot(neighbor_key)
+    if base is None or intent == "hold":
+        return []
+    if intent == "push_higher":
+        return [step_wheel(base, 1)]
+    if intent == "brighten":
+        return [flip_mode(base)]
+    if intent == "cool_down":
+        targets = [step_wheel(base, -1)]
+        if base[1] == "B":
+            targets.append(flip_mode(base))
+        return targets
+    return []
+
+
+def intent_allowed_keys(neighbor_key: str | None, intent: str) -> set[str] | None:
+    """Map a named intent to the allowed candidate-key set, relative to a neighbor.
+
+    Returns ``None`` for ``hold`` (no key filter) or when no targets can be
+    derived (unparseable neighbor / unknown intent) — i.e. no hard filter.
+    """
+    targets = move_targets(neighbor_key, intent)
+    if not targets:
+        return None
+    return {camelot_str(t) for t in targets}
+
+
+def intent_energy_delta(intent: str) -> float:
+    """Energy-target shift a named intent applies to the smooth baseline."""
+    return _INTENT_ENERGY_DELTA.get(intent, 0.0)
````

Verification:
- `.venv/bin/python -c "from kiku.setbuilder.camelot import move_targets, intent_allowed_keys, intent_energy_delta, step_wheel; assert move_targets('8A','push_higher')==[(9,'A')]; assert step_wheel((12,'A'),1)==(1,'A'); assert step_wheel((1,'A'),-1)==(12,'A'); assert intent_allowed_keys('8A','brighten')=={'8B'}; assert intent_allowed_keys('8A','hold') is None; assert set(move_targets('8B','cool_down'))=={(7,'B'),(8,'A')}; assert intent_energy_delta('cool_down')==-0.15"` (full cases in Task 10).

#### Task 2 — slot_picks.py: SlotPick + rank_slot_picks
Tools: editor
Create `src/kiku/setbuilder/slot_picks.py`. Reuses `score_replacement` as the sole both-neighbor scorer. Resolves `(prev, next)` by `mode` (insert N→N/N+1; replace N→N-1/N+1, track N dropped via the in-set exclusion). Applies the intent's energy shift to the baseline `target_energy_at`. Hard-filters by key when a constraint is present. Builds the honesty caveat with the `T = CLEAN_THRESHOLD = 0.8` algorithm.
Diff:
````diff
--- /dev/null
+++ b/src/kiku/setbuilder/slot_picks.py
@@
+"""Directional slot-recommendation ranker.
+
+Given a set, a slot ``position``, a ``mode`` (insert | replace) and a named
+directional ``intent`` (push_higher | brighten | cool_down | hold), rank the
+DJ's OWN tracks that make that harmonic move while still mixing cleanly out of
+the predecessor AND into the FIXED successor. Reuses ``score_replacement`` (the
+both-neighbor scorer) — no parallel scorer. Library excavation only.
+"""
+
+from __future__ import annotations
+
+import json
+from dataclasses import dataclass
+
+from sqlalchemy.orm import Session
+
+from kiku.config import BPM_TOLERANCE
+from kiku.db.models import Set, Track
+from kiku.setbuilder.camelot import (
+    camelot_str,
+    harmonic_score,
+    intent_allowed_keys,
+    intent_energy_delta,
+    move_targets,
+    parse_camelot,
+)
+from kiku.setbuilder.constraints import parse_energy_json, parse_energy_string
+from kiku.setbuilder.scoring import score_replacement
+
+# Harmonic scores >= this read as a clean mix (same 1.0 / adjacent 0.85 / mode
+# flip 0.8); below it a transition turns harsh. Grounds the honesty caveat.
+CLEAN_THRESHOLD = 0.8
+
+_MOVE_NAMES = {
+    "push_higher": "energy boost",
+    "brighten": "brighten",
+    "cool_down": "cool down",
+    "hold": "hold",
+}
+
+
+@dataclass
+class SlotPick:
+    """One ranked slot candidate with its harmonic move and any honesty caveat."""
+
+    track: Track
+    from_key: str | None  # the predecessor's key the move departs from
+    to_key: str | None  # the candidate's key
+    move: str  # human-readable move description (Show the Why)
+    energy_shift: float  # the applied energy-target shift
+    score: float  # both-neighbor combined score
+    incoming_breakdown: dict | None
+    outgoing_breakdown: dict | None
+    caveat: str | None  # set when the slot resists the requested move
+
+
+def _resolve_neighbors(ordered_tracks: list, position: int, mode: str):
+    """Resolve ``(prev, next)`` tracks for a slot per ``mode``.
+
+    insert at N  -> neighbors are tracks N and N+1 (the set grows between them)
+    replace at N -> neighbors are N-1 and N+1 (track N is dropped)
+    """
+    total = len(ordered_tracks)
+    if mode == "insert":
+        prev = ordered_tracks[position] if 0 <= position < total else None
+        nxt = ordered_tracks[position + 1] if position + 1 < total else None
+    else:  # replace
+        prev = ordered_tracks[position - 1] if position > 0 else None
+        nxt = ordered_tracks[position + 1] if position + 1 < total else None
+    return prev, nxt
+
+
+def _achievable_alt(prev_key: str | None, next_key: str | None):
+    """Find the directional alt whose target keeps BOTH harmonic sides clean.
+
+    Returns ``(alt_intent, alt_target_key_str)`` maximizing ``min(both sides)``
+    with both ``>= CLEAN_THRESHOLD``, or ``None`` when no directional alt is
+    both-clean.
+    """
+    best = None
+    best_min = -1.0
+    for alt in ("push_higher", "brighten", "cool_down"):
+        for tgt in move_targets(prev_key, alt):
+            tgt_str = camelot_str(tgt)
+            m = min(
+                harmonic_score(prev_key, tgt_str),
+                harmonic_score(tgt_str, next_key),
+            )
+            if m >= CLEAN_THRESHOLD and m > best_min:
+                best_min = m
+                best = (alt, tgt_str)
+    return best
+
+
+def _build_caveat(prev, cand, nxt, intent: str) -> str | None:
+    """Return an honesty caveat when the slot resists the requested move, else None.
+
+    Trips when the move mixes cleanly OUT of the predecessor
+    (``h_in >= T``) but the FIXED successor drags a harmonic side below clean
+    (``min < T``). Names the achievable move and the anchor that resists — the
+    teaching, not an afterthought. Guards missing neighbors and ``hold``.
+    """
+    if prev is None or nxt is None or intent == "hold":
+        return None
+    h_in = harmonic_score(prev.key, cand.key)
+    h_out = harmonic_score(cand.key, nxt.key)
+    if h_in < CLEAN_THRESHOLD or min(h_in, h_out) >= CLEAN_THRESHOLD:
+        return None  # move side already unclean (not our promise), or both clean
+    requested_name = _MOVE_NAMES.get(intent, intent)
+    alt = _achievable_alt(prev.key, nxt.key)
+    if alt:
+        alt_intent, alt_to = alt
+        alt_name = _MOVE_NAMES.get(alt_intent, alt_intent)
+        return (
+            f"The next track ({nxt.key}) pulls back toward it, so the cleanest "
+            f"move here is a {alt_name} ({prev.key}→{alt_to}), not a full "
+            f"{requested_name}."
+        )
+    return (
+        f"The next track ({nxt.key}) resists a clean {requested_name} here — "
+        f"holding a compatible key mixes smoother than forcing the move."
+    )
+
+
+def _build_move(prev, cand, nxt, intent: str, energy_shift: float, caveat: str | None) -> str:
+    """Build the move description shown on every pick (never a bare ranked list)."""
+    move_name = _MOVE_NAMES.get(intent, intent)
+    from_key = prev.key if prev else None
+    to_key = cand.key
+    shift = f"{energy_shift:+.2f}"
+    head = f"{from_key} → {to_key} {move_name}" if from_key else f"{to_key} {move_name}"
+    if caveat:
+        return f"{head} ({shift} energy) — see the caveat below."
+    if nxt is not None:
+        return f"{head}, {shift} energy, mixes into {nxt.key} clean."
+    return f"{head}, {shift} energy."
+
+
+def rank_slot_picks(
+    session: Session,
+    set_id: int,
+    position: int,
+    mode: str,
+    intent: str,
+    allowed_keys: set[str] | None = None,
+    energy_delta: float | None = None,
+    n: int = 10,
+    weights: dict[str, float] | None = None,
+    discovery_density: float = 0.0,
+) -> list[SlotPick]:
+    """Rank owned tracks that make the requested directional move at a slot.
+
+    Returns up to ``n`` picks ordered by both-neighbor score (descending), each
+    carrying its harmonic move and an honesty caveat when the slot resists it.
+    Returns an empty list when the set is missing, the position is out of range,
+    or nothing owned fits the requested move.
+    """
+    s = session.get(Set, set_id)
+    if not s:
+        return []
+
+    ordered = sorted(s.tracks, key=lambda st: st.position)
+    ordered_tracks = [st.track for st in ordered]
+    set_track_ids = {st.track_id for st in ordered}
+    total = len(ordered_tracks)
+    if position < 0 or position >= total:
+        return []
+
+    prev, nxt = _resolve_neighbors(ordered_tracks, position, mode)
+
+    # Energy profile (JSON first, then string fallback) -> baseline target.
+    profile = None
+    if s.energy_profile:
+        try:
+            try:
+                profile = parse_energy_json(s.energy_profile)
+            except (json.JSONDecodeError, KeyError):
+                profile = parse_energy_string(s.energy_profile)
+        except Exception:
+            profile = None
+    baseline = 0.5
+    if profile is not None:
+        elapsed = (position / max(total - 1, 1)) * (s.duration_min or 120)
+        baseline = profile.target_energy_at(elapsed)
+
+    # Directional shift: explicit override else the intent's shift.
+    energy_shift = energy_delta if energy_delta is not None else intent_energy_delta(intent)
+    shifted_target = min(1.0, max(0.0, baseline + energy_shift))
+
+    # Key constraint: explicit override else derived from the intent, measured
+    # against the PREVIOUS neighbor (mixing OUT of the predecessor is the move).
+    prev_key = prev.key if prev else None
+    if allowed_keys is not None:
+        key_filter = {camelot_str(pc) for k in allowed_keys if (pc := parse_camelot(k))}
+        key_filter = key_filter or None
+    else:
+        key_filter = intent_allowed_keys(prev_key, intent)
+
+    # Candidate pool: exclude in-set, BPM pre-filter around the neighbours
+    # (mirrors get_replacements: a +/-2*BPM_TOLERANCE window).
+    q = session.query(Track).filter(Track.id.notin_(set_track_ids))
+    ref_bpms = [t.bpm for t in (prev, nxt) if t and t.bpm and t.bpm > 0]
+    ref_bpm = sum(ref_bpms) / len(ref_bpms) if ref_bpms else 0
+    if ref_bpm and ref_bpm > 0:
+        q = q.filter(
+            Track.bpm.between(ref_bpm * (1 - BPM_TOLERANCE * 2), ref_bpm * (1 + BPM_TOLERANCE * 2))
+        )
+    candidates = q.all()
+
+    picks: list[SlotPick] = []
+    for cand in candidates:
+        # Hard key filter when a constraint is present (drop keyless / off-key).
+        if key_filter is not None:
+            pc = parse_camelot(cand.key)
+            if pc is None or camelot_str(pc) not in key_filter:
+                continue
+        combined, incoming, outgoing = score_replacement(
+            cand, prev, nxt, target_energy=shifted_target,
+            weights=weights, discovery_density=discovery_density,
+        )
+        caveat = _build_caveat(prev, cand, nxt, intent)
+        move = _build_move(prev, cand, nxt, intent, energy_shift, caveat)
+        picks.append(SlotPick(
+            track=cand,
+            from_key=prev.key if prev else None,
+            to_key=cand.key,
+            move=move,
+            energy_shift=round(energy_shift, 3),
+            score=combined,
+            incoming_breakdown=incoming,
+            outgoing_breakdown=outgoing,
+            caveat=caveat,
+        ))
+
+    picks.sort(key=lambda p: p.score, reverse=True)
+    return picks[:n]
````

Verification:
- `.venv/bin/python -m py_compile src/kiku/setbuilder/slot_picks.py` (full behavior in Task 11).

#### Task 3 — schemas.py: SlotSuggestionItem + SlotSuggestionsResponse
Tools: editor
Add after `ReplaceTrackRequest` (:551-552), in the Replace-Track models block. Reuses `TrackResponse` (:25) and `ReplacementBreakdown` (:512) — the `score_replacement` breakdown's extra `vibe`/`artist` keys are dropped upstream (Task 4 filters to `_BD_FIELDS`), so the model stays the replacements shape.
Diff:
````diff
--- a/src/kiku/api/schemas.py
+++ b/src/kiku/api/schemas.py
@@
 class ReplaceTrackRequest(BaseModel):
     new_track_id: int
+
+
+class SlotSuggestionItem(BaseModel):
+    track: TrackResponse
+    from_key: str | None = None
+    to_key: str | None = None
+    move: str
+    energy_shift: float
+    score: float
+    incoming_breakdown: ReplacementBreakdown | None = None
+    outgoing_breakdown: ReplacementBreakdown | None = None
+    caveat: str | None = None
+
+
+class SlotSuggestionsResponse(BaseModel):
+    set_id: int
+    position: int
+    mode: str
+    intent: str
+    allowed_keys: list[str] | None = None
+    energy_delta: float
+    suggestions: list[SlotSuggestionItem]
````

Verification:
- `.venv/bin/python -c "from kiku.api.schemas import SlotSuggestionItem, SlotSuggestionsResponse"`.

#### Task 4 — sets.py: GET /{set_id}/slots/{position}/suggestions endpoint
Tools: editor
Two edits. Edit 4a adds the schema imports; Edit 4b appends the endpoint after `get_artist_picks` (ends :1251). Mirrors `get_replacements` (404 missing set, 404 invalid position) + validates `mode`/`intent`. Empty `suggestions` (200) when the slot is too tight for any owned track.

Edit 4a — imports (add to the block at :16-44, after `SetWaveformTrackResponse` :39):
````diff
--- a/src/kiku/api/routes/sets.py
+++ b/src/kiku/api/routes/sets.py
@@
     SetUpdateRequest,
     SetWaveformTrackResponse,
+    SlotSuggestionItem,
+    SlotSuggestionsResponse,
     TrackSummary,
     TransitionResponse,
     TransitionScoreBreakdown,
     UnmatchedTrack,
 )
````

Edit 4b — append endpoint (after `get_artist_picks`'s final `return ArtistPicksResponse(...)` :1251):
````diff
--- a/src/kiku/api/routes/sets.py
+++ b/src/kiku/api/routes/sets.py
@@
     return ArtistPicksResponse(set_id=set_id, artist=artist, picks=picks)
+
+
+@router.get("/{set_id}/slots/{position}/suggestions", response_model=SlotSuggestionsResponse)
+def get_slot_suggestions(
+    set_id: int,
+    position: int,
+    mode: str = "insert",
+    intent: str = "hold",
+    allowed_keys: str | None = None,
+    energy_delta: float | None = None,
+    n: int = 10,
+    db: Session = Depends(get_db),
+):
+    """Rank owned tracks that make a directional move at a slot, both-neighbor aware.
+
+    ``mode`` (insert|replace) + ``intent`` (push_higher|brighten|cool_down|hold)
+    name the slot and the direction; Kiku answers with tracks the DJ already
+    owns, each reporting the harmonic move and any caveat when the slot resists
+    it. Library excavation only.
+    """
+    from kiku.setbuilder.camelot import intent_energy_delta
+    from kiku.setbuilder.slot_picks import rank_slot_picks
+
+    s = db.get(Set, set_id)
+    if not s:
+        raise HTTPException(status_code=404, detail="Set not found")
+
+    if mode not in ("insert", "replace"):
+        raise HTTPException(status_code=400, detail="mode must be 'insert' or 'replace'")
+    if intent not in ("push_higher", "brighten", "cool_down", "hold"):
+        raise HTTPException(
+            status_code=400,
+            detail="intent must be one of push_higher, brighten, cool_down, hold",
+        )
+
+    ordered = sorted(s.tracks, key=lambda st: st.position)
+    if position < 0 or position >= len(ordered):
+        raise HTTPException(status_code=404, detail="Invalid position")
+
+    keys = None
+    if allowed_keys:
+        keys = {k.strip() for k in allowed_keys.split(",") if k.strip()} or None
+
+    ranked = rank_slot_picks(
+        db, set_id, position, mode, intent,
+        allowed_keys=keys, energy_delta=energy_delta, n=n,
+    )
+
+    _BD_FIELDS = {
+        "harmonic", "energy_fit", "bpm_compat", "genre_coherence",
+        "track_quality", "total", "discovery_label", "set_appearances",
+    }
+
+    def _bd(b: dict | None) -> ReplacementBreakdown | None:
+        if not b:
+            return None
+        return ReplacementBreakdown(**{k: v for k, v in b.items() if k in _BD_FIELDS})
+
+    resolved_delta = energy_delta if energy_delta is not None else intent_energy_delta(intent)
+    suggestions = [
+        SlotSuggestionItem(
+            track=_track_response(p.track),
+            from_key=p.from_key,
+            to_key=p.to_key,
+            move=p.move,
+            energy_shift=p.energy_shift,
+            score=p.score,
+            incoming_breakdown=_bd(p.incoming_breakdown),
+            outgoing_breakdown=_bd(p.outgoing_breakdown),
+            caveat=p.caveat,
+        )
+        for p in ranked
+    ]
+    return SlotSuggestionsResponse(
+        set_id=set_id,
+        position=position,
+        mode=mode,
+        intent=intent,
+        allowed_keys=sorted(keys) if keys else None,
+        energy_delta=round(resolved_delta, 3),
+        suggestions=suggestions,
+    )
````

Verification:
- `.venv/bin/python -m py_compile src/kiku/api/routes/sets.py`.
- Endpoint behavior covered in Task 12.

#### Task 5 — cli.py: kiku slot-suggest command
Tools: editor
Append after `artist_picks_cmd` (ends :475). `click.Choice` validates `mode`/`intent` at the CLI boundary. Warm, never-blame copy; no banned words.
Diff:
````diff
--- a/src/kiku/cli.py
+++ b/src/kiku/cli.py
@@
     console.print(table)
+
+
+@cli.command("slot-suggest")
+@click.argument("set_name_or_id")
+@click.argument("position", type=int)
+@click.option(
+    "--mode",
+    type=click.Choice(["insert", "replace"]),
+    default="insert",
+    help="Grow the set (insert) or swap the track at the slot (replace)",
+)
+@click.option(
+    "--intent",
+    type=click.Choice(["push_higher", "brighten", "cool_down", "hold"]),
+    default="hold",
+    help="The directional move to make at this slot",
+)
+@click.option(
+    "--keys",
+    "allowed_keys",
+    default=None,
+    help="Comma-separated Camelot keys to hard-filter candidates (advanced override)",
+)
+@click.option(
+    "--energy-delta",
+    type=float,
+    default=None,
+    help="Explicit energy-target shift, overriding the intent's shift",
+)
+@click.option("-n", "--num", default=10, help="Number of picks")
+def slot_suggest_cmd(set_name_or_id, position, mode, intent, allowed_keys, energy_delta, num):
+    """Recommend owned tracks that make a directional move at a slot.
+
+    Name a slot and a direction — push_higher, brighten, cool_down, or
+    hold — and Kiku ranks tracks you own that make that move while still
+    mixing out of the track before AND into the track after. Each pick shows the
+    move, the energy shift, and any caveat when the slot resists.
+    """
+    from kiku.db.models import Set, get_session
+    from kiku.setbuilder.slot_picks import rank_slot_picks
+
+    session = get_session()
+
+    # Resolve set by ID or name.
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
+    keys = None
+    if allowed_keys:
+        keys = {k.strip() for k in allowed_keys.split(",") if k.strip()} or None
+
+    picks = rank_slot_picks(
+        session, s.id, position, mode, intent,
+        allowed_keys=keys, energy_delta=energy_delta, n=num,
+    )
+    if not picks:
+        console.print(
+            f"[yellow]No owned track makes a clean {intent.replace('_', ' ')} at slot "
+            f"{position + 1} of '{s.name}' — the slot may be too tight for that move. "
+            f"Try 'hold', or a different direction.[/]"
+        )
+        return
+
+    table = Table(
+        title=f"Slot {position + 1} of '{s.name}' — {mode}, {intent.replace('_', ' ')}"
+    )
+    table.add_column("#", justify="right", style="dim")
+    table.add_column("Title", style="cyan")
+    table.add_column("Artist")
+    table.add_column("Move", style="magenta")
+    table.add_column("Energy", justify="right")
+    table.add_column("Score", justify="right", style="green")
+    table.add_column("Caveat", style="yellow")
+
+    for i, p in enumerate(picks, 1):
+        table.add_row(
+            str(i),
+            p.track.title or "?",
+            p.track.artist or "?",
+            p.move,
+            f"{p.energy_shift:+.2f}",
+            f"{p.score:.3f}",
+            p.caveat or "—",
+        )
+
+    console.print(table)
````

Verification:
- `.venv/bin/python -m py_compile src/kiku/cli.py`.
- `source .venv/bin/activate && kiku slot-suggest <set> 3 --mode insert --intent brighten` prints a ranked Table or a warm empty message.

#### Task 6 — types/index.ts: SlotSuggestion + SlotSuggestionsResponse
Tools: editor
Add after `ArtistPicksResponse` (:557-561). Reuses `Track` (:7) + `ReplacementBreakdown` (:510).
Diff:
````diff
--- a/frontend/src/lib/types/index.ts
+++ b/frontend/src/lib/types/index.ts
@@
 export interface ArtistPicksResponse {
 	set_id: number;
 	artist: string;
 	picks: ArtistPick[];
 }
+
+export interface SlotSuggestion {
+	track: Track;
+	from_key: string | null;
+	to_key: string | null;
+	move: string;
+	energy_shift: number;
+	score: number;
+	incoming_breakdown: ReplacementBreakdown | null;
+	outgoing_breakdown: ReplacementBreakdown | null;
+	caveat: string | null;
+}
+
+export interface SlotSuggestionsResponse {
+	set_id: number;
+	position: number;
+	mode: string;
+	intent: string;
+	allowed_keys: string[] | null;
+	energy_delta: number;
+	suggestions: SlotSuggestion[];
+}
````

Verification:
- Covered by svelte-check (Task 13).

#### Task 7 — api/sets.ts: getSlotSuggestions client
Tools: editor
Two edits: import the type, add the function after `getArtistPicks` (ends :210).

Edit 7a — import (add to the block at :1-17):
````diff
--- a/frontend/src/lib/api/sets.ts
+++ b/frontend/src/lib/api/sets.ts
@@
 	SetWaveformTrack,
+	SlotSuggestionsResponse,
 	TransitionDetail,
 } from '$lib/types';
````

Edit 7b — function (after `getArtistPicks` :210):
````diff
--- a/frontend/src/lib/api/sets.ts
+++ b/frontend/src/lib/api/sets.ts
@@
 	const qs = new URLSearchParams({ artist, n: String(n) });
 	return fetchJson<ArtistPicksResponse>(`/api/sets/${setId}/artist-picks?${qs}`);
 }
+
+export async function getSlotSuggestions(
+	setId: number,
+	position: number,
+	opts: { mode: string; intent: string; allowedKeys?: string; energyDelta?: number; n?: number }
+): Promise<SlotSuggestionsResponse> {
+	const qs = new URLSearchParams({ mode: opts.mode, intent: opts.intent });
+	if (opts.allowedKeys) qs.set('allowed_keys', opts.allowedKeys);
+	if (opts.energyDelta !== undefined) qs.set('energy_delta', String(opts.energyDelta));
+	if (opts.n !== undefined) qs.set('n', String(opts.n));
+	return fetchJson<SlotSuggestionsResponse>(
+		`/api/sets/${setId}/slots/${position}/suggestions?${qs}`
+	);
+}
````

Verification:
- Covered by svelte-check (Task 13).

#### Task 8 — AddSlotPicksPanel.svelte (NEW)
Tools: editor
Mirrors `AddFromArtistPanel.svelte` (floating panel, Svelte 5 runes, `$props`/`$state`/`$derived`). Insert/replace toggle + a slot number input + four named-move buttons (Push higher / Brighten / Cool down / Hold). Ranked cards show the move + caveat; apply routes to `addTrackToSet` (insert) or `replaceTrackInSet` (replace), then `onApplied()`. Voice: "set", warm, never blame; no banned words.
Diff:
````diff
--- /dev/null
+++ b/frontend/src/lib/components/set/AddSlotPicksPanel.svelte
@@
+<script lang="ts">
+	import type { SlotSuggestion } from '$lib/types';
+	import { getSlotSuggestions, addTrackToSet, replaceTrackInSet } from '$lib/api/sets';
+
+	let {
+		setId,
+		trackCount,
+		onApplied,
+		onclose,
+	}: {
+		setId: number;
+		trackCount: number;
+		onApplied: () => void;
+		onclose: () => void;
+	} = $props();
+
+	const MOVES = [
+		{ intent: 'push_higher', label: 'Push higher' },
+		{ intent: 'brighten', label: 'Brighten' },
+		{ intent: 'cool_down', label: 'Cool down' },
+		{ intent: 'hold', label: 'Hold' },
+	];
+
+	let mode = $state<'insert' | 'replace'>('insert');
+	let intent = $state<string | null>(null);
+	// 1-based in the UI; the API/back end is 0-based.
+	let slotDisplay = $state(1);
+	let position = $derived(Math.max(0, Math.min(trackCount - 1, slotDisplay - 1)));
+	let suggestions = $state<SlotSuggestion[]>([]);
+	let loading = $state(false);
+	let searched = $state(false);
+	let error = $state<string | null>(null);
+	let applyingId = $state<number | null>(null);
+
+	async function loadSuggestions(nextIntent: string) {
+		intent = nextIntent;
+		loading = true;
+		searched = true;
+		error = null;
+		try {
+			const res = await getSlotSuggestions(setId, position, { mode, intent, n: 8 });
+			suggestions = res.suggestions;
+		} catch (e) {
+			error = e instanceof Error ? e.message : 'Something went wrong reading your library.';
+			suggestions = [];
+		} finally {
+			loading = false;
+		}
+	}
+
+	async function applyPick(pick: SlotSuggestion) {
+		applyingId = pick.track.id;
+		try {
+			if (mode === 'insert') {
+				await addTrackToSet(setId, pick.track.id, position);
+			} else {
+				await replaceTrackInSet(setId, position, pick.track.id);
+			}
+			onApplied();
+			onclose();
+		} catch (e) {
+			error = e instanceof Error ? e.message : "Couldn't apply that pick.";
+		} finally {
+			applyingId = null;
+		}
+	}
+</script>
+
+<div class="slot-panel">
+	<div class="panel-header">
+		<h3>Directional slot pick</h3>
+		<button class="close-btn" onclick={onclose} aria-label="Close">×</button>
+	</div>
+	<p class="hint">
+		Name a slot and a direction — Kiku ranks tracks you own that make the move
+		while still mixing out of the track before and into the one after.
+	</p>
+
+	<div class="controls">
+		<div class="mode-toggle" role="group" aria-label="Insert or replace">
+			<button class:active={mode === 'insert'} onclick={() => { mode = 'insert'; }}>Insert</button>
+			<button class:active={mode === 'replace'} onclick={() => { mode = 'replace'; }}>Replace</button>
+		</div>
+		<label class="slot-input">
+			Slot
+			<input type="number" min="1" max={trackCount} bind:value={slotDisplay} />
+		</label>
+	</div>
+
+	<div class="moves">
+		{#each MOVES as m (m.intent)}
+			<button
+				class="move-btn"
+				class:active={intent === m.intent}
+				onclick={() => loadSuggestions(m.intent)}
+			>
+				{m.label}
+			</button>
+		{/each}
+	</div>
+
+	{#if loading}
+		<div class="status">Reading your library…</div>
+	{:else if error}
+		<div class="status error">{error}</div>
+	{:else if searched && suggestions.length === 0}
+		<div class="status">
+			No owned track makes that move here cleanly — try Hold, or another direction.
+		</div>
+	{:else}
+		<ul class="picks">
+			{#each suggestions as pick (pick.track.id)}
+				<li class="pick-card">
+					<div class="pick-main">
+						<div class="pick-title">{pick.track.title ?? 'Untitled'}</div>
+						<div class="pick-artist">{pick.track.artist ?? ''}</div>
+						<div class="pick-move">{pick.move}</div>
+						{#if pick.caveat}
+							<div class="pick-caveat">{pick.caveat}</div>
+						{/if}
+					</div>
+					<div class="pick-side">
+						<div class="pick-score">{Math.round(pick.score * 100)}</div>
+						<button
+							class="apply-btn"
+							onclick={() => applyPick(pick)}
+							disabled={applyingId === pick.track.id}
+						>
+							{applyingId === pick.track.id
+								? 'Applying…'
+								: mode === 'insert'
+									? `Insert at ${slotDisplay}`
+									: `Replace ${slotDisplay}`}
+						</button>
+					</div>
+				</li>
+			{/each}
+		</ul>
+	{/if}
+</div>
+
+<style>
+	.slot-panel {
+		position: absolute;
+		top: 56px;
+		right: 16px;
+		z-index: 30;
+		width: 400px;
+		max-height: 72vh;
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
+	.controls {
+		display: flex;
+		align-items: center;
+		gap: 12px;
+		margin-bottom: 10px;
+	}
+	.mode-toggle {
+		display: inline-flex;
+		border: 1px solid var(--border, #2a2b30);
+		border-radius: 6px;
+		overflow: hidden;
+	}
+	.mode-toggle button {
+		background: transparent;
+		border: none;
+		color: var(--text-secondary, #9a9b9f);
+		padding: 5px 10px;
+		font-size: 12px;
+		cursor: pointer;
+	}
+	.mode-toggle button.active {
+		background: var(--accent, #7aa2f7);
+		color: #10131a;
+	}
+	.slot-input {
+		font-size: 12px;
+		color: var(--text-secondary, #9a9b9f);
+		display: inline-flex;
+		align-items: center;
+		gap: 6px;
+	}
+	.slot-input input {
+		width: 56px;
+		padding: 4px 6px;
+		background: var(--surface-2, #23242a);
+		border: 1px solid var(--border, #2a2b30);
+		border-radius: 6px;
+		color: inherit;
+	}
+	.moves {
+		display: flex;
+		flex-wrap: wrap;
+		gap: 6px;
+		margin-bottom: 8px;
+	}
+	.move-btn {
+		font-size: 12px;
+		padding: 5px 10px;
+		border: 1px solid var(--border, #2a2b30);
+		border-radius: 6px;
+		background: transparent;
+		color: var(--text-secondary, #9a9b9f);
+		cursor: pointer;
+	}
+	.move-btn.active {
+		border-color: var(--accent, #7aa2f7);
+		color: var(--accent, #7aa2f7);
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
+	.pick-move {
+		margin-top: 4px;
+		font-size: 12px;
+		color: var(--text-tertiary, #7a7b82);
+	}
+	.pick-caveat {
+		margin-top: 6px;
+		font-size: 12px;
+		color: var(--warn, #e5c07b);
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
+	.apply-btn {
+		font-size: 12px;
+		padding: 5px 9px;
+		border: 1px solid var(--accent, #7aa2f7);
+		border-radius: 6px;
+		background: transparent;
+		color: var(--accent, #7aa2f7);
+		cursor: pointer;
+		white-space: nowrap;
+	}
+	.apply-btn:disabled {
+		opacity: 0.5;
+		cursor: default;
+	}
+</style>
````

Verification:
- Covered by svelte-check (Task 13). Manual E2E: button opens panel, choose insert/replace + slot + a direction, ranked cards show move + caveat, apply inserts/replaces at the slot and the timeline reloads.

#### Task 9 — SetView.svelte: mount AddSlotPicksPanel
Tools: editor
Four edits: import, state flag, MenuItem toggle, panel mount. Reuses `handleTracksChanged` (:355) as the reload path and `selectedSet.track_count` for the slot bound.

Edit 9a — import (after `AddFromArtistPanel` import, :13):
````diff
--- a/frontend/src/lib/components/set/SetView.svelte
+++ b/frontend/src/lib/components/set/SetView.svelte
@@
 	import AddFromArtistPanel from './AddFromArtistPanel.svelte';
+	import AddSlotPicksPanel from './AddSlotPicksPanel.svelte';
````

Edit 9b — state flag (after `let showArtistPicks = $state(false);` :90):
````diff
--- a/frontend/src/lib/components/set/SetView.svelte
+++ b/frontend/src/lib/components/set/SetView.svelte
@@
 	let showArtistPicks = $state(false);
+	let showSlotPicks = $state(false);
````

Edit 9c — MenuItem toggle (after the "Add from an artist" MenuItem :496):
````diff
--- a/frontend/src/lib/components/set/SetView.svelte
+++ b/frontend/src/lib/components/set/SetView.svelte
@@
 						<MenuItem onselect={() => { showArtistPicks = !showArtistPicks; }}>Add from an artist</MenuItem>
+						<MenuItem onselect={() => { showSlotPicks = !showSlotPicks; }}>Directional slot pick</MenuItem>
````

Edit 9d — panel mount (after the `AddFromArtistPanel` block :640-646):
````diff
--- a/frontend/src/lib/components/set/SetView.svelte
+++ b/frontend/src/lib/components/set/SetView.svelte
@@
 	{#if showArtistPicks && selectedSet}
 		<AddFromArtistPanel
 			setId={selectedSet.id}
 			onInserted={handleTracksChanged}
 			onclose={() => { showArtistPicks = false; }}
 		/>
 	{/if}
+
+	{#if showSlotPicks && selectedSet}
+		<AddSlotPicksPanel
+			setId={selectedSet.id}
+			trackCount={selectedSet.track_count}
+			onApplied={handleTracksChanged}
+			onclose={() => { showSlotPicks = false; }}
+		/>
+	{/if}
 </div>
````

Verification:
- Covered by svelte-check (Task 13). Manual E2E per Task 8.

#### Task 10 — tests/test_camelot.py: move-helper additions
Tools: editor
Extend the import line and append tests for the new helpers, including the wheel wrap (`12A→1A` up, `1A→12A` down), brighten flip, cool_down's two-target set, intent→keys (`hold`→None), and intent→energy delta.

Edit 10a — import:
````diff
--- a/tests/test_camelot.py
+++ b/tests/test_camelot.py
@@
-from kiku.setbuilder.camelot import harmonic_score, parse_camelot
+from kiku.setbuilder.camelot import (
+    camelot_str,
+    flip_mode,
+    harmonic_score,
+    intent_allowed_keys,
+    intent_energy_delta,
+    move_targets,
+    parse_camelot,
+    step_wheel,
+)
````

Edit 10b — append tests (after `test_unknown_key`, :44):
````diff
--- a/tests/test_camelot.py
+++ b/tests/test_camelot.py
@@
 def test_unknown_key():
     assert harmonic_score(None, "8A") == 0.5
     assert harmonic_score("8A", None) == 0.5
+
+
+def test_camelot_str():
+    assert camelot_str((9, "A")) == "9A"
+    assert camelot_str((12, "B")) == "12B"
+
+
+def test_step_wheel_wrap():
+    assert step_wheel((8, "A"), 1) == (9, "A")
+    assert step_wheel((8, "A"), -1) == (7, "A")
+    assert step_wheel((12, "A"), 1) == (1, "A")  # wrap up
+    assert step_wheel((1, "A"), -1) == (12, "A")  # wrap down
+
+
+def test_flip_mode():
+    assert flip_mode((8, "A")) == (8, "B")
+    assert flip_mode((8, "B")) == (8, "A")
+
+
+def test_move_targets_push_higher():
+    assert move_targets("8A", "push_higher") == [(9, "A")]
+    assert move_targets("12A", "push_higher") == [(1, "A")]  # wheel wrap
+
+
+def test_move_targets_brighten():
+    assert move_targets("8A", "brighten") == [(8, "B")]
+
+
+def test_move_targets_cool_down():
+    assert move_targets("8A", "cool_down") == [(7, "A")]
+    assert set(move_targets("8B", "cool_down")) == {(7, "B"), (8, "A")}
+
+
+def test_move_targets_hold_and_unparseable():
+    assert move_targets("8A", "hold") == []
+    assert move_targets(None, "push_higher") == []
+    assert move_targets("nonsense", "push_higher") == []
+
+
+def test_intent_allowed_keys():
+    assert intent_allowed_keys("8A", "push_higher") == {"9A"}
+    assert intent_allowed_keys("8A", "brighten") == {"8B"}
+    assert intent_allowed_keys("8B", "cool_down") == {"7B", "8A"}
+    assert intent_allowed_keys("8A", "hold") is None
+    assert intent_allowed_keys(None, "push_higher") is None
+
+
+def test_intent_energy_delta():
+    assert intent_energy_delta("push_higher") == 0.15
+    assert intent_energy_delta("brighten") == 0.05
+    assert intent_energy_delta("cool_down") == -0.15
+    assert intent_energy_delta("hold") == 0.0
````

Verification:
- `source .venv/bin/activate && python -m pytest tests/test_camelot.py -q`.

#### Task 11 — tests/test_slot_picks.py (NEW): ranker
Tools: editor
Uses MagicMock tracks with the proven `test_artist_picks.py` recipe (`audio_features=None`, a real `resolved_energy_zone` tuple, `playlist_tags=None`, numeric quality fields, `.key`/`.bpm`/`.dir_genre`/`.rb_genre`) so the real scoring internals run against mocks. A fake session stubs `.get(Set, id)` + `query(Track)...all()`. Covers both modes' neighbor resolution, the allowed-keys hard filter, energy-shift re-ranking, the honesty/caveat path (resisting successor → alt named), the both-clean path (caveat None), in-set exclusion for replace, and the end-slot single-neighbor case.
Diff:
````diff
--- /dev/null
+++ b/tests/test_slot_picks.py
@@
+"""Unit tests for the directional slot-pick ranker."""
+
+from __future__ import annotations
+
+from unittest.mock import MagicMock
+
+from kiku.setbuilder.slot_picks import rank_slot_picks
+
+
+def _track(track_id, key="8A", bpm=124.0, genre="techno", zone="build"):
+    t = MagicMock()
+    t.id = track_id
+    t.artist = f"Artist {track_id}"
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
+    t.playlist_tags = None
+    # Scoring reads audio_features.energy first, then resolved_energy_zone.
+    t.audio_features = None
+    t.resolved_energy_zone = (zone, "dir_energy", 0.6)
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
+def test_missing_set_returns_empty():
+    session = _make_session(None, [])
+    assert rank_slot_picks(session, 999, 0, "insert", "hold") == []
+
+
+def test_out_of_range_position_returns_empty():
+    in_set = [_track(1), _track(2)]
+    s = _make_set([_set_track(t, i) for i, t in enumerate(in_set)])
+    session = _make_session(s, [_track(10)])
+    assert rank_slot_picks(session, 1, 9, "insert", "hold") == []
+
+
+def test_insert_mode_neighbors_and_ranking():
+    in_set = [_track(1, key="8A"), _track(2, key="8A"), _track(3, key="8A")]
+    s = _make_set([_set_track(t, i) for i, t in enumerate(in_set)])
+    pool = [_track(10 + i, key="8A") for i in range(6)]
+    session = _make_session(s, pool)
+    picks = rank_slot_picks(session, 1, 1, "insert", "hold", n=3)
+    assert len(picks) == 3
+    assert picks[0].score >= picks[1].score >= picks[2].score
+    for p in picks:
+        assert p.caveat is None  # hold never trips the caveat
+
+
+def test_replace_excludes_in_set_track():
+    shared = _track(2, key="8A")
+    in_set = [_track(1, key="8A"), shared, _track(3, key="8A")]
+    s = _make_set([_set_track(t, i) for i, t in enumerate(in_set)])
+    # ilike/BPM prefilter could hand back an in-set track — exclusion must drop it.
+    pool = [shared, _track(20, key="8A")]
+    session = _make_session(s, pool)
+    picks = rank_slot_picks(session, 1, 1, "replace", "hold")
+    ids = {p.track.id for p in picks}
+    assert 2 not in ids
+    assert 20 in ids
+
+
+def test_allowed_keys_hard_filter():
+    in_set = [_track(1, key="8A"), _track(2, key="8A"), _track(3, key="8A")]
+    s = _make_set([_set_track(t, i) for i, t in enumerate(in_set)])
+    pool = [_track(10, key="9A"), _track(11, key="8B"), _track(12, key="9A")]
+    session = _make_session(s, pool)
+    picks = rank_slot_picks(
+        session, 1, 1, "replace", "hold", allowed_keys={"9A"}
+    )
+    assert {p.track.id for p in picks} == {10, 12}
+
+
+def test_energy_shift_reranks():
+    # Two candidates identical but for energy zone; the shift decides the order.
+    in_set = [_track(1, key="8A"), _track(2, key="8A"), _track(3, key="8A")]
+    s = _make_set([_set_track(t, i) for i, t in enumerate(in_set)])
+    hot = _track(10, key="8A", zone="peak")
+    cool = _track(11, key="8A", zone="warmup")
+    session = _make_session(s, [hot, cool])
+    # Shift the target UP → the hotter track ranks first.
+    up = rank_slot_picks(session, 1, 1, "replace", "hold", energy_delta=0.4)
+    assert up[0].track.id == 10
+    # Shift the target DOWN → the cooler track ranks first.
+    down = rank_slot_picks(session, 1, 1, "replace", "hold", energy_delta=-0.4)
+    assert down[0].track.id == 11
+
+
+def test_caveat_names_achievable_alt():
+    # prev 8A, next 7B: a push_higher (candidate 9A) mixes clean out of 8A
+    # (0.85) but clashes into 7B (0.2) — the alt brighten (8A→8B) keeps both
+    # sides >= 0.8, so the caveat must recommend brighten to 8B.
+    in_set = [_track(1, key="8A"), _track(2, key="10A"), _track(3, key="7B")]
+    s = _make_set([_set_track(t, i) for i, t in enumerate(in_set)])
+    pool = [_track(10, key="9A")]  # matches push_higher's allowed key {9A}
+    session = _make_session(s, pool)
+    picks = rank_slot_picks(session, 1, 1, "replace", "push_higher")
+    assert len(picks) == 1
+    assert picks[0].caveat is not None
+    assert "brighten" in picks[0].caveat
+    assert "8B" in picks[0].caveat
+
+
+def test_no_caveat_when_both_sides_clean():
+    # prev 8A, next 9A: push_higher candidate 9A mixes 0.85 out, 1.0 in — clean.
+    in_set = [_track(1, key="8A"), _track(2, key="10A"), _track(3, key="9A")]
+    s = _make_set([_set_track(t, i) for i, t in enumerate(in_set)])
+    pool = [_track(10, key="9A")]
+    session = _make_session(s, pool)
+    picks = rank_slot_picks(session, 1, 1, "replace", "push_higher")
+    assert len(picks) == 1
+    assert picks[0].caveat is None
+
+
+def test_end_slot_single_neighbor():
+    # Insert at the last slot → prev = last track, next = None (one neighbor).
+    in_set = [_track(1, key="8A"), _track(2, key="8A")]
+    s = _make_set([_set_track(t, i) for i, t in enumerate(in_set)])
+    pool = [_track(10, key="8A")]
+    session = _make_session(s, pool)
+    picks = rank_slot_picks(session, 1, 1, "insert", "hold")
+    assert len(picks) == 1
+    assert picks[0].caveat is None  # no successor to assess
````

Verification:
- `source .venv/bin/activate && python -m pytest tests/test_slot_picks.py -q`.

#### Task 12 — tests/api/test_slot_suggestions_api.py (NEW): endpoint
Tools: editor
Uses `client` + `db_session` from `tests/api/conftest.py`. The seed keys are only `8A` (even ids) / `8B` (odd ids), set 1 holds ids 1-5. `brighten`/`hold` are directly testable; `push_higher` (needs `9A`) returns the warm-empty path on the default seed and is proven positively by inserting a purpose-keyed `9A` track. For a `brighten` insert at position 1, `prev = ordered[1]` = track 2 (`8A`) → allowed key `{8B}` → the seed's odd-id `8B` tracks (7,9,11,13,15,17) fall in the BPM window.
Diff:
````diff
--- /dev/null
+++ b/tests/api/test_slot_suggestions_api.py
@@
+"""Integration tests for GET /api/sets/{set_id}/slots/{position}/suggestions."""
+
+from __future__ import annotations
+
+from kiku.db.models import Track
+
+
+def test_brighten_insert_ranked(client):
+    # Insert at slot 1 → prev = track 2 (8A) → brighten targets 8B; seed's
+    # odd-id 8B tracks (not in set) qualify.
+    resp = client.get(
+        "/api/sets/1/slots/1/suggestions",
+        params={"mode": "insert", "intent": "brighten"},
+    )
+    assert resp.status_code == 200
+    body = resp.json()
+    assert body["set_id"] == 1
+    assert body["position"] == 1
+    assert body["mode"] == "insert"
+    assert body["intent"] == "brighten"
+    suggestions = body["suggestions"]
+    assert len(suggestions) >= 1
+    ids = {sg["track"]["id"] for sg in suggestions}
+    assert ids.isdisjoint({1, 2, 3, 4, 5})  # in-set tracks excluded
+    for sg in suggestions:
+        assert sg["move"]  # Show the Why — never a bare ranked list
+        assert "caveat" in sg
+    scores = [sg["score"] for sg in suggestions]
+    assert scores == sorted(scores, reverse=True)
+
+
+def test_hold_ranked(client):
+    resp = client.get(
+        "/api/sets/1/slots/2/suggestions",
+        params={"mode": "insert", "intent": "hold"},
+    )
+    assert resp.status_code == 200
+    assert len(resp.json()["suggestions"]) >= 1
+
+
+def test_push_higher_warm_empty_on_default_seed(client):
+    # prev key is 8A → push_higher needs a 9A candidate; the seed has none.
+    resp = client.get(
+        "/api/sets/1/slots/1/suggestions",
+        params={"mode": "insert", "intent": "push_higher"},
+    )
+    assert resp.status_code == 200
+    assert resp.json()["suggestions"] == []
+
+
+def test_push_higher_with_seeded_key(client, db_session):
+    # Add a purpose-keyed 9A track in the neighbours' BPM window.
+    db_session.add(Track(
+        id=99, title="Lift", artist="Purpose", bpm=123.0, key="9A",
+        dir_genre="techno", dir_energy="high", duration_sec=320.0,
+        rating=4, play_count=5, kiku_play_count=1,
+    ))
+    db_session.commit()
+    resp = client.get(
+        "/api/sets/1/slots/1/suggestions",
+        params={"mode": "insert", "intent": "push_higher"},
+    )
+    assert resp.status_code == 200
+    ids = {sg["track"]["id"] for sg in resp.json()["suggestions"]}
+    assert 99 in ids
+
+
+def test_missing_set_404(client):
+    resp = client.get(
+        "/api/sets/9999/slots/0/suggestions",
+        params={"mode": "insert", "intent": "hold"},
+    )
+    assert resp.status_code == 404
+
+
+def test_invalid_mode_400(client):
+    resp = client.get(
+        "/api/sets/1/slots/0/suggestions",
+        params={"mode": "sideways", "intent": "hold"},
+    )
+    assert resp.status_code == 400
+
+
+def test_invalid_intent_400(client):
+    resp = client.get(
+        "/api/sets/1/slots/0/suggestions",
+        params={"mode": "insert", "intent": "levitate"},
+    )
+    assert resp.status_code == 400
+
+
+def test_out_of_range_position_404(client):
+    resp = client.get(
+        "/api/sets/1/slots/99/suggestions",
+        params={"mode": "insert", "intent": "hold"},
+    )
+    assert resp.status_code == 404
````

Verification:
- `source .venv/bin/activate && python -m pytest tests/api/test_slot_suggestions_api.py -q`.

#### Task 13 — Lint / type-check (changed files)
Tools: shell
ruff is NOT installed — use `py_compile` for Python. Capture the svelte-check baseline (currently 0 errors, 4 warnings from the 020 slice) — only NEW errors are failures.
Commands:
- `source .venv/bin/activate && python -m py_compile src/kiku/setbuilder/camelot.py src/kiku/setbuilder/slot_picks.py src/kiku/api/schemas.py src/kiku/api/routes/sets.py src/kiku/cli.py tests/test_camelot.py tests/test_slot_picks.py tests/api/test_slot_suggestions_api.py`
- `cd /home/mantis/Development/mantis-dev/waveform-builer/frontend && npx svelte-check --tsconfig ./tsconfig.json 2>&1 | tail -3` (expect `0 errors`; warnings unchanged from baseline)
- `source .venv/bin/activate && python -m pytest tests/ -q` (full backend suite; the new camelot/slot_picks/API tests green — note the 5 pre-existing `test_energy.py` failures are unrelated to this spec)

Expectations:
- All `py_compile` succeed; svelte-check 0 errors; new tests pass; no regression beyond the known `test_energy.py` baseline.

#### Task 14 — Commit changed files
Tools: git
Commit ONLY the files created/modified in Tasks 1-12 (leave untracked `trees/`, `BACKEND_MIGRATION.md`, `SOUNDCLOUD_EXPORT.md`, `scripts/sc_feasibility_spike.py`, `frontend/test-results/`). Never commit to main.
Commands:
- `cd <directional-slot-picks worktree root> && git branch --show-current` (expect `directional-slot-picks`; abort if `main`)
- `git add src/kiku/setbuilder/camelot.py src/kiku/setbuilder/slot_picks.py src/kiku/api/schemas.py src/kiku/api/routes/sets.py src/kiku/cli.py frontend/src/lib/types/index.ts frontend/src/lib/api/sets.ts frontend/src/lib/components/set/AddSlotPicksPanel.svelte frontend/src/lib/components/set/SetView.svelte tests/test_camelot.py tests/test_slot_picks.py tests/api/test_slot_suggestions_api.py`
- Commit message:
  ```
  spec(024): IMPLEMENT - directional slot recommendations (camelot moves, ranker, API, CLI, UI)

  Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
  ```

### Validate

Each Human Section requirement → compliance note with task/line refs.

- **HLO: name a slot + a direction; rank owned tracks that make the move while mixing out of the track before AND into the track after; each reports the harmonic MOVE + why; library only** (L5): `rank_slot_picks` resolves `(prev, next)` by mode and scores via `score_replacement` against both neighbors; every `SlotPick` carries `move` + `caveat` + breakdowns; candidate pool is the DJ's own library minus in-set ids (Task 2). Surfaced via API/CLI/UI (Tasks 4,5,8).
- **HLO: serves Arc / Grow-the-Ear / Opinions-you-can-see-through** (L5): both-neighbor scoring judges the slot against the flow (Arc); the `move` string + caveat teach the harmonic move (Grow-the-Ear); `move` + `energy_shift` + `incoming/outgoing_breakdown` show the math (Opinions) — Tasks 2,3,4.
- **MLO: Camelot move helpers enumerate target key(s) per named move; map intent → allowed_keys + energy shift; unit-tested standalone** (L8): `move_targets`, `intent_allowed_keys`, `intent_energy_delta`, `step_wheel` (wrap), `flip_mode`, `camelot_str` in `camelot.py` (Task 1); proven in Task 10.
- **MLO: ranker module with mode/intent + optional allowed_keys/energy_delta; reuses score_replacement on BOTH neighbors; hard-filters by allowed keys; scores against the shifted energy target; returns ranked owned tracks with move + caveat** (L9): `rank_slot_picks(... mode, intent, allowed_keys, energy_delta ...)` (Task 2) — `shifted_target = clamp(baseline + shift)`, key hard-filter, `score_replacement` reuse; proven Task 11.
- **MLO: API `GET /sets/{id}/slots/{position}/suggestions?mode=&intent=&allowed_keys=&energy_delta=&n=` mirroring replacements + per-candidate move/caveat** (L10): Task 4 endpoint returns `SlotSuggestionsResponse{...suggestions:[{track,from_key,to_key,move,energy_shift,score,incoming/outgoing_breakdown,caveat}]}`.
- **MLO: CLI `kiku slot-suggest <set> <position> --mode --intent [--allowed-keys --energy-delta]` — warm ranked table with move/why/caveat** (L11): Task 5 `slot-suggest` (`--keys` flag maps to the `allowed_keys` param), rich Table with Move / Energy / Score / Caveat columns; warm empty message.
- **MLO: frontend slot affordance — insert/replace + named-move buttons + ranked cards with move+caveat + one-click apply** (L12): Task 8 `AddSlotPicksPanel` (mode toggle + Push higher/Brighten/Cool down/Hold + slot input), cards show `move` + `caveat`, apply via `addTrackToSet` (insert) / `replaceTrackInSet` (replace); mounted Task 9.
- **MLO: tests — camelot helper, ranker (both modes/filter/shift/caveat), API** (L13): Tasks 10, 11, 12.
- **DT: two modes — insert neighbors N/N+1 (set grows), replace neighbors N-1/N+1 (swap)** (L23-26): `_resolve_neighbors` (Task 2); proven `test_insert_mode_neighbors_and_ranking` + `test_replace_excludes_in_set_track` (Task 11).
- **DT: direction — push_higher +1 same letter, brighten mode flip, cool_down -1 or B→A, hold no shift; + allowed_keys/energy_delta overrides** (L27-37): `move_targets` per intent + `intent_energy_delta` (Task 1); explicit override precedence in `rank_slot_picks` (Task 2, `allowed_keys is not None` / `energy_delta is not None`).
- **DT: honesty constraint — never silently return a bad transition; name the achievable move / the anchor that resists; every candidate reports the move** (L39-40): `_build_caveat` (T=0.8 detection + `_achievable_alt`) names the resisting successor and the achievable alt; `_build_move` always states the move (Task 2); proven `test_caveat_names_achievable_alt` + `test_no_caveat_when_both_sides_clean` (Task 11).
- **DT: reuse score_replacement (both-neighbor), get_replacements machinery, target_energy_at; new camelot helpers** (L42-47): `score_replacement` is the sole scorer; energy-profile parse + BPM prefilter + in-set exclusion mirror `get_replacements`; `target_energy_at` shifted by the intent (Task 2).
- **DT: library excavation only; allowed_keys HARD filter (hold none); honesty over silence; Show the Why; warm voice / no banned words; warm edge cases; DO NOT OVERCOMPLICATE** (L49-56): pool from local `Track` query minus in-set (Task 2); `key_filter` hard-drops off-key when a constraint is present, `hold`→None; caveat surfaces the ceiling; `move`+breakdown on every pick; CLI/UI copy uses "set"/"flow", warm empty messages, no banned words (Tasks 5,8); minimal helper+ranker+endpoint+CLI+one panel reusing the replacements machinery.
- **DT: testing — camelot enumeration + wrap + intent maps; ranker both modes/filter/shift/caveat; API 200+move+caveat/mode+intent parse/overrides/in-set exclusion/404/out-of-range warm** (L58-62): Tasks 10, 11, 12 cover each; the `push_higher` seed gotcha handled by a warm-empty assertion plus a purpose-keyed positive test.
- **DT: E2E manual acceptance — open set, pick slot, choose insert/replace + direction, cards show move+caveat, one-click apply** (L62): Task 8/9 verification notes the manual flow.
- **Behavior: reuse score_replacement + the replacements endpoint machinery (no parallel path); camelot moves as clean tested functions; make the honesty caveat real** (L64-65): Task 1 (standalone tested camelot vocabulary), Task 2 (reuses `score_replacement`, no new scorer; `_build_caveat` is the teaching), Task 4 (mirrors `get_artist_picks`/`get_replacements`).

## Plan Review
<!-- Filled if required to validate plan -->

## Implement

### TODO
1. Camelot move helpers (`src/kiku/setbuilder/camelot.py`) — Status: Done
2. Ranker `slot_picks.py` (`src/kiku/setbuilder/slot_picks.py`) — Status: Done (see deviation)
3. Schemas `SlotSuggestionItem` + `SlotSuggestionsResponse` (`src/kiku/api/schemas.py`) — Status: Done
4. API endpoint `GET /{set_id}/slots/{position}/suggestions` (`src/kiku/api/routes/sets.py`) — Status: Done
5. CLI `kiku slot-suggest` (`src/kiku/cli.py`) — Status: Done
6. Frontend types (`frontend/src/lib/types/index.ts`) — Status: Done
7. Frontend API client `getSlotSuggestions` (`frontend/src/lib/api/sets.ts`) — Status: Done
8. Frontend `AddSlotPicksPanel.svelte` (NEW) — Status: Done
9. Frontend mount in `SetView.svelte` — Status: Done
10. Unit tests `tests/test_camelot.py` — Status: Done (16 passed)
11. Unit tests `tests/test_slot_picks.py` (NEW) — Status: Done (9 passed)
12. API tests `tests/api/test_slot_suggestions_api.py` (NEW) — Status: Done (8 passed)
13. Lint / type-check / full suite — Status: Done (406 passed; svelte-check 0 errors/0 warnings)
14. Commit — Status: Done (see hash below)

### Notes & Deviations
- All planned diffs applied against the real file content with no context drift; anchor line refs were accurate.
- **Task 2 / Task 11 deviation (in-set exclusion):** the Task 2 diff excluded in-set tracks purely via the SQL `Track.id.notin_(set_track_ids)` query filter. The Task 11 unit test `test_replace_excludes_in_set_track` uses a pure `MagicMock` session whose `.filter()` is a no-op, so the SQL-only exclusion was not observable and the test failed (an in-set track leaked into `pool.all()`). Fix: added an explicit Python-side guard at the top of the candidate loop in `rank_slot_picks` (`if cand.id in set_track_ids: continue`). This is defensive (a library function may be called with any pool), keeps the exclusion testable, and changes no scoring numbers. Production DB behavior is unchanged (SQL filter still runs); the API test also asserts exclusion via `isdisjoint({1..5})`.
- **Task 11 caveat/harmonic scenario reproduced exactly as planned:** prev `8A`, next `7B`, candidate `9A` → `h_in = harmonic_score(8A,9A) = 0.85`, `h_out = harmonic_score(9A,7B) = 0.2`; `_achievable_alt` selected `brighten → 8B` (both sides ≥ 0.8: `h(8A,8B)=0.8`, `h(8B,7B)=0.85`). Caveat contains "brighten" and "8B" as expected. No expectation adjustment needed.
- **Task 11 energy-shift scenario:** zone→numeric peak=0.9 / warmup=0.25; energy_delta +0.4 ranks the peak track first, −0.4 ranks the warmup track first. Reproduced as planned.
- **Task 12 push_higher seed gotcha handled per Plan:** default seed has only 8A/8B, so `push_higher` (needs 9A) is asserted via the warm-empty path plus a purpose-keyed 9A track (id=99) inserted in-test for the positive case.
- **Task 13 baseline differs from Plan (better):** svelte-check reported **0 errors, 0 warnings** across 337 files (the Plan noted a 4-warning 020-slice baseline — not present on this branch). Full backend suite = **406 passed, 0 failures**; the Plan's anticipated ~5 pre-existing `test_energy.py` failures are NOT present on this branch (`test_energy.py` passes). Only unrelated `datetime.utcnow` DeprecationWarnings remain.
- **Environment note (no committed change):** the worktree frontend had no `node_modules`/`.svelte-kit`. To type-check, symlinked the main repo's `node_modules` into the worktree and ran `svelte-kit sync` to generate the worktree's `.svelte-kit`. Both are gitignored — nothing outside the Plan's file list is committed.


## Test Evidence & Outputs
<!-- Filled by explicit testing after /spec IMPLEMENT -->

## Updated Doc
<!-- Filled by explicit documentation udpates after /spec IMPLEMENT -->

## Post-Implement Review

Adversarial post-hoc review (branch `spec-024-review`, code already on `main`). Every finding traced against the committed lines; areas that verified clean are stated as such rather than padded with invented issues.

### Verdict

**Ship-quality, with one must-fix honesty defect in the `move` copy.** The core machinery is correct and well-tested where it counts: the Camelot wheel-wrap math, the mode-flip direction, insert/replace neighbour indexing + self-exclusion, `allowed_keys` normalization/override, the energy-shift override + clamp, and the caveat *detection* logic (which side resists) are all right. The one real problem is that the human-readable `move` string asserts a mix is "clean" without ever checking the harmonic — and it does so on the **default** `intent=hold` path, so it is trivially reachable and directly contradicts the feature's stated soul ("Never silently return a bad transition… Show the why, don't hide the math," Human §39-40, §53-54). That is a must-fix. Everything else is should-fix/nit polish.

### Findings (ranked)

#### 1. [must-fix] `move` string claims "mixes into {next} clean" without verifying the harmonic — false on the default `hold` path
- **File**: `src/kiku/setbuilder/slot_picks.py:125-136` (`_build_move`), reached for every non-caveat pick from `rank_slot_picks` (`:227`).
- **Defect**: `_build_move` appends `", mixes into {nxt.key} clean."` whenever `caveat is None and nxt is not None`. But `caveat` is `None` in three distinct cases, and only one of them is actually clean:
  1. both sides genuinely `>= 0.8` (legit),
  2. `intent == "hold"` — `_build_caveat` returns `None` unconditionally at `:103` regardless of harmonics,
  3. explicit `allowed_keys` override where the incoming side is unclean (`h_in < CLEAN_THRESHOLD` → early `return None` at `:107`).
  In cases (2) and (3) the word "clean" is asserted over a harsh clash. The harmonic is never recomputed in `_build_move`, so the claim is decoupled from reality.
- **Failure scenario (default flow, no overrides)**: a set whose fixed neighbours are `8A` and `5A`; DJ runs `kiku slot-suggest <set> <slot> --intent hold` (or the UI "Hold" button, or `GET …?intent=hold`, the API default). A candidate keyed `8A` mixes out of `8A` at 1.0 but into `5A` at `harmonic_score("8A","5A") = 0.2` (three steps → clash). The pick renders: `"8A → 8A hold, +0.00 energy, mixes into 5A clean."` Kiku labels a key clash a clean mix — the exact thing the honesty constraint forbids. (The score/ranking itself is honest; only the teaching copy lies.) Secondary smell: `hold` still prints `from → to` with a key change and the label "hold," which reads contradictorily.
- **Suggested fix**: in `_build_move`, compute `h_out = harmonic_score(cand.key, nxt.key)` (and optionally `h_in`) and only emit the "clean" clause when `h_out >= CLEAN_THRESHOLD`; otherwise state the mix honestly (e.g. `"…, mixes into {nxt.key} (tighter than ideal)"`), or drop the adjective. This keeps the copy truthful on `hold` and on explicit-key overrides without touching the ranking.

#### 2. [should-fix] The `move`-string honesty is entirely untested — nothing asserts the "clean" claim, so finding #1 slipped through
- **File**: `tests/test_slot_picks.py` (whole file) and `tests/api/test_slot_suggestions_api.py:26` (only asserts `sg["move"]` is truthy, never its content).
- **Defect**: caveat *presence/absence* is tested (`test_caveat_names_achievable_alt`, `test_no_caveat_when_both_sides_clean`), but no test asserts the actual `move` text for a candidate that clashes into the fixed successor on a `hold` (or explicit-keys) suggestion. So the false-"clean" copy is uncovered.
- **Failure scenario**: the bug in #1 is green across 406 tests because no assertion ever inspects the move string of a harmonically-clashing pick.
- **Suggested fix**: add a `hold` case with neighbours `8A`/`5A` and a `5A`-clashing candidate asserting the `move` string does NOT contain "clean" (after the #1 fix), plus a keyless-neighbour case (below).

#### 3. [should-fix] Keyless / unparseable-key neighbour and candidate behaviour is unverified
- **File**: `src/kiku/setbuilder/slot_picks.py:105-107` (caveat uses `harmonic_score`, which returns `0.5` neutral for a `None`/unparseable key), `:218-221` (candidate key filter).
- **Defect**: the logic *handles* keyless data correctly by design — a `0.5` neutral score is `< 0.8`, so a keyless successor can't spuriously report "clean," and `parse_camelot(cand.key) is None` drops keyless candidates when a filter is active — but none of this is exercised by a test. The Human Section §55 explicitly calls out keyless/edge handling as in-scope.
- **Failure scenario**: a future refactor that, say, made `harmonic_score` raise or return `1.0` on `None` would break the honesty guard silently, with no test to catch it.
- **Suggested fix**: add a ranker test where `nxt.key = None` (assert no false "clean", no crash) and one where a candidate has `key=None` under an active `allowed_keys`/intent filter (assert it is dropped).

#### 4. [nit] An all-invalid explicit `allowed_keys` silently degrades to "no filter" while the response still echoes the requested keys
- **File**: `src/kiku/setbuilder/slot_picks.py:193-195` (`key_filter = {…} or None`) and `src/kiku/api/routes/sets.py:1332` (`allowed_keys=sorted(keys)` echoed regardless).
- **Defect**: if every supplied key is unparseable (e.g. `--keys "Hmm"`), the set-comprehension yields `{}`, `or None` collapses it to `None`, and the hard filter is skipped — the DJ gets the full unfiltered candidate list, yet the API context reports `allowed_keys: ["Hmm"]` as if honoured.
- **Failure scenario**: `GET …?allowed_keys=xyz&intent=hold` returns unrelated tracks with `allowed_keys:["xyz"]` in the context — a silent no-op filter that looks applied.
- **Suggested fix**: distinguish "no keys given" from "keys given but none parsed"; in the latter case return an empty result (or surface a warm note), or echo the resolved (parsed) key set rather than the raw input.

#### 5. [nit] `_achievable_alt` names a move the DJ may own no track for
- **File**: `src/kiku/setbuilder/slot_picks.py:73-92`, used by `_build_caveat:110`.
- **Defect**: the achievable-alt search enumerates theoretical `move_targets` and picks the best-harmonic one without checking the candidate pool contains a track in that key. The caveat can therefore recommend, e.g., a `brighten (8A→8B)` when the library has no clean `8B` in the BPM window.
- **Failure scenario**: caveat says "the cleanest move here is a brighten (8A→8B)" but a follow-up `brighten` search returns empty. This is teaching-acceptable per the spec (it names the *move*, not a specific track), so only a nit — worth a doc note or a "if you own one" hedge.

#### 6. [nit] Caveat copy "pulls back toward it" has a dangling referent; spec pattern named the key
- **File**: `src/kiku/setbuilder/slot_picks.py:115` — `f"The next track ({nxt.key}) pulls back toward it, …"`.
- **Defect**: "toward **it**" has no antecedent (the Research §159 pattern was "Track {N+1} pulls back toward {next.key}"). Reads slightly off for a feature whose caveat *is* the teaching. Voice-only; no behavioural impact.
- **Suggested fix**: e.g. `"The next track ({nxt.key}) pulls back toward its own key, …"` or restore the spec's phrasing.

#### 7. [nit] CLI flag is `--keys`, Human §MLO wrote `--allowed-keys`; and the endpoint double-loads the set
- **Files**: `src/kiku/cli.py:493-498` (`--keys` vs the Human Section's `--allowed-keys`; Plan Task 5 chose `--keys`, so this is a spec-wording drift, not a bug); `src/kiku/api/routes/sets.py:1277-1291` loads + sorts the set, then `rank_slot_picks:158-162` re-loads + re-sorts it. Minor duplicate DB work per request (mild vs the "EFFICIENCY in every implementation" principle). Neither is worth a code change on its own; noting for completeness.

### Verified clean (no action)
- **Wheel-wrap math** (`camelot.py:131-138`): `((num-1+delta)%12)+1` — `12A` push_higher → `1A`, `1A` cool_down → `12A` both correct (Python's `-1 % 12 == 11`); covered by `test_step_wheel_wrap` and `test_move_targets_push_higher`.
- **Mode-flip direction** (`camelot.py:141-144`, `:160-168`): `brighten` A→B and `cool_down` B-key adds B→A, not inverted; covered.
- **Insert vs replace indexing** (`slot_picks.py:57-70`): insert → `(N, N+1)`, replace → `(N-1, N+1)` with the track at N excluded via `set_track_ids` (`:164, :201`) plus the explicit `:215-216` guard; tail/single-neighbour handled (`test_end_slot_single_neighbour`, `test_replace_excludes_in_set_track`).
- **Caveat resisting-anchor labelling** (`slot_picks.py:107`): because intent-derived candidates always satisfy `h_in >= T`, the caveat can only fire when the *successor* is the resister — so "the next track pulls back" is never mislabelled on the intent path; the explicit-keys unclean-incoming case correctly suppresses the caveat.
- **`allowed_keys` normalization + override** (`slot_picks.py:193-197, :218-221`): `parse_camelot`→`camelot_str` round-trip makes `"8a"`, `"Am"` and `"8A"` all match; explicit keys override (not intersect) the intent-derived set, per spec.
- **Energy shift** (`slot_picks.py:187-188`): explicit `energy_delta` overrides the intent's shift and the shifted target is clamped to `[0,1]`; `test_energy_shift_reranks` covers direction.
- **DB access pattern**: raw SQLAlchemy (no `handlePromise`) matches the existing `get_replacements`/`artist_picks` Python convention — the handlePromise guidance is the TS/backend rule, not applicable here. Frontend `AddSlotPicksPanel.svelte` uses no `as`/`!`, warm never-blame copy, no banned words.

### Resolution (applied post-review, branch `spec-024-review`)

- **#1 (must-fix) — FIXED.** `_build_move` (`slot_picks.py:132-140`) now recomputes `h_out = harmonic_score(cand.key, nxt.key)` and only emits "mixes into {next} clean" when `h_out >= CLEAN_THRESHOLD`; otherwise it says "the blend into {next} is a stretch." The `hold` default and explicit-key paths can no longer label a clash clean.
- **#2 (should-fix) — CLOSED.** Added `test_move_string_never_calls_a_clash_clean` (8A→5A `hold` clash asserts no "clean") and `test_move_string_reports_clean_when_outgoing_holds` (8A→8A asserts "clean") in `tests/test_slot_picks.py`.
- **#3 (should-fix) — CLOSED.** Added `test_keyless_successor_never_reported_clean` and `test_keyless_candidate_dropped_under_key_filter` — locks the keyless-neighbour honesty guard and the keyless-candidate drop under an active filter.
- **#4–#7 (nits) — ACCEPTED / backlogged.** Not fixed here: #4 all-invalid `allowed_keys` silent no-op (echo raw vs resolved keys), #5 alt names a move the pool may lack a track for (teaching-acceptable per spec), #6 "pulls back toward it" dangling referent (voice), #7 `--keys` naming drift + endpoint double-loads the set (minor duplicate query). Candidates for a follow-up polish pass, none behaviour-critical.
- Full backend suite **410 passed** (was 406; +2 move-string, +2 keyless), svelte-check unaffected.

### Polish pass (applied, branch `spec-024-polish`)

- **#4 — FIXED.** All-invalid explicit `allowed_keys` no longer silently disables the filter. `rank_slot_picks` drops the `or None` collapse so an empty-after-parse filter matches nothing (`slot_picks.py:199-205`); the endpoint canonicalizes keys and echoes the *resolved* set, never raw invalid input (`routes/sets.py`). New `test_all_invalid_allowed_keys_returns_empty_not_unfiltered`.
- **#5 — FIXED (copy hedge).** The caveat now hedges "the cleanest move here **(if you own one)**…" since `_achievable_alt` names a move, not a guaranteed-owned track (`slot_picks.py:114-118`).
- **#6 — FIXED.** "pulls back toward **it**" → "pulls back toward **its own key**" (dangling referent).
- **#7 (naming) — FIXED.** CLI now accepts `--allowed-keys` as an alias of `--keys` (`cli.py:493-499`).
- **#7 (double-load) — NOT changed (intentional).** The endpoint's `db.get(Set, id)` and the ranker's are the same SQLAlchemy session → the second is an identity-map hit, not a second query; the only duplication is an in-memory sort of a few dozen rows. Adding a pass-through param to dedupe it wasn't worth the complexity (DO NOT OVERCOMPLICATE).
- Full backend suite **411 passed**; svelte-check 0/0.
