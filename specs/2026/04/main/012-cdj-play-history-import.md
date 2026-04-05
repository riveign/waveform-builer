# Human Section
Critical: any text/subsection here cannot be modified by AI.

## High-Level Objective (HLO)

Import CDJ/XDJ play history from USB sticks into Kiku so DJs can learn from their live sets. When a DJ plugs in the USB they gig with, Kiku reads which tracks were played, in what order, and when — turning every gig into a lesson about what worked and why.

## Mid-Level Objectives (MLO)

1. **READ** Pioneer USB play history from `PIONEER/rekordbox/export.pdb` (legacy Device Library format) — extract HISTORY playlists with track order and session dates
2. **MATCH** history tracks to Kiku library entries using the existing track matching pipeline (exact path → case-insensitive → fuzzy duration match)
3. **CREATE** sets in Kiku from each CDJ history session, preserving play order and session date
4. **SUPPORT** Rekordbox desktop history as a secondary source — read `DjmdHistory` + `DjmdSongHistory` tables via pyrekordbox for DJs who sync USB back to Rekordbox first
5. **EXPOSE** via CLI (`kiku import-history <usb-path>`) and API (`POST /api/sets/import/cdj-history`)
6. **DETECT** format automatically — PDB (legacy) vs Device Library Plus (encrypted SQLite on newer CDJs like CDJ-3000)
7. **TRIGGER** auto-analysis on imported history sets so the DJ immediately sees transition scores and teaching moments

## Details (DT)

### Pioneer USB Structure
- USB sticks exported from Rekordbox have `PIONEER/rekordbox/export.pdb` (DeviceSQL binary format)
- CDJs write history rows directly into `export.pdb` during playback — no separate history files
- History playlists are named by date (e.g., "HISTORY 001") containing tracks in play order
- Track registered after ~60s of selection/playback on deck
- Max 999 tracks per history session

