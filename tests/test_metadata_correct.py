"""Tests for the correction engine: diff building, discovery, apply."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from kiku.db.models import AlbumMetadata, Base, Track
from kiku.metadata.correct import (
    apply_correction,
    build_correction,
    discover_tracks_for_release,
)
from kiku.metadata.models import (
    FieldChange,
    RecordingCandidate,
    ReleaseCandidate,
)


@pytest.fixture()
def session(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path/'t.db'}", poolclass=NullPool)
    Base.metadata.create_all(engine)
    s = sessionmaker(bind=engine)()
    yield s
    s.close()


def _hadone_candidate() -> ReleaseCandidate:
    return ReleaseCandidate(
        source="bandcamp",
        source_id="https://x.bandcamp.com/album/bite",
        album="Bite The Hand That Feeds You",
        artist="Hadone",
        label="Primal Instinct",
        year=2026,
        recordings=[
            RecordingCandidate(title="Bite The Hand That Feeds You", position=1, disc=1),
            RecordingCandidate(title="Leave The Door Open", position=2, disc=1),
            RecordingCandidate(title="Sit In Their Seat", position=3, disc=1),
        ],
    )


# ── FieldChange semantics ────────────────────────────────────────────────

def test_field_change_changed_detects_real_changes():
    assert FieldChange("title", "old", "new").changed is True
    assert FieldChange("title", "Same", "same").changed is False  # case/space-insensitive
    assert FieldChange("title", "x", None).changed is False        # never blank out
    assert FieldChange("title", "x", "   ").changed is False
    assert FieldChange("track_number", None, 1).changed is True


# ── build_correction ─────────────────────────────────────────────────────

def test_build_correction_produces_full_identity_diff(session):
    # Mangled like the real Hadone masters: side-position in artist, junk in title.
    t = Track(id=1, title="bite the hand that feeds you_MASTER_24", artist="A1 hadone")
    session.add(t)
    session.commit()

    corr = build_correction([t], _hadone_candidate())
    assert len(corr) == 1
    c = corr[0]
    assert c.confidence > 0.6  # fuzzy title match despite the _MASTER junk
    changed = {ch.field: (ch.old, ch.new) for ch in c.changes if ch.changed}
    assert changed["title"][1] == "Bite The Hand That Feeds You"
    assert changed["artist"] == ("A1 hadone", "Hadone")
    assert changed["album"][1] == "Bite The Hand That Feeds You"
    assert changed["label"][1] == "Primal Instinct"
    assert changed["release_year"][1] == 2026
    assert changed["track_number"][1] == 1


def test_build_correction_respects_field_allowlist(session):
    t = Track(id=1, title="Sit In Their Seat", artist="B1 hadone")
    session.add(t)
    session.commit()
    corr = build_correction([t], _hadone_candidate(), fields=("artist",))
    fields = {ch.field for ch in corr[0].changes}
    assert fields == {"artist"}


# ── discover_tracks_for_release ───────────────────────────────────────────

def test_discover_recovers_ungrouped_album_and_rejects_subset_false_positives(session):
    # Real members (no album grouping, garbled artist)
    session.add(Track(id=1, title="Bite The Hand That Feeds You", artist="A1 hadone"))
    session.add(Track(id=2, title="Sit In Their Seat", artist="B1 hadone"))
    # Decoys: subset/superset titles that token_set_ratio would wrongly accept
    session.add(Track(id=3, title="YOU", artist="Someone"))
    session.add(Track(id=4, title="Close (Some Remix)", artist="Other"))
    session.commit()

    found = discover_tracks_for_release(session, _hadone_candidate())
    ids = {t.id for t in found}
    assert ids == {1, 2}  # only true title matches, decoys rejected


def test_discover_scopes_by_like_pattern(session):
    session.add(Track(id=1, title="Sit In Their Seat", artist="x",
                      file_path="/m/2026/Hadone - sit.wav"))
    session.add(Track(id=2, title="Sit In Their Seat", artist="y",
                      file_path="/m/2019/other.wav"))
    session.commit()
    found = discover_tracks_for_release(session, _hadone_candidate(), like="%2026%")
    assert {t.id for t in found} == {1}


# ── apply_correction ──────────────────────────────────────────────────────

def test_apply_writes_only_allowed_fields_and_records_provenance(session):
    t = Track(id=1, title="sit in their seat_MASTER", artist="B1 hadone")
    session.add(t)
    session.commit()

    cand = _hadone_candidate()
    corr = build_correction([t], cand)
    touched = apply_correction(session, corr, fields=("title", "artist"), candidate=cand)

    assert touched == 1
    refreshed = session.get(Track, 1)
    assert refreshed.title == "Sit In Their Seat"
    assert refreshed.artist == "Hadone"
    # album/label/year NOT in the allowlist → untouched
    assert refreshed.album is None
    assert refreshed.label is None

    # Provenance recorded under the derived album_key even without one passed in.
    md = session.query(AlbumMetadata).filter_by(source="bandcamp").one()
    assert md.album == "Bite The Hand That Feeds You"
    assert md.match_status == "applied"


def test_apply_is_idempotent_noop_when_already_correct(session):
    t = Track(id=1, title="Sit In Their Seat", artist="Hadone",
              album="Bite The Hand That Feeds You", label="Primal Instinct",
              release_year=2026, track_number=3, disc_number=1)
    session.add(t)
    session.commit()
    corr = build_correction([t], _hadone_candidate())
    touched = apply_correction(session, corr, fields=tuple(
        ["title", "artist", "album", "label", "release_year", "track_number", "disc_number"]
    ))
    assert touched == 0
