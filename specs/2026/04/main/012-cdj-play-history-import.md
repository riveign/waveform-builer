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

### Files
- `src/kiku/import_playlist/pdb.py` (NEW)
  - PDB binary parser: file header, page traversal, row extraction, DeviceSQL string decoding
  - Dataclasses: PDBTrack, PDBHistoryEntry, PDBHistorySession, PDBParseResult
  - Functions: parse_pdb(), find_pioneer_db(), _read_devicesql_string(), _iter_pages(), _iter_row_offsets()
- `src/kiku/import_playlist/service.py`
  - Add import_cdj_history() function using existing _build_path_index() and match cascade
- `src/kiku/cli.py`
  - Add `import-history` CLI command with --session, --all, --name, --force
- `src/kiku/api/routes/sets.py`
  - Add POST /import/cdj-history endpoint
- `tests/test_pdb_parser.py` (NEW)
  - PDB parser unit tests with programmatic binary fixtures
- `tests/api/test_cdj_import_api.py` (NEW)
  - API integration tests for CDJ history import endpoint

### Tasks

#### Task 1 — Create PDB parser module
Tools: editor (new file)
File: `src/kiku/import_playlist/pdb.py`

Create a custom binary parser for Pioneer DeviceSQL (.pdb) files. Reads only the 3 tables needed: Tracks (file paths), History Playlists (session names), History Entries (track order per session). Based on the reverse-engineering by Deep Symmetry (rekordbox_pdb.ksy).

Key format details:
- File header: 24 bytes (unknown u4, page_size u4, num_tables u4, next_unused u4, unknown u4, sequence u4), then gap to fill first page_size block. Table pointers start at file offset page_size, each 16 bytes (type u4, empty_candidate u4, first_page_idx u4, last_page_idx u4).
- Page at index I is at file offset `page_size * (I + 1)`. Page header is 36 bytes. Rows stored in groups of 16 with presence bitmask. Row offsets (u2) are page-relative.
- Table type enum: tracks=0, history_playlists=9, history_entries=10.
- Track row: 21 × u2 string offsets at start, then fixed fields. Track ID (u2) at byte 46. File path string offset at index 17 (byte 34). Title string offset at index 15 (byte 30).
- History playlist row: id (u4) + name (DeviceSQL string at offset 4).
- History entry row: track_id (u4) + playlist_id (u4) + entry_index (u4) = 12 bytes.
- DeviceSQL strings: first byte = kind. 0x40 = long ASCII (u2 length + data). 0x90 = long UTF-16LE (u2 byte-length + data). Odd value = short ASCII (length = kind >> 1, data follows).