### Data Available per Session
- Track list in play order (track_id references into the track table)
- Session date (from playlist name)
- Full track metadata via track table join (title, artist, BPM, key, genre, duration, file_path)
- **NOT available**: per-track timestamps, play counts (CDJs don't update play_count on USB)

### Device Library Plus (Newer CDJs)
- CDJ-3000, XDJ-XZ with recent firmware use encrypted SQLite (`PIONEER/rekordbox/master.db`)
- pyrekordbox can decrypt with SQLCipher via `[unlocked]` extra
- History stored in SQLite tables rather than PDB binary format
- `rbox` library also supports this format

### Existing Kiku Capabilities
- pyrekordbox v0.4.4 already installed (sync, ANLZ waveform import, XML export)
- USB mount access pattern proven via `kiku import-waveforms` (reads `PIONEER/USBANLZ`)
- Track matching pipeline exists from M3U8 import (exact → nocase → fuzzy ±10s)
- Auto-analysis pipeline exists from set-analysis feature (spec 011)
- DB has `play_count` + `kiku_play_count` columns, but no session-level history table

### Phasing
- **Phase 1**: PDB history reader — covers most CDJ gigs (CDJ-2000NXS2, XDJ-1000MK2, etc.)
- **Phase 2**: Rekordbox desktop history — read from `DjmdHistory`/`DjmdSongHistory` tables
- **Phase 3**: Device Library Plus — encrypted SQLite for CDJ-3000 and newer

### Dependencies
- PDB parsing: `crate_digger` (Java) or Kaitai Struct + `rekordbox_pdb.ksy` (Python-compilable) or write minimal parser using Deep Symmetry's reverse-engineering docs
- Device Library Plus: pyrekordbox `[unlocked]` extra + SQLCipher

### Testing
- Unit tests: PDB parser with fixture data (sample export.pdb with known history)
- Integration tests: import flow from USB path → matched tracks → created set
- E2E: plug USB, run CLI, verify set appears in frontend with analysis

## Behavior

You are a senior backend engineer building on Kiku's existing import infrastructure. Reuse the track matching pipeline from M3U8 import (`src/kiku/import_playlist/service.py`). Follow the same patterns as `import-waveforms` for USB mount detection. Sets created from CDJ history should be marked with `source='cdj_history'` and trigger auto-analysis like M3U8 imports do.

# AI Section
Critical: AI can ONLY modify this section.

## Research

### Pioneer USB PDB Format

CDJs write play history directly into `PIONEER/rekordbox/export.pdb` on the USB stick. The format (DeviceSQL) is fully reverse-engineered by [Deep Symmetry](https://github.com/Deep-Symmetry/crate-digger) / James Elliott, Henry Betts, and Fabian Lesniak.

**History tables in PDB:**
- **History Playlist rows**: `id` (4B) + `name` (DeviceSQL string, e.g. "HISTORY 001")
- **History Entry rows**: `track_id` (4B) + `playlist_id` (4B) + `entry_index` (4B) — preserves exact play order
- **Track rows**: `id`, `title`, `artist_id`, `file_path`, `tempo` (BPM×100), `duration`, etc.

**What CDJs record**: Track loaded on deck for >60s gets added to current history session. Max 999 tracks/session. Play order preserved via `entry_index`.

**What CDJs DON'T record**: Per-track timestamps, deck assignment, play counts (only update in Rekordbox desktop after USB sync), BPM adjustments, crossfade/transition data.

**Device Library Plus** (CDJ-3000, OPUS-QUAD, XDJ-AZ): Encrypted SQLite at `PIONEER/rekordbox/exportLibrary.db`. Same schema as Rekordbox desktop (`djmdHistory` + `djmdSongHistory`). CDJ-3000 dual-writes both PDB + DL+ for backward compat. Newer-only devices (OPUS-QUAD, OMNIS-DUO) write DL+ only.

### Python PDB Parsing Options Evaluated

| Option | Deps | Files | Pros | Cons |
|--------|------|-------|------|------|
| **Kaitai Struct** (`rekordbox_pdb.ksy` → Python) | `kaitaistruct` runtime + Java compiler at build | 1 generated | Battle-tested spec from Deep Symmetry | Needs Java build step, verbose generated code |
| **python-prodj-link pdblib** (vendor) | `construct>=2.9` | 19 files | Full PDB support, proven | Heavy — 19 files for 3 tables we need, not on PyPI, `construct` dep |
| **Custom minimal parser** | None | 1 file | Zero deps, full control, only parses what we need | Manual binary parsing, maintenance burden |
| **rbox** (DL+ only) | `rbox` | pip install | Clean API for encrypted SQLite | DL+ only — doesn't cover legacy CDJs |

**Recommendation: Custom minimal parser** (Option C for Phase 1)
- We only need 3 tables: History Playlists, History Entries, Tracks
- The binary format is well-documented (page headers, row offsets, DeviceSQL strings)
- Zero new dependencies — consistent with Kiku's minimal approach
- ~200-300 lines of focused code vs vendoring 19 files or adding build steps
- Phase 2 (DL+) can use pyrekordbox's existing SQLite support or `rbox`

### Existing Kiku Infrastructure (Audit)

**What we can reuse:**
- **Track matching**: `src/kiku/import_playlist/service.py` — 3-tier cascade (exact path → nocase → fuzzy ±10s). PDB parser just needs to produce file paths.
- **Path normalization**: `src/kiku/db/paths.py` — `normalize_path()` with `_PATH_ALIASES` for macOS↔Linux mount prefixes
- **USB access pattern**: `kiku import-waveforms` already reads from `PIONEER/USBANLZ/` — proven mount detection
- **Set creation**: `import_playlist()` in service.py creates Set with `source`, `source_ref`, tracks at positions
- **Auto-analysis**: SSE pipeline in `src/kiku/api/routes/sets.py` — `_analyze_set()` stores result in `Set.analysis_cache`
- **DB schema**: `Set.source` field (existing values: "kiku", "manual", "m3u8"), `Set.source_ref` for dedup

**What we need to add:**
- PDB parser module: `src/kiku/import_playlist/pdb.py` (~200-300 lines)
- CLI command: `kiku import-history <usb-path>` with `--session`, `--all`, `--force` flags
- API endpoint: `POST /api/sets/import/cdj-history` (follows M3U8 import pattern)
- Frontend: Import dialog USB tab (optional — CLI-first for Phase 1)
- No schema migration needed — reuse existing `Set.source='cdj_history'` + `Set.source_ref`

### DeviceSQL Binary Format Reference

```
PDB File Layout:
  [4B magic: 0x00000000] [4B ?] [4B ?] [4B page_size]
  [Table pointers: type → first_page offset]
  [Pages: header (28B) + row_groups → rows]

Page Header (28B):
  [4B ?] [4B page_index] [4B type] [4B next_page]
  [4B ?] [4B ?] [2B num_rows_small] [2B ?]
  [2B ?] [2B num_rows_large]

Row Group:
  [2B first_row_index] [2B ?] [row_offsets...] [row_data...]

DeviceSQL Strings:
  [1B type] → 0x03=UTF-16-BE, 0x02=ASCII/ISO-8859-1
  [payload...]
```

### Test Infrastructure

**Existing patterns** (from M3U8 import):
- `tests/api/conftest.py`: in-memory SQLite, seeded 20 tracks, TestClient with DI override
- `tests/api/test_import_api.py`: 8 tests (upload, name override, unmatched, zero matches, dedup, force, no file, invalid format)
- `tests/test_m3u8_parser.py`: 8 parser unit tests with fixture data
- Test file paths: `/Volumes/SSD/Musica/2025/Techno/Track {i}.mp3`

**For CDJ history tests:**
- Unit tests: PDB parser with a crafted binary fixture (known history sessions + tracks)
- Integration tests: import flow → matched tracks → created set with `source='cdj_history'`
- Need fixture: minimal valid `export.pdb` with 2 history sessions, 3-5 tracks each

### Strategy

**Phase 1 — PDB History Reader (this spec)**

1. **Parser** (`src/kiku/import_playlist/pdb.py`):
   - Custom binary parser targeting History Playlist, History Entry, Track tables only
   - Returns `PDBHistorySession` dataclass: `name`, `tracks: list[PDBTrack]` (with `file_path`, `title`, `artist`, `bpm`, `key`, `duration`)
   - Handle DeviceSQL string encoding (UTF-16-BE + ASCII)
   - Auto-detect PIONEER directory from USB mount path

2. **Service integration** (`src/kiku/import_playlist/service.py`):
   - New `import_cdj_history()` function that takes PDB sessions → creates Kiku sets
   - Reuse `match_tracks()` cascade with PDB file paths
   - Set `source='cdj_history'`, `source_ref='HISTORY 003 @ /media/usb'`
   - Multi-session support: list available sessions, import one or all

3. **CLI** (`src/kiku/cli.py`):
   - `kiku import-history <usb-path>` — list sessions found
   - `kiku import-history <usb-path> --session 3` — import specific session
   - `kiku import-history <usb-path> --all` — import all sessions
   - `--force` to re-import, `--name` to override set name

4. **API** (`src/kiku/api/routes/sets.py`):
   - `POST /api/sets/import/cdj-history` with `usb_path` + optional `session_id`
   - Returns `ImportResultResponse` (same schema as M3U8 import)
   - Auto-analysis triggered after import

5. **Testing**:
   - Unit: PDB parser with binary fixture (~8 tests: parse sessions, parse entries, string decoding, missing file, corrupt data)
   - Integration: full import flow (~6 tests: single session, all sessions, dedup, force, no PIONEER dir, no history)
   - Fixture: hand-crafted minimal `export.pdb` with known structure

**Phase 2 — Rekordbox Desktop History (future)**
- Read `DjmdHistory` + `DjmdSongHistory` via pyrekordbox `Rekordbox6Database`
- Richer data: actual timestamps, deck info from Rekordbox's post-import enrichment

**Phase 3 — Device Library Plus (future)**
- Decrypt `exportLibrary.db` via pyrekordbox `[unlocked]` or `rbox`
- Query SQLite history tables directly
- Auto-detect format: check for `exportLibrary.db` first, fall back to `export.pdb`

## Plan
<!-- Filled by /spec PLAN -->

## Plan Review
<!-- Filled if required to validate plan -->

## Implement
<!-- Filled by /spec IMPLEMENT -->

## Test Evidence & Outputs
<!-- Filled by explicit testing after /spec IMPLEMENT -->

## Updated Doc
<!-- Filled by explicit documentation updates after /spec IMPLEMENT -->

## Post-Implement Review
<!-- Filled by /spec REVIEW -->
