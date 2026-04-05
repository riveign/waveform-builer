"""Unit tests for Pioneer PDB (DeviceSQL) parser."""

from __future__ import annotations

import struct
from pathlib import Path

import pytest

from kiku.import_playlist.pdb import (
    PDBParseResult,
    _read_devicesql_string,
    find_pioneer_db,
    parse_pdb,
)


# ── DeviceSQL string encoding helpers ──


def _make_long_ascii(text: str) -> bytes:
    """Build a DeviceSQL long ASCII string (kind=0x40)."""
    encoded = text.encode("ascii")
    return bytes([0x40]) + struct.pack("<H", len(encoded)) + encoded


def _make_long_utf16(text: str) -> bytes:
    """Build a DeviceSQL long UTF-16LE string (kind=0x90)."""
    encoded = text.encode("utf-16-le")
    return bytes([0x90]) + struct.pack("<H", len(encoded)) + encoded


def _make_short_ascii(text: str) -> bytes:
    """Build a DeviceSQL short ASCII string (kind = len<<1 | 1)."""
    encoded = text.encode("ascii")
    kind = (len(encoded) << 1) | 1
    return bytes([kind]) + encoded


# ── String decoding tests ──


def test_read_long_ascii():
    data = _make_long_ascii("hello")
    assert _read_devicesql_string(data, 0) == "hello"


def test_read_long_utf16():
    data = _make_long_utf16("Ünïcödé")
    assert _read_devicesql_string(data, 0) == "Ünïcödé"


def test_read_short_ascii():
    data = _make_short_ascii("hi")
    assert _read_devicesql_string(data, 0) == "hi"


def test_read_string_empty_offset():
    assert _read_devicesql_string(b"\x00\x00\x00", 0) == ""
    assert _read_devicesql_string(b"\x00", -1) == ""


# ── PDB fixture builder ──


def _build_page(
    page_size: int,
    page_index: int,
    page_type: int,
    next_page: int,
    rows: list[bytes],
) -> bytes:
    """Build a single PDB page with the given rows.

    Page header (36 bytes), then one row group with all rows.
    Row offsets point to row data placed after the group metadata.
    """
    num_rows = len(rows)
    page = bytearray(page_size)

    # Page header (36 bytes)
    struct.pack_into("<I", page, 0, 0)  # gap
    struct.pack_into("<I", page, 4, page_index)
    struct.pack_into("<I", page, 8, page_type)
    struct.pack_into("<I", page, 12, next_page)  # next_page index
    struct.pack_into("<I", page, 16, 0)  # unknown1
    struct.pack_into("<I", page, 20, 0)  # unknown2
    page[24] = min(num_rows, 255)  # num_rows_small
    page[25] = 0  # unknown3
    page[26] = 0  # unknown4
    page[27] = 0x34  # page_flags
    struct.pack_into("<H", page, 28, 0)  # free_size
    struct.pack_into("<H", page, 30, 0)  # used_size
    struct.pack_into("<H", page, 32, 0)  # unknown5
    struct.pack_into("<H", page, 34, num_rows)  # num_rows_large

    if num_rows == 0:
        return bytes(page)

    # Row group: group_id (u2) + present_flags (u2) + row_offsets (num_rows x u2)
    group_start = 36
    struct.pack_into("<H", page, group_start, 0)  # group_id
    present_flags = (1 << num_rows) - 1  # all rows present
    struct.pack_into("<H", page, group_start + 2, present_flags)

    # Row data starts after group metadata
    row_data_start = group_start + 4 + num_rows * 2
    current_ofs = row_data_start

    for i, row_data in enumerate(rows):
        ofs_pos = group_start + 4 + i * 2
        struct.pack_into("<H", page, ofs_pos, current_ofs)
        page[current_ofs : current_ofs + len(row_data)] = row_data
        current_ofs += len(row_data)

    return bytes(page)


def _build_track_row(track_id: int, file_path: str, title: str) -> bytes:
    """Build a minimal track row with id, file_path, and title strings."""
    # 21 u2 string offsets + fixed fields
    fixed_size = 42 + 2 + 2 + 2 + 2 + 2 + 2 + 2 + 2 + 2 + 4  # 64 bytes
    title_str = _make_long_ascii(title)
    path_str = _make_long_ascii(file_path)
    ofs_title = fixed_size  # title string starts right after fixed fields
    ofs_path = fixed_size + len(title_str)

    row = bytearray(fixed_size + len(title_str) + len(path_str))
    # String offset 15 (title) at byte 30
    struct.pack_into("<H", row, 30, ofs_title)
    # String offset 17 (file_path) at byte 34
    struct.pack_into("<H", row, 34, ofs_path)
    # Track ID (u2) at byte 46
    struct.pack_into("<H", row, 46, track_id)
    # Append string data
    row[ofs_title : ofs_title + len(title_str)] = title_str
    row[ofs_path : ofs_path + len(path_str)] = path_str
    return bytes(row)


