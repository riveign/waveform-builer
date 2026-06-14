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

### Files
- src/kiku/api/schemas.py
  - `SetBuildRequest` (260-274): add `preferred_artists: list[str] | None = None` + `artist_intensity: float = 0.0` after the vibe fields.
- src/kiku/setbuilder/scoring.py
  - Add import of `artist_matches` from `kiku.artists` (top, ~13).
  - Add `_ARTIST_SPAN = 0.2` near `_VIBE_SPAN` (398).
  - Add `artist_matches_any()` helper + `artist_term()` (after `vibe_term`, ~441).
  - Thread `preferred_artists` + `artist_intensity` through `transition_score()` (443-476) and `score_replacement()` (479-535).
- src/kiku/setbuilder/planner.py
  - `build_set()` signature (133-148): add the two params.
  - Docstring (149-157): document the two params.
  - `transition_score(...)` call at 257: pass artist params.
  - `transition_score(...)` call at 323 (persisted score): pass artist params for consistency.
- src/kiku/api/routes/sets.py
  - `build_set(...)` call (350-365): pass `preferred_artists=body.preferred_artists, artist_intensity=body.artist_intensity`.
- frontend/src/lib/types/index.ts
  - `SetBuildParams` (326-341): add `preferred_artists?: string[] | null; artist_intensity?: number;`.
- frontend/src/lib/components/set/BuildSetDialog.svelte
  - Imports: `autocompleteArtists`, `Typeahead`.
  - State: `preferredArtists`, `artistIntensity`.
  - `resetForm()`: reset both.
  - Params assembly (178-182): attach artist fields only when a list is present.
  - Markup: "Featured artists" field after the Vibe field (~290).
- tests/test_artist_bias.py (NEW)
  - Unit tests for `artist_term`, `transition_score`, soft-bias contract.
- tests/api/test_sets_api.py
  - Add `test_build_set_with_preferred_artists` smoke test.

### Tasks

#### Task 1 — schemas.py: add preferred_artists + artist_intensity to SetBuildRequest
Tools: editor
Mirror the vibe fields field-for-field (defaults → zero behavior change when unused).
Diff:
````diff
--- a/src/kiku/api/schemas.py
+++ b/src/kiku/api/schemas.py
@@ class SetBuildRequest(BaseModel):
     vibe_preset: str | None = None        # e.g. "dark & deep", "euphoric" — see VIBE_PRESETS
     vibe_intensity: float = 0.0           # 0 = ignore vibe, 1 = vibe steers strongly
+    preferred_artists: list[str] | None = None  # artists the DJ asked to feature — soft bias, never a filter
+    artist_intensity: float = 0.0         # 0 = ignore, 1 = strong nudge toward preferred artists
````
Verification:
- `source .venv/bin/activate && python -c "from kiku.api.schemas import SetBuildRequest; SetBuildRequest(name='x', preferred_artists=['Bicep'], artist_intensity=0.5)"` succeeds.

#### Task 2 — scoring.py: add _ARTIST_SPAN, artist_matches_any, artist_term
Tools: editor
Add the import, the span constant, and the two helpers (positive-only nudge with a breakdown for transparency).
Diff (import):
````diff
--- a/src/kiku/setbuilder/scoring.py
+++ b/src/kiku/setbuilder/scoring.py
@@
-from kiku.config import BPM_TOLERANCE, SCORING_WEIGHTS
+from kiku.artists import artist_matches
+from kiku.config import BPM_TOLERANCE, SCORING_WEIGHTS
 from kiku.db.models import Track
 from kiku.setbuilder.camelot import harmonic_score
 from kiku.setbuilder.constraints import dir_energy_to_numeric, zone_to_numeric
 from kiku.vibe import resolve_vibe, vibe_distance
````
Diff (span constant — add right after `_VIBE_SPAN`):
````diff
--- a/src/kiku/setbuilder/scoring.py
+++ b/src/kiku/setbuilder/scoring.py
@@
 _VIBE_SPAN = 0.3  # max ± shift at vibe_strength = 1.0
