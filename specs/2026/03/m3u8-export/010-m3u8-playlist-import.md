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

### Files

- `alembic/versions/xxxx_add_import_columns.py` (CREATE)
  - New migration: 4 columns on sets, 2 on set_tracks, index on tracks.file_path
- `src/kiku/db/models.py` (EDIT lines 122-133, 135-144)
  - Add source, source_ref, is_analyzed, analysis_cache to Set
  - Add inferred_energy, inference_source to SetTrack
- `src/kiku/import_playlist/__init__.py` (CREATE)
  - Empty package init
- `src/kiku/import_playlist/m3u8.py` (CREATE)
  - M3U8 parser: M3U8Track, M3U8ParseResult dataclasses, parse_m3u8()
- `src/kiku/import_playlist/service.py` (CREATE)
  - Import service: batch matching, TrackMatchResult, import_playlist()
- `src/kiku/api/schemas.py` (EDIT lines 80-87, add new schemas)
  - Add source to SetResponse; add UnmatchedTrack, ImportResultResponse
- `src/kiku/api/routes/sets.py` (EDIT lines 1-49, add import endpoint before /{set_id})
  - Add POST /import/m3u8 endpoint
- `src/kiku/cli.py` (EDIT after line 15, add import-playlist command)
  - Add `kiku import-playlist` CLI command
- `frontend/src/lib/types/index.ts` (EDIT lines 68-74, add import types)
  - Add source to DJSet, add ImportResult, UnmatchedTrack types
- `frontend/src/lib/api/sets.ts` (EDIT after line 211)
  - Add importPlaylist() function
- `frontend/src/lib/components/set/ImportPlaylistDialog.svelte` (CREATE)
  - File drop zone, name field, result display
- `frontend/src/lib/components/set/SetPicker.svelte` (EDIT lines 22-41)
  - Add import button
- `tests/test_m3u8_parser.py` (CREATE)
  - 6 parser unit tests
- `tests/api/test_import_api.py` (CREATE)
  - 8 integration tests

### Tasks

#### Task 1 — models.py: add import columns to Set and SetTrack
Tools: editor
Diff:
````diff
--- a/src/kiku/db/models.py
+++ b/src/kiku/db/models.py
@@
 class Set(Base):
     __tablename__ = "sets"

     id = Column(Integer, primary_key=True)
     name = Column(String)
     created_at = Column(String, default=lambda: datetime.now().isoformat())
     duration_min = Column(Integer)
     energy_profile = Column(Text)  # JSON
     genre_filter = Column(Text)  # JSON
+    source = Column(String)  # "kiku", "manual", "m3u8", "rb_playlist"
+    source_ref = Column(Text)  # Original filename or playlist name
+    is_analyzed = Column(Integer, default=0)  # Whether analysis has been run
+    analysis_cache = Column(Text)  # JSON blob for cached analysis (Phase 2)

     tracks = relationship("SetTrack", back_populates="set_", cascade="all, delete-orphan")
@@
 class SetTrack(Base):
     __tablename__ = "set_tracks"

     set_id = Column(Integer, ForeignKey("sets.id"), primary_key=True)
     position = Column(Integer, primary_key=True)
     track_id = Column(Integer, ForeignKey("tracks.id"))
     transition_score = Column(Float)
+    inferred_energy = Column(Float)  # Position-inferred energy (Phase 2)
+    inference_source = Column(String)  # How energy was inferred (Phase 2)

     set_ = relationship("Set", back_populates="tracks")
     track = relationship("Track")
````

Verification:
- `python -c "from kiku.db.models import Set, SetTrack; print(Set.__table__.columns.keys()); print(SetTrack.__table__.columns.keys())"` should list new columns.

#### Task 2 — Alembic migration: add import columns + file_path index
Tools: shell
Run: `source .venv/bin/activate && cd /home/mantis/Development/mantis-dev/waveform-builer && alembic revision --autogenerate -m "add import columns and file_path index"`
Then EDIT the generated migration to ensure it contains EXACTLY these operations (autogenerate may not detect the index — add manually if missing):

````diff
--- a/alembic/versions/xxxx_add_import_columns_and_file_path_index.py
+++ b/alembic/versions/xxxx_add_import_columns_and_file_path_index.py
@@
+"""add import columns and file_path index
+
+Revision ID: <auto>
+Revises: b57b41372f67
+Create Date: <auto>
+"""
+from typing import Sequence, Union
+
+from alembic import op
+import sqlalchemy as sa
+
+
+revision: str = '<auto>'
+down_revision: Union[str, None] = 'b57b41372f67'
+branch_labels: Union[str, Sequence[str], None] = None
+depends_on: Union[str, Sequence[str], None] = None
+
+
+def upgrade() -> None:
+    # Sets table: import provenance + analysis columns
+    op.add_column('sets', sa.Column('source', sa.String(), nullable=True))
+    op.add_column('sets', sa.Column('source_ref', sa.Text(), nullable=True))
+    op.add_column('sets', sa.Column('is_analyzed', sa.Integer(), server_default='0', nullable=True))
+    op.add_column('sets', sa.Column('analysis_cache', sa.Text(), nullable=True))
+
+    # SetTracks table: energy inference columns (Phase 2)
+    op.add_column('set_tracks', sa.Column('inferred_energy', sa.Float(), nullable=True))
+    op.add_column('set_tracks', sa.Column('inference_source', sa.String(), nullable=True))
+
+    # Index on tracks.file_path for fast import matching
+    op.create_index('ix_tracks_file_path', 'tracks', ['file_path'])
+
+
+def downgrade() -> None:
+    op.drop_index('ix_tracks_file_path', table_name='tracks')
+    op.drop_column('set_tracks', 'inference_source')
+    op.drop_column('set_tracks', 'inferred_energy')
+    op.drop_column('sets', 'analysis_cache')
+    op.drop_column('sets', 'is_analyzed')
+    op.drop_column('sets', 'source_ref')
+    op.drop_column('sets', 'source')
````

Verification:
- `source .venv/bin/activate && alembic upgrade head` succeeds without errors.
- `source .venv/bin/activate && python -c "from kiku.db.models import get_session; s=get_session(); s.execute(__import__('sqlalchemy').text('PRAGMA index_list(tracks)')).fetchall()"` should show ix_tracks_file_path.

#### Task 3 — M3U8 parser module
Tools: editor
Create file `src/kiku/import_playlist/__init__.py` with empty content.
Create file `src/kiku/import_playlist/m3u8.py`:

