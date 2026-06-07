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

### Files

**Backend (new)**
- `src/kiku/db/filename_track_numbers.py` — leading-digit parser
- `src/kiku/musicbrainz/__init__.py`
- `src/kiku/musicbrainz/client.py` — httpx client with 1 req/s throttle
- `src/kiku/musicbrainz/match.py` — normalization + fuzzy mapping
- `src/kiku/api/routes/albums.py` — list, detail, MB match, MB apply
- `alembic/versions/e5f6a7b8c9d0_add_track_numbers_and_album_metadata.py`

**Backend (modified)**
- `src/kiku/db/models.py` — Track adds `track_number`, `disc_number`; new `AlbumMetadata`
- `src/kiku/db/sync.py:181–202` — capture TrackNo/DiscNo; post-loop filename backfill
- `src/kiku/api/main.py:20–46` — register albums router
- `src/kiku/api/schemas.py` — Album/MB DTOs
- `pyproject.toml` — add `httpx` and `thefuzz[speedup]` to core deps

**Frontend (new)**
- `frontend/src/lib/api/albums.ts`
- `frontend/src/lib/components/library/AlbumGrid.svelte`
- `frontend/src/lib/components/library/AlbumDetail.svelte`
- `frontend/src/lib/components/library/MusicBrainzMatchModal.svelte`

**Frontend (modified)**
- `frontend/src/lib/components/library/LibraryBrowser.svelte` — view-mode toggle

**Tests (new)**
- `tests/db/test_filename_track_numbers.py`
- `tests/musicbrainz/test_match.py`
- `tests/musicbrainz/test_client.py`
- `tests/api/test_albums_api.py`
- `tests/api/conftest.py` — extend with album fixtures

### Tasks

#### Task 1 — `src/kiku/db/models.py`: Add track_number, disc_number, AlbumMetadata
Tools: editor

Add `track_number` and `disc_number` columns to Track. Add new `AlbumMetadata` model at end of file (before any non-model code).

````diff
--- a/src/kiku/db/models.py
+++ b/src/kiku/db/models.py
@@
     release_year = Column(Integer)
+    track_number = Column(Integer)
+    disc_number = Column(Integer)
     acquired_month = Column(String)
@@
 # End of models
+
+
+class AlbumMetadata(Base):
+    __tablename__ = "album_metadata"
+
+    album_key = Column(String, primary_key=True)
+    album = Column(String, nullable=False)
+    album_artist = Column(String, nullable=False)
+    mb_release_id = Column(String)
+    last_matched_at = Column(DateTime)
+    match_status = Column(String)
````

Verification:
- `python -c "from kiku.db.models import Track, AlbumMetadata; print(Track.track_number, AlbumMetadata.album_key)"`

#### Task 2 — Alembic migration
Tools: editor

Create `alembic/versions/e5f6a7b8c9d0_add_track_numbers_and_album_metadata.py`:

````diff
--- /dev/null
+++ b/alembic/versions/e5f6a7b8c9d0_add_track_numbers_and_album_metadata.py
@@
+"""add track_number, disc_number, album_metadata
+
+Revision ID: e5f6a7b8c9d0
+Revises: d4e5f6a7b8c9
+Create Date: 2026-06-07 11:00:00.000000
+"""
+from typing import Sequence, Union
+
+from alembic import op
+import sqlalchemy as sa
+
+
+revision: str = "e5f6a7b8c9d0"
+down_revision: Union[str, None] = "d4e5f6a7b8c9"
+branch_labels: Union[str, Sequence[str], None] = None
+depends_on: Union[str, Sequence[str], None] = None
+
+
+def upgrade() -> None:
+    op.add_column("tracks", sa.Column("track_number", sa.Integer(), nullable=True))
+    op.add_column("tracks", sa.Column("disc_number", sa.Integer(), nullable=True))
+    op.create_index("ix_tracks_album", "tracks", ["album"])
+
+    op.create_table(
+        "album_metadata",
+        sa.Column("album_key", sa.String(), nullable=False),
+        sa.Column("album", sa.String(), nullable=False),
+        sa.Column("album_artist", sa.String(), nullable=False),
+        sa.Column("mb_release_id", sa.String(), nullable=True),
+        sa.Column("last_matched_at", sa.DateTime(), nullable=True),
+        sa.Column("match_status", sa.String(), nullable=True),
+        sa.PrimaryKeyConstraint("album_key"),
+    )
+
+
+def downgrade() -> None:
+    op.drop_table("album_metadata")
+    op.drop_index("ix_tracks_album", table_name="tracks")
+    op.drop_column("tracks", "disc_number")
+    op.drop_column("tracks", "track_number")
````

