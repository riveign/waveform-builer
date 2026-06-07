# Human Section
Critical: any text/subsection here cannot be modified by AI.

## High-Level Objective (HLO)
Give the DJ a way to browse their library by album/EP — see the releases they own as releases, not just as flat track rows — and play any album in order with one click. Fill the gap in album track ordering by syncing Rekordbox `TrackNo`/`DiscNo` where available, parsing filename prefixes as a fallback, and offering an on-demand MusicBrainz match per album for the rest. This serves "Your Library Is the Lesson" — the DJ rediscovers what they already own as releases, with the artist's intended sequence preserved.

## Mid-Level Objectives (MLO)

### Phase A — Foundation (data + sync)
- ADD `track_number` (Integer, nullable) and `disc_number` (Integer, nullable) columns to `tracks` via Alembic migration
- UPDATE `kiku sync` to pull `TrackNo` and `DiscNo` from Rekordbox `DjmdContent`
- CREATE filename-prefix backfill (e.g. `01-18 Title.flac` → `track_number=18`, leading two-digit groups as `disc-track` when both present), ONLY fills NULLs — never overwrites Rekordbox values
- ENSURE backfill runs as part of `kiku sync` after Rekordbox values are applied (idempotent)

### Phase B — Albums API + browsing UI
- ADD `GET /api/albums` — aggregated `(album, normalized_artist)` groups returning album_key, title, artist, year, label, track_count, cover_track_id
  - Filters: `search`, `artist[]`, `label[]`, `year_min`, `year_max`, sort by `recent` | `artist` | `year`
  - Pagination matching existing `/api/tracks/search` pattern (`limit`, `offset`, `total`)
- ADD `GET /api/albums/{album_key}/tracks` — tracks ordered by `disc_number NULLS LAST, track_number NULLS LAST, file_path`
- UPDATE `LibraryBrowser.svelte` with view-mode toggle (Tracks ⇄ Albums), persisted in URL/local state
- CREATE `AlbumGrid.svelte` — card grid (artwork from first track, title, artist, year, track count)
- CREATE `AlbumDetail.svelte` — track list with positions, ▶ Play Album button using `playSet(negativeAlbumId, tracks, 0)` on the existing player store
- HANDLE compilations: when artist varies within `album`, group under "Various Artists" (album_key includes normalized album name)

### Phase C — MusicBrainz enrichment (on-demand)
- ADD `album_metadata` table keyed by `album_key` (album+artist normalized hash) storing `mb_release_id`, `last_matched_at`, `match_status`
- ADD `POST /api/albums/{album_key}/match-musicbrainz` — queries MB by `release:"<album>" AND artist:"<artist>"`, returns top 1–3 candidate releases with year, label, country, track count, recording titles
- ADD `POST /api/albums/{album_key}/apply-mb-mapping` — accepts user-confirmed `mb_release_id` + proposed `track_id → (disc_number, track_number)` mapping, writes to `tracks`, caches `mb_release_id` on `album_metadata`
- IMPLEMENT MusicBrainz client: `src/kiku/musicbrainz/client.py` — `httpx` async, 1 req/sec rate limit, `User-Agent: Kiku/<version> (riveign@gmail.com)`
- IMPLEMENT fuzzy track-mapping in `src/kiku/musicbrainz/match.py` — `rapidfuzz.token_set_ratio` on titles after stripping `(Original Mix)`, `feat. X`, remix suffixes; per-track confidence score
- UPDATE `AlbumDetail.svelte` with "Match on MusicBrainz" button → modal with candidate release picker → mapping review (your track → their position + confidence color) → Apply

## Details (DT)

### Data
- `tracks` table location: `src/kiku/db/models.py` (Track model lines 36–83)
- Existing album fields: `album`, `label`, `release_year` (all nullable, synced from Rekordbox)
- Current data: 4,307 tracks total, 3,255 with non-null album (~76%), 737 with Rekordbox `TrackNo > 0` (~22% of synced)
- Filename pattern coverage: ~50% of album tracks start with `NN-` or `NN ` prefix (sampled)
- Rekordbox source: `pyrekordbox.db6.tables.DjmdContent.TrackNo` (Integer), `.DiscNo` (Integer, mostly 0 in this lib)

### Album identity
- `album_key` derivation: `sha256(normalize(album) + "|" + normalize(album_artist_or_first_artist))[:12]` — stable, URL-safe
- Compilation detection: if >1 distinct artist within `(album)` group, set `album_artist = "Various Artists"` for keying
- Tracks with NULL album: excluded from `/api/albums`

### Track ordering
- Resolution at query time, never persisted: `ORDER BY COALESCE(disc_number, 1), COALESCE(track_number, 9999), file_path`
- This keeps unnumbered tracks at the end of their disc, ordered by filename — predictable fallback

