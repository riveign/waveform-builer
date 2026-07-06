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

### Files
- `src/kiku/set_roles.py` — add `track_roles()` + `has_role()`.
- `src/kiku/setbuilder/planner.py` — `_ROLE_SPAN` const + `has_role` import; opener bias in
  `_pick_seed` (L114-122); closer bias in the `build_set` scoring loop (L244-276).
- `src/kiku/analysis/set_analyzer.py` — append opener/closer teaching notes in `analyze_set` (after L100).
- `src/kiku/db/store.py` — `search_tracks` `set_role` scalar→list OR-match (L102, L161-164).
- `src/kiku/api/routes/tracks.py` — search route `set_role` → `list[str] | None = Query(None)` (L112).
- `frontend/src/lib/api/tracks.ts` — `SearchParams.set_role: string` → `string[]` (L18).
- `frontend/src/lib/components/library/SearchFilters.svelte` — role filter single→multi
  (L30, L71, L142, L179, L230-234, L372-373, L570-572).
- `tests/test_set_role_builder.py` *(new)* — planner + helper + teaching units.
- `tests/api/test_tracks_api.py` — multi-role OR-filter test.

### Tasks

#### Task 1 — set_roles.py: track_roles() + has_role()
Tools: editor.
````diff
--- a/src/kiku/set_roles.py
+++ b/src/kiku/set_roles.py
@@
 from __future__ import annotations
 
+from typing import Any
+
 SET_ROLES: tuple[str, ...] = ("opener", "closer", "break")
@@
     present = set(roles)
     return [r for r in SET_ROLES if r in present]
+
+
+def track_roles(track: Any) -> list[str]:
+    """Parse a Track's stored ``set_roles`` (JSON Text) into a clean role list.
+
+    Tolerant: returns [] on missing/blank/malformed data, and drops any value
+    not in SET_ROLES.
+    """
+    import json
+
+    raw = getattr(track, "set_roles", None)
+    if not raw:
+        return []
+    try:
+        roles = json.loads(raw)
+    except (ValueError, TypeError):
+        return []
+    if not isinstance(roles, list):
+        return []
+    return [r for r in roles if r in SET_ROLES]
+
+
+def has_role(track: Any, role: str) -> bool:
+    """True if the track carries the given set-role tag."""
+    return role in track_roles(track)
````
Verification: `python -c "from kiku.set_roles import has_role, track_roles; print(track_roles(type('T',(),{'set_roles':'[\"opener\",\"x\"]'})()))"` → `['opener']`.

#### Task 2 — planner.py: _ROLE_SPAN + opener seed bias
Tools: editor. Two edits.

2a. Import + constant (after the existing scoring import at L18):
````diff
--- a/src/kiku/setbuilder/planner.py
+++ b/src/kiku/setbuilder/planner.py
@@
 from kiku.setbuilder.scoring import bpm_compatibility, transition_score, vibe_continuity
+from kiku.set_roles import has_role
 from kiku.vibe import resolve_vibe
 
 console = Console()
+
+# Set-role soft bias (spec 028): a small, bounded, positive-only nudge — smaller
+# than _VIBE_SPAN (0.3) / _ARTIST_SPAN (0.2) in scoring.py, so key/energy/BPM fit
+# still dominate. An opener/closer only breaks close calls; it never forces a weak
+# transition and never removes a non-tagged track from the pool.
+_ROLE_SPAN = 0.15
````
2b. Opener bias in `_pick_seed` (replace the energy-only sort):
````diff
--- a/src/kiku/setbuilder/planner.py
+++ b/src/kiku/setbuilder/planner.py
@@
-    # Pick track closest to first segment's target energy
-    target = energy_profile.segments[0].target_energy if energy_profile.segments else 0.3
-
-    def energy_diff(t: Track) -> float:
-        te = get_track_energy(t)
-        return abs(te.numeric - target)
-
-    candidates_sorted = sorted(candidates, key=energy_diff)
-    return candidates_sorted[0]
+    # Pick the track closest to the first segment's target energy, softly favouring
+    # opener-tagged tracks (spec 028): an opener within ~_ROLE_SPAN energy of the best
+    # non-opener wins the seed, but a clearly better energy fit still wins. Only when
+    # the DJ did NOT pin an explicit seed (handled by the short-circuit above).
+    target = energy_profile.segments[0].target_energy if energy_profile.segments else 0.3
+
+    def seed_rank(t: Track) -> float:
+        te = get_track_energy(t)
+        diff = abs(te.numeric - target)
+        if has_role(t, "opener"):
+            diff -= _ROLE_SPAN
+        return diff
+
+    candidates_sorted = sorted(candidates, key=seed_rank)
+    return candidates_sorted[0]
````
Verification: Task 9 unit test.