````diff
--- /dev/null
+++ b/src/kiku/import_playlist/m3u8.py
@@
+"""Parse Rekordbox M3U8 playlist exports.
+
+Handles UTF-8 BOM, NFC/NFD Unicode normalization, Windows backslashes,
+and the #PLAYLIST tag for set name override.
+"""
+
+from __future__ import annotations
+
+import unicodedata
+from dataclasses import dataclass, field
+from pathlib import Path
+
+from kiku.db.paths import normalize_path
+
+
+@dataclass
+class M3U8Track:
+    path: str  # Raw path from M3U8
+    normalized_path: str  # After normalize_path() + NFC
+    title: str | None  # From #EXTINF display title
+    duration_sec: int  # From #EXTINF duration (-1 if unknown)
+    line_number: int  # Source line for error reporting
+
+
+@dataclass
+class M3U8ParseResult:
+    tracks: list[M3U8Track] = field(default_factory=list)
+    playlist_name: str = ""  # From #PLAYLIST tag or filename
+    source_path: str = ""  # Original file path
+    warnings: list[str] = field(default_factory=list)
+
+
+def _normalize_m3u8_path(raw_path: str) -> str:
+    """NFC-normalize + backslash convert + normalize_path()."""
+    p = raw_path.strip()
+    p = p.replace("\\", "/")
+    p = unicodedata.normalize("NFC", p)
+    return normalize_path(p)
+
+
+def parse_m3u8(content: str, *, source_path: str = "") -> M3U8ParseResult:
+    """Parse M3U8 content string into tracks.
+
+    Parameters
+    ----------
+    content : str
+        Raw M3U8 file content (BOM should already be stripped by caller
+        using utf-8-sig encoding).
+    source_path : str
+        Original file path for error reporting and default set name.
+    """
+    result = M3U8ParseResult(source_path=source_path)
+
+    # Default name from filename (without extension)
+    if source_path:
+        result.playlist_name = Path(source_path).stem
+
+    lines = content.splitlines()
+
+    # Check for #EXTM3U header
+    has_header = False
+    if lines and lines[0].strip().startswith("#EXTM3U"):
+        has_header = True
+
+    if not has_header:
+        result.warnings.append("Missing #EXTM3U header — parsing anyway")
+
+    pending_extinf: tuple[int, str | None] | None = None  # (duration, title)
+    pending_line: int = 0
+
+    for line_num, raw_line in enumerate(lines, start=1):
+        line = raw_line.strip()
+
+        # Skip empty lines
+        if not line:
+            continue
+
+        # #PLAYLIST tag — set name override
+        if line.startswith("#PLAYLIST:"):
+            result.playlist_name = line[len("#PLAYLIST:"):].strip()
+            continue
+
+        # #EXTINF — parse duration and display title
+        if line.startswith("#EXTINF:"):
+            info = line[len("#EXTINF:"):]
+            comma_idx = info.find(",")
+            if comma_idx >= 0:
+                try:
+                    duration = int(info[:comma_idx].strip())
+                except ValueError:
+                    duration = -1
+                title = info[comma_idx + 1:].strip() or None
+            else:
+                # Malformed — try to parse just the number
+                try:
+                    duration = int(info.strip())
+                except ValueError:
+                    duration = -1
+                title = None
+                result.warnings.append(f"Line {line_num}: malformed #EXTINF (no comma)")
+            pending_extinf = (duration, title)
+            pending_line = line_num
+            continue
+
+        # Skip other comment/directive lines
+        if line.startswith("#"):
+            continue
+
+        # This is a file path line
+        raw_path = line
+        norm_path = _normalize_m3u8_path(raw_path)
+
+        duration = -1
+        title = None
+        ref_line = line_num
+
+        if pending_extinf is not None:
+            duration, title = pending_extinf
+            ref_line = pending_line
+            pending_extinf = None
+
+        result.tracks.append(M3U8Track(
+            path=raw_path,
+            normalized_path=norm_path,
+            title=title,
+            duration_sec=duration,
+            line_number=ref_line,
+        ))
+
+    return result
+
+
+def parse_m3u8_file(file_path: str) -> M3U8ParseResult:
+    """Read and parse an M3U8 file from disk."""
+    path = Path(file_path)
+    if not path.exists():
+        raise FileNotFoundError(f"File not found: {file_path}")
+    # utf-8-sig strips BOM automatically
+    content = path.read_text(encoding="utf-8-sig")
+    return parse_m3u8(content, source_path=str(path))
````

Verification:
- `python -c "from kiku.import_playlist.m3u8 import parse_m3u8; r = parse_m3u8('#EXTM3U\n#EXTINF:300,Artist - Title\n/path/to/file.mp3\n'); print(len(r.tracks), r.tracks[0].normalized_path)"` prints `1 /path/to/file.mp3`.

#### Task 4 — Import service with batch matching
Tools: editor
Create file `src/kiku/import_playlist/service.py`:

````diff
--- /dev/null
+++ b/src/kiku/import_playlist/service.py
@@
+"""Import M3U8 playlists into Kiku sets with batch track matching."""
+
+from __future__ import annotations
+
+import unicodedata
+from dataclasses import dataclass
+from pathlib import PurePosixPath
+
+from sqlalchemy.orm import Session
+
+from kiku.db.models import Set, SetTrack, Track
+from kiku.db.paths import normalize_path
+from kiku.import_playlist.m3u8 import M3U8ParseResult, M3U8Track
+
+
+@dataclass
+class TrackMatchResult:
+    m3u8_track: M3U8Track
+    matched_track: Track | None
+    match_method: str  # "exact_path", "nocase_path", "fuzzy_filename", "unmatched"
+
+
+@dataclass
+class ImportResult:
+    set_id: int
+    name: str
+    source: str
+    total_tracks: int
+    matched_count: int
+    unmatched_count: int
+    unmatched: list[dict]  # [{path, title, line}]
+    match_methods: dict[str, int]
+    warnings: list[str]
+    duplicate_set_id: int | None = None  # Set if source_ref already exists
+
+
+def _build_path_index(
+    session: Session,
+) -> tuple[dict[str, Track], dict[str, Track], dict[str, list[Track]]]:
+    """Load all tracks and build in-memory lookup dicts.
+
+    Returns
+    -------
+    exact_index : dict mapping normalized file_path → Track
+    nocase_index : dict mapping lowercased normalized file_path → Track
+    stem_index : dict mapping lowercased filename stem → [Track, ...]
+    """
+    all_tracks = session.query(Track).filter(Track.file_path.isnot(None)).all()
+
+    exact_index: dict[str, Track] = {}
+    nocase_index: dict[str, Track] = {}
+    stem_index: dict[str, list[Track]] = {}
+
+    for t in all_tracks:
+        norm = normalize_path(t.file_path)
+        norm_nfc = unicodedata.normalize("NFC", norm)
+        exact_index[norm_nfc] = t
+        nocase_index[norm_nfc.lower()] = t
+
+        stem = PurePosixPath(norm_nfc).stem.lower()
+        stem_index.setdefault(stem, []).append(t)
+
+    return exact_index, nocase_index, stem_index
+
+
+def match_tracks(
+    parse_result: M3U8ParseResult,
+    session: Session,
+) -> list[TrackMatchResult]:
+    """Match parsed M3U8 tracks to library using batch approach.
+
+    Cascade: exact normalized path → case-insensitive → fuzzy filename ±10s.
+    """
+    exact_idx, nocase_idx, stem_idx = _build_path_index(session)
+    results: list[TrackMatchResult] = []
+
+    for mt in parse_result.tracks:
+        # Level 1: exact normalized path
+        track = exact_idx.get(mt.normalized_path)
+        if track:
+            results.append(TrackMatchResult(mt, track, "exact_path"))
+            continue
+
+        # Level 2: case-insensitive
+        track = nocase_idx.get(mt.normalized_path.lower())
+        if track:
+            results.append(TrackMatchResult(mt, track, "nocase_path"))
+            continue
+
+        # Level 3: fuzzy filename + duration ±10s
+        stem = PurePosixPath(mt.normalized_path).stem.lower()
+        candidates = stem_idx.get(stem, [])
+        matched = None
+        if candidates and mt.duration_sec > 0:
+            for cand in candidates:
+                if cand.duration_sec and abs(cand.duration_sec - mt.duration_sec) <= 10:
+                    matched = cand
+                    break
+        elif candidates:
+            # No duration info — take first stem match
+            matched = candidates[0]
+
+        if matched:
+            results.append(TrackMatchResult(mt, matched, "fuzzy_filename"))
+        else:
+            results.append(TrackMatchResult(mt, None, "unmatched"))
+
+    return results
+
+
+def import_playlist(
+    session: Session,
+    parse_result: M3U8ParseResult,
+    *,
+    name: str | None = None,
+    force: bool = False,
+) -> ImportResult:
+    """Import parsed M3U8 into a new set.
+
+    Parameters
+    ----------
+    session : Session
+        SQLAlchemy session.
+    parse_result : M3U8ParseResult
+        Parsed M3U8 data.
+    name : str, optional
+        Set name override (defaults to playlist_name from parse result).
+    force : bool
+        If True, create set even if source_ref already exists.
+    """
+    set_name = name or parse_result.playlist_name or "Imported Set"
+    source_ref = parse_result.source_path or set_name
+
+    # Check for duplicate set
+    existing = session.query(Set).filter(Set.source_ref == source_ref).first()
+    if existing and not force:
+        return ImportResult(
+            set_id=existing.id,
+            name=existing.name or "",
+            source="m3u8",
+            total_tracks=len(parse_result.tracks),
+            matched_count=0,
+            unmatched_count=0,
+            unmatched=[],
+            match_methods={},
+            warnings=[],
+            duplicate_set_id=existing.id,
+        )
+
+    # Match tracks
+    matches = match_tracks(parse_result, session)
+
+    matched = [m for m in matches if m.matched_track is not None]
+    unmatched = [m for m in matches if m.matched_track is None]
+
+    if not matched:
+        return ImportResult(
+            set_id=0,
+            name=set_name,
+            source="m3u8",
+            total_tracks=len(parse_result.tracks),
+            matched_count=0,
+            unmatched_count=len(unmatched),
+            unmatched=[
+                {"path": m.m3u8_track.path, "title": m.m3u8_track.title, "line": m.m3u8_track.line_number}
+                for m in unmatched
+            ],
+            match_methods={},
+            warnings=parse_result.warnings,
+        )
+
+    # Compute total duration from matched tracks
+    total_dur_sec = sum(
+        m.matched_track.duration_sec for m in matched
+        if m.matched_track and m.matched_track.duration_sec
+    )
+    duration_min = int(total_dur_sec / 60) if total_dur_sec else None
+
+    # Create set
+    new_set = Set(
+        name=set_name,
+        duration_min=duration_min,
+        source="m3u8",
+        source_ref=source_ref,
+    )
+    session.add(new_set)
+    session.flush()  # Get the ID
+
+    # Add tracks at 0-based positions
+    for position, m in enumerate(matched):
+        session.add(SetTrack(
+            set_id=new_set.id,
+            position=position,
+            track_id=m.matched_track.id,
+        ))
+
+    session.commit()
+
+    # Count match methods
+    method_counts: dict[str, int] = {}
+    for m in matched:
+        method_counts[m.match_method] = method_counts.get(m.match_method, 0) + 1
+
+    return ImportResult(
+        set_id=new_set.id,
+        name=set_name,
+        source="m3u8",
+        total_tracks=len(parse_result.tracks),
+        matched_count=len(matched),
+        unmatched_count=len(unmatched),
+        unmatched=[
+            {"path": m.m3u8_track.path, "title": m.m3u8_track.title, "line": m.m3u8_track.line_number}
+            for m in unmatched
+        ],
+        match_methods=method_counts,
+        warnings=parse_result.warnings,
+    )
````

