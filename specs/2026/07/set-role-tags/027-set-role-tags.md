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