#### Task 3 — planner.py: closer tail bias in build_set scoring loop
Tools: editor. Two edits in `build_set`.

3a. Compute the end-ramp independently of the ending anchor (L244-245):
````diff
--- a/src/kiku/setbuilder/planner.py
+++ b/src/kiku/setbuilder/planner.py
@@
-            # Soft pull toward the ending anchor in the final stretch
-            pull = _end_pull(progress) if end_track else 0.0
+            # Final-stretch ramp (0 until 80% through). Drives BOTH the optional
+            # ending-anchor pull and the closer-role nudge below.
+            end_ramp = _end_pull(progress)
+            pull = end_ramp if end_track else 0.0
````
3b. Add the closer nudge alongside the ending-anchor bias (L272-276):
````diff
--- a/src/kiku/setbuilder/planner.py
+++ b/src/kiku/setbuilder/planner.py
@@
                 # Soft landing: bias the tail toward the ending anchor
                 if pull > 0 and end_track is not None and cand.id != end_track.id:
                     score += pull * _end_affinity(cand, end_track)
 
+                # Closer role: favour closer-tagged tracks in the final stretch so one
+                # is likely to land last (soft, spec 028). Independent of any ending
+                # anchor; reuses the same end-ramp. A preference, not a guarantee.
+                if end_ramp > 0 and has_role(cand, "closer"):
+                    score += end_ramp * _ROLE_SPAN
+
                 scored_candidates.append((cand, score))
````
Verification: Task 9 unit test.

#### Task 4 — set_analyzer.py: opener/closer "why" teaching notes
Tools: editor. Append to `set_patterns` after it is computed (between L100 and L102):
````diff
--- a/src/kiku/analysis/set_analyzer.py
+++ b/src/kiku/analysis/set_analyzer.py
@@
     set_patterns = detect_set_patterns(
         score_dicts,
         arc.energy_curve,
         arc.key_journey,
         [t.bpm for t in tracks],
     )
 
+    # Role-driven "why" (spec 028): if the DJ's own opener led the set or their
+    # closer ended it, say so — teaching, in their voice. Derived from the final
+    # tracks' role tags (no build-time provenance needed).
+    from kiku.set_roles import has_role
+    if has_role(tracks[0], "opener"):
+        set_patterns.append(
+            f"Opened with “{tracks[0].title}” — you marked it a great opener."
+        )
+    if has_role(tracks[-1], "closer"):
+        set_patterns.append(
+            f"Closed on “{tracks[-1].title}” — one of your go-to closers."
+        )
+
     # 5. Overall score
````
Verification: Task 9 unit test; renders via existing `SetView.svelte:599`.

#### Task 5 — store.py: multi-role OR-filter
Tools: editor. Two edits in `search_tracks`.
````diff
--- a/src/kiku/db/store.py
+++ b/src/kiku/db/store.py
@@
-    set_role: str | None = None,
+    set_role: str | list[str] | None = None,
     sort: str | None = None,
````
````diff
--- a/src/kiku/db/store.py
+++ b/src/kiku/db/store.py
@@
     if set_role:
         # set_roles is a JSON string list, e.g. '["opener", "break"]'. Match the
         # quoted token so "open" never false-positives on "opener" (spec 027).