Verification:
- `python -c "from kiku.import_playlist.service import match_tracks, import_playlist; print('OK')"` succeeds.

#### Task 5 — Pydantic schemas: add import models + source on SetResponse
Tools: editor
Diff:
````diff
--- a/src/kiku/api/schemas.py
+++ b/src/kiku/api/schemas.py
@@
 class SetResponse(BaseModel):
     id: int
     name: str | None = None
     created_at: str | None = None
     duration_min: int | None = None
     track_count: int = 0
+    source: str | None = None

     model_config = {"from_attributes": True}
@@
 class ReplaceTrackRequest(BaseModel):
     new_track_id: int
+
+
+# ── Import playlist models ──
+
+
+class UnmatchedTrack(BaseModel):
+    path: str
+    title: str | None = None
+    line: int
+
+
+class ImportResultResponse(BaseModel):
+    set_id: int
+    name: str
+    source: str
+    total_tracks: int
+    matched_count: int
+    unmatched_count: int
+    unmatched_paths: list[UnmatchedTrack] = []
+    match_methods: dict[str, int] = {}
+    warnings: list[str] = []
+    duplicate_set_id: int | None = None
````

Verification:
- `python -c "from kiku.api.schemas import ImportResultResponse, UnmatchedTrack, SetResponse; print(SetResponse.model_fields.keys())"` includes 'source'.

#### Task 6 — API endpoint: POST /api/sets/import/m3u8
Tools: editor
This endpoint MUST be registered BEFORE any `/{set_id}` routes to avoid FastAPI matching "import" as a set_id parameter.

Diff (add import at top of file and endpoint AFTER the `/build` route but BEFORE the `POST ""` create route):
````diff
--- a/src/kiku/api/routes/sets.py
+++ b/src/kiku/api/routes/sets.py
@@
 from fastapi import APIRouter, Depends, HTTPException, Response
+from fastapi import UploadFile, File, Form
 from fastapi.responses import StreamingResponse
@@
 from kiku.api.schemas import (
     CueCreateRequest,
     CueResponse,
+    ImportResultResponse,
     ReplaceTrackRequest,
@@
     SetResponse,
@@
     TransitionScoreBreakdown,
+    UnmatchedTrack,
 )
@@
 router = APIRouter(prefix="/api/sets", tags=["sets"])
@@
+@router.post("/import/m3u8", response_model=ImportResultResponse)
+async def import_m3u8_playlist(
+    file: UploadFile | None = File(None),
+    file_path: str | None = Form(None),
+    name: str | None = Form(None),
+    force: bool = Form(False),
+    db: Session = Depends(get_db),
+):
+    """Import a Rekordbox M3U8 playlist as a new set.
+
+    Accepts either a file upload (multipart) or a file_path (form field).
+    Matches tracks to the library — never creates new track rows.
+    """
+    from kiku.import_playlist.m3u8 import parse_m3u8
+    from kiku.import_playlist.service import import_playlist
+
+    # Get content from upload or file path
+    if file is not None:
+        raw = await file.read()
+        # Handle BOM
+        content = raw.decode("utf-8-sig")
+        source_path = file.filename or "upload.m3u8"
+    elif file_path:
+        from pathlib import Path
+        p = Path(file_path)
+        if not p.exists():
+            raise HTTPException(status_code=400, detail=f"File not found: {file_path}")
+        content = p.read_text(encoding="utf-8-sig")
+        source_path = file_path
+    else:
+        raise HTTPException(status_code=400, detail="Provide a file upload or file_path")
+
+    # Validate it looks like M3U8
+    if not content.strip().startswith("#EXTM3U") and not any(
+        line.strip().startswith("#EXTINF:") for line in content.splitlines()[:20]
+    ):
+        raise HTTPException(
+            status_code=400,
+            detail="This doesn't look like an M3U8 file — check the file format",
+        )
+
+    parse_result = parse_m3u8(content, source_path=source_path)
+
+    if not parse_result.tracks:
+        raise HTTPException(status_code=400, detail="No tracks found in the playlist file")
+
+    result = import_playlist(db, parse_result, name=name, force=force)
+
+    # Duplicate set detected (not forced)
+    if result.duplicate_set_id is not None:
+        return ImportResultResponse(
+            set_id=result.duplicate_set_id,
+            name=result.name,
+            source=result.source,
+            total_tracks=result.total_tracks,
+            matched_count=0,
+            unmatched_count=0,
+            unmatched_paths=[],
+            match_methods={},
+            warnings=[f"Already imported as set {result.duplicate_set_id}. Use force=true to re-import."],
+            duplicate_set_id=result.duplicate_set_id,
+        )
+
+    # Zero matches
+    if result.matched_count == 0:
+        raise HTTPException(
+            status_code=400,
+            detail="None of the tracks matched your library. Check path aliases or sync from Rekordbox first.",
+        )
+
+    return ImportResultResponse(
+        set_id=result.set_id,
+        name=result.name,
+        source=result.source,
+        total_tracks=result.total_tracks,
+        matched_count=result.matched_count,
+        unmatched_count=result.unmatched_count,
+        unmatched_paths=[UnmatchedTrack(**u) for u in result.unmatched],
+        match_methods=result.match_methods,
+        warnings=result.warnings,
+    )
+
+
 @router.post("/build")
 def build_set_sse(body: SetBuildRequest, db: Session = Depends(get_db)):
