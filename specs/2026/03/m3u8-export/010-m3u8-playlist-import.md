# Human Section
Critical: any text/subsection here cannot be modified by AI.

## High-Level Objective (HLO)

Import Rekordbox M3U8 playlist exports into Kiku as "imported sets" — parsing the M3U8 format, matching tracks to the DJ's library, and creating sets that preserve the original track order. This is Phase 1 of a 3-phase feature (Import → Analyze → Build) that will teach DJs why their freestyle sessions work by scoring transitions and identifying teaching moments. The import phase unblocks all subsequent analysis and set-building phases.

## Mid-Level Objectives (MLO)

- ADD Alembic migration: 4 columns on `sets` (source, source_ref, is_analyzed, analysis_cache) + 2 columns on `set_tracks` (inferred_energy, inference_source)
- CREATE M3U8 parser module at `src/kiku/import_playlist/m3u8.py` — manual line-by-line parsing with BOM handling, NFC/NFD Unicode normalization, backslash conversion, `#PLAYLIST` tag support
- IMPLEMENT track matching cascade: exact normalized path → case-insensitive path → fuzzy filename with ±10s duration proximity
- ADD API endpoint `POST /api/sets/import/m3u8` — accepts multipart file upload OR JSON with file_path; returns `ImportResultResponse` with match report
- ADD CLI command `kiku import <file>` with `--name`, `--analyze`, `--dry-run` flags
- CREATE frontend `ImportPlaylistDialog.svelte` — file drop zone, name field, analyze toggle, result display with matched/unmatched breakdown
- ADD API client function `importPlaylist()` in `frontend/src/lib/api/sets.ts`
- ENSURE 0-based position indexing (matching `add_track_to_set` in `store.py`)
- ADD index on `tracks.file_path` in the migration for fast path lookups
- IMPLEMENT batch matching: load all tracks into memory dict once, match in O(1) per track — no N+1 queries
- ENSURE no new Track rows are created during import — match only, report unmatched
- ADD duplicate set detection: warn if `source_ref` already exists, require `--force` / `force: true` to re-import
- ADD 14 tests covering parser unit tests and import integration tests

## Details (DT)

### Design References
- Feature design: `tmp/mux/20260322-1302-rekordbox-playlist-import/consolidated/feature-design.md` (Phase 1 section)
- Sentinel review: `tmp/mux/20260322-1302-rekordbox-playlist-import/consolidated/sentinel-review.md`
- Phase manifest: `outputs/phases/20260325-rekordbox-playlist-import/manifest.yml`

### Sentinel Resolutions
- **BLOCKER-1**: Add `analysis_cache TEXT` column to `sets` table in the migration (for Phase 2 to store analysis JSON)
- **WARNING-1**: Use 0-based positions (matching `add_track_to_set` in `store.py`)
- **WARNING-2**: Add `inferred_energy FLOAT` + `inference_source VARCHAR` to `set_tracks` (for Phase 2 energy inference)
- **WARNING-3**: Use `POST /api/sets/import/m3u8` endpoint path — register BEFORE `/{set_id}` routes to avoid FastAPI routing conflict
- **NOTE-2**: Handle `#PLAYLIST` tag in parser for set name override (fallback to filename)
- **NOTE-4**: Use ±10 second duration proximity threshold for fuzzy filename matching

### M3U8 Parser Data Structures
```python
@dataclass
class M3U8Track:
    path: str              # Raw path from M3U8
    normalized_path: str   # After normalize_path() + NFC
    title: str | None      # From #EXTINF display title
    duration_sec: int      # From #EXTINF duration (-1 if unknown)
    line_number: int       # Source line for error reporting

@dataclass
class M3U8ParseResult:
    tracks: list[M3U8Track]
    playlist_name: str     # From #PLAYLIST tag or filename
    source_path: str       # Original file path
```

### Track Matching
```python
@dataclass
class TrackMatchResult:
    m3u8_track: M3U8Track
    matched_track: Track | None
    match_method: str  # "exact_path", "nocase_path", "fuzzy_filename", "unmatched"
```

Cascade: `normalize_path(m3u8_path)` → exact match on `tracks.file_path` → COLLATE NOCASE match → filename stem + duration ±10s fallback.