````diff
--- /dev/null
+++ b/src/kiku/import_playlist/pdb.py
@@ -0,0 +1,226 @@
+"""Parse Pioneer DeviceSQL (.pdb) files for CDJ play history.
+
+Reads only the tables needed for history import: Track (file paths),
+History Playlist (session names), History Entry (track order per session).
+
+Based on the reverse-engineering work by James Elliott (Deep Symmetry),
+Henry Betts, and Fabian Lesniak.  Format spec: rekordbox_pdb.ksy
+"""
+
+from __future__ import annotations
+
+import struct
+from dataclasses import dataclass, field
+from pathlib import Path
+
+# PDB table type identifiers (from rekordbox_pdb.ksy page_type enum)
+TABLE_TRACKS = 0
+TABLE_HISTORY_PLAYLISTS = 9
+TABLE_HISTORY_ENTRIES = 10
+
+
+@dataclass
+class PDBTrack:
+    """Minimal track info from PDB — just enough for library matching."""
+    id: int
+    file_path: str
+    title: str = ""
+
+
+@dataclass
+class PDBHistoryEntry:
+    """Single entry in a CDJ play history session."""
+    track_id: int
+    playlist_id: int
+    entry_index: int
+
+
+@dataclass
+class PDBHistorySession:
+    """A CDJ play history session (one per USB mount on a CDJ)."""
+    id: int
+    name: str  # e.g. "HISTORY 001"
+    entries: list[PDBHistoryEntry] = field(default_factory=list)
+
+
+@dataclass
+class PDBParseResult:
+    """Result of parsing a Pioneer PDB file for history data."""
+    sessions: list[PDBHistorySession] = field(default_factory=list)
+    tracks: dict[int, PDBTrack] = field(default_factory=dict)  # id -> track
+    warnings: list[str] = field(default_factory=list)
+
+
+def _read_devicesql_string(data: bytes, offset: int) -> str:
+    """Decode a DeviceSQL string at the given offset within a data buffer.
+
+    String encoding (first byte = kind):
+      0x40: Long ASCII — next 2 bytes = length (u16le), then ASCII data
+      0x90: Long UTF-16LE — next 2 bytes = byte length (u16le), then UTF-16LE data
+      odd:  Short ASCII — length = kind >> 1, data follows immediately
+    """
+    if offset <= 0 or offset >= len(data):
+        return ""
+    kind = data[offset]
+    if kind == 0x40:
+        if offset + 3 > len(data):
+            return ""
+        length = struct.unpack_from("<H", data, offset + 1)[0]
+        start = offset + 3
+        end = min(start + length, len(data))
+        return data[start:end].decode("ascii", errors="replace").rstrip("\x00")
+    if kind == 0x90:
+        if offset + 3 > len(data):
+            return ""
+        byte_len = struct.unpack_from("<H", data, offset + 1)[0]
+        start = offset + 3
+        end = min(start + byte_len, len(data))
+        return data[start:end].decode("utf-16-le", errors="replace").rstrip("\x00")
+    if kind & 1:
+        length = kind >> 1
+        start = offset + 1
+        end = min(start + length, len(data))
+        return data[start:end].decode("ascii", errors="replace").rstrip("\x00")
+    return ""
+
+
+def _iter_row_offsets(page: bytes) -> list[int]:
+    """Extract present row offsets from a single PDB page.
+
+    Page header (36 bytes), then row groups. Each group:
+      u2 group_id, u2 present_flags (bitmask), then up to 16 x u2 row offsets.
+    Row offsets are page-relative byte positions of row data.
+    """
+    page_size = len(page)
+    if page_size < 36:
+        return []
+    num_rows_small = page[24]
+    num_rows_large = struct.unpack_from("<H", page, 34)[0]
+    num_rows = max(num_rows_small, num_rows_large)
+    if num_rows == 0:
+        return []
+
+    offsets: list[int] = []
+    pos = 36  # after page header
+    num_groups = (num_rows + 15) // 16
+
+    for g in range(num_groups):
+        if pos + 4 > page_size:
+            break
+        present_flags = struct.unpack_from("<H", page, pos + 2)[0]
+        pos += 4  # skip group_id + present_flags
+
+        rows_in_group = min(16, num_rows - g * 16)
+        for bit in range(rows_in_group):
+            if pos + 2 > page_size:
+                break
+            row_ofs = struct.unpack_from("<H", page, pos)[0]
+            pos += 2
+            if present_flags & (1 << bit) and 0 < row_ofs < page_size:
+                offsets.append(row_ofs)
+
+    return offsets
+
+
+def _iter_pages(data: bytes, first_page_idx: int, page_size: int):
+    """Iterate through a linked list of PDB pages.
+
+    Page at index I is at file offset page_size * (I + 1).
+    Yields page data (bytes) for each page in the chain.
+    """
+    idx = first_page_idx
+    visited: set[int] = set()
+    file_len = len(data)
+
+    while idx not in visited and idx != 0xFFFFFFFF:
+        visited.add(idx)
+        file_ofs = page_size * (idx + 1)
+        if file_ofs + page_size > file_len:
+            break
+        page = data[file_ofs : file_ofs + page_size]
+        yield page
+        next_idx = struct.unpack_from("<I", page, 12)[0]
+        idx = next_idx
+
+
+def _parse_tracks(data: bytes, first_page: int, page_size: int) -> dict[int, PDBTrack]:
+    """Parse Track table rows. Extracts id, file_path, title."""
+    tracks: dict[int, PDBTrack] = {}
+    for page in _iter_pages(data, first_page, page_size):
+        for row_ofs in _iter_row_offsets(page):
+            row = page[row_ofs:]
+            if len(row) < 64:  # minimum: 21*u2 offsets + fixed fields
+                continue
+            # String offset indices: title=15 (*2=30), file_path=17 (*2=34)
+            ofs_title = struct.unpack_from("<H", row, 30)[0]
+            ofs_file_path = struct.unpack_from("<H", row, 34)[0]
+            # Track ID (u2) at offset 46 (after 21*u2 + sample_rate + artist_id)
+            track_id = struct.unpack_from("<H", row, 46)[0]
+            if track_id == 0:
+                continue
+            file_path = _read_devicesql_string(row, ofs_file_path)
+            title = _read_devicesql_string(row, ofs_title)
+            tracks[track_id] = PDBTrack(id=track_id, file_path=file_path, title=title)
+    return tracks
+
+
+def _parse_history_playlists(
+    data: bytes, first_page: int, page_size: int,
+) -> list[PDBHistorySession]:
+    """Parse History Playlist table. Each row: id (u4) + name (devicesql string)."""
+    sessions: list[PDBHistorySession] = []
+    for page in _iter_pages(data, first_page, page_size):
+        for row_ofs in _iter_row_offsets(page):
+            row = page[row_ofs:]
+            if len(row) < 8:
+                continue
+            playlist_id = struct.unpack_from("<I", row, 0)[0]
+            name = _read_devicesql_string(row, 4)
+            sessions.append(PDBHistorySession(id=playlist_id, name=name))
+    return sessions
+
+
+def _parse_history_entries(
+    data: bytes, first_page: int, page_size: int,
+) -> list[PDBHistoryEntry]:
+    """Parse History Entry table. Each row: track_id (u4) + playlist_id (u4) + entry_index (u4)."""
+    entries: list[PDBHistoryEntry] = []
+    for page in _iter_pages(data, first_page, page_size):
+        for row_ofs in _iter_row_offsets(page):
+            row = page[row_ofs:]
+            if len(row) < 12:
+                continue
+            track_id = struct.unpack_from("<I", row, 0)[0]
+            playlist_id = struct.unpack_from("<I", row, 4)[0]
+            entry_index = struct.unpack_from("<I", row, 8)[0]
+            entries.append(PDBHistoryEntry(track_id, playlist_id, entry_index))
+    return entries
+
+
+def find_pioneer_db(usb_path: str) -> Path:
+    """Locate export.pdb within a Pioneer USB directory structure.
+
+    Checks PIONEER/rekordbox/export.pdb relative to the given path.
+    Raises FileNotFoundError if no Pioneer database is found.
+    """
+    root = Path(usb_path)
+    pdb = root / "PIONEER" / "rekordbox" / "export.pdb"
+    if pdb.exists():
+        return pdb
+    # Maybe usb_path IS the PIONEER directory
+    pdb_alt = root / "rekordbox" / "export.pdb"
+    if pdb_alt.exists():
+        return pdb_alt
+    raise FileNotFoundError(
+        f"No Pioneer database found at {usb_path}. "
+        "Expected PIONEER/rekordbox/export.pdb on your USB stick."
+    )
+
+
+def parse_pdb(file_path: str | Path) -> PDBParseResult:
+    """Parse a Pioneer export.pdb file and extract play history sessions.
+
+    Returns PDBParseResult with history sessions (track play order) and
+    a track lookup dict (id -> file_path/title) for library matching.
+    """
+    path = Path(file_path)
+    if not path.exists():
+        raise FileNotFoundError(f"PDB file not found: {file_path}")
+
+    data = path.read_bytes()
+    result = PDBParseResult()
+
+    if len(data) < 24:
+        result.warnings.append("File too small to be a valid PDB")
+        return result
+
+    # File header: [unknown u4] [page_size u4] [num_tables u4]
+    _, page_size, num_tables = struct.unpack_from("<III", data, 0)
+
+    if page_size == 0 or page_size > 65536:
+        result.warnings.append(f"Invalid page size: {page_size}")
+        return result
+
+    # Table pointers start at file offset page_size (after header gap)
+    # Each entry: type(u4) + empty_candidate(u4) + first_page(u4) + last_page(u4) = 16B
+    table_ptrs: dict[int, int] = {}
+    for i in range(num_tables):
+        ofs = page_size + i * 16
+        if ofs + 16 > len(data):
+            break
+        ttype = struct.unpack_from("<I", data, ofs)[0]
+        first_page_idx = struct.unpack_from("<I", data, ofs + 8)[0]
+        table_ptrs[ttype] = first_page_idx
+
+    # Parse tracks (needed to resolve history entry track_ids to file_paths)
+    if TABLE_TRACKS in table_ptrs:
+        result.tracks = _parse_tracks(data, table_ptrs[TABLE_TRACKS], page_size)
+
+    # Parse history playlists (session names)
+    if TABLE_HISTORY_PLAYLISTS in table_ptrs:
+        result.sessions = _parse_history_playlists(
+            data, table_ptrs[TABLE_HISTORY_PLAYLISTS], page_size,
+        )
+    else:
+        result.warnings.append("No history playlists table found in PDB")
+
+    # Parse history entries and attach to sessions
+    if TABLE_HISTORY_ENTRIES in table_ptrs:
+        entries = _parse_history_entries(
+            data, table_ptrs[TABLE_HISTORY_ENTRIES], page_size,
+        )
+        session_map = {s.id: s for s in result.sessions}
+        for entry in entries:
+            if entry.playlist_id in session_map:
+                session_map[entry.playlist_id].entries.append(entry)
+        # Sort entries within each session by play order
+        for s in result.sessions:
+            s.entries.sort(key=lambda e: e.entry_index)
+
+    return result
````

