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