### Performance: Batch Matching (No N+1 Queries)
The importer MUST NOT issue one query per track. Instead:
1. **Load a path index once**: `SELECT id, file_path, title, artist, duration_sec FROM tracks` → build a `dict[str, Track]` keyed by normalized `file_path` (+ a lowercase variant for nocase fallback)
2. **Match in memory**: For each M3U8 track, look up the dict (O(1) per track)
3. **Fuzzy fallback**: Only for unmatched tracks after dict lookup — build a secondary `dict[str, list[Track]]` keyed by filename stem for fuzzy matching with ±10s duration check
4. **Result**: ~4,122 tracks loaded once, all matching is in-memory. Zero per-track DB queries.

### No Track Creation
The importer NEVER creates new Track rows. It only matches M3U8 entries to existing library tracks. Unmatched tracks are reported in the response — the DJ resolves them by syncing from Rekordbox or configuring path aliases.

### Duplicate Set Prevention
Before creating a new set, check if a set with the same `source_ref` (M3U8 filename) already exists:
- If found: return a warning with the existing set ID and ask the DJ to confirm re-import
- API adds `force: bool = False` parameter — if `true`, creates the set regardless
- CLI adds `--force` flag
- Frontend shows confirmation dialog: "You already imported 'Friday Night Set' on March 20. Import again?"

### Database Index on file_path
The migration MUST add an index on `tracks.file_path` for fast lookups:
```python
op.create_index('ix_tracks_file_path', 'tracks', ['file_path'])
```
This benefits both the import batch load and any future path-based queries.

### Schema Changes (sets table)
| Column | Type | Default | Purpose |
|--------|------|---------|---------|
| `source` | VARCHAR | NULL | "kiku", "manual", "m3u8", "rb_playlist" |
| `source_ref` | TEXT | NULL | Original M3U8 filename or playlist name |
| `is_analyzed` | INTEGER | 0 | Whether analysis has been run |
| `analysis_cache` | TEXT | NULL | JSON blob for cached analysis (Phase 2) |

### Schema Changes (set_tracks table)
| Column | Type | Default | Purpose |
|--------|------|---------|---------|
| `inferred_energy` | FLOAT | NULL | Position-inferred energy value (Phase 2) |
| `inference_source` | VARCHAR | NULL | How energy was inferred (Phase 2) |

### API Response
```json
{
  "set_id": 8,
  "name": "Friday Night Set",
  "source": "m3u8",
  "total_tracks": 22,
  "matched_count": 19,
  "unmatched_count": 3,
  "unmatched_paths": [
    {"path": "/Volumes/SSD/Musica/...", "title": "Artist - Title", "line": 14}
  ],
  "match_methods": {"exact_path": 17, "nocase_path": 1, "fuzzy_filename": 1}
}
```

### Error Handling
| Error | Response | UX |
|-------|----------|-----|
| Not M3U/M3U8 file | 400 | "This doesn't look like an M3U8 file -- check the file format" |
| No #EXTM3U header | Accept (graceful) | Warning in response |
| 0 tracks matched | 400 | "None of the tracks matched your library. Check path aliases." |
| Partial match | 200 + unmatched_paths | Yellow toast + unmatched list |
| All matched | 200 | Green toast + navigate to set |

### CLI Output (Kiku Voice)
```
Reading your session from "Friday Night Set.m3u8"...

  22 tracks found in the playlist
  19 matched to your library
   3 couldn't be found:
     /Volumes/SSD/Musica/Techno/Unknown/mystery_track.mp3
     ...

Created set "Friday Night Set" with 19 tracks.
Run `kiku analyze-set "Friday Night Set"` to see how your transitions scored.
```