+
+# ── Featured artists ─────────────────────────────────────────────────────
+# When the DJ names artists to feature, a candidate from one of them earns a
+# small positive-only nudge — a visible soft bias, never a filter. Smaller
+# than _VIBE_SPAN so it tilts the odds without ever dominating harmony/energy.
+_ARTIST_SPAN = 0.2  # max + bonus at artist_intensity = 1.0
````
Diff (helpers — add directly after the `vibe_term` function, before `transition_score`):
````diff
--- a/src/kiku/setbuilder/scoring.py
+++ b/src/kiku/setbuilder/scoring.py
@@
         "contribution": round(contribution, 3),
     }
     return contribution, breakdown
+
+
+def artist_matches_any(
+    candidate_artist: str | None,
+    preferred: list[str] | None,
+) -> bool:
+    """True when the candidate's artist matches any preferred artist.
+
+    Uses the collaboration-aware token matcher, so a featured "Bicep" also
+    matches "Bicep & Chroma".
+    """
+    if not preferred:
+        return False
+    return any(artist_matches(p, candidate_artist) for p in preferred)
+
+
+def artist_term(
+    to_track: Track,
+    preferred_artists: list[str] | None,
+    artist_intensity: float,
+) -> tuple[float, dict | None]:
+    """Bounded positive-only bonus when the DJ asked for this track's artist.
+
+    Returns (contribution, breakdown). contribution is 0.0 when the feature
+    is off or the artist does not match. A soft bias, never a filter.
+    """
+    if artist_intensity <= 0 or not preferred_artists:
+        return 0.0, None
+    if not artist_matches_any(to_track.artist, preferred_artists):
+        return 0.0, None
+    contribution = artist_intensity * _ARTIST_SPAN
+    breakdown = {
+        "matched": True,
+        "contribution": round(contribution, 3),
+    }
+    return contribution, breakdown
````
Verification:
- Covered by Task 7 unit tests; py_compile in Task 9.

#### Task 3 — scoring.py: thread artist params through transition_score
Tools: editor
Add the two params (defaulted off) and fold the contribution into the return.
Diff:
````diff
--- a/src/kiku/setbuilder/scoring.py
+++ b/src/kiku/setbuilder/scoring.py
@@ def transition_score(
     set_appearance_counts: dict[int, int] | None = None,
     target_vibe: tuple[float, float] | None = None,
     vibe_strength: float = 0.0,
+    preferred_artists: list[str] | None = None,
+    artist_intensity: float = 0.0,
 ) -> float:
     """Compute overall transition score between two tracks.
 
     Args:
         weights: Optional per-request weight overrides. Falls back to global SCORING_WEIGHTS.
         target_vibe: Optional (brightness, density) target for this point in the set.
         vibe_strength: How strongly vibe steers selection (0 = off, 1 = full).
+        preferred_artists: Artists the DJ asked to feature (soft bias, never a filter).
+        artist_intensity: How strongly to nudge toward preferred artists (0 = off, 1 = strong).
     """
@@
     base = (w["harmonic"] * h + w["energy_fit"] * e + w["bpm_compat"] * b
             + w["genre_coherence"] * g + w["track_quality"] * q)
     vibe_contribution, _ = vibe_term(from_track, to_track, target_vibe, vibe_strength)
-    return base + vibe_contribution
+    artist_contribution, _ = artist_term(to_track, preferred_artists, artist_intensity)
+    return base + vibe_contribution + artist_contribution
````
Verification:
- Covered by Task 7 unit tests; py_compile in Task 9.

#### Task 4 — scoring.py: thread artist params through score_replacement
Tools: editor
Add the two params and fold `"artist": artist_bd` into each breakdown (transparency for suggest-next / artist-picks / transition-detail).
Diff:
````diff
--- a/src/kiku/setbuilder/scoring.py
+++ b/src/kiku/setbuilder/scoring.py
@@ def score_replacement(
     set_appearance_counts: dict[int, int] | None = None,
     target_vibe: tuple[float, float] | None = None,
     vibe_strength: float = 0.0,
+    preferred_artists: list[str] | None = None,
+    artist_intensity: float = 0.0,
 ) -> tuple[float, dict | None, dict | None]:
     """Score a candidate as a replacement considering both neighbors.
 
     Returns (combined_score, incoming_breakdown, outgoing_breakdown).
     Breakdowns are dicts with keys: harmonic, energy_fit, bpm_compat,
-    genre_coherence, track_quality, vibe, total.
+    genre_coherence, track_quality, vibe, artist, total.
     """
@@
         vibe_contribution, vibe_bd = vibe_term(from_t, to_t, target_vibe, vibe_strength)
