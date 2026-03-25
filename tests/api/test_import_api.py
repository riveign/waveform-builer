"""Tests for M3U8 playlist import API endpoint."""

from __future__ import annotations

import io

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from kiku.db.models import Track


@pytest.fixture(autouse=True)
def seed_file_paths(db_session: Session):
    """Add file_path to seed tracks so import matching works."""
    for i in range(1, 21):
        t = db_session.get(Track, i)
        t.file_path = f"/Volumes/SSD/Musica/2025/Techno/Track {i}.mp3"
    db_session.commit()


def _m3u8_content(paths: list[str], name: str | None = None) -> str:
    lines = ["#EXTM3U"]
    if name:
        lines.append(f"#PLAYLIST:{name}")
    for i, p in enumerate(paths):
        lines.append(f"#EXTINF:300,Artist - Track {i + 1}")
        lines.append(p)
    return "\n".join(lines) + "\n"


def test_import_upload(client: TestClient):
    content = _m3u8_content(
        [f"/Volumes/SSD/Musica/2025/Techno/Track {i}.mp3" for i in range(1, 4)],
        name="Test Import",
    )
    resp = client.post(
        "/api/sets/import/m3u8",
        files={"file": ("test.m3u8", io.BytesIO(content.encode()), "audio/x-mpegurl")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["matched_count"] == 3
    assert data["name"] == "Test Import"
    assert data["source"] == "m3u8"
    assert data["set_id"] > 0


def test_import_with_name_override(client: TestClient):
    content = _m3u8_content(
        ["/Volumes/SSD/Musica/2025/Techno/Track 1.mp3"],
    )
    resp = client.post(
        "/api/sets/import/m3u8",
        files={"file": ("test.m3u8", io.BytesIO(content.encode()), "audio/x-mpegurl")},
        data={"name": "My Custom Name"},
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "My Custom Name"


def test_import_unmatched_tracks(client: TestClient):
    content = _m3u8_content([
        "/Volumes/SSD/Musica/2025/Techno/Track 1.mp3",
        "/Volumes/SSD/Musica/2025/Techno/Nonexistent.mp3",
    ])
    resp = client.post(
        "/api/sets/import/m3u8",
        files={"file": ("test.m3u8", io.BytesIO(content.encode()), "audio/x-mpegurl")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["matched_count"] == 1
    assert data["unmatched_count"] == 1
    assert len(data["unmatched_paths"]) == 1


def test_import_zero_matches(client: TestClient):
    content = _m3u8_content(["/nonexistent/path.mp3"])
    resp = client.post(
        "/api/sets/import/m3u8",
        files={"file": ("test.m3u8", io.BytesIO(content.encode()), "audio/x-mpegurl")},
    )
    assert resp.status_code == 400
    assert "None of the tracks matched" in resp.json()["detail"]


def test_import_duplicate_detection(client: TestClient):
    content = _m3u8_content(
        ["/Volumes/SSD/Musica/2025/Techno/Track 1.mp3"],
    )
    # First import
    resp1 = client.post(
        "/api/sets/import/m3u8",
        files={"file": ("dup.m3u8", io.BytesIO(content.encode()), "audio/x-mpegurl")},
    )
    assert resp1.status_code == 200

    # Second import — duplicate
    resp2 = client.post(
        "/api/sets/import/m3u8",
        files={"file": ("dup.m3u8", io.BytesIO(content.encode()), "audio/x-mpegurl")},
    )
    assert resp2.status_code == 200
    data = resp2.json()
    assert data["duplicate_set_id"] is not None
    assert "Already imported" in data["warnings"][0]


def test_import_force_re_import(client: TestClient):
    content = _m3u8_content(
        ["/Volumes/SSD/Musica/2025/Techno/Track 1.mp3"],
    )
    # First import
    client.post(
        "/api/sets/import/m3u8",
        files={"file": ("force.m3u8", io.BytesIO(content.encode()), "audio/x-mpegurl")},
    )
    # Force re-import
    resp = client.post(
        "/api/sets/import/m3u8",
        files={"file": ("force.m3u8", io.BytesIO(content.encode()), "audio/x-mpegurl")},
        data={"force": "true"},
    )
    assert resp.status_code == 200
    assert resp.json()["matched_count"] == 1
    assert resp.json()["duplicate_set_id"] is None


def test_import_no_file(client: TestClient):
    resp = client.post("/api/sets/import/m3u8")
    assert resp.status_code == 400


def test_import_invalid_format(client: TestClient):
    resp = client.post(
        "/api/sets/import/m3u8",
        files={"file": ("bad.txt", io.BytesIO(b"just some text"), "text/plain")},
    )
    assert resp.status_code == 400
    assert "M3U8" in resp.json()["detail"]