### MusicBrainz constraints
- API: `https://musicbrainz.org/ws/2/release/?query=...&fmt=json`
- Rate limit: 1 req/sec sustained, enforced client-side via `asyncio.Semaphore` + last-request timestamp
- User-Agent mandatory per MB etiquette
- No API key required
- Candidate ranking: track count match (strongest signal) > year proximity to our `release_year` > label match

### Fuzzy matching
- Title normalization: lowercase, strip `(Original Mix|Extended Mix|Radio Edit|Club Mix)`, strip `feat. X` / `ft. X`, strip remix suffix `(... Remix)` keeping primary title
- Confidence: `rapidfuzz.fuzz.token_set_ratio` ≥ 85 → green, 70–84 → yellow, <70 → red (manual override required)
- Mapping algorithm: greedy bipartite — for each Kiku track pick best-scoring MB position not yet taken

### Files (likely touched)
- Backend:
  - `src/kiku/db/models.py` — Track model additions, new AlbumMetadata model
  - `alembic/versions/<new>_add_track_numbers_and_album_metadata.py` — migration
  - `src/kiku/db/sync.py` — TrackNo/DiscNo capture (lines 181–202 region)
  - `src/kiku/db/filename_track_numbers.py` — new module, backfill parser
  - `src/kiku/api/routes/albums.py` — new file
  - `src/kiku/api/routes/__init__.py` — register router
  - `src/kiku/api/schemas.py` — AlbumResponse, AlbumDetailResponse, MBCandidateResponse, MBApplyRequest
  - `src/kiku/musicbrainz/client.py` — new
  - `src/kiku/musicbrainz/match.py` — new
- Frontend:
  - `frontend/src/lib/components/library/LibraryBrowser.svelte` — view-mode toggle
  - `frontend/src/lib/components/library/AlbumGrid.svelte` — new
  - `frontend/src/lib/components/library/AlbumDetail.svelte` — new
  - `frontend/src/lib/components/library/MusicBrainzMatchModal.svelte` — new
  - `frontend/src/lib/api/albums.ts` — new
- Tests:
  - `tests/db/test_filename_track_numbers.py` — parser unit tests
  - `tests/api/test_albums.py` — endpoint integration tests
  - `tests/musicbrainz/test_match.py` — fuzzy matching unit tests
  - `tests/musicbrainz/test_client.py` — MB client with mocked httpx

### Testing

**Unit tests:**
- Filename prefix parser: `01 - X`, `01-02 X`, `1.X`, `X` (no prefix), unicode titles, disc-track combos
- Title normalization: strips `(Original Mix)`, `feat.`, remix suffixes; preserves real titles
- Fuzzy matcher confidence buckets (green/yellow/red thresholds)
- Album key derivation: same input → same key, compilation detection
- Track ordering SQL: nulls last, file_path tiebreaker

**Integration / API:**
- `GET /api/albums` — pagination, filters (search, artist, year range), sort modes
- `GET /api/albums/{album_key}/tracks` — ordering correctness with mixed null/numbered tracks
- `POST /api/albums/{album_key}/match-musicbrainz` — mocked MB responses, candidate ranking
- `POST /api/albums/{album_key}/apply-mb-mapping` — writes track_number/disc_number, caches mb_release_id, idempotent re-apply
- Rate-limit guard (mocked clock, asserts 1 req/sec)

**E2E (manual):**
- Sync after migration: TrackNo populated for known albums (verify ≥1 case from real lib)
- Toggle Tracks/Albums view, scroll grid, click album, play in order, verify A/B deck advances in track order
- Match on MusicBrainz for an album with NULL track numbers, review mapping, apply, verify reload shows positions

### Constraints
- Migration is additive only (no destructive changes to existing columns)
- Backfill must be idempotent and skip non-NULL values
- MusicBrainz writes are user-confirmed only — never silent
- Album view must not regress Tracks view performance (separate routes, no shared blocking queries)

## Behavior
Implement in stage commits (Phase A → B → C). Each phase is independently shippable and testable. Prefer extending the existing `LibraryBrowser` over a new top-level route to keep filters/state cohesive. Honor branding voice — CTAs read "Match on MusicBrainz" (not "Auto-fill" or "Smart match"), modal headings frame review as "Does this look right?", and confidence buckets surface the *why* (green = strong title match, yellow = partial, red = manual pick recommended). Never silent writes from MusicBrainz — the DJ always reviews the mapping before it persists.

# AI Section
Critical: AI can ONLY modify this section.

## Research

