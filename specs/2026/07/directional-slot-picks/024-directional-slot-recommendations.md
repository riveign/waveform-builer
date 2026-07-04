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
