# Human Section
Critical: any text/subsection here cannot be modified by AI.

## High-Level Objective (HLO)
Let a DJ mark a track with **set-role affinity tags** — **opener**, **closer**, and/or **break** — a
curation signal that says "this track earns its place at a certain moment in a set" *independent of*
its energy, key, genre, or mode. Some tracks are simply great openers or closers regardless of where
the math would put them; some are perfect for a mid-set breather. This is a fourth DJ-provided curation
axis alongside `rating`, the energy-zone override, and `vibe` — the DJ's ear, made durable.

The tags are **non-exclusive and non-restrictive**: a track can hold more than one role (e.g. both
opener and break), and holding a role never stops the track from being used anywhere else in a set.
It is an affinity, not a filter. This directly serves Kiku Principle 6 ("Every Track Deserves a
Chance") and Principle 2 ("Your Library Is the Lesson").

## Mid-Level Objectives (MLO)
- **ADD** durable storage for per-track set-role tags on the Track model (`set_roles`, a JSON list),
  with a canonical `SET_ROLES = ["opener", "closer", "break"]` constant.
- **ADD** an API endpoint to set/clear a track's roles, and surface `set_roles` on the track response.
- **CREATE** a `SetRolePicker` UI control and wire it into the track context menu alongside the
  existing energy-zone and star-rating controls (optimistic update → PATCH → column write).
- **ADD** a small badge shown wherever tracks render, so a tagged track reads its role at a glance.
- **ADD** a way to filter/find "my openers / closers / break tracks" while hand-building a set.
- **ENSURE** all user-facing copy frames the tag as the DJ's own judgement ("you marked this a great
  opener"), never as the tool's verdict.

## Details (DT)

### Scope — V1 (deliberately tight, confirmed with user)
**IN:**
1. Storage for the tag.
2. A picker to set/clear roles per track in the track context menu.
3. A badge shown wherever tracks render.
4. The ability to filter/find "my openers / closers / break tracks" when hand-building a set.

**OUT (explicitly deferred to a later spec — document as a follow-up, do NOT build):**
- Any auto-builder behavior change. The builder does **not** yet prefer opener-tagged tracks for the
  first slot, closer-tagged tracks for the last slot, or auto-place break-tagged tracks at energy
  dips. The v1 deliverable is the curation signal itself + manual surfacing; wiring it into set
  generation is a separate, later spec.

### Design direction (follow existing patterns; confirmed via codebase research)
- **Storage:** a `set_roles` JSON-list column on the `Track` model, mirroring the existing
  `playlist_tags` Text/JSON column in `src/kiku/db/models.py`. Define `SET_ROLES = ["opener",
  "closer", "break"]`. Add an Alembic migration copying
  `alembic/versions/a7b8c9d0e1f2_add_vibe_columns.py`.
- **API:** `PATCH /api/tracks/{id}/set-roles` copying the `update_track_rating` route in
  `src/kiku/api/routes/tracks.py`; add `set_roles` to `TrackResponse` and `_track_to_response()`;
  add a request schema copying `TrackRatingRequest`. Validate incoming roles against `SET_ROLES`.
- **Frontend:** `SetRolePicker.svelte` copying `EnergyZonePicker.svelte`; wire into
  `TrackContextMenu.svelte` alongside the energy-zone + rating controls; add `updateTrackSetRoles()`
  to `frontend/src/lib/api/tracks.ts` copying `updateTrackRating()`; add `set_roles` to the `Track`
  type; a badge on the track cards; a filter affordance for hand-building.
- **Closest end-to-end precedent to follow:** the energy-zone edit flow (optimistic UI update →
  PATCH → column write), spanning `EnergyZonePicker.svelte` → `TrackContextMenu.svelte` → route →
  persistence.

### Constraints
- Non-exclusive: multiple roles per track allowed; empty list = untagged.
- Non-restrictive: a role must never filter a track out of any set-building candidate pool.
- Keep changes minimal; reuse existing patterns rather than inventing new machinery.
- All user-facing copy follows Kiku voice (warm, teaching; set = "set", DJ = "you").

### Testing
- **Unit:** `set_roles` round-trips through the model and migration; API endpoint validates roles
  against `SET_ROLES` and rejects unknown values; `_track_to_response()` includes `set_roles`;
  empty/clear path works.
- **E2E / integration:** DJ opens the track context menu → sets a role → badge appears; clears the
  role → badge disappears; the roles persist across reload; the hand-building filter surfaces only
  tracks with the chosen role.

## Behavior
You are a senior engineer implementing the smallest correct change that ships the curation signal
end to end. Prefer reusing the established rating / energy-zone / vibe patterns over new abstractions.
Do not touch the set-building/scoring path in v1 — record it as a documented follow-up instead.

# AI Section
Critical: AI can ONLY modify this section.

## Research

The tag mirrors the existing `playlist_tags` JSON-in-Text pattern end to end. Every extension point
below is verified against current source (line numbers are current as of this stage).

### Backend

- **`src/kiku/db/models.py:64`** — `playlist_tags = Column(Text)` on `Track` is the exact storage
  precedent (JSON list stored as Text). New `set_roles = Column(Text)` column goes right after it
  (before `last_synced` at L65). No `AudioFeatures` change — this is DJ intent, belongs on `Track`.
- **Canonical roles constant** — no existing home; define `SET_ROLES = ("opener", "closer", "break")`
  in a small module. `src/kiku/analysis/autotag.py:27` (`ENERGY_ZONES`) is the sibling precedent, but
  set-roles are not energy, so a dedicated location (`src/kiku/setbuilder/` or a new
  `src/kiku/set_roles.py`) is cleaner and import-cycle-safe (schemas + store + route all need it).
- **Migration** — head revision is **`d0e1f2a3b4c5`** (verified via `alembic heads`). New migration
  copies `alembic/versions/a7b8c9d0e1f2_add_vibe_columns.py` (single `op.add_column` /
  `op.drop_column` pair), with `down_revision = 'd0e1f2a3b4c5'`. Column is `sa.Text()`, nullable.
- **Request schema** — `src/kiku/api/schemas.py:8-16` `TrackRatingRequest` (Pydantic + `field_validator`)
  is the template. New `TrackSetRolesRequest` holds `roles: list[str]` and validates each against
  `SET_ROLES` (reject unknown), dedupes, allows empty list = clear.
- **Response schema** — `src/kiku/api/schemas.py:52` `playlist_tags: list[str] = []` is the exact
  precedent. Add `set_roles: list[str] = []` right after it (L52).
- **Response builder** — `src/kiku/api/routes/tracks.py:44-51` parses `playlist_tags` JSON into
  `tags`; L82 passes `playlist_tags=tags`. Mirror both: parse `set_roles` JSON → `roles`, pass
  `set_roles=roles` in the `TrackResponse(...)` call (add after L82).
- **PATCH route** — `src/kiku/api/routes/tracks.py:175-189` `update_track_rating` is the exact
  template: get-or-404, mutate column, `db.commit()`, `db.refresh()`, return `_track_to_response`.
  New `PATCH /{track_id}/set-roles` writes `track.set_roles = json.dumps(validated_roles)` (or
  `None`/`"[]"` when empty). Add its schema import to the `from kiku.api.schemas import (...)` block
  at L10-23.
- **Filter (hand-building)** — `src/kiku/db/store.py:87-176` `search_tracks`. The `rating_min` block
  at L158-159 is the simplest filter precedent. Add a keyword-only `set_role: str | None = None`
  param; SQLite has no JSON operators guaranteed, so filter with `Track.set_roles.ilike(f'%"{role}"%')`
  (roles are stored as a JSON string list, so the quoted token match is exact-enough and index-free).
  Wire through the route: `src/kiku/api/routes/tracks.py:87-105` (add `set_role` Query param),
  pass-through at L107-125, and add to the `other_filters` tuple at L131-134.

### Frontend

- **Picker** — `frontend/src/lib/components/library/EnergyZonePicker.svelte` (module script defines
  list + colors + tips; renders `MenuItem`s). Clone as `SetRolePicker.svelte` with
  `ROLES = ['opener','closer','break']`. Difference from energy: roles are **multi-select toggles**
  (a track can hold several), so `MenuItem selected={roles.includes(role)}` and `onselect` toggles
  membership rather than replacing a single value.
- **Context menu** — `frontend/src/lib/components/library/TrackContextMenu.svelte`. The energy block
  (L54-63, submenu + `handleZoneSelect` optimistic pattern at L27-39) and rating block (L67-74) are
  the templates. Add a "Set role" section + `handleRoleToggle()` doing optimistic
  `ontrackupdated?.({ set_roles })` → `updateTrackSetRoles()` → rollback on catch (mirrors L41-51).
- **API client** — `frontend/src/lib/api/tracks.ts:56-62` `updateTrackRating`. Add
  `updateTrackSetRoles(trackId, roles: string[])` PATCHing `/api/tracks/${id}/set-roles`. Add
  `set_role?: string` to `SearchParams` (L4-21) for the filter.
- **Type** — `frontend/src/lib/types/index.ts:34` `playlist_tags: string[]`. Add
  `set_roles: string[];` right after it in `interface Track` (L7-36).
- **Badge** — render sites that already read `playlist_tags`/`resolved_energy`:
  `TrackCard.svelte`, `TrackTable.svelte`, `RelatedTrackCard.svelte` (all in
  `frontend/src/lib/components/library/`). A small role chip (opener/closer/break) rendered from
  `track.set_roles`.
- **Filter affordance** — `frontend/src/lib/components/library/SearchFilters.svelte` +
  `LibraryBrowser.svelte` host the existing filter chips (energy_zone, rating_min) and call
  `searchTracks`. Add a set-role filter control there, feeding `set_role` into `SearchParams`.

### Tests

- **API tests** — `tests/api/test_tracks_api.py` with fixtures in `tests/api/conftest.py` (in-memory
  SQLite via `Base.metadata.create_all`, seeds tracks 1-20, provides `client` + `db_session`).
  `test_track_features_includes_vibe` (L8-19) is the response-field regression pattern to copy.
  New tests: PATCH set-roles persists + returns them; unknown role → 422; empty list clears;
  `_track_to_response` includes `set_roles`; `search?set_role=opener` filters correctly.
- **Migration** — `Base.metadata.create_all` (used by tests) builds schema from models, so the new
  column is picked up automatically; migration is verified separately by `alembic upgrade head` on a
  scratch DB.
- **Frontend** — no frontend test infra exists (per project memory: "zero frontend tests"); validate
  via `npx svelte-check` + manual E2E.

### Strategy

**Build order (backend-first, each layer independently verifiable):**

1. **Constant + model + migration** — add `SET_ROLES`, `Track.set_roles` column, Alembic migration
   off head `d0e1f2a3b4c5`. Verify: `alembic upgrade head` on a scratch DB; model round-trips a list.
2. **Schemas** — `TrackSetRolesRequest` (validate against `SET_ROLES`), `set_roles` on
   `TrackResponse`. Verify: unit test rejects unknown role, accepts empty.
3. **Route + response builder** — `PATCH /{id}/set-roles`; parse+emit `set_roles` in
   `_track_to_response`. Verify: API test round-trips and 404s/422s correctly.
4. **Filter** — `set_role` in `search_tracks` + search route + `other_filters` tuple. Verify: API
   test `search?set_role=opener` returns only tagged tracks; JSON-token match doesn't false-positive
   on substrings (test "open" vs "opener" — the quoted-token match `%"opener"%` guards this).
5. **Frontend type + API client** — `set_roles` on `Track`, `updateTrackSetRoles`, `set_role` on
   `SearchParams`. Verify: `svelte-check` clean.
6. **Picker + context menu** — `SetRolePicker.svelte` (multi-toggle) wired into `TrackContextMenu`
   with optimistic update + rollback. Verify: `svelte-check`; manual toggle in browser.
7. **Badge + filter UI** — role chip on track cards; filter control in `SearchFilters`. Verify:
   manual E2E (tag a track → badge appears → filter surfaces it → clear → gone).

**Testing strategy:** unit + API tests co-located in `tests/api/test_tracks_api.py` (extend, don't
create new file) using the existing `client`/`db_session` fixtures. Cover: persist, clear, unknown-role
rejection, response inclusion, filter correctness incl. the substring false-positive guard. Frontend
validated by `svelte-check` + a manual end-to-end pass (no test infra to hook into).

**Voice/principle checks:** picker + badge copy read as the DJ's own judgement (P5/P6); the filter is
additive, never removes a track from any other pool (non-restrictive constraint, spec Details L…).

**Explicit non-goals (guard against scope creep):** do NOT touch `planner._pick_seed`,
`scoring.track_quality`, `filler`, or `set_analyzer`. The auto-builder wiring is the deferred
follow-up spec.

## Plan

### Files
- `src/kiku/set_roles.py` *(new)* — `SET_ROLES` constant + `normalize_roles()` validator.
- `src/kiku/db/models.py` — add `set_roles` Text column on `Track` (after L64).
- `alembic/versions/e1f2a3b4c5d6_add_set_roles_column.py` *(new)* — add/drop `tracks.set_roles`,
  `down_revision='d0e1f2a3b4c5'` (current head).
- `src/kiku/api/schemas.py` — `TrackSetRolesRequest` (after L16); `set_roles` field on `TrackResponse`
  (after L52).
- `src/kiku/api/routes/tracks.py` — import schema (L10-23); parse+emit `set_roles` in
  `_track_to_response` (L44-84); `PATCH /{id}/set-roles` (after L189); `set_role` search param (L87-105,
  pass-through L107-125, `other_filters` L131-134).
- `src/kiku/db/store.py` — `set_role` filter in `search_tracks` (param L104ish; filter after L159).
- `frontend/src/lib/types/index.ts` — `set_roles: string[]` on `Track` (after L34).
- `frontend/src/lib/api/tracks.ts` — `updateTrackSetRoles()` (after L62); `set_role?` on `SearchParams`
  (L4-21).
- `frontend/src/lib/components/library/SetRolePicker.svelte` *(new)* — multi-toggle picker.
- `frontend/src/lib/components/library/SetRoleBadge.svelte` *(new)* — role chip(s).
- `frontend/src/lib/components/library/TrackContextMenu.svelte` — wire picker (imports L1-11, handler
  after L39, UI after L63).
- `frontend/src/lib/components/library/TrackCard.svelte`, `RelatedTrackCard.svelte`, `TrackTable.svelte`
  — render `SetRoleBadge`.
- `frontend/src/lib/components/library/SearchFilters.svelte` — set-role filter control + active chip.
- `tests/api/test_tracks_api.py` — extend with set-role tests.

### Tasks

#### Task 1 — set_roles.py: constant + validator (new file)
Tools: editor. Create `src/kiku/set_roles.py` with EXACT content:
````python
"""Set-role affinity tags — a DJ curation axis independent of energy, key, or genre.

A track can carry any combination of these roles, and a role never restricts where
the track may be placed in a set (non-exclusive, non-restrictive). See spec 027.
"""
from __future__ import annotations

SET_ROLES: tuple[str, ...] = ("opener", "closer", "break")


def normalize_roles(roles: list[str]) -> list[str]:
    """Validate + dedupe roles against SET_ROLES, returned in canonical order.

    Raises ValueError on any unknown role.
    """
    unknown = [r for r in roles if r not in SET_ROLES]
    if unknown:
        raise ValueError(f"unknown set role(s): {', '.join(sorted(set(unknown)))}")
    present = set(roles)
    return [r for r in SET_ROLES if r in present]
````
Verification: `python -c "from kiku.set_roles import normalize_roles; print(normalize_roles(['break','opener','opener']))"` → `['opener', 'break']`.

#### Task 2 — models.py: add set_roles column
Tools: editor.
````diff
--- a/src/kiku/db/models.py
+++ b/src/kiku/db/models.py
@@
     playlist_tags = Column(Text)  # JSON list of playlist names this track belongs to
+    set_roles = Column(Text)  # JSON list of DJ set-role tags: opener/closer/break (spec 027)
     last_synced = Column(String)
````
Verification: ruff on file.

#### Task 3 — Alembic migration (new file)
Tools: editor. Create `alembic/versions/e1f2a3b4c5d6_add_set_roles_column.py` with EXACT content:
````python
"""add set_roles column to tracks

Revision ID: e1f2a3b4c5d6
Revises: d0e1f2a3b4c5
Create Date: 2026-07-05 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e1f2a3b4c5d6'
down_revision: Union[str, None] = 'd0e1f2a3b4c5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('tracks', sa.Column('set_roles', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('tracks', 'set_roles')
````
Verification: `source .venv/bin/activate && alembic heads` shows single head `e1f2a3b4c5d6`; `alembic upgrade head` on a scratch DB copy succeeds.

#### Task 4 — schemas.py: request + response field
Tools: editor.
````diff
--- a/src/kiku/api/schemas.py
+++ b/src/kiku/api/schemas.py
@@
     @field_validator('rating')
     @classmethod
     def validate_rating(cls, v: int) -> int:
         if not 0 <= v <= 5:
             raise ValueError('rating must be between 0 and 5')
         return v
 
 
+class TrackSetRolesRequest(BaseModel):
+    roles: list[str] = []
+
+    @field_validator('roles')
+    @classmethod
+    def validate_roles(cls, v: list[str]) -> list[str]:
+        from kiku.set_roles import normalize_roles
+        return normalize_roles(v)
+
+
 class EnergyConflictResponse(BaseModel):
@@
     comment: str | None = None
     playlist_tags: list[str] = []
+    set_roles: list[str] = []
     genre_family: str | None = None
````
Verification: ruff; `TrackSetRolesRequest(roles=['banger'])` raises ValidationError.

#### Task 5 — routes/tracks.py: import, response builder, PATCH route, search filter
Tools: editor. Four edits in one file.

5a. Import the request schema:
````diff
--- a/src/kiku/api/routes/tracks.py
+++ b/src/kiku/api/routes/tracks.py
@@
     TrackRatingRequest,
     TrackResponse,
     TrackSetAppearance,
+    TrackSetRolesRequest,
     TransitionScoreBreakdown,
 )
````
5b. Parse + emit `set_roles` in `_track_to_response`:
````diff
--- a/src/kiku/api/routes/tracks.py
+++ b/src/kiku/api/routes/tracks.py
@@
     # Parse playlist_tags JSON
     tags: list[str] = []
     if t.playlist_tags:
         try:
             tags = _json.loads(t.playlist_tags)
         except (ValueError, TypeError):
             pass
 
+    # Parse set_roles JSON (DJ curation tags — spec 027)
+    roles: list[str] = []
+    if t.set_roles:
+        try:
+            roles = _json.loads(t.set_roles)
+        except (ValueError, TypeError):
+            pass
+
     genre = t.dir_genre or t.rb_genre
@@
         playlist_tags=tags,
+        set_roles=roles,
         genre_family=family,
     )
````
5c. Add PATCH route after `update_track_rating` (after its `return` at L189):
````diff
--- a/src/kiku/api/routes/tracks.py
+++ b/src/kiku/api/routes/tracks.py
@@
     track.rating = body.rating if body.rating > 0 else None
     track.rating_source = "kiku"
     db.commit()
     db.refresh(track)
     return _track_to_response(track)
 
 
+@router.patch("/{track_id}/set-roles", response_model=TrackResponse)
+def update_track_set_roles(
+    track_id: int,
+    body: TrackSetRolesRequest,
+    db: Session = Depends(get_db),
+) -> TrackResponse:
+    """Set a track's set-role tags (opener/closer/break). Empty list clears them.
+
+    Roles are a DJ curation signal, non-exclusive and non-restrictive — a track can
+    hold several and a role never stops it being used elsewhere in a set (spec 027).
+    """
+    import json as _json
+
+    track = db.get(Track, track_id)
+    if not track:
+        raise HTTPException(status_code=404, detail="Track not found")
+    track.set_roles = _json.dumps(body.roles) if body.roles else None
+    db.commit()
+    db.refresh(track)
+    return _track_to_response(track)
+
+
 @router.post("/{track_id}/played", status_code=204)
````
5d. Add `set_role` search param + pass-through + `other_filters`:
````diff
--- a/src/kiku/api/routes/tracks.py
+++ b/src/kiku/api/routes/tracks.py
@@
     rating_min: int | None = None,
     plays_min: int | None = None,
     plays_max: int | None = None,
+    set_role: str | None = None,
     sort: str | None = None,
     limit: int = 50,
     offset: int = 0,
     db: Session = Depends(get_db),
 ):
     tracks, total = search_tracks(
         db,
         search=search,
         title=title,
         artist=artist,
         genre=genre,
         bpm_min=bpm_min,
         bpm_max=bpm_max,
         energy=energy,
         energy_zone=energy_zone,
         key=key,
         label=label,
         rating_min=rating_min,
         plays_min=plays_min,
         plays_max=plays_max,
+        set_role=set_role,
         sort=sort,
         limit=limit,
         offset=offset,
     )
@@
     other_filters = any(
         f is not None for f in (title, artist, genre, key, label, bpm_min, bpm_max,
-                                energy, energy_zone, rating_min, plays_min, plays_max)
+                                energy, energy_zone, rating_min, plays_min, plays_max,
+                                set_role)
     )
````
Verification: ruff; endpoints exercised by Task 14.

#### Task 6 — store.py: set_role filter in search_tracks
Tools: editor.
````diff
--- a/src/kiku/db/store.py
+++ b/src/kiku/db/store.py
@@
     rating_min: int | None = None,
     plays_min: int | None = None,
     plays_max: int | None = None,
+    set_role: str | None = None,
     sort: str | None = None,
     search: str | None = None,
     limit: int = 50,
     offset: int = 0,
 ) -> tuple[list[Track], int]:
@@
     if rating_min is not None:
         q = q.filter(Track.rating >= rating_min)
+    if set_role:
+        # set_roles is a JSON string list, e.g. '["opener", "break"]'. Match the
+        # quoted token so "open" never false-positives on "opener" (spec 027).
+        q = q.filter(Track.set_roles.ilike(f'%"{set_role}"%'))
     if plays_min is not None:
````
Verification: ruff; filter covered by Task 14.

#### Task 7 — types/index.ts: set_roles on Track
Tools: editor.
````diff
--- a/frontend/src/lib/types/index.ts
+++ b/frontend/src/lib/types/index.ts
@@
 	comment: string | null;
 	playlist_tags: string[];
+	set_roles: string[];
 	genre_family: string | null;
 }
````
Verification: svelte-check.

#### Task 8 — tracks.ts: client fn + SearchParams
Tools: editor.
````diff
--- a/frontend/src/lib/api/tracks.ts
+++ b/frontend/src/lib/api/tracks.ts
@@
 	rating_min?: number;
 	plays_min?: number;
 	plays_max?: number;
+	set_role?: string;
 	sort?: string;
 	limit?: number;
 	offset?: number;
 }
@@
 export async function updateTrackRating(trackId: number, rating: number): Promise<Track> {
 	return fetchJson<Track>(`/api/tracks/${trackId}/rating`, {
 		method: 'PATCH',
 		headers: { 'Content-Type': 'application/json' },
 		body: JSON.stringify({ rating }),
 	});
 }
 
+export async function updateTrackSetRoles(trackId: number, roles: string[]): Promise<Track> {
+	return fetchJson<Track>(`/api/tracks/${trackId}/set-roles`, {
+		method: 'PATCH',
+		headers: { 'Content-Type': 'application/json' },
+		body: JSON.stringify({ roles }),
+	});
+}
+
 export function getTrackArtworkUrl(id: number): string {
````
Verification: svelte-check.

#### Task 9 — SetRolePicker.svelte (new, multi-toggle)
Tools: editor. Create `frontend/src/lib/components/library/SetRolePicker.svelte` with EXACT content:
````svelte
<script lang="ts" module>
	export const SET_ROLES = ['opener', 'closer', 'break'] as const;
	export type SetRole = (typeof SET_ROLES)[number];

	export const ROLE_TIPS: Record<string, string> = {
		opener: 'A track you reach for to open — it sets the room, whatever its energy',
		closer: 'A track that sends people home — the last-track feeling',
		break: 'A breather mid-set — a moment to reset the room',
	};
</script>

<script lang="ts">
	import MenuItem from '$lib/components/primitives/MenuItem.svelte';

	let {
		current = [],
		ontoggle,
	}: {
		current: string[];
		ontoggle: (role: string) => void;
	} = $props();
</script>

<div class="role-picker" role="menu">
	{#each SET_ROLES as role}
		<MenuItem selected={current.includes(role)} onselect={() => ontoggle(role)}>
			{#snippet icon()}
				<span class="role-check" aria-hidden="true">{current.includes(role) ? '✓' : ''}</span>
			{/snippet}
			{role}
		</MenuItem>
	{/each}
</div>

<style>
	.role-picker {
		display: flex;
		flex-direction: column;
		gap: var(--space-2xs);
	}
	.role-check {
		width: 10px;
		display: inline-flex;
		justify-content: center;
		color: var(--text-2);
		flex-shrink: 0;
	}
</style>
````
Verification: svelte-check.

#### Task 10 — SetRoleBadge.svelte (new)
Tools: editor. Create `frontend/src/lib/components/library/SetRoleBadge.svelte` with EXACT content:
````svelte
<script lang="ts">
	let { roles = [] }: { roles: string[] } = $props();
</script>

{#if roles.length}
	<span class="set-roles" role="group" aria-label="Set roles">
		{#each roles as role}
			<span class="set-role-badge" title="You marked this a great {role}">{role}</span>
		{/each}
	</span>
{/if}

<style>
	.set-roles {
		display: inline-flex;
		gap: var(--space-2xs);
	}
	.set-role-badge {
		font-size: var(--text-2xs, 0.65rem);
		text-transform: uppercase;
		letter-spacing: 0.04em;
		padding: 1px var(--space-2xs);
		border-radius: var(--radius-sm);
		background: var(--surface-2);
		color: var(--text-2);
		border: 1px solid var(--border-default);
		line-height: 1.4;
		white-space: nowrap;
	}
</style>
````
Verification: svelte-check.

#### Task 11 — TrackContextMenu.svelte: wire picker
Tools: editor. Three edits.
11a. Imports:
````diff
--- a/frontend/src/lib/components/library/TrackContextMenu.svelte
+++ b/frontend/src/lib/components/library/TrackContextMenu.svelte
@@
 	import { submitDecision } from '$lib/api/tinder';
-	import { updateTrackRating } from '$lib/api/tracks';
+	import { updateTrackRating, updateTrackSetRoles } from '$lib/api/tracks';
 	import { getPlayerStore } from '$lib/stores/player.svelte';
 	import EnergyZonePicker from './EnergyZonePicker.svelte';
 	import { ZONE_COLORS } from './EnergyZonePicker.svelte';
+	import SetRolePicker from './SetRolePicker.svelte';
 	import StarRating from '../primitives/StarRating.svelte';
````
11b. Handler after `handleZoneSelect` (after its closing brace, before `handleRatingChange`):
````diff
--- a/frontend/src/lib/components/library/TrackContextMenu.svelte
+++ b/frontend/src/lib/components/library/TrackContextMenu.svelte
@@
 		try {
 			await submitDecision(track.id, 'override', zone);
 		} catch {
 			ontrackupdated?.({ resolved_energy: previousZone, energy_source: previousSource, energy_confidence: previousConfidence });
 		}
 	}
 
+	async function handleRoleToggle(role: string) {
+		const previous = track.set_roles ?? [];
+		const next = previous.includes(role)
+			? previous.filter((r) => r !== role)
+			: [...previous, role];
+		// Keep the menu open — the DJ may toggle several roles at once.
+		ontrackupdated?.({ set_roles: next });
+
+		try {
+			await updateTrackSetRoles(track.id, next);
+		} catch {
+			ontrackupdated?.({ set_roles: previous });
+		}
+	}
+
 	async function handleRatingChange(rating: number) {
````
11c. UI section after the energy submenu snippet (between `{/snippet}` at L63 and the `<MenuSeparator />` at L65):
````diff
--- a/frontend/src/lib/components/library/TrackContextMenu.svelte
+++ b/frontend/src/lib/components/library/TrackContextMenu.svelte
@@
 {#snippet energySub()}
 	<EnergyZonePicker current={track.resolved_energy} onselect={handleZoneSelect} />
 {/snippet}
 
+<MenuSeparator />
+
+<span class="menu-label" id="ctx-role-label">Set role</span>
+<MenuItem submenu={roleSub} submenuLabel="Set role">
+	{track.set_roles?.length ? track.set_roles.join(', ') : 'not set'}
+</MenuItem>
+{#snippet roleSub()}
+	<SetRolePicker current={track.set_roles ?? []} ontoggle={handleRoleToggle} />
+{/snippet}
+
 <MenuSeparator />
 
 <span class="menu-label" id="ctx-rating-label">Rating</span>
````
Verification: svelte-check; menu shows "Set role" with a submenu of three toggles.

#### Task 12 — Render SetRoleBadge in track cards
Tools: editor. In each of `TrackCard.svelte`, `RelatedTrackCard.svelte`, `TrackTable.svelte`:
1. Add import in the instance `<script lang="ts">` block: `import SetRoleBadge from './SetRoleBadge.svelte';`
2. Place `<SetRoleBadge roles={track.set_roles} />` in the identity/chip row so it renders only when
   the track has roles (the component self-hides on empty):
   - `TrackCard.svelte`: inside the `.zone-chips` row (grep anchor: the `<div class="zone-chips">` at
     both the RELATED tier ~L357 and STANDALONE tier ~L489) — add after the energy chip block.
   - `RelatedTrackCard.svelte`: inside `<div class="chips">` (~L271), after the energy chip (~L303).
   - `TrackTable.svelte`: in the row cell that renders `resolved_energy` (~L137-138), append the badge
     after the `.cell-energy` span.
Verification: svelte-check; a tagged track shows an uppercase opener/closer/break chip; an untagged
track shows nothing (no empty span).

#### Task 13 — SearchFilters.svelte: set-role filter control
Tools: editor. Mirror the `ratingMin` filter end-to-end:
1. State (near `let ratingMin = $state('');` L28): `let setRole = $state('');`
2. `buildParams()` (after `if (ratingMin) params.rating_min = Number(ratingMin);` L68):
   `if (setRole) params.set_role = setRole;`
3. `hasActiveFilters` (add to the boolean chain incl. `ratingMin !== ''` ~L138): `|| setRole !== ''`
4. Clear/reset block (near `ratingMin = '';` ~L174): `setRole = '';`
5. Active-filter chip (mirror the rating chip at L359-361):
   `{#if setRole}<Chip value={setRole} size="sm" removable removeLabel="Clear set-role filter" onremove={() => { setRole = ''; searchNow(); }} />{/if}`
6. Control in the advanced-filter area (mirror the rating `<select class="small-select">` at L545):
````svelte
	<select class="small-select" bind:value={setRole} onchange={searchNow} aria-label="Set role">
		<option value="">Any role</option>
		<option value="opener">Openers</option>
		<option value="closer">Closers</option>
		<option value="break">Break tracks</option>
	</select>
````
Verification: svelte-check; selecting "Openers" filters the library to opener-tagged tracks; the active
chip appears and clears.

#### Task 14 — API tests
Tools: editor. Append to `tests/api/test_tracks_api.py`:
````python
def test_update_set_roles_persists_and_returns(client):
    resp = client.patch("/api/tracks/1/set-roles", json={"roles": ["opener", "break"]})
    assert resp.status_code == 200
    assert set(resp.json()["set_roles"]) == {"opener", "break"}
    # Persisted + canonical order on read
    resp2 = client.get("/api/tracks/1")
    assert resp2.json()["set_roles"] == ["opener", "break"]


def test_update_set_roles_clear(client):
    client.patch("/api/tracks/1/set-roles", json={"roles": ["closer"]})
    resp = client.patch("/api/tracks/1/set-roles", json={"roles": []})
    assert resp.status_code == 200
    assert resp.json()["set_roles"] == []


def test_update_set_roles_rejects_unknown(client):
    resp = client.patch("/api/tracks/1/set-roles", json={"roles": ["banger"]})
    assert resp.status_code == 422


def test_update_set_roles_404(client):
    resp = client.patch("/api/tracks/999/set-roles", json={"roles": ["opener"]})
    assert resp.status_code == 404


def test_search_filter_set_role(client):
    client.patch("/api/tracks/3/set-roles", json={"roles": ["opener"]})
    client.patch("/api/tracks/4/set-roles", json={"roles": ["closer"]})
    resp = client.get("/api/tracks/search?set_role=opener")
    data = resp.json()
    ids = {t["id"] for t in data["items"]}
    assert 3 in ids
    assert 4 not in ids
    assert all("opener" in t["set_roles"] for t in data["items"])
````
Note: `normalize_roles` returns canonical order (opener, closer, break), so the persisted-order
assertion is deterministic.
Verification: Task 15 runs them.

#### Task 15 — Lint + type-check
Tools: shell.
- `source .venv/bin/activate && ruff check src/kiku/set_roles.py src/kiku/db/models.py src/kiku/api/schemas.py src/kiku/api/routes/tracks.py src/kiku/db/store.py alembic/versions/e1f2a3b4c5d6_add_set_roles_column.py`
- `source .venv/bin/activate && python -m pytest tests/api/test_tracks_api.py -q`
- `cd frontend && npx svelte-check --tsconfig ./tsconfig.json`
Expectation: ruff clean, all API tests green, svelte-check no new errors.

#### Task 16 — E2E (manual)
Tools: shell + browser. Start API + frontend; in the library:
1. Open a track's context menu → "Set role" → toggle "opener" and "break" → both show ✓, menu stays
   open, badge appears on the row/card.
2. Reload → roles persist.
3. Advanced filters → "Openers" → only opener-tagged tracks show; active chip appears; clear it → full
   list returns.
4. Re-open menu → toggle "opener" off → badge updates.
Expectation: all steps pass; no track is ever removed from any other view by having a role.

#### Task 17 — Commit
Tools: git.
- `git add -- src/kiku/set_roles.py src/kiku/db/models.py alembic/versions/e1f2a3b4c5d6_add_set_roles_column.py src/kiku/api/schemas.py src/kiku/api/routes/tracks.py src/kiku/db/store.py frontend/src/lib/types/index.ts frontend/src/lib/api/tracks.ts frontend/src/lib/components/library/SetRolePicker.svelte frontend/src/lib/components/library/SetRoleBadge.svelte frontend/src/lib/components/library/TrackContextMenu.svelte frontend/src/lib/components/library/TrackCard.svelte frontend/src/lib/components/library/RelatedTrackCard.svelte frontend/src/lib/components/library/TrackTable.svelte frontend/src/lib/components/library/SearchFilters.svelte tests/api/test_tracks_api.py`
- `BRANCH=$(git rev-parse --abbrev-ref HEAD); [ "$BRANCH" != "main" ] || { echo 'ERROR: on main' >&2; exit 2; }`
- `git commit -m "spec(027): IMPLEMENT - set-role-tags"`

### Validate
- **HLO — opener/closer/break tag independent of energy/key/genre** (L4-9): stored on `Track` as its
  own `set_roles` column (Task 2), never derived from energy/audio — satisfied.
- **HLO — non-exclusive (multiple roles per track)** (L11-13): JSON list storage + multi-toggle picker
  (Tasks 2, 9, 11) — satisfied.
- **HLO — non-restrictive (never filters a track out of a set)** (L11-13): the tag drives only an
  additive search filter (Task 6) + badges; no set-building/candidate code touched (Task list has none)
  — satisfied.
- **MLO — durable storage + SET_ROLES constant** (L18-19): Tasks 1-3 — satisfied.
- **MLO — API to set/clear + surface on response** (L20): Tasks 4, 5 (empty list clears via `None`) —
  satisfied.
- **MLO — picker in context menu** (L21-22): Tasks 9, 11 — satisfied.
- **MLO — badge wherever tracks render** (L23): Tasks 10, 12 (3 card surfaces) — satisfied.
- **MLO — filter/find my openers/closers/break** (L24): Tasks 6, 8, 13 — satisfied.
- **MLO — copy frames as DJ's own judgement** (L25-26): badge title "You marked this a great {role}"
  (Task 10), picker tips (Task 9) — satisfied.
- **DT — validate roles against SET_ROLES, reject unknown** (L… Details): `normalize_roles` +
  `field_validator` (Tasks 1, 4), tested 422 (Task 14) — satisfied.
- **DT — follow existing patterns (rating/energy/vibe), minimal change** (L… Details): every task
  mirrors a named precedent; no new abstractions beyond one tiny constant module — satisfied.
- **DT — Kiku voice** (L… Details): "not set", "Openers/Break tracks", "sends people home" copy —
  satisfied.
- **Testing (unit + e2e)** (L… Testing): Task 14 (persist/clear/reject/filter) + Task 16 (manual E2E)
  — satisfied.
- **Scope OUT — no auto-builder change** (L… Scope): no task touches `planner`/`scoring`/`filler`/
  `set_analyzer`; recorded as the deferred follow-up — satisfied.

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