### M3U8 Format Gotchas
- UTF-8 BOM: Open with `utf-8-sig` to auto-strip Windows BOM
- Unicode NFC/NFD: macOS uses NFD, normalize both sides with `unicodedata.normalize('NFC', ...)`
- Windows backslashes: Convert `\` → `/` before normalize_path()
- No percent-encoding: Rekordbox M3U8 uses literal characters (unlike XML which uses URI encoding)
- Line endings: Handle both `\r\n` and `\n`

### Existing Code to Reuse
- `src/kiku/db/paths.py` — `normalize_path()` with `PATH_ALIASES`
- `src/kiku/db/store.py` — `add_track_to_set()` (0-based positions)
- `src/kiku/db/models.py` — `Set`, `SetTrack`, `Track` models
- `src/kiku/api/routes/sets.py` — existing router pattern
- `alembic/versions/16f80a5c17e9_add_label_column_to_tracks.py` — migration pattern

### Testing
**Unit tests (parser)**:
- Parse valid Rekordbox M3U8 (macOS paths)
- Parse M3U8 with Windows BOM
- Parse M3U8 with Windows backslash paths
- Parse M3U8 with Unicode filenames (NFC/NFD)
- Parse M3U8 with empty lines and comments
- Parse malformed EXTINF (missing comma)

**Unit tests (matching)**:
- Track matching by exact path
- Track matching by case-insensitive path
- Track matching reports unmatched with line numbers

**Integration tests (API)**:
- Import creates set with correct source and track order
- Import preserves track order (0-based positions)
- Import handles 0 matches (400)
- Import handles partial matches (200 + unmatched)
- CLI import with --dry-run

### Frontend Component
`ImportPlaylistDialog.svelte` in `frontend/src/lib/components/set/`:
1. File drop zone (drag-and-drop or click-to-browse for .m3u8/.m3u)
2. Name field (pre-filled from filename, editable)
3. "Analyze after import" toggle (defaults to on)
4. Import button → POST /api/sets/import/m3u8
5. Result display: matched/unmatched counts + expandable unmatched list
6. Auto-navigate to new set on success

Import button added to Sets panel header (alongside "Build Set").

## Behavior

You are a senior engineer implementing Phase 1 of the Rekordbox Import feature for Kiku (聴く), a DJ craft mentorship tool. Follow the existing codebase patterns exactly — FastAPI routers with Pydantic schemas, SQLAlchemy ORM, Alembic migrations, Click CLI, Svelte 5 runes with TypeScript. All user-facing copy must follow Kiku voice: warm, direct, questions over verdicts, no forbidden words (smart, powerful, seamless, leverage, magic, synergy, next-level, game-changer). Read the feature design and sentinel review for complete context before implementing.

# AI Section
Critical: AI can ONLY modify this section.

## Research

### Codebase Findings

**Database models** (`src/kiku/db/models.py`):
- `Track`: `file_path` column has NO index, NO UNIQUE constraint. `rb_id` has UNIQUE.
- `Set`: id, name, created_at, duration_min, energy_profile, genre_filter. No source/provenance columns yet.
- `SetTrack`: composite PK (set_id, position). Has `transition_score` column.
- `add_track_to_set()` in `store.py:270` uses **0-based** positions (appends at `len(existing)`, clamps `max(0, ...)`).
- Test fixtures in `conftest.py` seed SetTrack with **1-based** positions (pos 1-5). Inconsistency confirmed.

**Path normalization** (`src/kiku/db/paths.py`):
- `normalize_path()`: simple prefix replacement `/Volumes/` → `/run/media/mantis/`. No NFC/NFD handling. No backslash conversion.
- M3U8 import needs to add NFC normalization + backslash→forwardslash BEFORE calling normalize_path().

**Sync pattern** (`src/kiku/db/sync.py`):
- Match cascade: `rb_id` first → `normalize_path(file_path)` exact → raw file_path exact. Two separate queries per track.
- Sync creates/updates Track rows. Import must NOT create — only match.
- `_parse_artist_from_title()` splits "Artist - Title" — useful for parsing EXTINF display titles if needed.

**Export M3U8** (`src/kiku/export/m3u8.py`):
- Writes `#EXTM3U` + `#EXTINF:<duration>,<Artist - Title>` + file_path. Uses `export_path()` for platform aliasing.
- `export_path()` reverses `normalize_path()` (Linux → macOS). Import needs the opposite direction.
- The export already outputs `# kiku:` metadata comments when `with_metadata=True`.

**API router** (`src/kiku/api/routes/sets.py`):
- Router: `APIRouter(prefix="/api/sets")`. Routes include `POST ""`, `POST /build`, `GET /{set_id}`, etc.
- `POST /api/sets/import/m3u8` must be registered BEFORE `/{set_id}` to avoid FastAPI matching "import" as a set_id.
- Pattern: all endpoints use `Depends(get_db)` for session injection.
- SSE pattern exists in `build_set_sse()` — useful reference for Phase 3 but not needed for Phase 1.

**Schemas** (`src/kiku/api/schemas.py`):
- Pydantic models: `SetResponse` (id, name, created_at, duration_min, track_count), `SetCreateRequest`, etc.
- New schemas needed: `ImportPlaylistRequest`, `ImportResultResponse`, `UnmatchedTrack`.
- `SetResponse` needs `source` field added.