+        artist_contribution, artist_bd = artist_term(to_t, preferred_artists, artist_intensity)
         return {
             "harmonic": round(h, 3),
             "energy_fit": round(e, 3),
             "bpm_compat": round(b, 3),
             "genre_coherence": round(g, 3),
             "track_quality": round(q, 3),
             "vibe": vibe_bd,
-            "total": round(base + vibe_contribution, 3),
+            "artist": artist_bd,
+            "total": round(base + vibe_contribution + artist_contribution, 3),
             "discovery_label": label,
````
Verification:
- py_compile in Task 9; breakdown shape covered indirectly by API smoke (Task 8).

#### Task 5 — planner.py: add params to build_set and thread into both transition_score calls
Tools: editor
Mirror vibe: add the two params, document them, pass into the per-candidate score (257) and the persisted score (323) so the recorded score matches what beam search used.
Diff (signature + docstring):
````diff
--- a/src/kiku/setbuilder/planner.py
+++ b/src/kiku/setbuilder/planner.py
@@ def build_set(
     end_title: str | None = None,
     preset_vibe: tuple[float, float] | None = None,
     vibe_intensity: float = 0.0,
+    preferred_artists: list[str] | None = None,
+    artist_intensity: float = 0.0,
 ) -> Set | None:
     """Generate a DJ set using beam search.
 
     Args:
         end_title: Optional ending-track anchor (soft — pulls the tail toward it).
         preset_vibe: Optional (brightness, density) target vibe from a preset.
         vibe_intensity: How strongly vibe steers selection (0 = off, 1 = full).
+        preferred_artists: Artists the DJ asked to feature — a soft bias during
+            scoring, never a filter. The candidate pool stays whole.
+        artist_intensity: How strongly to nudge toward preferred artists
+            (0 = off, 1 = strong). The artist cooldown still wins over the bias.
 
     Returns a saved Set object with SetTrack entries, or None on failure.
     """
````
Diff (per-candidate scoring call at 257):
````diff
--- a/src/kiku/setbuilder/planner.py
+++ b/src/kiku/setbuilder/planner.py
@@
-                score = transition_score(current, cand, target_energy=target_e, prefer_playlists=prefer_playlists, weights=weights, discovery_density=discovery_density, set_appearance_counts=set_appearance_counts, target_vibe=target_vibe, vibe_strength=vibe_intensity)
+                score = transition_score(current, cand, target_energy=target_e, prefer_playlists=prefer_playlists, weights=weights, discovery_density=discovery_density, set_appearance_counts=set_appearance_counts, target_vibe=target_vibe, vibe_strength=vibe_intensity, preferred_artists=preferred_artists, artist_intensity=artist_intensity)
````
Diff (persisted score call at 323):
````diff
--- a/src/kiku/setbuilder/planner.py
+++ b/src/kiku/setbuilder/planner.py
@@
-        t_score = transition_score(prev_track, track, prefer_playlists=prefer_playlists, weights=weights, discovery_density=discovery_density, set_appearance_counts=set_appearance_counts) if prev_track else None
+        t_score = transition_score(prev_track, track, prefer_playlists=prefer_playlists, weights=weights, discovery_density=discovery_density, set_appearance_counts=set_appearance_counts, preferred_artists=preferred_artists, artist_intensity=artist_intensity) if prev_track else None
````
Note: `_violates_artist_cooldown(seq, cand)` at 246-247 is UNCHANGED — it gates before scoring, so the cooldown always wins over the bias. The candidate pool (`candidate_set`) is never narrowed by `preferred_artists`.
Verification:
- Covered by Task 7 planner test; py_compile in Task 9.

#### Task 6 — routes/sets.py: thread request fields into build_set (no resolve step)
Tools: editor
Pass the strings straight through — artists need no `resolve_preset`.
Diff:
````diff
--- a/src/kiku/api/routes/sets.py
+++ b/src/kiku/api/routes/sets.py
@@
                 end_title=end_title,
                 preset_vibe=preset_vibe,
                 vibe_intensity=body.vibe_intensity,
+                preferred_artists=body.preferred_artists,
+                artist_intensity=body.artist_intensity,
             )
````
Verification:
- Covered by Task 8 API smoke; py_compile in Task 9.