def _build_pdb(
    page_size: int = 4096,
    tracks: list[tuple[int, str, str]] | None = None,
    playlists: list[tuple[int, str]] | None = None,
    entries: list[tuple[int, int, int]] | None = None,
) -> bytes:
    """Build a minimal valid PDB file for testing."""
    tracks = tracks or []
    playlists = playlists or []
    entries = entries or []

    # Header page
    header = bytearray(page_size)
    struct.pack_into("<I", header, 0, 0)  # unknown
    struct.pack_into("<I", header, 4, page_size)
    struct.pack_into("<I", header, 8, 3)  # num_tables

    # Table pointers page (page index 0, file offset = page_size)
    tbl_page = bytearray(page_size)
    # Table 0: tracks -> page index 1
    struct.pack_into("<I", tbl_page, 0, 0)   # type=tracks
    struct.pack_into("<I", tbl_page, 8, 1)   # first_page
    # Table 1: history_playlists -> page index 2
    struct.pack_into("<I", tbl_page, 16, 9)  # type=history_playlists
    struct.pack_into("<I", tbl_page, 24, 2)  # first_page
    # Table 2: history_entries -> page index 3
    struct.pack_into("<I", tbl_page, 32, 10)  # type=history_entries
    struct.pack_into("<I", tbl_page, 40, 3)   # first_page

    # Data pages
    track_rows = [_build_track_row(tid, fp, title) for tid, fp, title in tracks]
    playlist_rows = []
    for pid, pname in playlists:
        row = bytearray(4) + _make_long_ascii(pname)
        struct.pack_into("<I", row, 0, pid)
        playlist_rows.append(bytes(row))
    entry_rows = [struct.pack("<III", tid, pid, idx) for tid, pid, idx in entries]

    tracks_pg = _build_page(page_size, 1, 0, 0xFFFFFFFF, track_rows)
    playlists_pg = _build_page(page_size, 2, 9, 0xFFFFFFFF, playlist_rows)
    entries_pg = _build_page(page_size, 3, 10, 0xFFFFFFFF, entry_rows)

    return bytes(header) + bytes(tbl_page) + tracks_pg + playlists_pg + entries_pg


# ── Parser integration tests ──


def test_parse_pdb_basic(tmp_path):
    pdb_data = _build_pdb(
        tracks=[(1, "/Music/track1.mp3", "Track One"), (2, "/Music/track2.wav", "Track Two")],
        playlists=[(10, "HISTORY 001")],
        entries=[(1, 10, 0), (2, 10, 1)],
    )
    pdb_file = tmp_path / "export.pdb"
    pdb_file.write_bytes(pdb_data)
    result = parse_pdb(str(pdb_file))
    assert len(result.sessions) == 1
    assert result.sessions[0].name == "HISTORY 001"
    assert len(result.sessions[0].entries) == 2
    assert result.sessions[0].entries[0].track_id == 1
    assert result.sessions[0].entries[1].track_id == 2
    assert result.tracks[1].file_path == "/Music/track1.mp3"
    assert result.tracks[2].title == "Track Two"


def test_parse_pdb_multiple_sessions(tmp_path):
    pdb_data = _build_pdb(
        tracks=[(1, "/a.mp3", "A"), (2, "/b.mp3", "B"), (3, "/c.mp3", "C")],
        playlists=[(10, "HISTORY 001"), (11, "HISTORY 002")],
        entries=[(1, 10, 0), (2, 10, 1), (3, 11, 0), (1, 11, 1)],
    )
    pdb_file = tmp_path / "export.pdb"
    pdb_file.write_bytes(pdb_data)
    result = parse_pdb(str(pdb_file))
    assert len(result.sessions) == 2
    s1 = next(s for s in result.sessions if s.id == 10)
    s2 = next(s for s in result.sessions if s.id == 11)
    assert len(s1.entries) == 2
    assert len(s2.entries) == 2


def test_parse_pdb_empty_file(tmp_path):
    pdb_file = tmp_path / "empty.pdb"
    pdb_file.write_bytes(b"\x00" * 10)
    result = parse_pdb(str(pdb_file))
    assert len(result.sessions) == 0
    assert len(result.warnings) > 0


def test_parse_pdb_file_not_found():
    with pytest.raises(FileNotFoundError):
        parse_pdb("/nonexistent/export.pdb")


def test_find_pioneer_db(tmp_path):
    pioneer_dir = tmp_path / "PIONEER" / "rekordbox"
    pioneer_dir.mkdir(parents=True)
    (pioneer_dir / "export.pdb").write_bytes(b"\x00")
    found = find_pioneer_db(str(tmp_path))
    assert found == pioneer_dir / "export.pdb"


def test_find_pioneer_db_missing(tmp_path):
    with pytest.raises(FileNotFoundError, match="No Pioneer database"):
        find_pioneer_db(str(tmp_path))


def test_parse_pdb_entry_order(tmp_path):
    """Entries within a session should be sorted by entry_index."""
    pdb_data = _build_pdb(
        tracks=[(1, "/a.mp3", "A"), (2, "/b.mp3", "B"), (3, "/c.mp3", "C")],
        playlists=[(10, "HISTORY 001")],
        # Entries out of order
        entries=[(3, 10, 2), (1, 10, 0), (2, 10, 1)],
    )
    pdb_file = tmp_path / "export.pdb"
    pdb_file.write_bytes(pdb_data)
    result = parse_pdb(str(pdb_file))
    indices = [e.entry_index for e in result.sessions[0].entries]
    assert indices == [0, 1, 2]


def test_parse_pdb_no_history(tmp_path):
    """PDB with tracks but no history tables."""
    pdb_data = _build_pdb(
        tracks=[(1, "/a.mp3", "A")],
        playlists=[],
        entries=[],
    )
    pdb_file = tmp_path / "export.pdb"
    pdb_file.write_bytes(pdb_data)
    result = parse_pdb(str(pdb_file))
    assert len(result.sessions) == 0
    assert len(result.tracks) == 1