**CLI** (`src/kiku/cli.py`):
- Click group at top-level `cli()`. Commands: sync, scan, search, build, export, serve, etc.
- `kiku import` will be a new `@cli.command()`. Pattern: click options → rich console output → session logic.
- `sync` has `--dry-run` and `--yes` pattern — reuse for import's `--dry-run` and `--force`.

**Frontend** (`frontend/src/lib/`):
- `api/sets.ts`: fetchJson wrapper, typed API functions. Add `importPlaylist()` here.
- `api/client.ts`: `fetchJson<T>(url, init)` + `API_BASE` constant.
- `components/set/SetView.svelte`: Main set view with SetPicker, SetTimeline, TransitionDetail, EnergyFlowChart.
- `components/set/BuildSetDialog.svelte`: Dialog pattern with overlay — reuse structure for ImportPlaylistDialog.
- `types/index.ts`: TypeScript interfaces for all API types.
- Svelte 5 runes: `$state`, `$derived`, `$effect` throughout.

**Tests** (`tests/`):
- `tests/api/conftest.py`: in-memory SQLite, seed 20 tracks + 1 set + tinder + hunt data. FastAPI TestClient with DI override.
- `tests/api/test_sets_api.py`: 11 tests for set CRUD, build SSE, track mutations. Pattern: `client.get/post/put/delete` + assert status + assert JSON.
- No existing M3U8/import tests. New test file: `tests/test_m3u8_parser.py` (unit) + `tests/api/test_import_api.py` (integration).

**Alembic** (`alembic/versions/`):
- 2 migrations: `455598dafd10` (initial) → `16f80a5c17e9` (add label). Pattern: `op.add_column`, `op.drop_column`.
- New migration chains from `16f80a5c17e9`.

### Key Decisions

1. **Position indexing**: Use 0-based (matching `add_track_to_set`). The conftest seeds 1-based but that's test data only — the actual code uses 0-based.
2. **Batch matching**: Load all tracks once as `{normalized_path: Track}` dict. No per-track DB queries.
3. **NFC normalization**: Apply `unicodedata.normalize('NFC', path)` in import parser before normalize_path(). Don't modify normalize_path() itself.
4. **Route registration**: Register `POST /api/sets/import/m3u8` BEFORE `/{set_id}` routes in sets.py router.
5. **File upload**: Use FastAPI `UploadFile` for multipart. Also accept JSON `file_path` for CLI backend calls.
6. **No track creation**: Import only matches. Unmatched tracks reported, never inserted.
7. **Duplicate set detection**: Query `Set.source_ref == filename` before creating. Return 409 if exists without `force=True`.

### Strategy

**Implementation order:**
1. Alembic migration (adds columns to sets + set_tracks + index on tracks.file_path)
2. M3U8 parser module (`src/kiku/import_playlist/m3u8.py`)
3. Track matching logic (in import module, batch approach)
4. Import API endpoint (in sets.py router)
5. Pydantic schemas (in schemas.py)
6. CLI command (in cli.py)
7. Frontend ImportPlaylistDialog + API client
8. Tests (parser unit + API integration)

**Testing strategy:**
- `tests/test_m3u8_parser.py`: 6 parser unit tests (BOM, backslash, NFC, empty lines, malformed EXTINF, #PLAYLIST tag)
- `tests/api/test_import_api.py`: 8 integration tests (full match, partial match, zero match, duplicate set, force re-import, dry-run via CLI, position ordering, source/source_ref validation)
- Reuse `conftest.py` fixture pattern: in-memory SQLite + TestClient. Seed tracks with known file_path values. Create fixture M3U8 content as strings (no file I/O needed — use UploadFile mock).

**Files to create:**
- `alembic/versions/xxx_add_import_columns.py`
- `src/kiku/import_playlist/__init__.py`
- `src/kiku/import_playlist/m3u8.py`
- `frontend/src/lib/components/set/ImportPlaylistDialog.svelte`
- `tests/test_m3u8_parser.py`
- `tests/api/test_import_api.py`

**Files to modify:**
- `src/kiku/db/models.py` (Set + SetTrack columns)
- `src/kiku/api/schemas.py` (new schemas + SetResponse.source)
- `src/kiku/api/routes/sets.py` (import endpoint, route ordering)
- `src/kiku/cli.py` (import command)
- `frontend/src/lib/api/sets.ts` (importPlaylist function)
- `frontend/src/lib/types/index.ts` (ImportResult type)
- `frontend/src/lib/components/set/SetView.svelte` (import button)

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