````

Also update every `SetResponse(...)` construction in the file to include `source=s.source` (or `source=set_.source`). There are 3 locations:

In `create_set`:
````diff
@@
     return SetResponse(
         id=set_.id,
         name=set_.name,
         created_at=set_.created_at,
         duration_min=set_.duration_min,
         track_count=0,
+        source=set_.source,
     )
````

In `update_set`:
````diff
@@
     return SetResponse(
         id=set_.id,
         name=set_.name,
         created_at=set_.created_at,
         duration_min=set_.duration_min,
         track_count=len(set_.tracks),
+        source=set_.source,
     )
````

In `list_sets`:
````diff
@@
     return [
         SetResponse(
             id=s.id,
             name=s.name,
             created_at=s.created_at,
             duration_min=s.duration_min,
             track_count=len(s.tracks),
+            source=s.source,
         )
         for s in sets
     ]
````

Verification:
- `source .venv/bin/activate && python -c "from kiku.api.routes.sets import router; routes = [r.path for r in router.routes]; print(routes)"` should show `/import/m3u8` before `/{set_id}`.

#### Task 7 — CLI command: kiku import-playlist
Tools: editor
Add after the `export` command in `src/kiku/cli.py` (after line 547):

````diff
--- a/src/kiku/cli.py
+++ b/src/kiku/cli.py
@@
 @cli.command()
+@click.argument("file", type=click.Path(exists=True))
+@click.option("--name", default=None, help="Set name (defaults to filename)")
+@click.option("--dry-run", is_flag=True, help="Show match report without creating a set")
+@click.option("--force", is_flag=True, help="Re-import even if this file was already imported")
+def import_playlist(file: str, name: str | None, dry_run: bool, force: bool):
+    """Import a Rekordbox M3U8 playlist as a set.
+
+    Matches playlist tracks to your library — no new tracks are created.
+    Unmatched tracks are listed so you can sync them from Rekordbox.
+    """
+    from kiku.db.models import get_session
+    from kiku.import_playlist.m3u8 import parse_m3u8_file
+    from kiku.import_playlist.service import import_playlist as do_import
+
+    console.print(f'\nReading your session from "{file}"...\n')
+
+    try:
+        parse_result = parse_m3u8_file(file)
+    except Exception as e:
+        console.print(f"[red]Couldn't read the playlist:[/] {e}")
+        return
+
+    if not parse_result.tracks:
+        console.print("[yellow]No tracks found in this file.[/]")
+        return
+
+    for w in parse_result.warnings:
+        console.print(f"  [yellow]{w}[/]")
+
+    if dry_run:
+        session = get_session()
+        from kiku.import_playlist.service import match_tracks
+
+        matches = match_tracks(parse_result, session)
+        matched = [m for m in matches if m.matched_track is not None]
+        unmatched = [m for m in matches if m.matched_track is None]
+
+        console.print(f"  {len(parse_result.tracks)} tracks found in the playlist")
+        console.print(f"  [green]{len(matched)}[/] matched to your library")
+
+        if unmatched:
+            console.print(f"  [yellow]{len(unmatched)}[/] couldn't be found:")
+            for m in unmatched:
+                console.print(f"    {m.m3u8_track.path}")
+
+        # Count methods
+        methods: dict[str, int] = {}
+        for m in matched:
+            methods[m.match_method] = methods.get(m.match_method, 0) + 1
+        if methods:
+            console.print(f"\n  Match methods: {methods}")
+
+        console.print("\n[dim]Dry run — no set created. Remove --dry-run to import.[/]")
+        session.close()
+        return
+
+    session = get_session()
+    result = do_import(session, parse_result, name=name, force=force)
+
+    if result.duplicate_set_id is not None:
+        console.print(
+            f"[yellow]This file was already imported as set #{result.duplicate_set_id} "
+            f'("{result.name}"). Use --force to import again.[/]'
+        )
+        session.close()
+        return
+
+    if result.matched_count == 0:
+        console.print(
+            "[yellow]None of the tracks matched your library.[/]\n"
+            "  Check your path aliases or run [cyan]kiku sync[/] first."
+        )
+        session.close()
+        return
+
+    console.print(f"  {result.total_tracks} tracks found in the playlist")
+    console.print(f"  [green]{result.matched_count}[/] matched to your library")
+
+    if result.unmatched_count > 0:
+        console.print(f"  [yellow]{result.unmatched_count}[/] couldn't be found:")
+        for u in result.unmatched[:5]:
+            console.print(f"    {u['path']}")
+        if result.unmatched_count > 5:
+            console.print(f"    ... and {result.unmatched_count - 5} more")
+
+    console.print(f'\n[green]Created set "{result.name}" with {result.matched_count} tracks.[/]')
+    session.close()
+
+
 @cli.command()
 @click.option("--port", default=8000, help="HTTP port for the API server")
````

The command is named `import-playlist` (with hyphen) to avoid shadowing Python's `import` keyword.

Verification:
- `source .venv/bin/activate && kiku import-playlist --help` shows usage.

#### Task 8 — Frontend TypeScript types
Tools: editor
Diff:
````diff
--- a/frontend/src/lib/types/index.ts
+++ b/frontend/src/lib/types/index.ts
@@
 export interface DJSet {
 	id: number;
 	name: string | null;
 	created_at: string | null;
 	duration_min: number | null;
 	track_count: number;
+	source: string | null;
 }
@@
 export interface ReplacementSuggestionsResponse {
 	context: ReplacementContext;
 	candidates: ReplacementCandidate[];
 }
+
+// ── Import playlist types ──
+
+export interface UnmatchedTrack {
+	path: string;
+	title: string | null;
+	line: number;
+}
+
+export interface ImportResult {
+	set_id: number;
+	name: string;
+	source: string;
+	total_tracks: number;
+	matched_count: number;
+	unmatched_count: number;
+	unmatched_paths: UnmatchedTrack[];
+	match_methods: Record<string, number>;
+	warnings: string[];
+	duplicate_set_id: number | null;
+}
````

Verification:
- `cd frontend && npx svelte-check --tsconfig ./tsconfig.json 2>&1 | head -20` — no errors related to import types.

#### Task 9 — Frontend API client: importPlaylist()
Tools: editor
Diff:
````diff
--- a/frontend/src/lib/api/sets.ts
+++ b/frontend/src/lib/api/sets.ts
@@
 import type {
 	Cue,
 	DJSet,
+	ImportResult,
 	ReplacementSuggestionsResponse,
@@
 } from '$lib/types';