### Track model & migrations
- `src/kiku/db/models.py:36–83` — Track model. Relevant existing nullable fields: `album`, `label`, `release_year`. No `track_number` or `disc_number` columns.
- Junction-table template: `SetTrack` at `src/kiku/db/models.py:144–156` (composite PK, extra metadata columns).
- Alembic head: `alembic/versions/d4e5f6a7b8c9_add_track_affinities_table.py` (`down_revision='c3d4e5f6a7b8'`). New migration will branch from this head.
- Migration pattern: explicit `op.create_table(...)`, `op.create_index(...)`, server-default `sa.func.now()` for `created_at/updated_at` timestamps.

### Rekordbox sync
- `src/kiku/db/sync.py:150–202` — `track_data = dict(...)` block builds the row payload from `rb_track`. Patch point: add `track_number=rb_track.TrackNo or None` and `disc_number=rb_track.DiscNo or None` here.
- INSERT/UPDATE paths both consume `track_data`. UPDATE skips overwriting rating when `rating_source == "kiku"` — same idea will apply to keeping user-applied MusicBrainz mappings intact (handled at the AlbumMetadata level, not on Track).
- Filename-prefix backfill should run as a post-loop step inside `_process_tracks`, after `session.commit()`, only filling NULL `track_number`. Idempotent.

### API routes & schemas
- Router registration: `src/kiku/api/main.py:20–46` — add `app.include_router(albums.router)` next to existing entries.
- Search/pagination template: `src/kiku/api/routes/tracks.py:85–129` — `Query(None)` for array filters, `limit`/`offset` with defaults `50`/`0`, returns `PaginatedTracksResponse {items, total, offset, limit}`.
- CRUD template: `PATCH /api/tracks/{track_id}/rating` — `db.get(Track, id)`, 404 if missing, mutate, `db.commit()`, `db.refresh()`, return DTO.
- Pydantic style: `src/kiku/api/schemas.py` — `model_config = {"from_attributes": True}` for ORM mapping; `PaginatedX` follows `{items, total, offset, limit}`.
- DB session: `src/kiku/api/deps.py` — `get_db()` generator + `db: Session = Depends(get_db)` injection.

### Filename track-number parsing (new module)
- No existing track-number filename parser. Existing parser `src/kiku/parsing/directory.py` only handles parent-directory genre/energy.
- Sample filenames confirmed: `01-18 AMIGOS NUEVOS.flac`, `01-04 NO DA MÁS.flac`, `01-01 Guchi Polo.flac` — first group is `disc-track`. ~50% of album files match a leading-digit pattern.
- New module: `src/kiku/db/filename_track_numbers.py` with `parse_track_position(filename: str) -> tuple[int|None, int|None]` returning `(disc_number, track_number)`.

### Frontend library browser
- `frontend/src/lib/components/library/LibraryBrowser.svelte` — composes `<SearchFilters>` + `<TrackTable>`, drives `getTrackStore().search(params)`. View-mode toggle goes here.
- `TrackTable.svelte` — props `{tracks, selectedId, onselect}`, supports drag (`application/x-kiku-track`) + right-click context menu.
- `SearchFilters.svelte` — Svelte 5 runes, debounced text search (300ms), state-driven filter builder.
- Artwork URL: `frontend/src/lib/api/tracks.ts:64–66` — `getTrackArtworkUrl(id)`. Album cover = artwork of `cover_track_id`.
- Player: `frontend/src/lib/stores/player.svelte.ts:239–248` — `playSet(newSetId, tracks, startIndex=0)`. Use a synthetic negative id (e.g., `-1 * hash(album_key)`) to avoid colliding with real set ids.

### Modal pattern
- `frontend/src/lib/components/set/ImportPlaylistDialog.svelte` — `$bindable(false)` `open` prop, `$effect` syncing `dialogEl.showModal()`, keyboard ESC handler, drop zone + result preview. Template for MusicBrainzMatchModal.

### External HTTP & dependencies
- `httpx` is used (e.g. `src/kiku/soundcloud/client.py:1–91`) but is NOT explicitly listed in `pyproject.toml` — it's a transitive dep. Pin it in `[project.optional-dependencies].api` to be safe, or add as a core dep.
- `musicbrainzngs>=0.7` already pinned in `hunting` extra — can be reused, but our needs are simple (one search endpoint) and the lib is sync-only. Direct `httpx` calls give more control over rate limiting and user-agent. **Decision: use raw httpx, not musicbrainzngs**, to keep `albums` feature in core (not hunting extra) and to control the request loop.
- `thefuzz[speedup]>=0.22` already pinned in `hunting` extra — but our album feature shouldn't require the hunting extra. **Decision: move `thefuzz[speedup]` to core deps** (rapidfuzz-backed, small).

