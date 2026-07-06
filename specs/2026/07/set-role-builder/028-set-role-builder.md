# Human Section
Critical: any text/subsection here cannot be modified by AI.

## High-Level Objective (HLO)
Wire the **set-role tags** (opener / closer / break) shipped in spec 027 into the **auto-builder**, so
a DJ's curation actually shapes **generated** sets — not just manual tagging + filtering. When you've
told Kiku which tracks are great openers or closers, the builder should *listen*: favour an opener for
the first slot and a closer for the last — and **tell you why it did**.

This is the v2 follow-up to spec 027 (merged to main via PR #37). It is deliberately **phased**: this
spec covers opener→first, closer→last, and multi-role filtering; break→dips is the next spec (029).

## Mid-Level Objectives (MLO)
- **BIAS** seed selection toward **opener**-tagged tracks (opener → first slot), as a soft preference.
- **BIAS** the final/trailing slot toward **closer**-tagged tracks (closer → last slot), as a soft
  preference.
- **UPGRADE** the library role filter from single-active to **multi-role OR-filtering** (accept several
  active roles at once, OR-matched) — backend list param + frontend multi-active chip-toggles.
- **SURFACE the WHY**: whenever a role influenced a build choice, the set explains it in plain,
  teaching language ("Opened with X — you marked it a great opener"). MANDATORY.
- **ENSURE** the bias never forces a musically weak transition and never removes a non-tagged track
  from eligibility (soft, non-restrictive — carried over from spec 027).

## Details (DT)

### Scope — spec 028 (phased, confirmed with user)
**IN:**
1. **opener → first slot** — soft-bias seed selection toward opener-tagged tracks.
2. **closer → last slot** — soft-bias the final/trailing slot toward closer-tagged tracks.
3. **multi-role OR-filter** — the library filter accepts multiple active roles, OR-matched (upgrades
   the v1 single-active scalar filter).
4. **"Show the Why" teaching** — plain-language explanation wherever a role shaped a build decision.

**OUT (deferred to a FAST FOLLOW-UP, spec 029 — document as the next step, do NOT build here):**
- **break → energy dips**: favour break-tagged tracks when filling a slot whose target energy is a
  local low point in the curve. Break is the least-defined and riskiest piece.

### Critical design direction (confirmed with user)
- **SOFT BIAS, not hard placement.** Roles are a **preference/bonus, never a rule.** An opener-tagged
  track is *favoured* for the first slot, but a clearly better-scoring untagged track can still win.
  This preserves the Kiku anti-principle **"Not a DJ autopilot"** and Principle 6 **"Every Track
  Deserves a Chance"**: a role must NEVER force a musically weak transition just to honour a tag, and
  must NEVER remove a non-tagged track from eligibility (non-restrictive, carried from spec 027).
- The bias is a **small additive bonus** in the existing scoring/selection path, **not a filter.**
  Prefer folding a position-conditional role-fit bonus into the current selection (e.g. the seed/tail
  hook or `track_quality()`) over new machinery. **DO NOT OVERCOMPLICATE.**
- The bonus magnitude should be tunable/defensible and small enough that key/energy/BPM fit still
  dominate — a role breaks ties and nudges close calls; it does not steamroll the score.

### Codebase anchors (from spec 027 RESEARCH — verify in this spec's RESEARCH)
- **Seed (opener):** `src/kiku/setbuilder/planner.py` `_pick_seed()` (~L99-122) — currently picks the
  DJ-specified seed or the track closest to the first segment's target energy. Inject an opener
  preference here.
- **Tail (closer):** no dedicated closer-picker today; the last slot emerges from the beam search +
  `src/kiku/setbuilder/filler.py` (~L93-101) targeting `energy_profile.target_energy_at(last_elapsed)`.
  Add a closer-preference hook at the final position.
- **Scoring:** `src/kiku/setbuilder/scoring.py` `track_quality()` (~L318-371) is the curation-signal
  dimension; `score_candidate()` / `score_transitions()` (~L497+) already accept context params
  (e.g. `target_vibe`, `vibe_strength`) — a role/position context param follows that pattern.
- **Teaching:** `src/kiku/analysis/set_analyzer.py` `analyze_set()` + its teaching-moments pattern is
  where the "why" should surface.
- **Multi-role filter:** backend `search_tracks` `set_role` scalar (spec 027) → accept a list
  (OR-match); route `set_role` Query param → list; frontend `SearchFilters.svelte` role chip-toggles
  (built single-active in spec 027) → make multi-active; `SearchParams.set_role` → `set_roles` /
  repeatable param.
- **Reuse from spec 027:** `set_roles` column, `SET_ROLES`, `normalize_roles` (`src/kiku/set_roles.py`).

### Constraints
- Non-restrictive: role bias never filters a track out of any candidate pool.
- Soft: a role bonus never overrides a clearly better key/energy/BPM fit.
- Minimal change; reuse existing scoring/selection hooks; no new subsystems.
- All user-facing copy in Kiku voice (warm, teaching; set = "set", DJ = "you").

### Testing
- **Unit:** seed selection prefers an opener when scores are close but does NOT when a non-opener is
  clearly better; tail selection prefers a closer under the same rule; role bonus is additive and
  bounded; a set with no role-tagged tracks builds identically to pre-028 (no regression). Multi-role
  filter OR-matches (a track with ANY selected role is returned) and empty selection = no filter.
- **E2E / integration:** build a set from a library with opener/closer-tagged tracks → the opener
  leads and a closer trails when musically reasonable; the "why" note appears; multiple filter
  toggles return the union.

## Behavior
You are a senior engineer implementing the smallest correct change that makes curation shape
generation. Reuse the established scoring/selection + teaching-moment patterns; do not invent new
subsystems. SOFT bias only. Do not touch break→dips — record it as the documented spec 029 follow-up.

# AI Section
Critical: AI can ONLY modify this section.

## Research

Verified against current source. The codebase already has the EXACT soft-bias precedent this spec
needs — `preferred_artists`/`artist_intensity` ("a soft bias during scoring, never a filter; the
candidate pool stays whole") and the `_end_pull`/`_end_affinity` tail mechanism. Roles map onto both.

### 1. opener → seed (soft)
- **`src/kiku/setbuilder/planner.py` `_pick_seed()` (L99-122).** Returns the explicit `seed_title`
  track if given (short-circuit, L106-109) — so an opener bias must only apply when the DJ did NOT
  pin a seed. Otherwise it sorts candidates ascending by `energy_diff` (distance to the first
  segment's target energy, L114-122).
- **Injection:** subtract a small opener bonus from the sort key so opener-tagged tracks rank higher
  without being forced: `key(t) = energy_diff(t) − (OPENER_BONUS if has_role(t,"opener") else 0)`.
  With `OPENER_BONUS ≈ 0.15` (on the 0–1 energy scale), an opener within ~0.15 energy of the best
  non-opener wins the seed; a clearly-better-fitting non-opener still wins. Non-restrictive (pool
  unchanged) and soft.

### 2. closer → tail (soft)
- **No dedicated closer-picker exists.** The last track emerges from the beam search
  (`build_set`, planner.py L210-311); the best beam's final element is whatever ended it.
- **Existing precedent to mirror:** the ending-anchor "soft landing" — `_end_pull(progress)` ramps
  0→0.25 over the last 20% (L65-69), and in the scoring loop `score += pull * _end_affinity(...)`
  (L272-274) biases the tail toward a specific `end_track`.
- **Injection:** in the same scoring loop (after L263), add a closer nudge:
  `if _end_pull(progress) > 0 and has_role(cand,"closer"): score += _end_pull(progress) * _ROLE_SPAN`.
  This favours closer-tagged tracks in the final stretch, so one is *likely* to land last. **Honest
  SOFT semantics:** this is a final-stretch preference, NOT a guaranteed last slot — matches the
  user-chosen "soft bias" and the existing end-pull behaviour. Compatible with an explicit
  `end_title` (both nudges just add).

### 3. Bonus magnitude / where it lives
- **Precedent:** `scoring.py` `_VIBE_SPAN = 0.3` (L404), `_ARTIST_SPAN = 0.2` (L410); `artist_term()`
  (L469-488) returns `intensity * _ARTIST_SPAN` as a bounded positive-only nudge. `transition_score()`
  (L491-529) sums base 5-dim + vibe + artist contributions.
- **Decision:** the role bias is **position-conditional** (opener only at the seed, closer only in the
  final stretch), so it must live in **`planner.py`** where position/progress is known — NOT inside
  `transition_score()` (which is position-agnostic and also used by suggest-next). Define
  `_ROLE_SPAN ≈ 0.15` as a planner-local constant (smaller than vibe/artist, so key/energy/BPM still
  dominate). **No change to `transition_score` / `track_quality` / `score_candidate`.**

### 4. Reading a track's roles
- `set_roles` is a JSON Text column (spec 027). Add a tiny helper to **`src/kiku/set_roles.py`**:
  `track_roles(track) -> list[str]` (safe JSON parse → list) and `has_role(track, role) -> bool`.
  Reuse in planner + analyzer. (`SET_ROLES`, `normalize_roles` already live here.)

### 5. "Show the Why" teaching
- **Surface is already wired end-to-end:** `SetAnalysisResult.set_patterns: list[str]` (set_analyzer.py
  L59) → API `schemas.py:648` → frontend `SetView.svelte:599` (`{#each analysis.set_patterns as
  pattern}`) → `types/index.ts:204`. **No schema/frontend change needed.**
- `detect_set_patterns()` (teaching.py L152) does NOT receive the track objects — but `analyze_set()`
  (set_analyzer.py L66-125) has `tracks`. **Injection:** after `set_patterns` is computed (L93-100),
  append role notes based on `tracks[0]`/`tracks[-1]` roles, e.g. *"Opened with {title} — you marked
  it a great opener."* / *"Closed on {title} — one of your go-to closers."* Contained, minimal.

### 6. multi-role OR-filter (upgrade v1 single-active)
- **Backend `search_tracks`** (`src/kiku/db/store.py`): v1 `set_role: str | None` → `set_role: str |
  list[str] | None`; when a list, OR-match: `or_(*[Track.set_roles.ilike(f'%"{r}"%') for r in roles])`.
- **Route** (`src/kiku/api/routes/tracks.py`): `set_role: str | None` Query → `set_role: list[str] |
  None = Query(None)`; pass through; add to the `other_filters` tuple.
- **Frontend** (`SearchFilters.svelte`): the role chip-toggles are single-active today
  (`toggleSetRole` swaps). Make them multi-active (a `Set<string>` of active roles, OR semantics);
  `SearchParams.set_role: string` → `set_role?: string[]`; API client sends a repeatable `set_role`
  param; active-filter chips per selected role.

### 7. No-change confirmations (scope guard)
- **`SetBuildRequest`** (schemas.py:272-289) needs NO new field — opener/closer bias is automatic
  (reads roles off DB tracks); soft bias is always-on, no dial (user choice).
- **`suggest_next`** (tracks.py:321) / `score_replacement` are slot-level, not positional — OUT of
  scope, untouched.
- **break → dips** — NOT here; documented spec 029 follow-up.

### 8. Tests
- Setbuilder currently has thin/no planner tests (known gap). Add `tests/test_set_role_builder.py`:
  seed prefers an opener when energy is close, does NOT when a non-opener is clearly better; the
  no-role library builds identically (bonus = 0 → no regression); closer nudge raises a closer's
  final-stretch score; `track_roles`/`has_role` parse correctly. Extend `tests/api/test_tracks_api.py`
  for multi-role OR-filter (a track with ANY selected role returned; empty = no filter). Teaching:
  unit-assert `analyze_set` appends the opener/closer note when first/last are tagged.

### Strategy

**Build order (backend-first, each independently verifiable):**
1. **Role helpers** — `track_roles()` + `has_role()` in `set_roles.py`. Unit test parse/membership.
2. **Opener seed bias** — `_ROLE_SPAN`/`OPENER_BONUS` constant + `_pick_seed` sort-key change (guarded
   by the explicit-seed short-circuit). Unit: close→opener wins, clear-loss→non-opener wins.
3. **Closer tail bias** — final-stretch nudge in the `build_set` scoring loop, reusing `_end_pull`.
   Unit: closer's score rises in the last 20%, unchanged early; no-role set identical.
4. **Teaching** — append opener/closer notes to `set_patterns` in `analyze_set`. Unit: note present
   when first/last tagged, absent otherwise. (Renders via existing `SetView` path — manual check.)
5. **Multi-role filter** — `search_tracks` list OR-match → route list param → frontend multi-toggle +
   `SearchParams` + client. API test OR semantics; `svelte-check`.

**Testing strategy:** new `tests/test_set_role_builder.py` (planner + helper + teaching units) using an
in-memory session with a handful of seeded tracks (some role-tagged); extend `tests/api/test_tracks_api.py`
for the multi-role filter. Regression guard: an explicit no-role build test asserting byte-identical
sequence vs. pre-028. Frontend: `svelte-check` + manual E2E (build a set from a role-tagged library →
opener leads, closer trails when reasonable, "why" note shows; multi-toggle filter returns the union).

**Voice/principle checks:** teaching copy in Kiku voice ("you marked it a great opener"); soft bias
preserves "Not a DJ autopilot" (P-anti) + "Every Track Deserves a Chance" (P6); seed/tail choices serve
the whole-set narrative (P3 "The Arc Over the Moment").

**Explicit non-goals:** no `transition_score`/`track_quality`/`suggest_next`/`score_replacement`
change; no `SetBuildRequest` field; no break→dips.

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