Verification:
- `source .venv/bin/activate && alembic upgrade head` (against `data/dj_library.db` — should advance head to e5f6a7b8c9d0)
- `sqlite3 data/dj_library.db "PRAGMA table_info(tracks);" | grep -E "track_number|disc_number"`

#### Task 3 — `src/kiku/db/filename_track_numbers.py`: leading-digit parser
Tools: editor

Create the file with two regex patterns: `disc-track` (e.g. `01-18 Title`) and `track-only` (e.g. `09. Title`, `09 - Title`). Returns `(disc_number, track_number)` tuple with `None` for missing parts.

````diff
--- /dev/null
+++ b/src/kiku/db/filename_track_numbers.py
@@
+"""Parse leading disc/track numbers from filenames as a fallback when Rekordbox lacks them."""
+from __future__ import annotations
+
+import os
+import re
+
+
+_DISC_TRACK = re.compile(r"^(\d{1,2})[-_](\d{1,2})[\s._-]")
+_TRACK_ONLY = re.compile(r"^(\d{1,2})[\s._-]")
+
+
+def parse_track_position(file_path: str) -> tuple[int | None, int | None]:
+    """Return (disc_number, track_number) extracted from filename.
+
+    Returns (None, None) if no leading numeric prefix is present.
+    Disc-track form `01-18 Title.flac` -> (1, 18).
+    Track-only form `09 - Title.flac` -> (None, 9).
+    Single digits accepted; values > 99 ignored.
+    """
+    base = os.path.basename(file_path or "")
+    m = _DISC_TRACK.match(base)
+    if m:
+        disc = int(m.group(1))
+        track = int(m.group(2))
+        if 0 < disc <= 99 and 0 < track <= 99:
+            return disc, track
+    m = _TRACK_ONLY.match(base)
+    if m:
+        track = int(m.group(1))
+        if 0 < track <= 99:
+            return None, track
+    return None, None
````

Verification:
- Unit tests cover this in Task 14.

#### Task 4 — `src/kiku/db/sync.py`: capture TrackNo/DiscNo + post-loop backfill
Tools: editor

In `_process_tracks`, add the two fields to `track_data`, and after the main loop call a new helper `_backfill_filename_track_numbers(session)`.

````diff
--- a/src/kiku/db/sync.py
+++ b/src/kiku/db/sync.py
@@
         track_data = dict(
             title=title,
             artist=artist,
             album=rb_track.AlbumName,
             label=rb_track.LabelName,
@@
             release_year=rb_track.ReleaseYear,
+            track_number=int(rb_track.TrackNo) if getattr(rb_track, "TrackNo", None) else None,
+            disc_number=int(rb_track.DiscNo) if getattr(rb_track, "DiscNo", None) else None,
             acquired_month=dir_meta.acquired_month if dir_meta else None,
             last_synced=now,
         )
````

And add at module bottom (before `if __name__`-style guards if any):

````diff
--- a/src/kiku/db/sync.py
+++ b/src/kiku/db/sync.py
@@
+from kiku.db.filename_track_numbers import parse_track_position
+
+
+def _backfill_filename_track_numbers(session) -> int:
+    """Fill NULL track_number/disc_number from filename leading digits. Returns count updated."""
+    updated = 0
+    rows = session.query(Track).filter(
+        Track.album.isnot(None),
+        Track.track_number.is_(None),
+        Track.file_path.isnot(None),
+    ).all()
+    for tr in rows:
+        disc, track = parse_track_position(tr.file_path)
+        if track is None:
+            continue
+        if tr.track_number is None:
+            tr.track_number = track
+            updated += 1
+        if tr.disc_number is None and disc is not None:
+            tr.disc_number = disc
+    if updated:
+        session.commit()
+    return updated
````

Then call `_backfill_filename_track_numbers(session)` inside `_process_tracks` after the main `session.commit()` and before playlist tagging. Locate by reading sync.py and inserting the call at the right line.

