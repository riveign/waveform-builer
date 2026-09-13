"""A track with no file must not become a corrupt playlist row."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from kiku.db.models import Base, Set, SetTrack, Track
from kiku.export.m3u8 import export_set_to_m3u8


@pytest.fixture()
def session(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'e.db'}", poolclass=NullPool)
    Base.metadata.create_all(engine)
    s = sessionmaker(bind=engine)()
    yield s
    s.close()


@pytest.fixture()
def hybrid_set(session):
    digital = Track(
        title="A file",
        artist="Someone",
        bpm=134.0,
        file_path="/run/media/mantis/SSD/Musica/a.aiff",
        duration_sec=360.0,
        medium="digital",
    )
    record = Track(
        title="AF 97",
        artist="Alarico",
        bpm=136.0,
        duration_sec=372.0,
        medium="vinyl",
        vinyl_position="A1",
    )
    session.add_all([digital, record])
    session.flush()
    s = Set(name="Hybrid")
    session.add(s)
    session.flush()
    session.add_all(
        [
            SetTrack(set_id=s.id, position=0, track_id=digital.id),
            SetTrack(set_id=s.id, position=1, track_id=record.id),
        ]
    )
    session.commit()
    return s


def test_m3u8_leaves_the_record_out_and_says_so(session, hybrid_set, tmp_path):
    result = export_set_to_m3u8(hybrid_set, str(tmp_path / "hybrid.m3u8"))

    assert len(result.skipped) == 1
    assert result.skipped[0].title == "AF 97"
    assert "A1" in result.skipped[0].reason


def test_m3u8_never_writes_an_extinf_without_a_path(session, hybrid_set, tmp_path):
    """The bug this closes: an #EXTINF followed by an empty line is corrupt."""
    out = tmp_path / "hybrid.m3u8"
    export_set_to_m3u8(hybrid_set, str(out))
    lines = out.read_text().splitlines()

    for i, line in enumerate(lines):
        if line.startswith("#EXTINF"):
            nxt = lines[i + 1]
            assert nxt and not nxt.startswith("#"), f"#EXTINF with no path at line {i}"
    assert "" not in lines


def test_m3u8_names_the_side_to_pull(session, hybrid_set, tmp_path):
    out = tmp_path / "hybrid.m3u8"
    export_set_to_m3u8(hybrid_set, str(out))
    text = out.read_text()

    assert "# kiku:vinyl" in text
    assert "AF 97" in text
    assert "A1" in text


def test_a_digital_only_set_reports_nothing_skipped(session, tmp_path):
    track = Track(
        title="A file",
        artist="Someone",
        bpm=134.0,
        file_path="/run/media/mantis/SSD/Musica/a.aiff",
        medium="digital",
    )
    session.add(track)
    session.flush()
    s = Set(name="Digital")
    session.add(s)
    session.flush()
    session.add(SetTrack(set_id=s.id, position=0, track_id=track.id))
    session.commit()

    result = export_set_to_m3u8(s, str(tmp_path / "d.m3u8"))
    assert result.skipped == []


def test_a_track_whose_file_vanished_is_skipped_too():
    """Not a vinyl-only guard — any fileless row would have exported blank."""
    from kiku.export.utils import skip_reason

    orphan = Track(title="Lost", artist="Someone", medium="digital", file_path=None)
    assert skip_reason(orphan) == "no file on disk"