@@
 export async function exportM3U8(setId: number): Promise<Blob> {
 	const res = await fetch(`${API_BASE}/api/sets/${setId}/export/m3u8`, { method: 'POST' });
 	if (!res.ok) {
 		const text = await res.text().catch(() => 'Export failed');
 		throw new Error(text);
 	}
 	return res.blob();
 }
+
+export async function importPlaylist(
+	file: File,
+	options?: { name?: string; force?: boolean }
+): Promise<ImportResult> {
+	const formData = new FormData();
+	formData.append('file', file);
+	if (options?.name) formData.append('name', options.name);
+	if (options?.force) formData.append('force', 'true');
+	const res = await fetch(`${API_BASE}/api/sets/import/m3u8`, {
+		method: 'POST',
+		body: formData,
+	});
+	if (!res.ok) {
+		const text = await res.text().catch(() => 'Import failed');
+		let detail = text;
+		try {
+			const json = JSON.parse(text);
+			detail = json.detail || text;
+		} catch {
+			// Use raw text
+		}
+		throw new Error(detail);
+	}
+	return res.json();
+}
````

Verification:
- `cd frontend && npx svelte-check --tsconfig ./tsconfig.json 2>&1 | head -20` — no errors.

#### Task 10 — Frontend ImportPlaylistDialog.svelte
Tools: editor
Create file `frontend/src/lib/components/set/ImportPlaylistDialog.svelte`:

