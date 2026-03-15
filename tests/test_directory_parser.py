"""Tests for directory name parser."""

from kiku.parsing.directory import parse_directory_name, parse_track_path


def test_full_format_with_energy():
    meta = parse_directory_name("09 - 2025 - Rumble Techno Warmup")
    assert meta.genre == "Rumble Techno"
    assert meta.energy == "Warmup"
    assert meta.acquired_month == "2025-09"


def test_full_format_no_energy():
    meta = parse_directory_name("03 - 2024 - Techno")
    assert meta.genre == "Techno"
    assert meta.energy is None
    assert meta.acquired_month == "2024-03"


def test_hardgroove_mid():
    meta = parse_directory_name("06 - 2023 - HardGroove Mid")
    assert meta.genre == "Hard Groove"
    assert meta.energy == "Mid"


def test_multi_word_genre_with_energy():
    meta = parse_directory_name("11 - 2024 - Hard Techno Peak")
    assert meta.genre == "Hard Techno"
    assert meta.energy == "Peak"


def test_energy_low():
    meta = parse_directory_name("01 - 2022 - Dub Techno Low")
    assert meta.genre == "Dub Techno"
    assert meta.energy == "Low"


def test_energy_up():
    meta = parse_directory_name("07 - 2024 - Acid Techno Up")
    assert meta.genre == "Acid Techno"
    assert meta.energy == "Up"


def test_energy_dance():
    meta = parse_directory_name("05 - 2023 - Afro House Dance")
    assert meta.genre == "Afro House"
    assert meta.energy == "Dance"


def test_energy_closing():
    meta = parse_directory_name("12 - 2024 - Deep House Closing")
    assert meta.genre == "Deep House"
    assert meta.energy == "Closing"


def test_no_match():
    meta = parse_directory_name("random_folder")
    assert meta.genre is None
    assert meta.energy is None


def test_parse_track_path():
    path = "/Volumes/SSD/Musica/2025/09 - 2025 - Rumble Techno Warmup/track.mp3"
    meta = parse_track_path(path)
    assert meta.genre == "Rumble Techno"
    assert meta.energy == "Warmup"
    assert meta.acquired_month == "2025-09"