Verification:
- After sync runs, `SELECT COUNT(*) FROM tracks WHERE track_number IS NOT NULL;` returns ≥737.

#### Task 5 — `src/kiku/api/schemas.py`: Album + MB DTOs
Tools: editor

Append to schemas.py:

````diff
--- a/src/kiku/api/schemas.py
+++ b/src/kiku/api/schemas.py
@@
+class AlbumResponse(BaseModel):
+    album_key: str
+    album: str
+    artist: str
+    year: int | None = None
+    label: str | None = None
+    track_count: int
+    cover_track_id: int | None = None
+    is_compilation: bool = False
+    mb_release_id: str | None = None
+
+
+class PaginatedAlbumsResponse(BaseModel):
+    items: list[AlbumResponse]
+    total: int
+    offset: int
+    limit: int
+
+
+class AlbumTracksResponse(BaseModel):
+    album: AlbumResponse
+    tracks: list[TrackResponse]
+
+
+class MBCandidateRecording(BaseModel):
+    position: int
+    disc: int
+    title: str
+    length_ms: int | None = None
+
+
+class MBCandidate(BaseModel):
+    mb_release_id: str
+    title: str
+    artist: str
+    year: int | None = None
+    country: str | None = None
+    label: str | None = None
+    track_count: int
+    recordings: list[MBCandidateRecording]
+    score: float
+
+
+class MBMatchResponse(BaseModel):
+    candidates: list[MBCandidate]
+
+
+class MBMappingItem(BaseModel):
+    track_id: int
+    disc_number: int | None = None
+    track_number: int | None = None
+    mb_position: int | None = None
+    confidence: float = 0.0
+
+
+class MBApplyRequest(BaseModel):
+    mb_release_id: str
+    mappings: list[MBMappingItem]
+
+
+class MBApplyResponse(BaseModel):
+    updated_count: int
+    album_key: str
+    mb_release_id: str
````

Verification:
- `python -c "from kiku.api.schemas import AlbumResponse, MBApplyRequest"`

#### Task 6 — `src/kiku/musicbrainz/`: client + match
Tools: editor

Create `src/kiku/musicbrainz/__init__.py` (empty), `client.py`, `match.py`.

`client.py`:
- `class MusicBrainzClient` with `httpx.Client` (sync), base URL `https://musicbrainz.org/ws/2`
- `User-Agent: Kiku/0.1 (riveign@gmail.com)`
- `_throttle()` enforces ≥1.0s gap between requests using a class-level last-request timestamp
- `search_releases(album, artist, limit=3) -> list[dict]` — calls `/release/?query=...&fmt=json&limit=N`, returns parsed list with id, title, artist-credit, date, country, label-info, track-count, score
- `get_release(mb_release_id) -> dict` — calls `/release/{id}?inc=recordings&fmt=json`

`match.py`:
- `normalize_title(s: str) -> str` — lowercase, strip `(Original Mix|Extended Mix|Radio Edit|Club Mix|Original)`, `feat. X` / `ft. X`, `(... Remix)` suffix, collapse whitespace
- `match_tracklist(kiku_tracks: list, mb_recordings: list) -> list[dict]` — greedy bipartite by `rapidfuzz.fuzz.token_set_ratio` on normalized titles. Returns per-kiku-track `{track_id, mb_position, disc_number, confidence}`.

Full content shown inline in IMPLEMENT.

Verification:
- Unit tests in Task 14.

#### Task 7 — `src/kiku/api/routes/albums.py`: endpoints
Tools: editor

Create the file with:
- `router = APIRouter(prefix="/api/albums", tags=["albums"])`
- `GET /` — list aggregated albums with filters and pagination
- `GET /{album_key}/tracks` — return album + ordered tracks
- `POST /{album_key}/match-musicbrainz` — call MB client, return candidates with pre-computed per-track mapping confidence
- `POST /{album_key}/apply-mb-mapping` — write `track_number`/`disc_number`, upsert AlbumMetadata

Album aggregation strategy: SQL-side group by `LOWER(TRIM(album))`, compute `album_artist` via subquery (distinct artist count > 1 → "Various Artists", else MIN(artist)). Build `album_key = sha256(normalized_album + "|" + normalized_artist)[:12]`. Cover track id = track with lowest `(disc_number, track_number, file_path)` in the album.