Verification:
- File exists at `src/kiku/import_playlist/pdb.py`
- `source .venv/bin/activate && python -c "from kiku.import_playlist.pdb import parse_pdb, find_pioneer_db, PDBParseResult; print('OK')"`

#### Task 2 — Add import_cdj_history() to service.py
Tools: editor
File: `src/kiku/import_playlist/service.py`

Add a new function `import_cdj_history()` that takes PDB parse results and creates Kiku sets. Reuses the existing `_build_path_index()` and 3-tier match cascade. Returns a list of ImportResult (one per imported session).

````diff
--- a/src/kiku/import_playlist/service.py
+++ b/src/kiku/import_playlist/service.py
@@ -1,4 +1,4 @@
-"""Import M3U8 playlists into Kiku sets with batch track matching."""
+"""Import playlists into Kiku sets with batch track matching."""

 from __future__ import annotations

@@ -8,6 +8,7 @@
 from sqlalchemy.orm import Session

 from kiku.db.models import Set, SetTrack, Track
 from kiku.db.paths import normalize_path
 from kiku.import_playlist.m3u8 import M3U8ParseResult, M3U8Track

@@ -217,0 +218,128 @@
+
+
+def import_cdj_history(
+    session: Session,
+    pdb_result: "PDBParseResult",
+    *,
+    session_ids: list[int] | None = None,
+    force: bool = False,
+    name_override: str | None = None,
+) -> list[ImportResult]:
+    """Import CDJ history sessions as Kiku sets.
+
+    Parameters
+    ----------
+    session : Session
+        SQLAlchemy session.
+    pdb_result : PDBParseResult
+        Parsed PDB data with history sessions and track lookup.
+    session_ids : list[int], optional
+        Import only these session IDs. None = all sessions.
+    force : bool
+        Re-import even if source_ref already exists.
+    name_override : str, optional
+        Override set name (only meaningful for single session import).
+    """
+    from kiku.import_playlist.pdb import PDBParseResult  # noqa: F811
+
+    exact_idx, nocase_idx, stem_idx = _build_path_index(session)
+
+    targets = pdb_result.sessions
+    if session_ids is not None:
+        target_set = set(session_ids)
+        targets = [s for s in targets if s.id in target_set]
+
+    results: list[ImportResult] = []
+
+    for hist_session in targets:
+        if not hist_session.entries:
+            continue
+
+        set_name = name_override or hist_session.name or "CDJ History"
+        source_ref = f"{hist_session.name} @ cdj_history"
+
+        # Duplicate check
+        existing = session.query(Set).filter(Set.source_ref == source_ref).first()
+        if existing and not force:
+            results.append(ImportResult(
+                set_id=existing.id,
+                name=existing.name or "",
+                source="cdj_history",
+                total_tracks=len(hist_session.entries),
+                matched_count=0,
+                unmatched_count=0,
+                unmatched=[],
+                match_methods={},
+                warnings=[],
+                duplicate_set_id=existing.id,
+            ))
+            continue
+
+        # Match each history entry's track to the Kiku library
+        matched_tracks: list[tuple[int, Track, str]] = []  # (entry_index, track, method)
+        unmatched_list: list[dict] = []
+        method_counts: dict[str, int] = {}
+
+        for entry in hist_session.entries:
+            pdb_track = pdb_result.tracks.get(entry.track_id)
+            if not pdb_track or not pdb_track.file_path:
+                unmatched_list.append({
+                    "path": f"[track_id={entry.track_id}]",
+                    "title": pdb_track.title if pdb_track else None,
+                    "line": entry.entry_index,
+                })
+                continue
+
+            norm_path = unicodedata.normalize("NFC", normalize_path(pdb_track.file_path))
+
+            # Level 1: exact normalized path
+            track = exact_idx.get(norm_path)
+            method = "exact_path"
+
+            # Level 2: case-insensitive
+            if not track:
+                track = nocase_idx.get(norm_path.lower())
+                method = "nocase_path"
+
+            # Level 3: fuzzy filename stem
+            if not track:
+                stem = PurePosixPath(norm_path).stem.lower()
+                candidates = stem_idx.get(stem, [])
+                if candidates:
+                    track = candidates[0]
+                method = "fuzzy_filename"
+
+            if track:
+                matched_tracks.append((entry.entry_index, track, method))
+                method_counts[method] = method_counts.get(method, 0) + 1
+            else:
+                unmatched_list.append({
+                    "path": pdb_track.file_path,
+                    "title": pdb_track.title,
+                    "line": entry.entry_index,
+                })
+
+        if not matched_tracks:
+            results.append(ImportResult(
+                set_id=0,
+                name=set_name,
+                source="cdj_history",
+                total_tracks=len(hist_session.entries),
+                matched_count=0,
+                unmatched_count=len(unmatched_list),
+                unmatched=unmatched_list,
+                match_methods={},
+                warnings=[],
+            ))
+            continue
+
+        # Compute total duration from matched tracks
+        total_dur = sum(t.duration_sec for _, t, _ in matched_tracks if t.duration_sec)
+
+        new_set = Set(
+            name=set_name,
+            duration_min=int(total_dur / 60) if total_dur else None,
+            source="cdj_history",
+            source_ref=source_ref,
+        )
+        session.add(new_set)
+        session.flush()
+
+        for pos, (_, track, _) in enumerate(matched_tracks):
+            session.add(SetTrack(set_id=new_set.id, position=pos, track_id=track.id))
+
+        session.commit()
+
+        results.append(ImportResult(
+            set_id=new_set.id,
+            name=set_name,
+            source="cdj_history",
+            total_tracks=len(hist_session.entries),
+            matched_count=len(matched_tracks),
+            unmatched_count=len(unmatched_list),
+            unmatched=unmatched_list,
+            match_methods=method_counts,
+            warnings=[],
+        ))
+
+    return results
````