#### Task 7 — frontend types: extend SetBuildParams
Tools: editor
Diff:
````diff
--- a/frontend/src/lib/types/index.ts
+++ b/frontend/src/lib/types/index.ts
@@ export interface SetBuildParams {
 	vibe_preset?: string | null;
 	vibe_intensity?: number;
+	preferred_artists?: string[] | null;
+	artist_intensity?: number;
 }
````
Verification:
- `cd frontend && npx svelte-check --tsconfig ./tsconfig.json` (Task 9) — no new errors.

#### Task 8 — BuildSetDialog.svelte: Featured artists Typeahead + intensity slider
Tools: editor
Add the imports, state, reset, params assembly, and a "Featured artists" field mirroring the Vibe field. Voice: the bonus honors the DJ's ask.
Diff (imports):
````diff
--- a/frontend/src/lib/components/set/BuildSetDialog.svelte
+++ b/frontend/src/lib/components/set/BuildSetDialog.svelte
@@
 	import VibePresetPicker from './VibePresetPicker.svelte';
+	import Typeahead from '$lib/components/library/Typeahead.svelte';
+	import { autocompleteArtists } from '$lib/api/tracks';
 	import type { Track } from '$lib/types';
````
Diff (state — after `vibeIntensity`):
````diff
--- a/frontend/src/lib/components/set/BuildSetDialog.svelte
+++ b/frontend/src/lib/components/set/BuildSetDialog.svelte
@@
 	let vibePreset = $state<string | null>(null);
 	let vibeIntensity = $state(60);
+	let preferredArtists = $state<string[]>([]);
+	let artistIntensity = $state(0);
 	let endTrack = $state<Track | null>(null);
````
Diff (resetForm — after `vibeIntensity = 60;`):
````diff
--- a/frontend/src/lib/components/set/BuildSetDialog.svelte
+++ b/frontend/src/lib/components/set/BuildSetDialog.svelte
@@ function resetForm() {
 		vibePreset = null;
 		vibeIntensity = 60;
+		preferredArtists = [];
+		artistIntensity = 0;
 		endTrack = null;
 	}
````
Diff (params assembly — after the vibe block):
````diff
--- a/frontend/src/lib/components/set/BuildSetDialog.svelte
+++ b/frontend/src/lib/components/set/BuildSetDialog.svelte
@@
 		// Vibe — a preset target plus how strongly it should steer
 		if (vibePreset) {
 			params.vibe_preset = vibePreset;
 			params.vibe_intensity = vibeIntensity / 100;
 		}
+
+		// Featured artists — a soft nudge toward the artists you asked for, never a filter
+		if (preferredArtists.length) {
+			params.preferred_artists = preferredArtists;
+			params.artist_intensity = artistIntensity / 100;
+		}
 
 		onbuild?.(params);
````
Diff (markup — insert after the Vibe field block, before the Discovery / Density field):
````diff
--- a/frontend/src/lib/components/set/BuildSetDialog.svelte
+++ b/frontend/src/lib/components/set/BuildSetDialog.svelte
@@
 			<!-- Vibe -->
 			<div class="field">
 				<span class="field-label">Vibe</span>
 				<VibePresetPicker bind:preset={vibePreset} bind:intensity={vibeIntensity} />
 			</div>
