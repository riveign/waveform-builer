"""Tests for M3U8 parser."""

from kiku.import_playlist.m3u8 import parse_m3u8


def test_basic_m3u8():
    content = "#EXTM3U\n#EXTINF:300,Artist - Title\n/music/track.mp3\n"
    result = parse_m3u8(content)
    assert len(result.tracks) == 1
    assert result.tracks[0].title == "Artist - Title"
    assert result.tracks[0].duration_sec == 300


def test_playlist_name_tag():
    content = "#EXTM3U\n#PLAYLIST:My Set\n#EXTINF:120,A\n/a.mp3\n"
    result = parse_m3u8(content)
    assert result.playlist_name == "My Set"


def test_bom_stripped():
    content = "\ufeff#EXTM3U\n#EXTINF:60,Track\n/t.mp3\n"
    result = parse_m3u8(content)
    assert len(result.tracks) == 1


def test_backslash_converted():
    content = "#EXTM3U\n#EXTINF:60,T\nC:\\Music\\track.mp3\n"
    result = parse_m3u8(content)
    assert "\\" not in result.tracks[0].normalized_path


def test_missing_header_warning():
    content = "#EXTINF:60,T\n/t.mp3\n"
    result = parse_m3u8(content)
    assert len(result.tracks) == 1
    assert any("Missing #EXTM3U" in w for w in result.warnings)


def test_malformed_extinf():
    content = "#EXTM3U\n#EXTINF:abc\n/t.mp3\n"
    result = parse_m3u8(content)
    assert len(result.tracks) == 1
    assert result.tracks[0].duration_sec == -1
    assert any("malformed" in w for w in result.warnings)


def test_multiple_tracks():
    content = "#EXTM3U\n"
    for i in range(5):
        content += f"#EXTINF:{60 * (i + 1)},Artist {i} - Track {i}\n/music/track{i}.mp3\n"
    result = parse_m3u8(content)
    assert len(result.tracks) == 5
    assert result.tracks[2].title == "Artist 2 - Track 2"


def test_source_path_sets_default_name():
    content = "#EXTM3U\n#EXTINF:60,T\n/t.mp3\n"
    result = parse_m3u8(content, source_path="/playlists/My Session.m3u8")
    assert result.playlist_name == "My Session"
    assert result.source_path == "/playlists/My Session.m3u8"
