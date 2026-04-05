"""Tests for CDJ play history import API endpoint."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from kiku.db.models import Track

# Reuse PDB fixture builder from parser tests
from tests.test_pdb_parser import _build_pdb


@pytest.fixture(autouse=True)
def seed_file_paths(db_session: Session):
    """Add file_path to seed tracks so import matching works."""
    for i in range(1, 21):
        t = db_session.get(Track, i)
        t.file_path = f"/Volumes/SSD/Musica/2025/Techno/Track {i}.mp3"
    db_session.commit()


@pytest.fixture()
def usb_path(tmp_path) -> str:
    """Create a fake Pioneer USB structure with a PDB containing history."""
    pioneer_dir = tmp_path / "PIONEER" / "rekordbox"
    pioneer_dir.mkdir(parents=True)
    pdb_data = _build_pdb(
        tracks=[
            (1, "/Volumes/SSD/Musica/2025/Techno/Track 1.mp3", "Track 1"),
            (2, "/Volumes/SSD/Musica/2025/Techno/Track 2.mp3", "Track 2"),
            (3, "/Volumes/SSD/Musica/2025/Techno/Track 3.mp3", "Track 3"),
            (99, "/Volumes/SSD/Musica/Unknown/Missing.mp3", "Missing Track"),
        ],
        playlists=[(10, "HISTORY 001")],
        entries=[(1, 10, 0), (2, 10, 1), (3, 10, 2), (99, 10, 3)],
    )
    (pioneer_dir / "export.pdb").write_bytes(pdb_data)
    return str(tmp_path)


def test_import_cdj_history(client: TestClient, usb_path: str):
    resp = client.post(
        "/api/sets/import/cdj-history",
        data={"usb_path": usb_path},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["source"] == "cdj_history"
    assert data["matched_count"] == 3
    assert data["unmatched_count"] == 1
    assert data["set_id"] > 0


def test_import_specific_session(client: TestClient, usb_path: str):
    resp = client.post(
        "/api/sets/import/cdj-history",
        data={"usb_path": usb_path, "session_id": "10"},
    )
    assert resp.status_code == 200
    assert resp.json()["matched_count"] == 3


def test_import_duplicate_detection(client: TestClient, usb_path: str):
    client.post("/api/sets/import/cdj-history", data={"usb_path": usb_path})
    resp = client.post("/api/sets/import/cdj-history", data={"usb_path": usb_path})
    assert resp.status_code == 200
    data = resp.json()
    assert data["duplicate_set_id"] is not None
    assert "Already imported" in data["warnings"][0]


def test_import_force_re_import(client: TestClient, usb_path: str):
    client.post("/api/sets/import/cdj-history", data={"usb_path": usb_path})
    resp = client.post(
        "/api/sets/import/cdj-history",
        data={"usb_path": usb_path, "force": "true"},
    )
    assert resp.status_code == 200
    assert resp.json()["matched_count"] == 3
    assert resp.json()["duplicate_set_id"] is None


def test_import_no_pioneer_dir(client: TestClient, tmp_path):
    resp = client.post(
        "/api/sets/import/cdj-history",
        data={"usb_path": str(tmp_path)},
    )
    assert resp.status_code == 400
    assert "No Pioneer database" in resp.json()["detail"]


def test_import_with_name_override(client: TestClient, usb_path: str):
    resp = client.post(
        "/api/sets/import/cdj-history",
        data={"usb_path": usb_path, "name": "Friday Night Gig"},
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Friday Night Gig"