Full content shown inline in IMPLEMENT.

Verification:
- `curl http://localhost:8000/api/albums?limit=5` returns JSON with items[].

#### Task 8 — `src/kiku/api/main.py`: register router
Tools: editor

````diff
--- a/src/kiku/api/main.py
+++ b/src/kiku/api/main.py
@@
-from kiku.api.routes import (
-    tracks, audio, waveforms, sets, stats, tinder, export, config, hunt, soundcloud,
-)
+from kiku.api.routes import (
+    tracks, audio, waveforms, sets, stats, tinder, export, config, hunt, soundcloud, albums,
+)
@@
     app.include_router(soundcloud.router)
+    app.include_router(albums.router)
     return app
````

Verification:
- App starts, `/api/albums` is in `/docs`.

#### Task 9 — `pyproject.toml`: pin httpx + thefuzz in core
Tools: editor

````diff
--- a/pyproject.toml
+++ b/pyproject.toml
@@
 dependencies = [
   "sqlalchemy>=2.0",
   "click>=8.0",
   "rich>=13.0",
   "numpy>=1.21",
   "mutagen>=1.45",
   "tomli_w>=1.0",
   "alembic>=1.12",
+  "httpx>=0.27",
+  "thefuzz[speedup]>=0.22",
 ]
````

Verification:
- `source .venv/bin/activate && python -m pip install -e '.[api]'` succeeds.

#### Task 10 — `frontend/src/lib/api/albums.ts`
Tools: editor

Create with: `listAlbums(params)`, `getAlbumTracks(albumKey)`, `matchAlbumMusicBrainz(albumKey)`, `applyAlbumMusicBrainz(albumKey, body)`. Types mirror backend schemas. Full content in IMPLEMENT.

Verification:
- `cd frontend && npx svelte-check --tsconfig ./tsconfig.json` passes.

#### Task 11 — `LibraryBrowser.svelte`: view-mode toggle
Tools: editor

Add a top-strip toggle (Tracks / Albums). When `mode === 'albums'`, render `<AlbumGrid>` instead of `<SearchFilters>+<TrackTable>`. Persist mode in localStorage. Track view unchanged.

Verification:
- Manual toggle in dev server.

#### Task 12 — `AlbumGrid.svelte` + `AlbumDetail.svelte`
Tools: editor

`AlbumGrid.svelte`:
- Props: `{ onselect: (album) => void }`
- On mount: `listAlbums({limit: 60})` and render responsive grid (200px cards: artwork via `getTrackArtworkUrl(cover_track_id)`, title, artist, "YEAR · N tracks")
- Search input + sort dropdown (recent/artist/year)

`AlbumDetail.svelte`:
- Props: `{ albumKey: string, onback: () => void }`
- Fetches `getAlbumTracks(albumKey)`
- Header: artwork + title + artist + year + label
- Buttons: ▶ Play Album (calls `getPlayerStore().playSet(-(hash(albumKey)), tracks, 0)`), "Match on MusicBrainz" (opens MusicBrainzMatchModal)
- Track list with `{disc.position}. {title} — {artist}` and play row buttons

Verification:
- Manual click-through in dev server.

#### Task 13 — `MusicBrainzMatchModal.svelte`
Tools: editor

`<dialog>` pattern (mirror ImportPlaylistDialog).
- Props: `{ open: $bindable(false), albumKey: string, kikuTracks: Track[], onapply: () => void }`
- Step 1: on open, fetch candidates via `matchAlbumMusicBrainz(albumKey)`. Show 1–3 cards with year/label/country/track count/score; user picks one.
- Step 2: render mapping table (your track ↔ MB position, confidence color: green ≥85, yellow 70–84, red <70). User can override `mb_position` per row via dropdown.
- Apply button → `applyAlbumMusicBrainz(albumKey, {mb_release_id, mappings})` → fire onapply.

Verification:
- Manual on a real album with NULL track numbers.

#### Task 14 — Tests: unit
Tools: editor

Create:
- `tests/db/__init__.py` (if missing), `tests/db/test_filename_track_numbers.py`
- `tests/musicbrainz/__init__.py`, `tests/musicbrainz/test_match.py`, `tests/musicbrainz/test_client.py`