````diff
--- /dev/null
+++ b/frontend/src/lib/components/set/ImportPlaylistDialog.svelte
@@
+<script lang="ts">
+	import type { ImportResult } from '$lib/types';
+	import { importPlaylist } from '$lib/api/sets';
+
+	let {
+		open = $bindable(false),
+		onimported,
+	}: {
+		open: boolean;
+		onimported?: (result: ImportResult) => void;
+	} = $props();
+
+	let file = $state<File | null>(null);
+	let name = $state('');
+	let importing = $state(false);
+	let result = $state<ImportResult | null>(null);
+	let error = $state<string | null>(null);
+	let dragOver = $state(false);
+
+	function handleFile(f: File) {
+		if (!f.name.match(/\.m3u8?$/i)) {
+			error = "Pick an .m3u8 file";
+			return;
+		}
+		file = f;
+		error = null;
+		result = null;
+		// Pre-fill name from filename
+		if (!name) {
+			name = f.name.replace(/\.m3u8?$/i, '');
+		}
+	}
+
+	function handleDrop(e: DragEvent) {
+		e.preventDefault();
+		dragOver = false;
+		const f = e.dataTransfer?.files?.[0];
+		if (f) handleFile(f);
+	}
+
+	function handleInputChange(e: Event) {
+		const input = e.target as HTMLInputElement;
+		const f = input.files?.[0];
+		if (f) handleFile(f);
+	}
+
+	async function doImport(force = false) {
+		if (!file || importing) return;
+		importing = true;
+		error = null;
+		result = null;
+		try {
+			const r = await importPlaylist(file, { name: name || undefined, force });
+			result = r;
+			if (r.matched_count > 0 && !r.duplicate_set_id) {
+				onimported?.(r);
+			}
+		} catch (e) {
+			error = e instanceof Error ? e.message : 'Import failed';
+		} finally {
+			importing = false;
+		}
+	}
+
+	function close() {
+		open = false;
+		file = null;
+		name = '';
+		result = null;
+		error = null;
+	}
+</script>
+
+{#if open}
+<!-- svelte-ignore a11y_click_events_have_key_events -->
+<!-- svelte-ignore a11y_no_static_element_interactions -->
+<div class="overlay" onclick={close}>
+	<div class="dialog" onclick={(e) => e.stopPropagation()}>
+		<h3>Import Playlist</h3>
+
+		<!-- Drop zone -->
+		<div
+			class="drop-zone"
+			class:drag-over={dragOver}
+			ondragover={(e) => { e.preventDefault(); dragOver = true; }}
+			ondragleave={() => { dragOver = false; }}
+			ondrop={handleDrop}
+		>
+			{#if file}
+				<span class="file-name">{file.name}</span>
+			{:else}
+				<span class="drop-text">Drop an .m3u8 file here</span>
+				<span class="drop-sub">or click to browse</span>
+			{/if}
+			<input type="file" accept=".m3u8,.m3u" onchange={handleInputChange} />
+		</div>
+
+		<!-- Name field -->
+		<label class="name-field">
+			<span>Set name</span>
+			<input type="text" bind:value={name} placeholder="From filename" />
+		</label>
+
+		<!-- Action buttons -->
+		<div class="actions">
+			<button class="cancel-btn" onclick={close}>Cancel</button>
+			<button class="import-btn" onclick={() => doImport()} disabled={!file || importing}>
+				{importing ? 'Importing...' : 'Import'}
+			</button>
+		</div>
+
+		<!-- Error -->
+		{#if error}
+			<div class="error-msg">{error}</div>
+		{/if}
+
+		<!-- Result -->
+		{#if result}
+			{#if result.duplicate_set_id}
+				<div class="result warning">
+					<p>Already imported as "{result.name}". Import again?</p>
+					<button class="force-btn" onclick={() => doImport(true)}>Yes, re-import</button>
+				</div>
+			{:else}
+				<div class="result success">
+					<p>
+						<strong>{result.matched_count}</strong> of {result.total_tracks} tracks matched
+					</p>
+					{#if result.unmatched_count > 0}
+						<details>
+							<summary>{result.unmatched_count} unmatched</summary>
+							<ul class="unmatched-list">
+								{#each result.unmatched_paths as u}
+									<li>{u.title || u.path}</li>
+								{/each}
+							</ul>
+						</details>
+					{/if}
+				</div>
+			{/if}
+		{/if}
+	</div>
+</div>
+{/if}
+
+<style>
+	.overlay {
+		position: fixed;
+		inset: 0;
+		background: rgba(0, 0, 0, 0.6);
+		display: flex;
+		align-items: center;
+		justify-content: center;
+		z-index: 100;
+	}
+
+	.dialog {
+		background: var(--bg-secondary);
+		border: 1px solid var(--border);
+		border-radius: 8px;
+		padding: 20px;
+		width: 440px;
+		max-width: 90vw;
+	}
+
+	h3 {
+		margin: 0 0 16px;
+		font-size: 16px;
+	}
+
+	.drop-zone {
+		border: 2px dashed var(--border);
+		border-radius: 6px;
+		padding: 24px;
+		text-align: center;
+		position: relative;
+		cursor: pointer;
+		transition: border-color 0.15s;
+	}
+
+	.drop-zone.drag-over {
+		border-color: var(--accent);
+	}
+
+	.drop-zone input[type='file'] {
+		position: absolute;
+		inset: 0;
+		opacity: 0;
+		cursor: pointer;
+	}
+
+	.file-name {
+		font-weight: 600;
+		color: var(--accent);
+	}
+
+	.drop-text {
+		display: block;
+		font-size: 13px;
+		color: var(--text-secondary);
+	}
+
+	.drop-sub {
+		display: block;
+		font-size: 11px;
+		color: var(--text-dim);
+		margin-top: 4px;
+	}
+
+	.name-field {
+		display: block;
+		margin-top: 12px;
+	}
+
+	.name-field span {
+		font-size: 12px;
+		color: var(--text-secondary);
+		display: block;
+		margin-bottom: 4px;
+	}
+
+	.name-field input {
+		width: 100%;
+		padding: 6px 8px;
+		font-size: 13px;
+		background: var(--bg-tertiary);
+		border: 1px solid var(--border);
+		border-radius: 4px;
+		color: var(--text-primary);
+	}
+
+	.actions {
+		display: flex;
+		gap: 8px;
+		justify-content: flex-end;
+		margin-top: 16px;
+	}
+
+	.cancel-btn {
+		padding: 6px 16px;
+		font-size: 13px;
+		background: var(--bg-tertiary);
+		border: 1px solid var(--border);
+		border-radius: 4px;
+		color: var(--text-primary);
+	}
+
+	.import-btn {
+		padding: 6px 16px;
+		font-size: 13px;
+		font-weight: 600;
+		background: var(--accent);
+		border: 1px solid var(--accent);
+		border-radius: 4px;
+		color: #000;
+	}
+
+	.import-btn:disabled {
+		opacity: 0.4;
+		cursor: default;
+	}
+
+	.error-msg {
+		margin-top: 12px;
+		padding: 8px;
+		font-size: 12px;
+		color: var(--energy-high);
+		background: rgba(255, 80, 80, 0.1);
+		border-radius: 4px;
+	}
+
+	.result {
+		margin-top: 12px;
+		padding: 10px;
+		border-radius: 4px;
+		font-size: 13px;
+	}
+
+	.result.success {
+		background: rgba(80, 200, 120, 0.1);
+	}
+
+	.result.warning {
+		background: rgba(255, 200, 50, 0.1);
+	}
+
+	.result p {
+		margin: 0;
+	}
+
+	.force-btn {
+		margin-top: 8px;
+		padding: 4px 12px;
+		font-size: 12px;
+		background: var(--accent);
+		color: #000;
+		border: 1px solid var(--accent);
+		border-radius: 4px;
+	}
+
+	details {
+		margin-top: 8px;
+	}
+
+	summary {
+		cursor: pointer;
+		font-size: 12px;
+		color: var(--text-secondary);
+	}
+
+	.unmatched-list {
+		margin: 4px 0 0;
+		padding-left: 20px;
+		font-size: 11px;
+		color: var(--text-dim);
+		max-height: 120px;
+		overflow-y: auto;
+	}
+
+	.unmatched-list li {
+		margin: 2px 0;
+	}
+</style>
````

Verification:
- `cd frontend && npx svelte-check --tsconfig ./tsconfig.json 2>&1 | grep -i error | head -5` — no errors.

#### Task 11 — SetPicker.svelte: add Import button
Tools: editor
Diff:
````diff
--- a/frontend/src/lib/components/set/SetPicker.svelte
+++ b/frontend/src/lib/components/set/SetPicker.svelte
@@
 <script lang="ts">
 	import type { DJSet } from '$lib/types';
 	import { listSets } from '$lib/api/sets';
 	import { onMount } from 'svelte';
+	import ImportPlaylistDialog from './ImportPlaylistDialog.svelte';

-	let { onselect }: { onselect: (set: DJSet) => void } = $props();
+	let { onselect }: { onselect: (set: DJSet) => void } = $props();

 	let sets = $state<DJSet[]>([]);
 	let loading = $state(true);
+	let showImport = $state(false);

 	onMount(async () => {
 		try {
 			sets = await listSets();
@@
 </script>

 <div class="set-picker">
 	{#if loading}
 		<span class="dim">Finding your sets...</span>
 	{:else if sets.length === 0}
 		<span class="dim">No sets yet — run <code>kiku build</code> to create your first journey</span>
+		<button class="import-btn" onclick={() => { showImport = true; }}>Import</button>
 	{:else}
-		<select onchange={(e) => {
+		<div class="picker-row">
+		<select class="set-select" onchange={(e) => {
 			const id = Number((e.target as HTMLSelectElement).value);
 			const s = sets.find(s => s.id === id);
 			if (s) onselect(s);
 		}}>
 			<option value="">Choose a set...</option>
 			{#each sets as s (s.id)}
 				<option value={s.id}>
 					{s.name} ({s.track_count} tracks, {s.duration_min}min)
 				</option>
 			{/each}
 		</select>
+		<button class="import-btn" onclick={() => { showImport = true; }}>Import</button>
+		</div>
 	{/if}
 </div>

+<ImportPlaylistDialog
+	bind:open={showImport}
+	onimported={async (result) => {
+		showImport = false;
+		sets = await listSets();
+		const newSet = sets.find(s => s.id === result.set_id);
+		if (newSet) onselect(newSet);
+	}}
+/>
+
 <style>
@@
+	.picker-row {
+		display: flex;
+		gap: 8px;
+		align-items: center;
+	}
+
+	.set-select {
+		flex: 1;
+	}
+
 	select {
-		width: 100%;
 		padding: 8px 10px;
 		font-size: 13px;
 	}
+
+	.import-btn {
+		padding: 6px 12px;
+		font-size: 12px;
+		font-weight: 600;
+		background: var(--bg-tertiary);
+		border: 1px solid var(--border);
+		border-radius: 4px;
+		color: var(--text-primary);
+		white-space: nowrap;
+		transition: all 0.15s;
+	}
+
+	.import-btn:hover {
+		background: var(--accent);
+		color: #000;
+		border-color: var(--accent);
+	}
@@
 </style>
````

Verification:
- `cd frontend && npx svelte-check --tsconfig ./tsconfig.json 2>&1 | grep -i error | head -5` — no errors.

#### Task 12 — Unit tests: M3U8 parser
Tools: editor
Create file `tests/test_m3u8_parser.py`:

````diff
--- /dev/null
+++ b/tests/test_m3u8_parser.py
@@
+"""Unit tests for the M3U8 playlist parser."""
+
+from kiku.import_playlist.m3u8 import parse_m3u8
+
+
+def test_parse_valid_rekordbox_m3u8():
+    content = (
+        "#EXTM3U\n"
+        "#EXTINF:300,Artist One - Track Alpha\n"
+        "/Volumes/SSD/Musica/Techno/artist_one_track_alpha.mp3\n"
+        "#EXTINF:240,Artist Two - Track Beta\n"
+        "/Volumes/SSD/Musica/House/artist_two_track_beta.mp3\n"
+    )
+    result = parse_m3u8(content, source_path="test.m3u8")
+    assert len(result.tracks) == 2
+    assert result.tracks[0].title == "Artist One - Track Alpha"
+    assert result.tracks[0].duration_sec == 300
+    assert result.tracks[1].duration_sec == 240
+    assert result.playlist_name == "test"
+    assert not result.warnings
+
+
+def test_parse_m3u8_with_bom():
+    """BOM is handled by utf-8-sig, but if content starts with BOM char, strip it."""
+    bom = "\ufeff"
+    content = bom + "#EXTM3U\n#EXTINF:180,Test - Track\n/path/to/file.mp3\n"
+    result = parse_m3u8(content)
+    assert len(result.tracks) == 1
+
+
+def test_parse_m3u8_with_backslash_paths():
+    content = (
+        "#EXTM3U\n"
+        "#EXTINF:200,Artist - Title\n"
+        "C:\\Music\\Techno\\track.mp3\n"
+    )
+    result = parse_m3u8(content)
+    assert len(result.tracks) == 1
+    assert "\\" not in result.tracks[0].normalized_path
+    assert "C:/Music/Techno/track.mp3" == result.tracks[0].normalized_path
+
+
+def test_parse_m3u8_with_unicode_nfc():
+    """NFD 'ü' (u + combining diaeresis) should normalize to NFC."""
+    import unicodedata
+    nfd_u = "u\u0308"  # NFD form of ü
+    path = f"/Volumes/SSD/Musica/Techno/tr{nfd_u}ck.mp3"
+    content = f"#EXTM3U\n#EXTINF:200,Artist - Title\n{path}\n"
+    result = parse_m3u8(content)
+    assert len(result.tracks) == 1
+    # normalized_path should be NFC
+    assert unicodedata.is_normalized("NFC", result.tracks[0].normalized_path)
+
+
+def test_parse_m3u8_with_empty_lines_and_comments():
+    content = (
+        "#EXTM3U\n"
+        "\n"
+        "# This is a comment\n"
+        "#EXTINF:180,Artist - Track\n"
+        "\n"
+        "/path/to/file.mp3\n"
+        "\n"
+    )
+    result = parse_m3u8(content)
+    assert len(result.tracks) == 1
+
+
+def test_parse_malformed_extinf():
+    content = "#EXTM3U\n#EXTINF:abc\n/path/to/file.mp3\n"
+    result = parse_m3u8(content)
+    assert len(result.tracks) == 1
+    assert result.tracks[0].duration_sec == -1
+    assert any("malformed" in w.lower() for w in result.warnings)
+
+
+def test_parse_playlist_tag():
+    content = (
+        "#EXTM3U\n"
+        "#PLAYLIST:Friday Night Set\n"
+        "#EXTINF:300,Artist - Track\n"
+        "/path/to/file.mp3\n"
+    )
+    result = parse_m3u8(content, source_path="some_file.m3u8")
+    assert result.playlist_name == "Friday Night Set"
+
+
+def test_parse_no_header():
+    """Files without #EXTM3U header should parse with warning."""
+    content = "#EXTINF:300,Artist - Track\n/path/to/file.mp3\n"
+    result = parse_m3u8(content)
+    assert len(result.tracks) == 1
+    assert any("header" in w.lower() for w in result.warnings)
````

Verification:
- `source .venv/bin/activate && python -m pytest tests/test_m3u8_parser.py -x -q` — 8 tests pass.

#### Task 13 — Integration tests: API import endpoint
Tools: editor
Create file `tests/api/test_import_api.py`:

````diff
--- /dev/null
+++ b/tests/api/test_import_api.py
@@
+"""Integration tests for the M3U8 playlist import API."""
+
+from __future__ import annotations
+
+import io
+
+import pytest
+
+
+M3U8_TEMPLATE = "#EXTM3U\n"
+
+
+def _make_m3u8(*paths: str, name: str | None = None) -> str:
+    """Build a minimal M3U8 string with given file paths."""
+    lines = ["#EXTM3U"]
+    if name:
+        lines.append(f"#PLAYLIST:{name}")
+    for i, p in enumerate(paths):
+        lines.append(f"#EXTINF:300,Artist {i+1} - Track {i+1}")
+        lines.append(p)
+    return "\n".join(lines) + "\n"
+
+
+@pytest.fixture()
+def db_with_paths(db_session):
+    """Add file_path to seed tracks so import can match them."""
+    from kiku.db.models import Track
+
+    for i in range(1, 21):
+        t = db_session.get(Track, i)
+        t.file_path = f"/Volumes/SSD/Musica/Genre/track_{i}.mp3"
+    db_session.commit()
+    return db_session
+
+
+@pytest.fixture()
+def client_with_paths(db_with_paths):
+    """TestClient with DB that has file paths on tracks."""
+    from fastapi.testclient import TestClient
+
+    from kiku.api.deps import get_db
+    from kiku.api.main import create_app
+
+    app = create_app()
+
+    def override_get_db():
+        try:
+            yield db_with_paths
+        finally:
+            pass
+
+    app.dependency_overrides[get_db] = override_get_db
+    with TestClient(app) as c:
+        yield c
+    app.dependency_overrides.clear()
+
+
+def test_import_full_match(client_with_paths):
+    """All tracks match — creates set with correct count."""
+    m3u8 = _make_m3u8(
+        "/Volumes/SSD/Musica/Genre/track_1.mp3",
+        "/Volumes/SSD/Musica/Genre/track_2.mp3",
+        "/Volumes/SSD/Musica/Genre/track_3.mp3",
+        name="Full Match Set",
+    )
+    resp = client_with_paths.post(
+        "/api/sets/import/m3u8",
+        files={"file": ("test.m3u8", io.BytesIO(m3u8.encode()), "audio/x-mpegurl")},
+    )
+    assert resp.status_code == 200
+    data = resp.json()
+    assert data["matched_count"] == 3
+    assert data["unmatched_count"] == 0
+    assert data["set_id"] > 0
+    assert data["source"] == "m3u8"
+    assert data["name"] == "Full Match Set"
+
+
+def test_import_partial_match(client_with_paths):
+    """Some tracks match, others don't — returns 200 with unmatched."""
+    m3u8 = _make_m3u8(
+        "/Volumes/SSD/Musica/Genre/track_1.mp3",
+        "/Volumes/SSD/Musica/Unknown/nonexistent.mp3",
+    )
+    resp = client_with_paths.post(
+        "/api/sets/import/m3u8",
+        files={"file": ("test.m3u8", io.BytesIO(m3u8.encode()), "audio/x-mpegurl")},
+    )
+    assert resp.status_code == 200
+    data = resp.json()
+    assert data["matched_count"] == 1
+    assert data["unmatched_count"] == 1
+    assert len(data["unmatched_paths"]) == 1
+
+
+def test_import_zero_match(client_with_paths):
+    """No tracks match — returns 400."""
+    m3u8 = _make_m3u8(
+        "/Volumes/SSD/Musica/Unknown/no_match_1.mp3",
+        "/Volumes/SSD/Musica/Unknown/no_match_2.mp3",
+    )
+    resp = client_with_paths.post(
+        "/api/sets/import/m3u8",
+        files={"file": ("test.m3u8", io.BytesIO(m3u8.encode()), "audio/x-mpegurl")},
+    )
+    assert resp.status_code == 400
+    assert "None of the tracks matched" in resp.json()["detail"]
+
+
+def test_import_not_m3u8(client_with_paths):
+    """Non-M3U8 content — returns 400."""
+    content = "This is just text, not a playlist"
+    resp = client_with_paths.post(
+        "/api/sets/import/m3u8",
+        files={"file": ("test.m3u8", io.BytesIO(content.encode()), "audio/x-mpegurl")},
+    )
+    assert resp.status_code == 400
+    assert "M3U8" in resp.json()["detail"]
+
+
+def test_import_duplicate_set(client_with_paths):
+    """Second import of same file returns duplicate warning."""
+    m3u8 = _make_m3u8(
+        "/Volumes/SSD/Musica/Genre/track_1.mp3",
+        "/Volumes/SSD/Musica/Genre/track_2.mp3",
+    )
+    # First import
+    resp1 = client_with_paths.post(
+        "/api/sets/import/m3u8",
+        files={"file": ("friday.m3u8", io.BytesIO(m3u8.encode()), "audio/x-mpegurl")},
+    )
+    assert resp1.status_code == 200
+    set_id = resp1.json()["set_id"]
+
+    # Second import — duplicate
+    resp2 = client_with_paths.post(
+        "/api/sets/import/m3u8",
+        files={"file": ("friday.m3u8", io.BytesIO(m3u8.encode()), "audio/x-mpegurl")},
+    )
+    assert resp2.status_code == 200
+    data = resp2.json()
+    assert data["duplicate_set_id"] == set_id
+    assert any("Already imported" in w for w in data["warnings"])
+
+
+def test_import_force_reimport(client_with_paths):
+    """Force flag allows re-import of same file."""
+    m3u8 = _make_m3u8(
+        "/Volumes/SSD/Musica/Genre/track_1.mp3",
+    )
+    # First import
+    client_with_paths.post(
+        "/api/sets/import/m3u8",
+        files={"file": ("force_test.m3u8", io.BytesIO(m3u8.encode()), "audio/x-mpegurl")},
+    )
+
+    # Force re-import
+    resp = client_with_paths.post(
+        "/api/sets/import/m3u8",
+        files={"file": ("force_test.m3u8", io.BytesIO(m3u8.encode()), "audio/x-mpegurl")},
+        data={"force": "true"},
+    )
+    assert resp.status_code == 200
+    assert resp.json()["matched_count"] == 1
+    assert resp.json()["duplicate_set_id"] is None
+
+
+def test_import_preserves_order(client_with_paths):
+    """Tracks in the set follow M3U8 order (0-based positions)."""
+    m3u8 = _make_m3u8(
+        "/Volumes/SSD/Musica/Genre/track_5.mp3",
+        "/Volumes/SSD/Musica/Genre/track_3.mp3",
+        "/Volumes/SSD/Musica/Genre/track_1.mp3",
+    )
+    resp = client_with_paths.post(
+        "/api/sets/import/m3u8",
+        files={"file": ("order.m3u8", io.BytesIO(m3u8.encode()), "audio/x-mpegurl")},
+    )
+    assert resp.status_code == 200
+    set_id = resp.json()["set_id"]
+
+    # Verify order via set detail
+    detail = client_with_paths.get(f"/api/sets/{set_id}")
+    assert detail.status_code == 200
+    tracks = detail.json()["tracks"]
+    assert tracks[0]["track_id"] == 5
+    assert tracks[1]["track_id"] == 3
+    assert tracks[2]["track_id"] == 1
+    # Verify 0-based positions
+    assert tracks[0]["position"] == 0
+    assert tracks[1]["position"] == 1
+    assert tracks[2]["position"] == 2
+
+
+def test_import_source_fields(client_with_paths):
+    """Imported set has source='m3u8' and source_ref set."""
+    m3u8 = _make_m3u8("/Volumes/SSD/Musica/Genre/track_1.mp3")
+    resp = client_with_paths.post(
+        "/api/sets/import/m3u8",
+        files={"file": ("src_test.m3u8", io.BytesIO(m3u8.encode()), "audio/x-mpegurl")},
+    )
+    assert resp.status_code == 200
+    set_id = resp.json()["set_id"]
+
+    # Check via list endpoint (source field on SetResponse)
+    list_resp = client_with_paths.get("/api/sets")
+    imported_set = next(s for s in list_resp.json() if s["id"] == set_id)
+    assert imported_set["source"] == "m3u8"
````

Verification:
- `source .venv/bin/activate && python -m pytest tests/api/test_import_api.py -x -q` — 8 tests pass.

#### Task 14 — Lint all modified files
Tools: shell
Commands:
```bash
source .venv/bin/activate && ruff check --fix \
  src/kiku/db/models.py \
  src/kiku/import_playlist/__init__.py \
  src/kiku/import_playlist/m3u8.py \
  src/kiku/import_playlist/service.py \
  src/kiku/api/schemas.py \
  src/kiku/api/routes/sets.py \
  src/kiku/cli.py \
  tests/test_m3u8_parser.py \
  tests/api/test_import_api.py
```

And frontend:
```bash
cd frontend && npx svelte-check --tsconfig ./tsconfig.json
```

Fix any lint errors before committing.

#### Task 15 — Run all tests
Tools: shell
Commands:
```bash
source .venv/bin/activate && python -m pytest tests/ -x -q
```

All tests (existing + new parser + new import API) must pass.

#### Task 16 — Commit
Tools: git
Commands:
```bash
git add \
  src/kiku/db/models.py \
  src/kiku/import_playlist/__init__.py \
  src/kiku/import_playlist/m3u8.py \
  src/kiku/import_playlist/service.py \
  src/kiku/api/schemas.py \
  src/kiku/api/routes/sets.py \
  src/kiku/cli.py \
  frontend/src/lib/types/index.ts \
  frontend/src/lib/api/sets.ts \
  frontend/src/lib/components/set/ImportPlaylistDialog.svelte \
  frontend/src/lib/components/set/SetPicker.svelte \
  tests/test_m3u8_parser.py \
  tests/api/test_import_api.py \
  alembic/versions/*_add_import_columns*.py
```

Commit message: `feat: M3U8 playlist import — parser, batch matching, API, CLI, frontend dialog`

### Validate

- **HLO (L6)**: Import Rekordbox M3U8 playlists — covered by parser (Task 3), batch matching (Task 4), API (Task 6), CLI (Task 7), frontend (Tasks 10-11). ✅
- **MLO L10**: Alembic migration — Task 2 adds 4 cols on sets, 2 on set_tracks. ✅
- **MLO L11**: M3U8 parser at `src/kiku/import_playlist/m3u8.py` — Task 3 with BOM, NFC, backslash, #PLAYLIST. ✅
- **MLO L12**: Track matching cascade — Task 4 implements exact → nocase → fuzzy ±10s. ✅
- **MLO L13**: API endpoint `POST /api/sets/import/m3u8` — Task 6, registered before `/{set_id}`. ✅
- **MLO L14**: CLI `kiku import-playlist` — Task 7 with `--name`, `--dry-run`, `--force`. ✅
- **MLO L15**: Frontend `ImportPlaylistDialog.svelte` — Task 10 with drop zone, name field, result display. ✅
- **MLO L16**: API client `importPlaylist()` — Task 9. ✅
- **MLO L17**: 0-based positions — Task 4 service uses `enumerate(matched)` for 0-based. ✅
- **MLO L18**: Index on `tracks.file_path` — Task 2 migration creates `ix_tracks_file_path`. ✅
- **MLO L19**: Batch matching — Task 4 loads all tracks once as dict. ✅
- **MLO L20**: No new Track rows — Task 4 service only queries, never inserts tracks. ✅
- **MLO L21**: Duplicate set detection — Task 4 checks `source_ref` + `force` flag. ✅
- **MLO L22**: 14+ tests — Task 12 has 8 parser tests, Task 13 has 8 API tests (16 total). ✅
- **DT L35-36 (WARNING-1)**: 0-based positions via `enumerate()` in service. ✅
- **DT L33 (BLOCKER-1)**: `analysis_cache TEXT` column added in migration. ✅
- **DT L34 (WARNING-2)**: `inferred_energy` + `inference_source` on set_tracks. ✅
- **DT L35 (WARNING-3)**: `POST /import/m3u8` before `/{set_id}` in router. ✅
- **DT L36 (NOTE-2)**: `#PLAYLIST` tag handled in parser. ✅
- **DT L37 (NOTE-4)**: ±10s duration in fuzzy matching. ✅
- **DT L67-72 (Batch matching)**: Dict-based O(1) lookup, no per-track queries. ✅
- **DT L75-76 (No track creation)**: Service never creates Track rows. ✅
- **DT L78-82 (Duplicate set)**: Checks `source_ref`, returns duplicate_set_id, force flag. ✅
- **Kiku voice**: CLI output uses warm tone, no forbidden words. ✅

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