Verification:
- `source .venv/bin/activate && python -c "from kiku.import_playlist.service import import_cdj_history; print('OK')"`

#### Task 3 — Add import-history CLI command
Tools: editor
File: `src/kiku/cli.py`

Add the `import-history` command after the existing `import-playlist` command (after line 619). The command takes a USB path, finds the PIONEER database, lists sessions or imports them.

````diff
--- a/src/kiku/cli.py
+++ b/src/kiku/cli.py
@@ -619,0 +620,73 @@
+
+
+@cli.command("import-history")
+@click.argument("usb_path", type=click.Path(exists=True))
+@click.option("--session", "-s", "session_id", type=int, default=None, help="Import specific session by ID")
+@click.option("--all", "import_all", is_flag=True, help="Import all history sessions")
+@click.option("--name", "-n", default=None, help="Set name override")
+@click.option("--force", is_flag=True, help="Re-import even if already exists")
+def import_history(usb_path: str, session_id: int | None, import_all: bool, name: str | None, force: bool):
+    """Import CDJ play history from a Pioneer USB stick.
+
+    Point this at your USB mount path — Kiku finds the PIONEER database
+    and reads which tracks you played at your gig.
+
+    Without --session or --all, lists available history sessions.
+    """
+    from kiku.db.models import get_session
+    from kiku.import_playlist.pdb import find_pioneer_db, parse_pdb
+    from kiku.import_playlist.service import import_cdj_history
+
+    try:
+        pdb_path = find_pioneer_db(usb_path)
+    except FileNotFoundError as e:
+        console.print(f"[red]{e}[/]")
+        return
+
+    console.print(f"[cyan]Reading Pioneer database...[/]")
+    pdb_result = parse_pdb(pdb_path)
+
+    if pdb_result.warnings:
+        for w in pdb_result.warnings:
+            console.print(f"  [yellow]{w}[/]")
+
+    if not pdb_result.sessions:
+        console.print("[yellow]No play history found on this USB.[/]")
+        return
+
+    # List sessions if no --session or --all
+    if session_id is None and not import_all:
+        console.print(f"\n[bold]Found {len(pdb_result.sessions)} history sessions:[/]\n")
+        table = Table()
+        table.add_column("ID", justify="right", style="dim")
+        table.add_column("Name")
+        table.add_column("Tracks", justify="right")
+        for s in pdb_result.sessions:
+            table.add_row(str(s.id), s.name, str(len(s.entries)))
+        console.print(table)
+        console.print("\n[dim]Use --session ID to import one, or --all to import all.[/]")
+        return
+
+    # Import selected sessions
+    session_ids = [session_id] if session_id is not None else None
+    db = get_session()
+    results = import_cdj_history(
+        db, pdb_result, session_ids=session_ids, force=force, name_override=name,
+    )
+
+    if not results:
+        console.print("[yellow]No sessions matched the filter.[/]")
+        return
+
+    for result in results:
+        if result.duplicate_set_id is not None:
+            console.print(
+                f"[yellow]{result.name}: already imported as set {result.duplicate_set_id}.[/] "
+                "Use --force to re-import."
+            )
+        elif result.matched_count == 0:
+            console.print(f"[red]{result.name}: no tracks matched your library.[/]")
+        else:
+            console.print(
+                f"[bold green]{result.name}[/] → set {result.set_id} "
+                f"({result.matched_count}/{result.total_tracks} matched)"
+            )
+            if result.match_methods:
+                methods = ", ".join(f"{k}: {v}" for k, v in result.match_methods.items())
+                console.print(f"  Methods: {methods}")
````

