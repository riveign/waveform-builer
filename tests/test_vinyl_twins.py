"""A record you also own as files — found record-first, and only acted on when sure."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from kiku.db.models import Base, Track, VinylRelease, VinylTwinRejection
from kiku.setbuilder.planner import _get_candidate_pool
from kiku.vinyl.importer import remove_release
from kiku.vinyl.twins import (
    apply_pairings,
    link,
    link_release,
    link_shelf,
    match_release,
    pair_with_album,
    reject,
    title_score,
)


@pytest.fixture()
def session(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 't.db'}", poolclass=NullPool)
    Base.metadata.create_all(engine)
    s = sessionmaker(bind=engine)()
    yield s
    s.close()


def _record(session, title, artist, sides):
    rel = VinylRelease(title=title, artist=artist)
    session.add(rel)
    session.flush()
    rows = []
    for i, (pos, name, *rest) in enumerate(sides):
        t = Track(
            medium="vinyl",
            vinyl_release_id=rel.id,
            vinyl_position=pos,
            title=name,
            artist=rest[0] if rest else artist,
            album=title,
            track_number=i,
        )
        session.add(t)
        rows.append(t)
    session.flush()
    return rel, rows


def _file(session, title, artist, album=None, bpm=140.0, key="8A", **kw):
    t = Track(medium="digital", title=title, artist=artist, album=album, bpm=bpm, key=key, **kw)
    session.add(t)
    session.flush()
    return t


def test_album_match_links_the_sides_on_it(session):
    rel, (a1, a2, b1) = _record(
        session, "Sonora", "Alarico", [("A1", "Iruka"), ("A2", "Boiler"), ("B1", "Chlorid")]
    )
    iruka = _file(session, "Iruka", "Alarico", "Sonora", bpm=141.0, key="F#")
    boiler = _file(session, "Boiler", "Alarico", "Sonora", bpm=143.0)

    found = link_release(session, rel)
    session.commit()

    assert sorted(found.linked) == sorted([(a1.id, iruka.id), (a2.id, boiler.id)])
    assert a1.duplicate_of_track_id == iruka.id
    assert (a1.bpm, a1.key, a1.bpm_source) == (141.0, "F#", "library")
    assert b1.duplicate_of_track_id is None


def test_noisy_digital_album_names_still_are_the_record(session):
    rel, (a1,) = _record(session, "The Lawnmower EP", "Various", [("A1", "The Lawnmower", "Ikari")])
    f = _file(session, "The Lawnmower", "Ikari", "The Lawnmower EP [MLKL033]")
    assert link_release(session, rel).linked == [(a1.id, f.id)]


def test_a_word_inside_the_record_title_is_not_the_record(session):
    """ "Summer" is inside "…The Sound Of The Summer" — it's still another album."""
    rel, _ = _record(session, "The Sound Of The Summer", "The Trip", [("A1", "Heat")])
    _file(session, "Heat", "The Trip", "Summer")
    assert match_release(session, rel).linked == []


def test_a_same_title_by_someone_else_is_never_linked_or_suggested(session):
    """Measured: Portishead's "Numb" matched Linkin Park's by title alone."""
    rel, _ = _record(session, "Dummy", "Portishead", [("A1", "Numb")])
    _file(session, "Numb", "Linkin Park", "Meteora")
    found = match_release(session, rel)
    assert found.linked == [] and found.suggestions == []


def test_a_title_match_outside_the_album_is_only_suggested(session):
    rel, (a1, _) = _record(session, "Klockworks 38", "Alarico", [("A1", "AF 97"), ("A2", "Chromo")])
    af = _file(session, "Af 97", "Alarico", "AF 97")

    found = link_release(session, rel)
    assert found.linked == []
    assert [(g.vinyl_track_id, g.digital.id) for g in found.suggestions] == [(a1.id, af.id)]
    assert a1.duplicate_of_track_id is None


def test_a_remix_is_not_the_record(session):
    assert title_score("Riders On The Storm", "Riders On The Storm (Finder Music Remix)") < 90
    assert title_score("Quit (Eden)", "quit(eden)") >= 90
    assert title_score("Mejor No Hablar", "Mejor No Hablar (Album Version)") >= 90


def test_a_bpm_the_dj_typed_survives_linking(session):
    _, (side,) = _record(session, "Sonora", "Alarico", [("A1", "Iruka")])
    side.bpm, side.bpm_source = 139.0, "manual"
    f = _file(session, "Iruka", "Alarico", "Sonora", bpm=141.0, key="F#")

    link(session, side, f)
    assert (side.bpm, side.bpm_source) == (139.0, "manual")
    assert (side.key, side.key_source) == ("F#", "library")


def test_not_it_is_remembered_and_unlink_stops_claiming_the_file(session):
    rel, (side,) = _record(session, "Sonora", "Alarico", [("A1", "Iruka")])
    f = _file(session, "Iruka", "Alarico", "Sonora")
    link_release(session, rel)
    session.commit()

    reject(session, side, f.id)
    session.commit()
    assert side.duplicate_of_track_id is None
    assert side.bpm == 140.0 and side.bpm_source == "unlinked"

    again = link_release(session, rel)
    assert again.linked == [] and again.suggestions == []


