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
