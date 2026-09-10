"""Importing a record you own, and the provenance that keeps its numbers honest."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from kiku.db.models import Base, Track, VinylRelease
from kiku.metadata.models import RecordingCandidate, ReleaseCandidate
from kiku.vinyl.importer import apply_import, build_preview, set_manual_bpm_key


@pytest.fixture()
def session(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'v.db'}", poolclass=NullPool)
    Base.metadata.create_all(engine)
    s = sessionmaker(bind=engine)()
    yield s
    s.close()


def _twelve_inch() -> ReleaseCandidate:
    return ReleaseCandidate(
        source="discogs",
        source_id="4242",
        album="Klockworks 38",
        artist="Alarico",
        label="Klockworks",
        catalog_number="KW 38",
        year=2023,
        country="Germany",
        format='Vinyl, 12", 33 1/3 RPM, EP',
        recordings=[
            RecordingCandidate(
                title="AF 97", position=1, disc=1, position_raw="A1", length_ms=372000
            ),
            RecordingCandidate(title="Chromo", position=2, disc=1, position_raw="A2"),
            RecordingCandidate(title="Lost In Lima", position=1, disc=2, position_raw="B1"),
        ],
    )


def test_import_writes_one_row_per_side(session):
    release = apply_import(session, _twelve_inch())

    tracks = session.query(Track).order_by(Track.disc_number, Track.track_number).all()
    assert [t.vinyl_position for t in tracks] == ["A1", "A2", "B1"]
    assert all(t.medium == "vinyl" for t in tracks)
    assert all(t.file_path is None for t in tracks)
    assert all(t.vinyl_release_id == release.id for t in tracks)
    assert [t.disc_number for t in tracks] == [1, 1, 2]
    assert release.side_count == 2
    assert release.rpm == 33
    assert release.catalog_number == "KW 38"


def test_a_record_without_a_bpm_is_flagged_not_guessed(session):
    """Research R1: 1 recording in 54 had a BPM. A blank must stay a blank."""
    apply_import(session, _twelve_inch())
    tracks = session.query(Track).all()
    assert all(t.bpm is None for t in tracks)
    assert all(t.enrichment_status == "pending" for t in tracks)


def test_manual_bpm_marks_its_provenance(session):
    apply_import(session, _twelve_inch())
    track = session.query(Track).filter_by(vinyl_position="A1").one()

    set_manual_bpm_key(session, track.id, bpm=136.0, key="8A")

    session.refresh(track)
    assert track.bpm == 136.0
    assert track.bpm_source == "manual"
    assert track.key_source == "manual"
    assert track.enrichment_status == "manual"


def test_manual_bpm_rejects_a_number_that_isnt_one(session):
    apply_import(session, _twelve_inch())
    track = session.query(Track).first()
    with pytest.raises(ValueError):
        set_manual_bpm_key(session, track.id, bpm=0)
    with pytest.raises(ValueError):
        set_manual_bpm_key(session, track.id, bpm=1200)


def test_adding_the_same_record_twice_doesnt_duplicate_the_shelf(session):
    """The unique discogs id is what makes re-import safe (design §3)."""
    apply_import(session, _twelve_inch())
    apply_import(session, _twelve_inch())

    assert session.query(VinylRelease).count() == 1
    assert session.query(Track).count() == 3


def test_reimport_keeps_the_bpm_you_typed(session):
    apply_import(session, _twelve_inch())
    track = session.query(Track).filter_by(vinyl_position="A1").one()
    set_manual_bpm_key(session, track.id, bpm=136.0)

    apply_import(session, _twelve_inch())

    again = session.query(Track).filter_by(vinyl_position="A1").one()
    assert again.bpm == 136.0
    assert again.bpm_source == "manual"


def test_reimport_keeps_a_length_you_typed_over_a_blank_discogs_one(session):
    """Discogs left 12 of 17 sampled sides without a duration (Plan F2).

    Re-importing must not blank out the length the DJ supplied for one.
    """
    apply_import(session, _twelve_inch())
    chromo = session.query(Track).filter_by(vinyl_position="A2").one()
    assert chromo.duration_sec is None
    set_manual_bpm_key(session, chromo.id, bpm=134.0, duration_sec=348)

    apply_import(session, _twelve_inch())

    session.refresh(chromo)
    assert chromo.duration_sec == 348


def test_preview_marks_sides_already_on_the_shelf(session):
    apply_import(session, _twelve_inch())
    preview = build_preview(session, _twelve_inch())
    assert preview.is_reimport
    assert preview.new_count == 0
    assert all(r.existing_track_id is not None for r in preview.rows)


def test_a_vinyl_row_with_a_bpm_is_a_normal_track(session):
    """The finding that makes spec 030 cheap — nothing about scoring reads a file."""
    from kiku.setbuilder.camelot import harmonic_score
    from kiku.setbuilder.scoring import bpm_compatibility

    apply_import(session, _twelve_inch())
    track = session.query(Track).filter_by(vinyl_position="A1").one()
    set_manual_bpm_key(session, track.id, bpm=136.0, key="8A")

    digital = Track(title="A file", bpm=137.0, key="9A", medium="digital")
    assert harmonic_score(track.key, digital.key) > 0
    assert bpm_compatibility(track.bpm, digital.bpm) > 0