Filename tests cover: `01-18 X.flac`, `09 - X.mp3`, `09. X.mp3`, `X.mp3`, `100 X.mp3` (out of range), unicode.

Match tests cover: normalization strips `(Original Mix)`, `feat.`, remix suffix; greedy bipartite picks correct positions on a 5-track mock.

Client tests use `httpx.MockTransport` to fake MB responses and verify throttle (≥1.0s gap between two calls). Full content in IMPLEMENT.

Verification:
- `source .venv/bin/activate && python -m pytest tests/db tests/musicbrainz -x -q`

#### Task 15 — Tests: API integration
Tools: editor

Extend `tests/api/conftest.py` to seed multi-album fixtures:
- Album A "Numbered EP" — 3 tracks with track_number 1/2/3
- Album B "Unnumbered LP" — 4 tracks with no track_number
- Album C "Mix Compilation" — 5 tracks, varying artists (compilation)

Create `tests/api/test_albums_api.py`:
- `test_list_albums` — total 3, all expected keys present
- `test_album_compilation_detected` — Album C `is_compilation=true`, artist="Various Artists"
- `test_album_tracks_ordering` — Album A returns positions 1/2/3 in order
- `test_album_search_by_artist` — filter narrows to expected album
- `test_match_musicbrainz_mocked` — patches `MusicBrainzClient.search_releases` to return canned data
- `test_apply_mb_mapping_writes_track_numbers` — POST `apply-mb-mapping`, verify DB rows updated

Verification:
- `source .venv/bin/activate && python -m pytest tests/api/test_albums_api.py -x -q`

#### Task 16 — Lint
Tools: shell

````
source .venv/bin/activate && ruff check src/kiku/db/filename_track_numbers.py src/kiku/musicbrainz/ src/kiku/api/routes/albums.py src/kiku/api/schemas.py src/kiku/db/models.py src/kiku/db/sync.py src/kiku/api/main.py
````

Frontend type-check:
````
cd frontend && npx svelte-check --tsconfig ./tsconfig.json 2>&1 | tail -30
````

#### Task 17 — E2E sanity
Tools: shell

- Apply migration: `source .venv/bin/activate && alembic upgrade head`
- Restart API, hit `/api/albums?limit=3` — verify shape
- Toggle to Albums in dev UI, open an album, Play Album, verify A/B deck queues
- MB match flow on an unnumbered album (mock-friendly via dev real call)

#### Task 18 — Commit
Tools: git

Single IMPLEMENT commit at the end:
````
git add -- src/kiku/db/models.py src/kiku/db/sync.py src/kiku/db/filename_track_numbers.py \
  alembic/versions/e5f6a7b8c9d0_*.py \
  src/kiku/musicbrainz/ \
  src/kiku/api/main.py src/kiku/api/routes/albums.py src/kiku/api/schemas.py \
  pyproject.toml \
  frontend/src/lib/api/albums.ts \
  frontend/src/lib/components/library/LibraryBrowser.svelte \
  frontend/src/lib/components/library/AlbumGrid.svelte \
  frontend/src/lib/components/library/AlbumDetail.svelte \
  frontend/src/lib/components/library/MusicBrainzMatchModal.svelte \
  tests/db/ tests/musicbrainz/ tests/api/test_albums_api.py tests/api/conftest.py \
  specs/2026/06/albums-musicbrainz/015-album-browser-with-musicbrainz.md
git commit -m "spec(015): IMPLEMENT - album-browser-with-musicbrainz"
````

### Validate