### Tests
- `tests/api/conftest.py` — in-memory SQLite, `Base.metadata.create_all`, seeds 20 tracks + 1 set + tinder/hunt fixtures. `client` fixture overrides `get_db`.
- `tests/api/test_tracks_api.py` shape: `client.get("/api/...")` → assert `status_code`, key shape, totals.
- Pattern for mocked HTTP: not yet established for MusicBrainz; will use `httpx.MockTransport` injected via the MB client constructor.

### Strategy

**Sequencing (one commit per phase, but bundled into a single IMPLEMENT stage per user request):**

**Phase A — Foundation**
1. Add `track_number`, `disc_number` to `Track` model.
2. Create AlbumMetadata model (table `album_metadata`, PK `album_key TEXT`, columns `mb_release_id TEXT NULL`, `last_matched_at DATETIME NULL`, `match_status TEXT NULL`).
3. Single Alembic migration revision branching from `d4e5f6a7b8c9`.
4. Update `src/kiku/db/sync.py` to populate `track_number=rb_track.TrackNo or None`, `disc_number=rb_track.DiscNo or None`.
5. New `src/kiku/db/filename_track_numbers.py` + post-sync backfill step (NULL-only).

**Phase B — Albums API + UI**
6. New `src/kiku/api/routes/albums.py`:
   - `GET /api/albums` — group by `(LOWER(album), LOWER(album_artist))` via SQL; album_artist resolved as `MIN(artist) OVER (PARTITION BY album)` and detected as "Various Artists" if `COUNT(DISTINCT artist) > 1`. Return album_key (sha256 of normalized album+artist, truncated 12), title, artist, year, label, track_count, cover_track_id (lowest track_number or first by file_path).
   - `GET /api/albums/{album_key}/tracks` — returns ordered tracks (`ORDER BY COALESCE(disc_number, 1), COALESCE(track_number, 9999), file_path`).
7. New `src/kiku/api/schemas.py` additions: `AlbumResponse`, `AlbumDetailResponse`, `PaginatedAlbumsResponse`, `MBCandidateResponse`, `MBApplyRequest`, `MBApplyResponse`.
8. Register router in `src/kiku/api/main.py`.
9. Frontend:
   - `frontend/src/lib/api/albums.ts` — `listAlbums`, `getAlbumTracks`, `matchAlbumMusicBrainz`, `applyAlbumMusicBrainz`.
   - `LibraryBrowser.svelte` — add view-mode toggle (Tracks ⇄ Albums), persist in localStorage.
   - `AlbumGrid.svelte` — responsive card grid (artwork via `getTrackArtworkUrl(cover_track_id)`, title, artist, year/track count).
   - `AlbumDetail.svelte` — track list with `disc.track` positions, ▶ Play Album button (calls `playSet(-Math.abs(hash(album_key)), tracks, 0)`), "Match on MusicBrainz" button.

**Phase C — MusicBrainz**
10. New `src/kiku/musicbrainz/__init__.py`, `client.py`, `match.py`.
    - `client.py` — `httpx.Client` (sync, matches SoundCloud pattern), `User-Agent: Kiku/<version> (riveign@gmail.com)`, `_throttle()` enforces 1.0s gap between requests, `search_releases(album, artist) -> list[ReleaseCandidate]`, `get_release(mb_id) -> ReleaseDetail` (with tracklist).
    - `match.py` — title normalization regex (strip parens variants, `feat.`, remix suffix), `match_tracklist(kiku_tracks, mb_recordings) -> list[MatchedPosition]` with confidence.
11. Endpoints in `albums.py`:
    - `POST /api/albums/{album_key}/match-musicbrainz` — returns 1–3 candidates with year, label, country, track count, recordings, and a pre-computed mapping preview against our tracks.
    - `POST /api/albums/{album_key}/apply-mb-mapping` — body `{mb_release_id, mappings: [{track_id, disc_number, track_number}]}` → write to tracks, upsert album_metadata.
12. Frontend `MusicBrainzMatchModal.svelte` — candidate picker → mapping review (color-coded confidence: green ≥85, yellow 70–84, red <70) → Apply.

**Testing strategy**
- Unit: `tests/db/test_filename_track_numbers.py` (parser edge cases), `tests/musicbrainz/test_match.py` (normalization + fuzzy matcher buckets).
- API: `tests/api/test_albums_api.py` — search, pagination, filters, ordering, MB match (with `httpx.MockTransport`), apply mapping (mocked candidates, verify DB writes).
- Extend `tests/api/conftest.py` seeds with multi-album fixtures (1 numbered album, 1 unnumbered album, 1 compilation).
- Manual E2E: post-implement sanity check on real DB after migration + a sync run.

**Dependency changes**
- Add `httpx>=0.27` to core `dependencies` (already transitively present).
- Add `thefuzz[speedup]>=0.22` to core `dependencies` (currently in `hunting` extra).

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