def test_linking_by_hand_clears_an_earlier_not_it(session):
    _, (side,) = _record(session, "Sonora", "Alarico", [("A1", "Iruka")])
    f = _file(session, "Iruka", "Alarico")
    reject(session, side, f.id)
    link(session, side, f)
    session.commit()
    assert session.query(VinylTwinRejection).count() == 0


def test_link_refuses_two_records(session):
    _, (a,) = _record(session, "One", "X", [("A1", "Same")])
    _, (b,) = _record(session, "Two", "X", [("A1", "Same")])
    with pytest.raises(ValueError):
        link(session, a, b)


def test_removing_a_record_takes_its_not_its_with_it(session):
    rel, (side,) = _record(session, "Sonora", "Alarico", [("A1", "Iruka")])
    f = _file(session, "Iruka", "Alarico")
    reject(session, side, f.id)
    session.commit()
    remove_release(session, rel.id)
    assert session.query(VinylTwinRejection).count() == 0
    assert session.get(Track, f.id) is not None


def test_dry_run_writes_nothing(session):
    _record(session, "Sonora", "Alarico", [("A1", "Iruka")])
    _file(session, "Iruka", "Alarico", "Sonora")
    session.commit()
    results = link_shelf(session, apply=False)
    assert sum(len(r.linked) for r in results.values()) == 1
    assert session.query(Track).filter(Track.duplicate_of_track_id.isnot(None)).count() == 0


def test_a_linked_pair_is_one_track_to_the_builder(session):
    rel, (side,) = _record(session, "Sonora", "Alarico", [("A1", "Iruka")])
    f = _file(session, "Iruka", "Alarico", "Sonora")
    link_release(session, rel)
    session.commit()

    assert [t.id for t in _get_candidate_pool(session, include_vinyl=True)] == [f.id]


# ── pairing with an album the DJ picked ───────────────────────────────────


def test_a_misnamed_album_pairs_by_title_then_by_order(session):
    """The album is tagged wrong and one title is garbage — the DJ still knows it's the record."""
    rel, (a1, a2, b1) = _record(
        session, "Sonora", "Alarico", [("A1", "Iruka"), ("A2", "Boiler"), ("B1", "Chlorid")]
    )
    f1 = _file(session, "Boiler", "Alarico", "Unknown Album", track_number=2)
    f2 = _file(session, "Iruka", "Alarico", "Unknown Album", track_number=1)
    f3 = _file(session, "01 Track 3", "?", "Unknown Album", track_number=3)

    pairs = {
        p.vinyl_track_id: (p.digital_track_id, p.reason)
        for p in pair_with_album(session, rel, [f1.id, f2.id, f3.id])
    }
    assert pairs == {a1.id: (f2.id, "title"), a2.id: (f1.id, "title"), b1.id: (f3.id, "order")}
    assert a1.duplicate_of_track_id is None  # a proposal writes nothing


def test_order_is_not_guessed_when_the_counts_differ(session):
    rel, (a1, a2) = _record(session, "Sonora", "Alarico", [("A1", "Iruka"), ("A2", "Boiler")])
    f = _file(session, "01 Track 1", "?", "x")
    pairs = pair_with_album(session, rel, [f.id])
    # two sides, one file: order can't say which side it is
    assert all(p.digital_track_id is None for p in pairs)


def test_applying_a_pairing_replaces_a_wrong_link_and_remembers_it(session):
    rel, (a1, a2) = _record(session, "Sonora", "Alarico", [("A1", "Iruka"), ("A2", "Boiler")])
    wrong = _file(session, "Iruka", "Someone", "Other")
    right = _file(session, "Iruka (tagged wrong)", "?", "x")
    link(session, a1, wrong)
    session.commit()

    apply_pairings(session, rel, {a1.id: right.id, a2.id: None})
    session.commit()
    assert a1.duplicate_of_track_id == right.id
    assert (
        session.query(VinylTwinRejection)
        .filter_by(vinyl_track_id=a1.id, digital_track_id=wrong.id)
        .count()
        == 1
    )


def test_one_file_cannot_be_two_sides(session):
    rel, (a1, a2) = _record(session, "Sonora", "Alarico", [("A1", "Iruka"), ("A2", "Boiler")])
    f = _file(session, "Iruka", "Alarico")
    with pytest.raises(ValueError):
        apply_pairings(session, rel, {a1.id: f.id, a2.id: f.id})


def test_a_side_from_another_record_is_refused(session):
    rel, _ = _record(session, "Sonora", "Alarico", [("A1", "Iruka")])
    _, (other,) = _record(session, "Other", "X", [("A1", "Y")])
    f = _file(session, "Y", "X")
    with pytest.raises(ValueError):
        apply_pairings(session, rel, {other.id: f.id})