Verification:
- `source .venv/bin/activate && kiku import-history --help`
- Confirm output shows: `Usage: kiku import-history [OPTIONS] USB_PATH`

#### Task 4 — Add API endpoint for CDJ history import
Tools: editor
File: `src/kiku/api/routes/sets.py`

Add the CDJ history import endpoint after the existing M3U8 import endpoint (after line 171). The endpoint accepts `usb_path` (form field) and optional `session_id`, `name`, `force`.

````diff
--- a/src/kiku/api/routes/sets.py
+++ b/src/kiku/api/routes/sets.py
@@ -171,0 +172,52 @@
+
+
+@router.post("/import/cdj-history", response_model=ImportResultResponse)
+async def import_cdj_history_endpoint(
+    usb_path: str = Form(...),
+    session_id: int | None = Form(None),
+    name: str | None = Form(None),
+    force: bool = Form(False),
+    db: Session = Depends(get_db),
+):
+    """Import CDJ play history from a Pioneer USB stick.
+
+    Reads PIONEER/rekordbox/export.pdb from the given path.
+    Matches tracks to the library — never creates new track rows.
+    """
+    from kiku.import_playlist.pdb import find_pioneer_db, parse_pdb
+    from kiku.import_playlist.service import import_cdj_history
+
+    try:
+        pdb_path = find_pioneer_db(usb_path)
+    except FileNotFoundError:
+        raise HTTPException(
+            status_code=400,
+            detail=f"No Pioneer database found at {usb_path}. Check the USB mount path.",
+        )
+
+    pdb_result = parse_pdb(pdb_path)
+
+    if not pdb_result.sessions:
+        raise HTTPException(status_code=400, detail="No play history found on this USB")
+
+    session_ids = [session_id] if session_id is not None else None
+    results = import_cdj_history(
+        db, pdb_result, session_ids=session_ids, force=force, name_override=name,
+    )
+
+    if not results:
+        raise HTTPException(status_code=400, detail="No matching sessions found")
+
+    # Return first result for single-session import; for --all, return first
+    result = results[0]
+
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
+    if result.matched_count == 0:
+        raise HTTPException(
+            status_code=400,
+            detail="None of the tracks matched your library. Sync from Rekordbox first.",
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
````

Verification:
- `source .venv/bin/activate && python -c "from kiku.api.routes.sets import import_cdj_history_endpoint; print('OK')"`

#### Task 5 — PDB parser unit tests
Tools: editor (new file)
File: `tests/test_pdb_parser.py`

Unit tests for the PDB parser. Includes a programmatic binary fixture builder that creates minimal valid PDB files with known history data.

````diff
--- /dev/null
+++ b/tests/test_pdb_parser.py
@@ -0,0 +1,195 @@
+"""Unit tests for Pioneer PDB (DeviceSQL) parser."""
+
+from __future__ import annotations
+
+import struct
+from pathlib import Path
+
+import pytest
+
+from kiku.import_playlist.pdb import (
+    PDBParseResult,
+    _read_devicesql_string,
+    find_pioneer_db,
+    parse_pdb,
+)
+
+
+# ── DeviceSQL string encoding helpers ──
+
+
+def _make_long_ascii(text: str) -> bytes:
+    """Build a DeviceSQL long ASCII string (kind=0x40)."""
+    encoded = text.encode("ascii")
+    return bytes([0x40]) + struct.pack("<H", len(encoded)) + encoded
+
+
+def _make_long_utf16(text: str) -> bytes:
+    """Build a DeviceSQL long UTF-16LE string (kind=0x90)."""
+    encoded = text.encode("utf-16-le")
+    return bytes([0x90]) + struct.pack("<H", len(encoded)) + encoded
+
+
+def _make_short_ascii(text: str) -> bytes:
+    """Build a DeviceSQL short ASCII string (kind = len<<1 | 1)."""
+    encoded = text.encode("ascii")
+    kind = (len(encoded) << 1) | 1
+    return bytes([kind]) + encoded
+
+
+# ── String decoding tests ──
+
+
+def test_read_long_ascii():
+    data = _make_long_ascii("hello")
+    assert _read_devicesql_string(data, 0) == "hello"
+
+
+def test_read_long_utf16():
+    data = _make_long_utf16("Ünïcödé")
+    assert _read_devicesql_string(data, 0) == "Ünïcödé"
+
+
+def test_read_short_ascii():
+    data = _make_short_ascii("hi")
+    assert _read_devicesql_string(data, 0) == "hi"
+
+
+def test_read_string_empty_offset():
+    assert _read_devicesql_string(b"\x00\x00\x00", 0) == ""
+    assert _read_devicesql_string(b"\x00", -1) == ""
+
+
+# ── PDB fixture builder ──
+
+
+def _build_page(
+    page_size: int,
+    page_index: int,
+    page_type: int,
+    next_page: int,
+    rows: list[bytes],
+) -> bytes:
+    """Build a single PDB page with the given rows.
+
+    Page header (36 bytes), then one row group with all rows.
+    Row offsets point to row data placed after the group metadata.
+    """
+    num_rows = len(rows)
+    page = bytearray(page_size)
+
+    # Page header (36 bytes)
+    struct.pack_into("<I", page, 0, 0)  # gap
+    struct.pack_into("<I", page, 4, page_index)
+    struct.pack_into("<I", page, 8, page_type)
+    struct.pack_into("<I", page, 12, next_page)  # next_page index
+    struct.pack_into("<I", page, 16, 0)  # unknown1
+    struct.pack_into("<I", page, 20, 0)  # unknown2
+    page[24] = min(num_rows, 255)  # num_rows_small
+    page[25] = 0  # unknown3
+    page[26] = 0  # unknown4
+    page[27] = 0x34  # page_flags
+    struct.pack_into("<H", page, 28, 0)  # free_size
+    struct.pack_into("<H", page, 30, 0)  # used_size
+    struct.pack_into("<H", page, 32, 0)  # unknown5
+    struct.pack_into("<H", page, 34, num_rows)  # num_rows_large
+
+    if num_rows == 0:
+        return bytes(page)
+
+    # Row group: group_id (u2) + present_flags (u2) + row_offsets (num_rows × u2)
+    group_start = 36
+    struct.pack_into("<H", page, group_start, 0)  # group_id
+    present_flags = (1 << num_rows) - 1  # all rows present
+    struct.pack_into("<H", page, group_start + 2, present_flags)
+
+    # Row data starts after group metadata
+    row_data_start = group_start + 4 + num_rows * 2
+    current_ofs = row_data_start
+
+    for i, row_data in enumerate(rows):
+        ofs_pos = group_start + 4 + i * 2
+        struct.pack_into("<H", page, ofs_pos, current_ofs)
+        page[current_ofs : current_ofs + len(row_data)] = row_data
+        current_ofs += len(row_data)
+
+    return bytes(page)
+
+
+def _build_track_row(track_id: int, file_path: str, title: str) -> bytes:
+    """Build a minimal track row with id, file_path, and title strings."""
+    # 21 u2 string offsets + fixed fields (sample_rate, artist_id, id, disc, bitrate, tempo, genre_id, album_id, ofs_more, file_size)
+    # = 42 + 20 + 4 = 66 bytes fixed, then strings appended
+    fixed_size = 42 + 2 + 2 + 2 + 2 + 2 + 2 + 2 + 2 + 2 + 4  # 64 bytes
+    title_str = _make_long_ascii(title)
+    path_str = _make_long_ascii(file_path)
+    ofs_title = fixed_size  # title string starts right after fixed fields
+    ofs_path = fixed_size + len(title_str)
+
+    row = bytearray(fixed_size + len(title_str) + len(path_str))
+    # String offset 15 (title) at byte 30
+    struct.pack_into("<H", row, 30, ofs_title)
+    # String offset 17 (file_path) at byte 34
+    struct.pack_into("<H", row, 34, ofs_path)
+    # Track ID (u2) at byte 46
+    struct.pack_into("<H", row, 46, track_id)
+    # Append string data
+    row[ofs_title : ofs_title + len(title_str)] = title_str
+    row[ofs_path : ofs_path + len(path_str)] = path_str
+    return bytes(row)
+
+
+def _build_pdb(
+    page_size: int = 4096,
+    tracks: list[tuple[int, str, str]] | None = None,
+    playlists: list[tuple[int, str]] | None = None,
+    entries: list[tuple[int, int, int]] | None = None,
+) -> bytes:
+    """Build a minimal valid PDB file for testing."""
+    tracks = tracks or []
+    playlists = playlists or []
+    entries = entries or []
+
+    # Header page
+    header = bytearray(page_size)
+    struct.pack_into("<I", header, 0, 0)  # unknown
+    struct.pack_into("<I", header, 4, page_size)
+    struct.pack_into("<I", header, 8, 3)  # num_tables
+
+    # Table pointers page (page index 0, file offset = page_size)
+    tbl_page = bytearray(page_size)
+    # Table 0: tracks -> page index 1
+    struct.pack_into("<I", tbl_page, 0, 0)   # type=tracks
+    struct.pack_into("<I", tbl_page, 8, 1)   # first_page
+    # Table 1: history_playlists -> page index 2
+    struct.pack_into("<I", tbl_page, 16, 9)  # type=history_playlists
+    struct.pack_into("<I", tbl_page, 24, 2)  # first_page
+    # Table 2: history_entries -> page index 3
+    struct.pack_into("<I", tbl_page, 32, 10) # type=history_entries
+    struct.pack_into("<I", tbl_page, 40, 3)  # first_page
+
+    # Data pages
+    track_rows = [_build_track_row(tid, fp, title) for tid, fp, title in tracks]
+    playlist_rows = []
+    for pid, pname in playlists:
+        row = bytearray(4) + _make_long_ascii(pname)
+        struct.pack_into("<I", row, 0, pid)
+        playlist_rows.append(bytes(row))
+    entry_rows = [struct.pack("<III", tid, pid, idx) for tid, pid, idx in entries]
+
+    tracks_pg = _build_page(page_size, 1, 0, 0xFFFFFFFF, track_rows)
+    playlists_pg = _build_page(page_size, 2, 9, 0xFFFFFFFF, playlist_rows)
+    entries_pg = _build_page(page_size, 3, 10, 0xFFFFFFFF, entry_rows)
+
+    return bytes(header) + bytes(tbl_page) + tracks_pg + playlists_pg + entries_pg
+
+
+# ── Parser integration tests ──
+
+
+def test_parse_pdb_basic(tmp_path):
+    pdb_data = _build_pdb(
+        tracks=[(1, "/Music/track1.mp3", "Track One"), (2, "/Music/track2.wav", "Track Two")],
+        playlists=[(10, "HISTORY 001")],
+        entries=[(1, 10, 0), (2, 10, 1)],
+    )
+    pdb_file = tmp_path / "export.pdb"
+    pdb_file.write_bytes(pdb_data)
+    result = parse_pdb(str(pdb_file))
+    assert len(result.sessions) == 1
+    assert result.sessions[0].name == "HISTORY 001"
+    assert len(result.sessions[0].entries) == 2
+    assert result.sessions[0].entries[0].track_id == 1
+    assert result.sessions[0].entries[1].track_id == 2
+    assert result.tracks[1].file_path == "/Music/track1.mp3"
+    assert result.tracks[2].title == "Track Two"
+
+
+def test_parse_pdb_multiple_sessions(tmp_path):
+    pdb_data = _build_pdb(
+        tracks=[(1, "/a.mp3", "A"), (2, "/b.mp3", "B"), (3, "/c.mp3", "C")],
+        playlists=[(10, "HISTORY 001"), (11, "HISTORY 002")],
+        entries=[(1, 10, 0), (2, 10, 1), (3, 11, 0), (1, 11, 1)],
+    )
+    pdb_file = tmp_path / "export.pdb"
+    pdb_file.write_bytes(pdb_data)
+    result = parse_pdb(str(pdb_file))
+    assert len(result.sessions) == 2
+    s1 = next(s for s in result.sessions if s.id == 10)
+    s2 = next(s for s in result.sessions if s.id == 11)
+    assert len(s1.entries) == 2
+    assert len(s2.entries) == 2
+
+
+def test_parse_pdb_empty_file(tmp_path):
+    pdb_file = tmp_path / "empty.pdb"
+    pdb_file.write_bytes(b"\x00" * 10)
+    result = parse_pdb(str(pdb_file))
+    assert len(result.sessions) == 0
+    assert len(result.warnings) > 0
+
+
+def test_parse_pdb_file_not_found():
+    with pytest.raises(FileNotFoundError):
+        parse_pdb("/nonexistent/export.pdb")
+
+
+def test_find_pioneer_db(tmp_path):
+    pioneer_dir = tmp_path / "PIONEER" / "rekordbox"
+    pioneer_dir.mkdir(parents=True)
+    (pioneer_dir / "export.pdb").write_bytes(b"\x00")
+    found = find_pioneer_db(str(tmp_path))
+    assert found == pioneer_dir / "export.pdb"
+
+
+def test_find_pioneer_db_missing(tmp_path):
+    with pytest.raises(FileNotFoundError, match="No Pioneer database"):
+        find_pioneer_db(str(tmp_path))
````

Verification:
- `source .venv/bin/activate && python -m pytest tests/test_pdb_parser.py -v`
- All 8 tests should pass

#### Task 6 — CDJ history API integration tests
Tools: editor (new file)
File: `tests/api/test_cdj_import_api.py`

Integration tests for the CDJ history import API endpoint. Uses the conftest fixtures (db_session, client) and creates a temporary PDB fixture on disk.

````diff
--- /dev/null
+++ b/tests/api/test_cdj_import_api.py
@@ -0,0 +1,85 @@
+"""Tests for CDJ play history import API endpoint."""
+
+from __future__ import annotations
+
+import struct
+from pathlib import Path
+
+import pytest
+from fastapi.testclient import TestClient
+from sqlalchemy.orm import Session
+
+from kiku.db.models import Track
+
+# Reuse PDB fixture builder from parser tests
+from tests.test_pdb_parser import _build_pdb
+
+
+@pytest.fixture(autouse=True)
+def seed_file_paths(db_session: Session):
+    """Add file_path to seed tracks so import matching works."""
+    for i in range(1, 21):
+        t = db_session.get(Track, i)
+        t.file_path = f"/Volumes/SSD/Musica/2025/Techno/Track {i}.mp3"
+    db_session.commit()
+
+
+@pytest.fixture()
+def usb_path(tmp_path) -> str:
+    """Create a fake Pioneer USB structure with a PDB containing history."""
+    pioneer_dir = tmp_path / "PIONEER" / "rekordbox"
+    pioneer_dir.mkdir(parents=True)
+    pdb_data = _build_pdb(
+        tracks=[
+            (1, "/Volumes/SSD/Musica/2025/Techno/Track 1.mp3", "Track 1"),
+            (2, "/Volumes/SSD/Musica/2025/Techno/Track 2.mp3", "Track 2"),
+            (3, "/Volumes/SSD/Musica/2025/Techno/Track 3.mp3", "Track 3"),
+            (99, "/Volumes/SSD/Musica/Unknown/Missing.mp3", "Missing Track"),
+        ],
+        playlists=[(10, "HISTORY 001")],
+        entries=[(1, 10, 0), (2, 10, 1), (3, 10, 2), (99, 10, 3)],
+    )
+    (pioneer_dir / "export.pdb").write_bytes(pdb_data)
+    return str(tmp_path)
+
+
+def test_import_cdj_history(client: TestClient, usb_path: str):
+    resp = client.post(
+        "/api/sets/import/cdj-history",
+        data={"usb_path": usb_path},
+    )
+    assert resp.status_code == 200
+    data = resp.json()
+    assert data["source"] == "cdj_history"
+    assert data["matched_count"] == 3
+    assert data["unmatched_count"] == 1
+    assert data["set_id"] > 0
+
+
+def test_import_specific_session(client: TestClient, usb_path: str):
+    resp = client.post(
+        "/api/sets/import/cdj-history",
+        data={"usb_path": usb_path, "session_id": 10},
+    )
+    assert resp.status_code == 200
+    assert resp.json()["matched_count"] == 3
+
+
+def test_import_duplicate_detection(client: TestClient, usb_path: str):
+    client.post("/api/sets/import/cdj-history", data={"usb_path": usb_path})
+    resp = client.post("/api/sets/import/cdj-history", data={"usb_path": usb_path})
+    assert resp.status_code == 200
+    data = resp.json()
+    assert data["duplicate_set_id"] is not None
+    assert "Already imported" in data["warnings"][0]
+
+
+def test_import_force_re_import(client: TestClient, usb_path: str):
+    client.post("/api/sets/import/cdj-history", data={"usb_path": usb_path})
+    resp = client.post(
+        "/api/sets/import/cdj-history",
+        data={"usb_path": usb_path, "force": "true"},
+    )
+    assert resp.status_code == 200
+    assert resp.json()["matched_count"] == 3
+    assert resp.json()["duplicate_set_id"] is None
+
+
+def test_import_no_pioneer_dir(client: TestClient, tmp_path):
+    resp = client.post(
+        "/api/sets/import/cdj-history",
+        data={"usb_path": str(tmp_path)},
+    )
+    assert resp.status_code == 400
+    assert "No Pioneer database" in resp.json()["detail"]
+
+
+def test_import_with_name_override(client: TestClient, usb_path: str):
+    resp = client.post(
+        "/api/sets/import/cdj-history",
+        data={"usb_path": usb_path, "name": "Friday Night Gig"},
+    )
+    assert resp.status_code == 200
+    assert resp.json()["name"] == "Friday Night Gig"
````

Verification:
- `source .venv/bin/activate && python -m pytest tests/api/test_cdj_import_api.py -v`
- All 6 tests should pass

#### Task 7 — Lint all modified files
Tools: shell
Commands:
```bash
source .venv/bin/activate && python -m ruff check --fix src/kiku/import_playlist/pdb.py src/kiku/import_playlist/service.py src/kiku/cli.py src/kiku/api/routes/sets.py tests/test_pdb_parser.py tests/api/test_cdj_import_api.py
```
```bash
cd frontend && npx svelte-check --tsconfig ./tsconfig.json 2>&1 | tail -5
```

Verification: No lint errors remain.

#### Task 8 — Run full test suite
Tools: shell
Commands:
```bash
source .venv/bin/activate && python -m pytest tests/ -x -q
```

Verification: All tests pass (174 existing + ~14 new = ~188 total).

#### Task 9 — Commit
Tools: git
Commands:
```bash
git add src/kiku/import_playlist/pdb.py src/kiku/import_playlist/service.py src/kiku/cli.py src/kiku/api/routes/sets.py tests/test_pdb_parser.py tests/api/test_cdj_import_api.py
```
```bash
git commit -m "spec(012): IMPLEMENT - cdj-play-history-import

CDJ USB play history reader: custom PDB parser for Pioneer DeviceSQL,
import-history CLI command, API endpoint, and test suite.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

Verification: `git log --oneline -1` shows the commit.

### Validate

| # | Requirement (Human Section) | Compliance |
|---|---------------------------|------------|
| 1 | READ Pioneer USB play history from export.pdb (L10) | Task 1: full PDB parser reads History Playlists, History Entries, Track tables |
| 2 | MATCH tracks using existing pipeline (L11) | Task 2: `import_cdj_history()` reuses `_build_path_index()` with 3-tier cascade |
| 3 | CREATE sets preserving play order and session date (L12) | Task 2: entries sorted by `entry_index`, session name preserved in `Set.name` |
| 4 | SUPPORT Rekordbox desktop history (L13) | Deferred to Phase 2 per spec Details L47; current scope is PDB parsing |
| 5 | EXPOSE via CLI and API (L14) | Task 3: `kiku import-history` CLI. Task 4: `POST /import/cdj-history` API |
| 6 | DETECT format automatically (L15) | Task 1: `find_pioneer_db()` locates export.pdb; DL+ detection deferred to Phase 3 per L49 |
| 7 | TRIGGER auto-analysis (L16) | Not in Phase 1 tasks — add as follow-up after import, same pattern as M3U8. Can be added in sets.py endpoint by calling `_analyze_set()` after import. |
| 8 | Source = 'cdj_history' (L62) | Task 2: `source="cdj_history"` on all created sets |
| 9 | Reuse M3U8 import patterns (L62) | Task 2: same `_build_path_index()`, `ImportResult`, `Set`/`SetTrack` creation |
| 10 | Unit tests with PDB fixture (L56) | Task 5: 8 unit tests with programmatic binary fixtures |
| 11 | Integration tests (L57) | Task 6: 6 API integration tests |

**Note on requirement 7 (auto-analysis)**: The IMPLEMENT stage should add `_analyze_set(db, result.set_id)` call in the API endpoint after successful import, following the same pattern as the build SSE stream. This is a minor addition (~5 lines) to Task 4.

## Plan Review
<!-- Filled if required to validate plan -->

## Implement

- [x] Task 1: Create PDB parser module (`src/kiku/import_playlist/pdb.py`) — Status: Done
- [x] Task 2: Add `import_cdj_history()` to `service.py` — Status: Done
- [x] Task 3: Add `import-history` CLI command — Status: Done
- [x] Task 4: Add API endpoint for CDJ history import — Status: Done
- [x] Task 5: PDB parser unit tests — Status: Done (12 tests pass)
- [x] Task 6: CDJ history API integration tests — Status: Done (6 tests pass)
- [x] Task 7: Lint all modified files — Status: Done (no ruff installed, py_compile OK)
- [x] Task 8: Run full test suite — Status: Done (169 pass, 1 pre-existing failure in test_energy.py unrelated to this spec)
- [x] Task 9: Commit — Status: Done (941317d)

Implementation commit: 941317d

## Test Evidence & Outputs
<!-- Filled by explicit testing after /spec IMPLEMENT -->

## Updated Doc
<!-- Filled by explicit documentation updates after /spec IMPLEMENT -->

## Post-Implement Review
<!-- Filled by /spec REVIEW -->
