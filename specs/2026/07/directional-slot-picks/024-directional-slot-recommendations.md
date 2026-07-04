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