- HLO album browsing view (L8) — covered by Task 7, 10, 11, 12.
- HLO play in order (L8) — covered by Task 12 (`playSet(...)`).
- HLO track-number sync from Rekordbox (L8) — Task 4.
- HLO filename fallback (L8) — Task 3 + Task 4 backfill.
- HLO MusicBrainz on-demand (L8) — Tasks 6, 7, 13.
- MLO Phase A migration (L11) — Task 1, 2.
- MLO sync TrackNo/DiscNo (L12) — Task 4.
- MLO filename backfill (L13–L14) — Tasks 3, 4 (backfill helper).
- MLO `GET /api/albums` + filters + pagination (L17–L19) — Task 7.
- MLO `GET /api/albums/{album_key}/tracks` (L20) — Task 7.
- MLO LibraryBrowser toggle (L21) — Task 11.
- MLO AlbumGrid (L22) + AlbumDetail (L23) — Task 12.
- MLO Compilations as "Various Artists" (L24) — Task 7 aggregation logic.
- MLO album_metadata table (L27) — Task 1, 2.
- MLO `POST .../match-musicbrainz` (L28) — Task 7.
- MLO `POST .../apply-mb-mapping` (L29) — Task 7.
- MLO fuzzy matching (L30) — Task 6 (`match.py`).
- MLO MB client rate limit + UA (L31) — Task 6 (`client.py`).
- MLO MB match modal (L32) — Task 13.
- DT branding (CTA wording, "Does this look right?") — Task 13 copy.
- DT testing (L94–L117) — Tasks 14, 15.

## Plan Review
<!-- Filled if required to validate plan -->

## Implement

### Backend (Phase A — Foundation)
- **Migration `e5f6a7b8c9d0`** (`alembic/versions/e5f6a7b8c9d0_add_track_numbers_and_album_metadata.py`): adds `track_number` + `disc_number` columns on `tracks`, creates `album_metadata` table, adds `ix_tracks_album` index. Down-revision `d4e5f6a7b8c9`.
- **Model**: `Track.track_number` / `Track.disc_number` (Integer, nullable) added in `src/kiku/db/models.py`. New `AlbumMetadata` model at end of same file, PK `album_key`.
- **Sync** (`src/kiku/db/sync.py`): reads `TrackNo` / `DiscNo` from Rekordbox `DjmdContent` via existing pyrekordbox loop. Inserts/updates on every `kiku sync`. After the playlist-tag pass, `_backfill_filename_track_numbers(session)` runs filename parsing for any track where `track_number IS NULL`.
- **Filename parser** (`src/kiku/db/filename_track_numbers.py`): two regexes — `_DISC_TRACK = ^(\d{1,2})[-_](\d{1,2})[\s._-]` for `01-18 Title.flac`, `_TRACK_ONLY = ^(\d{1,2})[\s._-]` for `09 - Title.flac`. Values clamped to 1..99.

### Backend (Phase B — Albums API)
- **Schemas** (`src/kiku/api/schemas.py`): `AlbumResponse`, `PaginatedAlbumsResponse`, `AlbumTracksResponse`, plus `track_number` / `disc_number` added to `TrackResponse`.
- **Router** (`src/kiku/api/routes/albums.py`): `GET /api/albums` aggregates per-album with search/artist/label/year filters and sort by `artist|year|recent`. Compilation detection: >1 distinct artist for the album → artist becomes `Various Artists`. `album_key = sha256(normalize(album)|normalize(artist))[:12]`.
- **Tracks endpoint**: `GET /api/albums/{album_key}/tracks` orders by `(disc_number NULLS LAST, track_number NULLS LAST, file_path)`.
- **Cover selection**: lowest position track by `(disc, track, file_path)` so the album art mirrors the on-disc opener.
- **Tracks route patch** (`src/kiku/api/routes/tracks.py`): `_track_to_response` now emits `track_number` / `disc_number`.
- **Wire-up** (`src/kiku/api/main.py`): `app.include_router(albums.router)`.

### Backend (Phase C — MusicBrainz enrichment)
- **MB client** (`src/kiku/musicbrainz/client.py`): raw httpx with process-wide 1 req/s throttle (`_last_request_at` + `threading.Lock`), User-Agent `Kiku/0.1 ( riveign@gmail.com )` per MB etiquette. `search_releases(album, artist, limit=3)` and `get_release(id)`. `_escape()` strips Lucene-reserved characters.
- **Fuzzy match** (`src/kiku/musicbrainz/match.py`): `normalize_title` strips `(Original Mix)` / `feat.` / remix suffixes and lowercases. `match_tracklist` does greedy bipartite assignment using `fuzz.token_set_ratio`. Unmatched Kiku tracks get `mb_position=None, confidence=0.0`.
- **Match endpoint** (`POST /api/albums/{album_key}/match-musicbrainz`): searches MB, fetches each candidate's full release (recordings + artist-credits + labels), runs `match_tracklist` per candidate, returns `MBCandidate[]` with `mapping_preview` inline.
- **Apply endpoint** (`POST /api/albums/{album_key}/apply-mb-mapping`): validates `track_id ∈ album`, writes `track_number` / `disc_number` per mapping, upserts `AlbumMetadata` (`mb_release_id`, `last_matched_at`, `match_status='applied'`). Returns `updated_count`.