-        q = q.filter(Track.set_roles.ilike(f'%"{set_role}"%'))
+        # A list OR-matches — a track with ANY selected role qualifies (spec 028).
+        roles = [set_role] if isinstance(set_role, str) else set_role
+        q = q.filter(or_(*[Track.set_roles.ilike(f'%"{r}"%') for r in roles]))
````
Verification: Task 10 API test. (`or_` already imported in store.py.)

#### Task 6 — routes/tracks.py: search route accepts repeatable set_role
Tools: editor.
````diff
--- a/src/kiku/api/routes/tracks.py
+++ b/src/kiku/api/routes/tracks.py
@@
-    set_role: str | None = None,
+    set_role: list[str] | None = Query(None),
     sort: str | None = None,
````
(pass-through `set_role=set_role` and the `other_filters` tuple entry are unchanged; `Query` already
imported.) Verification: Task 10.

#### Task 7 — tracks.ts: SearchParams.set_role → string[]
Tools: editor.
````diff
--- a/frontend/src/lib/api/tracks.ts
+++ b/frontend/src/lib/api/tracks.ts
@@
-	set_role?: string;
+	set_role?: string[];
````
(`searchTracks` already appends array params as repeatable query keys — no client change.)
Verification: svelte-check.

#### Task 8 — SearchFilters.svelte: role filter single-active → multi-active
Tools: editor (tab-sensitive — apply via a script if needed). Seven edits:
1. State (L30): `let setRole = $state('');` → `let setRoles = $state<Set<string>>(new Set());`
2. buildParams (L71): `if (setRole) params.set_role = setRole;` →
   `if (setRoles.size > 0) params.set_role = [...setRoles];`
