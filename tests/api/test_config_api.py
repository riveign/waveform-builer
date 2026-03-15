"""Tests for config API endpoints (energy presets and genre families)."""

from __future__ import annotations


def test_get_energy_presets(client):
    resp = client.get("/api/config/energy-presets")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    names = {p["name"] for p in data}
    assert names == {"warmup", "peak-time", "journey", "afterhours"}
    for preset in data:
        assert "name" in preset
        assert "description" in preset
        assert "segments" in preset
        assert isinstance(preset["description"], str)
        assert len(preset["description"]) > 0


def test_energy_preset_segments(client):
    resp = client.get("/api/config/energy-presets")
    data = resp.json()
    for preset in data:
        segments = preset["segments"]
        assert isinstance(segments, list)
        assert len(segments) >= 1
        for seg in segments:
            assert "name" in seg
            assert "target_energy" in seg
            assert "duration_pct" in seg
            assert isinstance(seg["name"], str)
            assert 0.0 <= seg["target_energy"] <= 1.0
            assert 0.0 < seg["duration_pct"] <= 1.0
        total_pct = sum(s["duration_pct"] for s in segments)
        assert abs(total_pct - 1.0) < 0.01, (
            f"Preset '{preset['name']}' segments sum to {total_pct}, expected ~1.0"
        )


def test_get_genre_families(client):
    resp = client.get("/api/config/genre-families")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    family_names = {f["family_name"] for f in data}
    assert family_names == {"techno", "house", "groove", "trance", "breaks", "electronic", "other"}
    for family in data:
        assert "family_name" in family
        assert "genres" in family
        assert "compatible_with" in family


def test_genre_family_has_genres(client):
    resp = client.get("/api/config/genre-families")
    data = resp.json()
    for family in data:
        assert isinstance(family["genres"], list)
        assert len(family["genres"]) >= 1, (
            f"Family '{family['family_name']}' has no genres"
        )
        for genre in family["genres"]:
            assert isinstance(genre, str)
            assert len(genre) > 0


def test_genre_compatible_families_are_valid(client):
    resp = client.get("/api/config/genre-families")
    data = resp.json()
    all_family_names = {f["family_name"] for f in data}
    for family in data:
        for compat in family["compatible_with"]:
            assert compat in all_family_names, (
                f"Family '{family['family_name']}' lists '{compat}' as compatible, "
                f"but '{compat}' is not a known family"
            )
