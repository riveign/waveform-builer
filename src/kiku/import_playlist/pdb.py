"""Parse Pioneer DeviceSQL (.pdb) files for CDJ play history.

Reads only the tables needed for history import: Track (file paths),
History Playlist (session names), History Entry (track order per session).

Based on the reverse-engineering work by James Elliott (Deep Symmetry),
Henry Betts, and Fabian Lesniak.  Format spec: rekordbox_pdb.ksy
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field
from pathlib import Path

# PDB table type identifiers (from rekordbox_pdb.ksy page_type enum)
TABLE_TRACKS = 0
TABLE_HISTORY_PLAYLISTS = 9
TABLE_HISTORY_ENTRIES = 10


@dataclass
class PDBTrack:
    """Minimal track info from PDB — just enough for library matching."""
    id: int
    file_path: str
    title: str = ""


@dataclass
class PDBHistoryEntry:
    """Single entry in a CDJ play history session."""
    track_id: int
    playlist_id: int
    entry_index: int


@dataclass
class PDBHistorySession:
    """A CDJ play history session (one per USB mount on a CDJ)."""
    id: int
    name: str  # e.g. "HISTORY 001"
    entries: list[PDBHistoryEntry] = field(default_factory=list)


@dataclass
class PDBParseResult:
    """Result of parsing a Pioneer PDB file for history data."""
    sessions: list[PDBHistorySession] = field(default_factory=list)
    tracks: dict[int, PDBTrack] = field(default_factory=dict)  # id -> track
    warnings: list[str] = field(default_factory=list)


def _read_devicesql_string(data: bytes, offset: int) -> str:
    """Decode a DeviceSQL string at the given offset within a data buffer.

    String encoding (first byte = kind):
      0x40: Long ASCII — next 2 bytes = length (u16le), then ASCII data
      0x90: Long UTF-16LE — next 2 bytes = byte length (u16le), then UTF-16LE data
      odd:  Short ASCII — length = kind >> 1, data follows immediately
    """
    if offset < 0 or offset >= len(data):
        return ""
    kind = data[offset]
    if kind == 0x40:
        if offset + 3 > len(data):
            return ""
        length = struct.unpack_from("<H", data, offset + 1)[0]
        start = offset + 3
        end = min(start + length, len(data))
        return data[start:end].decode("ascii", errors="replace").rstrip("\x00")
    if kind == 0x90:
        if offset + 3 > len(data):
            return ""
        byte_len = struct.unpack_from("<H", data, offset + 1)[0]
        start = offset + 3
        end = min(start + byte_len, len(data))
        return data[start:end].decode("utf-16-le", errors="replace").rstrip("\x00")
    if kind & 1:
        length = kind >> 1
        start = offset + 1
        end = min(start + length, len(data))
        return data[start:end].decode("ascii", errors="replace").rstrip("\x00")
    return ""


def _iter_row_offsets(page: bytes) -> list[int]:
    """Extract present row offsets from a single PDB page.

    Page header (36 bytes), then row groups. Each group:
      u2 group_id, u2 present_flags (bitmask), then up to 16 x u2 row offsets.
    Row offsets are page-relative byte positions of row data.
    """
    page_size = len(page)
    if page_size < 36:
        return []
    num_rows_small = page[24]
    num_rows_large = struct.unpack_from("<H", page, 34)[0]
    num_rows = max(num_rows_small, num_rows_large)
    if num_rows == 0:
        return []

    offsets: list[int] = []
    pos = 36  # after page header
    num_groups = (num_rows + 15) // 16

    for g in range(num_groups):
        if pos + 4 > page_size:
            break
        present_flags = struct.unpack_from("<H", page, pos + 2)[0]
        pos += 4  # skip group_id + present_flags

        rows_in_group = min(16, num_rows - g * 16)
        for bit in range(rows_in_group):
            if pos + 2 > page_size:
                break
            row_ofs = struct.unpack_from("<H", page, pos)[0]
            pos += 2
            if present_flags & (1 << bit) and 0 < row_ofs < page_size:
                offsets.append(row_ofs)

    return offsets


def _iter_pages(data: bytes, first_page_idx: int, page_size: int):
    """Iterate through a linked list of PDB pages.

    Page at index I is at file offset page_size * (I + 1).
    Yields page data (bytes) for each page in the chain.
    """
    idx = first_page_idx
    visited: set[int] = set()
    file_len = len(data)

    while idx not in visited and idx != 0xFFFFFFFF:
        visited.add(idx)
        file_ofs = page_size * (idx + 1)
        if file_ofs + page_size > file_len:
            break
        page = data[file_ofs : file_ofs + page_size]
        yield page
        next_idx = struct.unpack_from("<I", page, 12)[0]
        idx = next_idx


def _parse_tracks(data: bytes, first_page: int, page_size: int) -> dict[int, PDBTrack]:
    """Parse Track table rows. Extracts id, file_path, title."""
    tracks: dict[int, PDBTrack] = {}
    for page in _iter_pages(data, first_page, page_size):
        for row_ofs in _iter_row_offsets(page):
            row = page[row_ofs:]
            if len(row) < 64:  # minimum: 21*u2 offsets + fixed fields
                continue
            # String offset indices: title=15 (*2=30), file_path=17 (*2=34)
            ofs_title = struct.unpack_from("<H", row, 30)[0]
            ofs_file_path = struct.unpack_from("<H", row, 34)[0]
            # Track ID (u2) at offset 46 (after 21*u2 + sample_rate + artist_id)
            track_id = struct.unpack_from("<H", row, 46)[0]
            if track_id == 0:
                continue
            file_path = _read_devicesql_string(row, ofs_file_path)
            title = _read_devicesql_string(row, ofs_title)
            tracks[track_id] = PDBTrack(id=track_id, file_path=file_path, title=title)
    return tracks


def _parse_history_playlists(
    data: bytes, first_page: int, page_size: int,
) -> list[PDBHistorySession]:
    """Parse History Playlist table. Each row: id (u4) + name (devicesql string)."""
    sessions: list[PDBHistorySession] = []
    for page in _iter_pages(data, first_page, page_size):
        for row_ofs in _iter_row_offsets(page):
            row = page[row_ofs:]
            if len(row) < 8:
                continue
            playlist_id = struct.unpack_from("<I", row, 0)[0]
            name = _read_devicesql_string(row, 4)
            sessions.append(PDBHistorySession(id=playlist_id, name=name))
    return sessions


def _parse_history_entries(
    data: bytes, first_page: int, page_size: int,
) -> list[PDBHistoryEntry]:
    """Parse History Entry table. Each row: track_id (u4) + playlist_id (u4) + entry_index (u4)."""
    entries: list[PDBHistoryEntry] = []
    for page in _iter_pages(data, first_page, page_size):
        for row_ofs in _iter_row_offsets(page):
            row = page[row_ofs:]
            if len(row) < 12:
                continue
            track_id = struct.unpack_from("<I", row, 0)[0]
            playlist_id = struct.unpack_from("<I", row, 4)[0]
            entry_index = struct.unpack_from("<I", row, 8)[0]
            entries.append(PDBHistoryEntry(track_id, playlist_id, entry_index))
    return entries


def find_pioneer_db(usb_path: str) -> Path:
    """Locate export.pdb within a Pioneer USB directory structure.

    Checks PIONEER/rekordbox/export.pdb relative to the given path.
    Raises FileNotFoundError if no Pioneer database is found.
    """
    root = Path(usb_path)
    pdb = root / "PIONEER" / "rekordbox" / "export.pdb"
    if pdb.exists():
        return pdb
    # Maybe usb_path IS the PIONEER directory
    pdb_alt = root / "rekordbox" / "export.pdb"
    if pdb_alt.exists():
        return pdb_alt
    raise FileNotFoundError(
        f"No Pioneer database found at {usb_path}. "
        "Expected PIONEER/rekordbox/export.pdb on your USB stick."
    )


def parse_pdb(file_path: str | Path) -> PDBParseResult:
    """Parse a Pioneer export.pdb file and extract play history sessions.

    Returns PDBParseResult with history sessions (track play order) and
    a track lookup dict (id -> file_path/title) for library matching.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"PDB file not found: {file_path}")

    data = path.read_bytes()
    result = PDBParseResult()

    if len(data) < 24:
        result.warnings.append("File too small to be a valid PDB")
        return result

    # File header: [unknown u4] [page_size u4] [num_tables u4]
    _, page_size, num_tables = struct.unpack_from("<III", data, 0)

    if page_size == 0 or page_size > 65536:
        result.warnings.append(f"Invalid page size: {page_size}")
        return result

    # Table pointers start at file offset page_size (after header gap)
    # Each entry: type(u4) + empty_candidate(u4) + first_page(u4) + last_page(u4) = 16B
    table_ptrs: dict[int, int] = {}
    for i in range(num_tables):
        ofs = page_size + i * 16
        if ofs + 16 > len(data):
            break
        ttype = struct.unpack_from("<I", data, ofs)[0]
        first_page_idx = struct.unpack_from("<I", data, ofs + 8)[0]
        table_ptrs[ttype] = first_page_idx

    # Parse tracks (needed to resolve history entry track_ids to file_paths)
    if TABLE_TRACKS in table_ptrs:
        result.tracks = _parse_tracks(data, table_ptrs[TABLE_TRACKS], page_size)

    # Parse history playlists (session names)
    if TABLE_HISTORY_PLAYLISTS in table_ptrs:
        result.sessions = _parse_history_playlists(
            data, table_ptrs[TABLE_HISTORY_PLAYLISTS], page_size,
        )
    else:
        result.warnings.append("No history playlists table found in PDB")

    # Parse history entries and attach to sessions
    if TABLE_HISTORY_ENTRIES in table_ptrs:
        entries = _parse_history_entries(
            data, table_ptrs[TABLE_HISTORY_ENTRIES], page_size,
        )
        session_map = {s.id: s for s in result.sessions}
        for entry in entries:
            if entry.playlist_id in session_map:
                session_map[entry.playlist_id].entries.append(entry)
        # Sort entries within each session by play order
        for s in result.sessions:
            s.entries.sort(key=lambda e: e.entry_index)

    return result