+
+			<!-- Featured artists — soft nudge, never a filter -->
+			<div class="field">
+				<span class="field-label">Featured artists</span>
+				<Typeahead
+					bind:selected={preferredArtists}
+					placeholder="Artists to favor..."
+					fetchSuggestions={(q) => autocompleteArtists(q, 10)}
+				/>
+				{#if preferredArtists.length > 0}
+					<label class="field-label" for="artist-intensity">
+						How strongly to lean in
+						<span class="field-hint">({artistIntensity}%)</span>
+					</label>
+					<input
+						id="artist-intensity"
+						type="range"
+						class="field-slider"
+						min={0}
+						max={100}
+						step={5}
+						bind:value={artistIntensity}
+					/>
+					<div class="slider-range">
+						<span>Just a nudge</span>
+						<span>Lean in</span>
+					</div>
+					<span class="field-subtext">A gentle tilt toward the artists you asked for — the rest of your library still plays.</span>
+				{/if}
+			</div>
 
 			<!-- Discovery / Density -->
 			<div class="field">
 				<DiscoveryDensitySlider bind:value={discoveryDensity} />
 			</div>
````
Verification:
- `cd frontend && npx svelte-check --tsconfig ./tsconfig.json` (Task 9) — no new errors (baseline 0 errors / 4 warnings).

#### Task 9 — Unit tests: tests/test_artist_bias.py
Tools: editor (new file)
Cover `artist_term` (match→scaled bonus; non-match→0; intensity 0→0; collaboration; bounded by `_ARTIST_SPAN`) and `transition_score` (higher with matching preferred artist at intensity>0; identical to baseline at intensity 0). MagicMock tracks like `tests/test_scoring.py`.
Diff:
````diff
--- /dev/null
+++ b/tests/test_artist_bias.py
@@
+"""Tests for the featured-artists soft bias (spec 021, Phase B)."""
+
+from unittest.mock import MagicMock
+
+from kiku.setbuilder.scoring import (
+    _ARTIST_SPAN,
+    artist_matches_any,
+    artist_term,
+    transition_score,
+)
+
+
+def _track(artist="Someone", key="8A", bpm=128.0, genre="techno", energy="mid"):
+    t = MagicMock()
+    t.id = 1
+    t.artist = artist
+    t.key = key
+    t.bpm = bpm
+    t.dir_genre = genre
+    t.rb_genre = genre
+    t.dir_energy = energy
+    t.rating = 3
+    t.play_count = 5
+    t.kiku_play_count = 0
+    t.playlist_tags = None
+    return t
+
+
+# ── artist_matches_any ──
+def test_matches_any_direct():
+    assert artist_matches_any("Bicep", ["Bicep"]) is True
+
+
+def test_matches_any_collaboration():
+    # Collaboration is matched via the token matcher.
+    assert artist_matches_any("Bicep & Chroma", ["Bicep"]) is True
+
+
+def test_matches_any_no_match():
+    assert artist_matches_any("Four Tet", ["Bicep"]) is False
+
+
+def test_matches_any_empty_list():
+    assert artist_matches_any("Bicep", []) is False
+    assert artist_matches_any("Bicep", None) is False
+
+
+# ── artist_term ──
+def test_term_off_when_intensity_zero():
+    contrib, bd = artist_term(_track("Bicep"), ["Bicep"], 0.0)
+    assert contrib == 0.0
+    assert bd is None
+
+
+def test_term_off_when_no_preferred():
+    contrib, bd = artist_term(_track("Bicep"), None, 0.5)
+    assert contrib == 0.0
+    assert bd is None
+
+
+def test_term_zero_on_non_match():
+    contrib, bd = artist_term(_track("Four Tet"), ["Bicep"], 0.5)
+    assert contrib == 0.0
+    assert bd is None
+
+
+def test_term_positive_on_match():
+    contrib, bd = artist_term(_track("Bicep"), ["Bicep"], 0.5)
+    assert contrib > 0.0
+    assert bd is not None
+    assert bd["matched"] is True
+
+
+def test_term_scales_with_intensity():
+    low, _ = artist_term(_track("Bicep"), ["Bicep"], 0.25)
+    high, _ = artist_term(_track("Bicep"), ["Bicep"], 0.75)
+    assert high > low
+
+
+def test_term_bounded_by_span():
+    contrib, _ = artist_term(_track("Bicep"), ["Bicep"], 1.0)
+    assert contrib == _ARTIST_SPAN
+
+
+def test_term_collaboration_matches():
+    contrib, _ = artist_term(_track("Bicep & Chroma"), ["Bicep"], 1.0)
+    assert contrib == _ARTIST_SPAN
+
+
+# ── transition_score integration ──
+def test_transition_higher_with_preferred_artist():
+    frm = _track("Origin")
+    to = _track("Bicep")
+    baseline = transition_score(frm, to)
+    boosted = transition_score(frm, to, preferred_artists=["Bicep"], artist_intensity=0.8)
+    assert boosted > baseline
+
+
+def test_transition_identical_at_intensity_zero():
+    frm = _track("Origin")
+    to = _track("Bicep")
+    baseline = transition_score(frm, to)
+    same = transition_score(frm, to, preferred_artists=["Bicep"], artist_intensity=0.0)
+    assert same == baseline
+
+
+def test_transition_unaffected_for_non_preferred():
+    # Soft bias only — a non-preferred track scores the same with or without prefs.
+    frm = _track("Origin")
+    to = _track("Four Tet")
+    baseline = transition_score(frm, to)
+    same = transition_score(frm, to, preferred_artists=["Bicep"], artist_intensity=0.8)
+    assert same == baseline
````
Verification:
- `source .venv/bin/activate && python -m pytest tests/test_artist_bias.py -x -q` passes.

#### Task 10 — Planner soft-bias test: tests/test_artist_bias.py (append)
Tools: editor
Assert the soft-bias contract at the planner level: building with `preferred_artists` set does NOT shrink the candidate pool and a non-preferred track can still be chosen. Use the real `build_set` against the API test DB seed pattern via an in-memory SQLite session (mirror `tests/api/conftest.py` seeding inline to avoid cross-fixture coupling).
Diff:
````diff
--- a/tests/test_artist_bias.py
+++ b/tests/test_artist_bias.py
@@
+
+# ── Planner-level soft-bias contract ──
+def _seeded_session():
+    from sqlalchemy import create_engine
+    from sqlalchemy.orm import sessionmaker
+    from sqlalchemy.pool import NullPool
+
+    from kiku.db.models import Base, Track
+
+    engine = create_engine("sqlite://", poolclass=NullPool)
+    Base.metadata.create_all(engine)
+    session = sessionmaker(bind=engine)()
+    for i in range(1, 21):
+        session.add(Track(
+            id=i,
+            title=f"Track {i}",
+            artist="Bicep" if i <= 3 else f"Artist {i}",
+            bpm=126.0 + (i % 5),
+            key="8A" if i % 2 == 0 else "8B",
+            dir_genre="techno",
+            dir_energy="mid",
+            duration_sec=360.0,
+            rating=3,
+            play_count=i,
+        ))
+    session.commit()
+    return session
+
+
+def test_planner_pool_not_filtered_by_preferred_artists():
+    """Preferred artists tilt scoring but never narrow the candidate pool."""
+    from kiku.setbuilder.planner import build_set
+
+    session = _seeded_session()
+    result = build_set(
+        session=session,
+        duration_min=30,
+        set_name="Artist Bias Test",
+        preferred_artists=["Bicep"],
+        artist_intensity=0.8,
+    )
+    assert result is not None
+    artists = {st.track.artist for st in result.tracks}
+    # The set leans toward Bicep but is NOT all-Bicep — other artists remain eligible.
+    assert any(a != "Bicep" for a in artists)
````
Verification:
- `source .venv/bin/activate && python -m pytest tests/test_artist_bias.py -x -q` passes.
- Note: if `result.tracks` is not the relationship name, the IMPLEMENT step inspects `kiku.db.models.Set` and uses the SetTrack→Track join present in that model (the API detail route already reads tracks via that relationship).

#### Task 11 — API smoke test: tests/api/test_sets_api.py
Tools: editor
Add a build test carrying `preferred_artists` + `artist_intensity`; assert the build completes. Uses existing `client` fixture.
Diff:
````diff
--- a/tests/api/test_sets_api.py
+++ b/tests/api/test_sets_api.py
@@ def test_build_set_with_vibe(client):
         # track_added events should carry the derived vibe
         assert "vibe_brightness" in body
 
 
+def test_build_set_with_preferred_artists(client):
+    resp = client.post("/api/sets/build", json={
+        "name": "Featured Set",
+        "duration_min": 30,
+        "energy_preset": "journey",
+        "beam_width": 2,
+        "preferred_artists": ["Artist 1"],
+        "artist_intensity": 0.8,
+    })
+    assert resp.status_code == 200
+    body = resp.text
+    assert "event: started" in body
+    assert "event: complete" in body or "event: error" in body
+
+
 def test_build_set_unknown_vibe(client):
````
Verification:
- `source .venv/bin/activate && python -m pytest tests/api/test_sets_api.py -x -q` passes.

#### Task 12 — Lint / type-check / test (changed files only)
Tools: shell
Note: ruff is NOT installed — use py_compile for Python syntax/type sanity.
Commands:
- `source .venv/bin/activate && python -m py_compile src/kiku/api/schemas.py src/kiku/setbuilder/scoring.py src/kiku/setbuilder/planner.py src/kiku/api/routes/sets.py tests/test_artist_bias.py tests/api/test_sets_api.py`
- `cd frontend && npx svelte-check --tsconfig ./tsconfig.json` — baseline is 0 errors / 4 warnings; only NEW errors are failures.
- `source .venv/bin/activate && python -m pytest tests/ -x -q` — full backend suite green (~182+ tests).

#### Task 13 — E2E (manual acceptance)
Tools: shell + browser
Steps:
- Start backend + frontend dev server (per CLAUDE.md run commands).
- Open Build a Set dialog → add a featured artist via the typeahead → set intensity → Build.
- Confirm more of that artist's tracks appear, but the set is NOT all-that-artist (soft bias holds).
- Confirm default (no featured artist) build is unchanged.

#### Task 14 — Commit (only changed files; never main)
Tools: git
Commands:
- `BRANCH=$(git rev-parse --abbrev-ref HEAD); [ "$BRANCH" != "main" ] || { echo 'ERROR: On main' >&2; exit 2; }`
- `git add -- src/kiku/api/schemas.py src/kiku/setbuilder/scoring.py src/kiku/setbuilder/planner.py src/kiku/api/routes/sets.py frontend/src/lib/types/index.ts frontend/src/lib/components/set/BuildSetDialog.svelte tests/test_artist_bias.py tests/api/test_sets_api.py`
- `git commit -m "$(printf 'spec(021): IMPLEMENT - featured-artists soft bias in set build\n\nCo-Authored-By: Claude Fable 5 <noreply@anthropic.com>')"`
- Leave untracked `trees/` alone.

### Validate

- L5 (HLO: soft nudge, not hard filter; beam can reach past): Task 2 `artist_term` is additive-only; Task 5 leaves `candidate_set`/cooldown untouched; Task 10 asserts pool not filtered and set not all-that-artist.
- L8 (MLO: add `preferred_artists` + `artist_intensity` to request & `build_set()`, mirroring vibe): Tasks 1 (schemas), 5 (planner), 6 (route) — same defaults/plumbing as vibe.
- L9 (MLO: soft artist bonus via token matcher; additive, never filter; non-preferred stay eligible): Task 2 reuses `artist_matches`; Task 9 `test_transition_unaffected_for_non_preferred`; Task 10 pool test.
- L10 (MLO: keep 5-track artist cooldown intact): Task 5 note — `_violates_artist_cooldown` at 246-247 unchanged, gates before scoring.
- L11 (MLO: surface the why — breakdown shows the nudge): Task 4 folds `"artist": artist_bd` into `score_replacement` breakdowns; Task 8 subtext "the artists you asked for".
- L12 (MLO: frontend typeahead + intensity, default off): Task 8 Typeahead + slider default `artistIntensity = 0`, attached only when list present.
- L13 (MLO: unit tests for scoring + planner, API test for request): Tasks 9, 10, 11.
- L18 (DT: reuse `artist_tokens`/`artist_matches`, don't reimplement): Task 2 imports `artist_matches`; no reimplementation.
- L19 (DT: artist knobs flow exactly like vibe request→API→planner→scoring): Tasks 1→6→5→3/4.
- L20 (DT: bonus is another small additive term in the same place): Task 3 adds `artist_contribution` beside `vibe_contribution`.
- L21 (DT: cooldown unchanged): Task 5 note.
- L24 (constraint: never a hard filter; pool unrestricted; differ by tilt not exclusion): Tasks 5 + 10.
- L25 (constraint: intensity-controlled and visible; default 0): Tasks 1/8 default 0.0; Task 4 breakdown contribution visible.
- L26 (constraint: collaborations count via token matcher): Task 9 `test_term_collaboration_matches`.
- L27 (constraint: cooldown wins over bias): Task 5 note (gate precedes scoring).
- L28 (constraint: voice — "set", warm, honors DJ's intent): Task 8 subtext + label wording ("the artists you asked for", "a gentle tilt"); commit/strings avoid banned words.
- L31-33 (out of scope: per-artist weighting / multi-anchor / avoidance): single `artist_intensity`, positive-only `artist_term`; no new pins or penalties.
- L36 (testing: match→bonus scaled; non-match→0; intensity 0→0; collab; planner not filtered): Tasks 9 + 10.
- L37 (testing: API accepts fields + threads, smoke): Task 11.
- L38 (E2E manual acceptance): Task 13.
- L41 (Behavior: honor principles, mirror vibe, reuse artists.py): mirrored throughout; Task 2 reuses `artist_matches`; soft-bias protected by Tasks 5/10.

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