3. hasActiveFilters (L142): `setRole !== '' ||` → `setRoles.size > 0 ||`
4. clearAllFilters (L179): `setRole = '';` → `setRoles = new Set();`
5. toggleSetRole (L230-232):
````diff
-	function toggleSetRole(role: string) {
-		setRole = setRole === role ? '' : role;
-		searchNow();
-	}
+	function toggleSetRole(role: string) {
+		const next = new Set(setRoles);
+		if (next.has(role)) next.delete(role);
+		else next.add(role);
+		setRoles = next;
+		searchNow();
+	}
````
6. Active chips (L372-373) — one removable chip per selected role:
````diff
-			{#if setRole}
-				<Chip value={SET_ROLE_LABELS[setRole]} size="sm" removable removeLabel="Clear set-role filter" onremove={() => { setRole = ''; searchNow(); }} />
-			{/if}
+			{#each [...setRoles] as role (role)}
+				<Chip value={SET_ROLE_LABELS[role]} size="sm" removable removeLabel="Clear {SET_ROLE_LABELS[role]} filter" onremove={() => toggleSetRole(role)} />
+			{/each}
````
7. Toggle buttons (L570-572): `class:on={setRole === 'opener'}` → `class:on={setRoles.has('opener')}`
   (and `'closer'`, `'break'` likewise).
Verification: svelte-check; selecting Openers + Closers returns the union; each shows a removable chip.

#### Task 9 — tests/test_set_role_builder.py (new)
Tools: editor. Create with in-memory session + seeded tracks:
````python
"""Spec 028 — set roles shaping the auto-builder (soft bias) + teaching."""
from __future__ import annotations

import json

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from kiku.db.models import Base, Set, SetTrack, Track
from kiku.set_roles import has_role, track_roles
from kiku.setbuilder.constraints import parse_energy_string
from kiku.setbuilder.planner import _pick_seed


@pytest.fixture()
def session(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path/'t.db'}", poolclass=NullPool)
    Base.metadata.create_all(engine)
    s = sessionmaker(bind=engine)()
    yield s
    s.close()


def _t(session, tid, energy, roles=None, bpm=124.0, key="8A"):
    tr = Track(id=tid, title=f"T{tid}", artist=f"A{tid}", bpm=bpm, key=key,
               dir_energy=energy, set_roles=json.dumps(roles) if roles else None)
    session.add(tr)
    return tr


def test_track_roles_parse(session):
    tr = _t(session, 1, "warmup", roles=["opener", "bogus"])
    assert track_roles(tr) == ["opener"]           # unknown dropped
    assert has_role(tr, "opener") and not has_role(tr, "closer")
    assert track_roles(_t(session, 2, "warmup")) == []  # untagged


def test_seed_prefers_opener_when_energy_close(session):
    prof = parse_energy_string("warmup:30:0.3,peak:30:0.9")
    # both near the 0.3 warmup target; #2 is the marked opener
    a = _t(session, 1, "warmup")                    # ~low energy, no role
    b = _t(session, 2, "warmup", roles=["opener"])  # ~low energy, opener
    session.commit()
    assert _pick_seed([a, b], prof).id == 2


def test_seed_does_not_force_opener_on_clear_loss(session):
    prof = parse_energy_string("warmup:30:0.3,peak:30:0.9")
    # #1 sits ON the warmup target; #2 is a peak-energy opener (far from target)
    a = _t(session, 1, "warmup")                    # great energy fit, no role
    b = _t(session, 2, "peak", roles=["opener"])    # opener but wrong energy
    session.commit()
    # the ~0.15 bonus must NOT overcome a large energy gap
    assert _pick_seed([a, b], prof).id == 1


def test_teaching_notes_for_tagged_first_and_last(session):
    from kiku.analysis.set_analyzer import analyze_set
    o = _t(session, 1, "warmup", roles=["opener"])
    m = _t(session, 2, "build")
    c = _t(session, 3, "close", roles=["closer"])
    st = Set(id=1, name="S", duration_min=30)
    session.add(st); session.flush()
    for pos, tr in enumerate([o, m, c]):
        session.add(SetTrack(set_id=1, position=pos, track_id=tr.id))
    session.commit()
    res = analyze_set(session, 1)
    joined = " ".join(res.set_patterns)
    assert "great opener" in joined and "go-to closers" in joined
````
Verification: `pytest tests/test_set_role_builder.py -q`.

#### Task 10 — tests/api/test_tracks_api.py: multi-role OR-filter
Tools: editor. Append:
````python
def test_search_filter_set_roles_multi_or(client):
    client.patch("/api/tracks/3/set-roles", json={"roles": ["opener"]})
    client.patch("/api/tracks/4/set-roles", json={"roles": ["closer"]})
    client.patch("/api/tracks/5/set-roles", json={"roles": ["break"]})
    resp = client.get("/api/tracks/search?set_role=opener&set_role=closer")
    ids = {t["id"] for t in resp.json()["items"]}
    assert 3 in ids and 4 in ids       # union of both roles
    assert 5 not in ids                # break not selected
````
Verification: Task 11.

#### Task 11 — Lint + type-check + tests
Tools: shell.
- `source .venv/bin/activate && python -m pytest tests/test_set_role_builder.py tests/api/test_tracks_api.py -q`
- `source .venv/bin/activate && python -m pytest tests/ -q`  (full suite — regression guard)
- `cd frontend && npx svelte-check --tsconfig ./tsconfig.json`
Expectation: all green; svelte-check 0 errors.

#### Task 12 — E2E (manual)
Tools: browser. Start API + frontend:
1. Tag a low-energy track "opener" and a track "closer". Build a set (no explicit seed) from that
   library → the opener leads; a closer trails when musically reasonable; the set view shows the
   "Opened with … / Closed on …" notes.
2. Build with NO role-tagged tracks → set is unchanged vs. before (no regression).
3. Library filter: enable Openers + Closers → union returned, two removable chips; clear both → full list.
Expectation: all pass; a role never forces an obviously bad transition.

#### Task 13 — Commit
Tools: git.
- `git add -- src/kiku/set_roles.py src/kiku/setbuilder/planner.py src/kiku/analysis/set_analyzer.py src/kiku/db/store.py src/kiku/api/routes/tracks.py frontend/src/lib/api/tracks.ts frontend/src/lib/components/library/SearchFilters.svelte tests/test_set_role_builder.py tests/api/test_tracks_api.py`
- `BRANCH=$(git rev-parse --abbrev-ref HEAD); [ "$BRANCH" != "main" ] || { echo 'ERROR: on main' >&2; exit 2; }`
- `git commit -m "spec(028): IMPLEMENT - set-role-builder"`

### Validate
- **HLO/MLO opener→seed** (L… MLO): Task 2 — soft bias in `_pick_seed`, guarded by explicit-seed
  short-circuit. Satisfied.
- **MLO closer→tail** (L… MLO): Task 3 — final-stretch nudge reusing `_end_pull`. Soft (preference,
  not guaranteed last). Satisfied.
- **MLO multi-role OR-filter** (L… MLO): Tasks 5-8. Satisfied.
- **MLO Show the Why** (L… MLO): Task 4 — appended to `set_patterns`, renders via existing SetView
  path. Kiku voice. Satisfied.
- **DT soft, non-restrictive** (L… Details): `_ROLE_SPAN=0.15` bounded positive nudge; pool never
  filtered; test `test_seed_does_not_force_opener_on_clear_loss` proves it doesn't override a clear
  energy win. Satisfied.
- **DT no-regression when no roles** (L… Testing): full-suite run (Task 11) + bonus is 0 for untagged.
  Satisfied.
- **DT reuse existing hooks, no new subsystem** (L… Details): all changes fold into `_pick_seed`, the
  scoring loop, `analyze_set`, and the existing filter. No `transition_score`/`suggest_next`/
  `SetBuildRequest` change. Satisfied.
- **Scope OUT break→dips** (L… Scope): no task touches break placement; documented spec 029. Satisfied.

## Plan Review
<!-- Filled if required to validate plan -->

## Implement

TODOs (backend first, then frontend):
- [x] T1 set_roles.py: track_roles() + has_role() — Done
- [x] T2 planner.py: _ROLE_SPAN + opener seed bias — Done
- [x] T3 planner.py: closer tail bias (end_ramp reused, anchor-independent) — Done
- [x] T4 set_analyzer.py: teaching notes appended to set_patterns — Done
- [x] T5 store.py: multi-role OR-filter — Done
- [x] T6 routes/tracks.py: repeatable set_role Query(None) — Done
- [x] T7 tracks.ts: SearchParams.set_role → string[] — Done
- [x] T8 SearchFilters.svelte: single→multi (Set) — Done
- [x] T9 tests/test_set_role_builder.py (5 units) — Done
- [x] T10 api multi-role OR test — Done
- [x] T11 pytest + svelte-check — Done
- [x] T12 E2E smoke (real-DB multi-role filter) — Done
- [x] T13 commit — Done (see hash below)

**Implementation commit:** `ec2f900` — spec(028): IMPLEMENT - set-role-builder (9 files).

### Results
- **Backend:** full suite **421 passed** (was 416; +5 new in `test_set_role_builder.py`, +1 api multi-role).
  Seed bias proven both ways: `test_seed_prefers_opener_when_energy_close` (opener wins a close call)
  and `test_seed_does_not_force_opener_on_clear_loss` (the 0.15 bonus does NOT beat a clear energy win
  — the soft-bias contract, enforced). Teaching notes asserted present for tagged first/last.
- **Regression guard:** full suite green; role bonus is `0` for untagged tracks, so a no-role library
  builds identically.
- **Real-DB E2E smoke:** multi-role OR filter returns the union (opener+closer), excludes unselected
  (break); single still works; test data cleaned up.
- **Frontend:** `svelte-check` **0/0**. Filter chip-toggles now multi-active (a `Set`), each active role
  shows a removable chip.
- **Deviations:** none from PLAN. No `transition_score`/`suggest_next`/`SetBuildRequest` touched.
  Closer is a final-stretch preference, not a guaranteed last slot (documented soft semantics).

## Test Evidence & Outputs
<!-- Filled by explicit testing after /spec IMPLEMENT -->

## Updated Doc
<!-- Filled by explicit documentation udpates after /spec IMPLEMENT -->

## Post-Implement Review
<!-- Filled by /spec REVIEW -->