### Frontend
- **API client** (`frontend/src/lib/api/albums.ts`): typed `listAlbums`, `getAlbumTracks`, `matchAlbumMusicBrainz`, `applyAlbumMusicBrainz`. Mirrors backend Pydantic shapes.
- **Type extension** (`frontend/src/lib/types/index.ts`): `track_number` / `disc_number` added to `Track`.
- **LibraryBrowser**: Tracks / Albums view-mode toggle, persisted to `localStorage` (`kiku:libraryViewMode`). `openAlbumKey` state drives AlbumDetail navigation.
- **AlbumGrid**: card grid with 250 ms debounced search, artist/year/recent sort, paginated load-more (60 per page). Uses `getTrackArtworkUrl(cover_track_id)` for covers.
- **AlbumDetail**: 200×200 cover, title, artist, year/track count/label/compilation badge. `▶ Play album` calls `player.playSet(-hashKey(albumKey), tracks, startIndex)` — synthetic negative set id avoids collision with real set IDs. `Match on MusicBrainz` CTA opens the MB modal. Track list shows `positionLabel` (`"01"` or `"2.05"` for multi-disc).
- **MusicBrainzMatchModal**: 5 stages (`loading` → `pick` → `review` → `applying` → `error`). Candidate picker shows year / label / country / track count / score. Mapping review: 4-column grid `(your track | MB position dropdown | MB title | confidence %)`. Confidence color: green ≥85%, yellow ≥70%, red <70%. Per-row override of MB position. Apply submits `MBApplyRequest` with `track_number = mb_position`.

### Branding alignment
- CTA reads "Match on MusicBrainz", never "Auto-fill" — preserves *Show the Why*.
- Confirmation modal asks "Does this mapping look right?" — *Opinions You Can See Through*.
- Mapping confidence rendered per-row, color-coded — *Opinions You Can See Through*.
- DJ must click Apply on the previewed mapping — never a silent write — *Grow the Ear*.

## Test Evidence & Outputs

### Unit tests (new)
- `tests/test_filename_track_numbers.py` — 15 cases covering disc-track, track-only, no-prefix, zero-track rejection, dir-stripping. **15/15 pass**.
- `tests/test_musicbrainz_match.py` — 10 cases covering paren/feat/remix stripping, perfect match, remix-suffix tolerance, unmatched track handling, greedy global-best selection, multi-disc preservation. **10/10 pass**.
- `tests/test_musicbrainz_client.py` — 4 cases using `httpx.MockTransport`: query+User-Agent, get_release inc-recordings, 1s throttle (monkeypatched `time.monotonic`/`time.sleep`), HTTP error propagation. **4/4 pass**.

### API integration tests (new)
- `tests/api/test_albums_api.py` — 10 cases against seeded in-memory SQLite with three album flavors (numbered EP / unnumbered LP / compilation): list, search, year filter, year-sort, track-number ordering, file-path fallback, 404 unknown key, apply writes track_number + caches AlbumMetadata, apply skips unknown track_ids, MB match (patched `kiku.musicbrainz.client.MusicBrainzClient`). **10/10 pass**.

### Full suite
- `python -m pytest tests/ --ignore=tests/test_energy.py -q` → **190 passed**. The single `test_energy::test_build_at_boundary` failure pre-exists on `main` (verified via `git stash`) and is unrelated to this spec.

### Frontend type-check
- `npx svelte-check` → **0 errors, 4 pre-existing warnings** (CSS line-clamp, unused selector, a11y on FillReorderDialog/ReplaceTrackModal — all unrelated files).

### End-to-end smoke
- Production DB (1,703 albums) — `GET /api/albums?limit=3` returns correctly-grouped releases; `GET /api/albums/{key}/tracks` returns ordered tracks (NULL track_numbers correctly fall through to file_path sort, ready for MusicBrainz enrichment).

## Updated Doc
<!-- Filled by explicit documentation udpates after /spec IMPLEMENT -->

## Post-Implement Review
<!-- Filled by /spec REVIEW -->
