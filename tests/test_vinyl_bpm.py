"""Where a record's BPM comes from, and what it must never claim.

The rule these all serve: a wrong BPM that looks certain is worse than a blank.
"""

from __future__ import annotations

from collections import Counter

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from kiku.db.models import Base, Track
from kiku.vinyl.bpm import (
    APPLY_THRESHOLD,
    find_bpm,
    fold_to_library,
    from_library,
    library_tempo_prior,
)


@pytest.fixture()
def session(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'b.db'}", poolclass=NullPool)
    Base.metadata.create_all(engine)
    s = sessionmaker(bind=engine)()
    yield s
    s.close()


@pytest.fixture()
def library(session):
    """A techno library: everything lives in the 140s, like the real one."""
    rows = [
        ("Alarico", "Af 97", 143.0, "Em"),
        ("Alarico", "Chromo", 144.0, "Cm"),
        ("Alarico", "Lost in Lima", 145.0, "Abm"),
        ("Alarico", "Nisba", 145.0, "Fm"),
    ]
    for artist, title, bpm, key in rows:
        session.add(
            Track(
                artist=artist,
                title=title,
                bpm=bpm,
                key=key,
                medium="digital",
                file_path=f"/music/{title}.aiff",
            )
        )
    for i in range(40):  # weight the prior toward 142, as the real library is
        session.add(
            Track(
                artist="X",
                title=f"t{i}",
                bpm=142.0,
                medium="digital",
                file_path=f"/music/t{i}.aiff",
            )
        )
    session.commit()
    return session


# ── the octave problem ────────────────────────────────────────────────────


def test_fold_uses_the_djs_own_tempos_to_pick_the_octave():
    """Measured: without this, a 120 BPM track read as 234.9 and a 139 as 184.6."""
    prior = Counter({142: 500, 143: 400, 144: 300, 120: 40, 117: 30})

    assert fold_to_library(234.9, prior) == pytest.approx(117.45, abs=0.1)
    assert fold_to_library(71.8, prior) == pytest.approx(143.6, abs=0.1)
    assert fold_to_library(143.6, prior) == pytest.approx(143.6, abs=0.1)


def test_fold_leaves_a_tempo_alone_when_the_library_says_nothing():
    assert fold_to_library(143.6, Counter()) == pytest.approx(143.6)


def test_fold_never_leaves_the_danceable_band():
    prior = Counter({142: 100})
    for raw in (30.0, 45.0, 300.0, 480.0):
        out = fold_to_library(raw, prior)
        assert 60.0 <= out <= 220.0, f"{raw} folded to {out}"


def test_the_prior_ignores_vinyl_rows(session, library):
    """A vinyl row's BPM was typed by the DJ; it belongs in the prior only once
    it isn't circular. Rows with no file are excluded to keep the prior about
    music that was actually analysed."""
    session.add(Track(artist="V", title="side", bpm=90.0, medium="vinyl"))
    session.commit()
    assert 90 not in library_tempo_prior(session)


# ── matching against your own files ───────────────────────────────────────


def test_an_exact_title_match_is_trusted(session, library):
    f = from_library(session, "Alarico", "AF 97")
    assert f.source == "library"
    assert f.bpm == 143.0
    assert f.key == "Em"
    assert f.confidence >= APPLY_THRESHOLD


def test_a_near_match_is_a_suggestion_not_a_fact(session, library):
    """The one that bit in testing: 'Lost In Time' is a different track on a
    different record, and scored 0.898 against 'Lost in Lima'."""
    f = from_library(session, "Alarico", "Lost In Time")

    assert f.source == "suggestion"
    assert f.bpm == 145.0  # shown, so the DJ can judge it
    assert "Lost in Lima" in f.note  # named, so the mismatch is obvious
    assert f.confidence < APPLY_THRESHOLD


def test_an_unrelated_title_matches_nothing(session, library):
    assert from_library(session, "Alarico", "Zzzq Unrelated").source == "none"


def test_a_vinyl_row_never_matches_itself(session, library):
    """Circular: the shelf row would hand its own blank back as an answer."""
    session.add(
        Track(artist="Alarico", title="AF 97", bpm=99.0, medium="vinyl", vinyl_position="A1")
    )
    session.commit()

    f = from_library(session, "Alarico", "AF 97")
    assert f.bpm == 143.0  # the file, not the shelf row


def test_a_library_row_with_no_bpm_teaches_nothing(session):
    session.add(Track(artist="Alarico", title="AF 97", medium="digital", file_path="/music/x.aiff"))
    session.commit()
    assert from_library(session, "Alarico", "AF 97").source == "none"


# ── the cascade ───────────────────────────────────────────────────────────


def test_your_own_file_wins_and_never_touches_the_network(session, library):
    """No client is passed; if this reached Deezer it would raise."""
    f = find_bpm(session, "Alarico", "AF 97", allow_preview=False)
    assert f.source == "library"
    assert f.bpm == 143.0


def test_without_a_preview_a_suggestion_survives_as_a_suggestion(session, library):
    f = find_bpm(session, "Alarico", "Lost In Time", allow_preview=False)
    assert f.source == "suggestion"
    assert f.needs_a_look
    assert not f.is_certain


def test_nothing_anywhere_is_an_honest_none(session, library):
    f = find_bpm(session, "Nobody", "Zzzq Unrelated", allow_preview=False)
    assert f.source == "none"
    assert f.bpm is None


# ── when the library can't advise ─────────────────────────────────────────


def test_a_new_library_still_folds_a_half_time_reading():
    """Found shipping: on an empty database the prior was empty, folding did
    nothing, and a 143 BPM record came back as 71.8 — which reads as broken
    rather than as an estimate."""
    assert fold_to_library(71.8, Counter()) == pytest.approx(143.6, abs=0.1)
    assert fold_to_library(234.9, Counter()) == pytest.approx(117.45, abs=0.1)


def test_a_library_too_thin_to_mean_anything_is_treated_as_none():
    """Three tracks is not a tempo distribution, it's an accident."""
    assert fold_to_library(71.8, Counter({142: 3})) == pytest.approx(143.6, abs=0.1)


def test_a_tempo_the_library_has_never_seen_falls_back_to_the_band():
    """A confident library that has no opinion here must not tie-break wildly."""
    out = fold_to_library(200.0, Counter({142: 500, 143: 400}))
    assert 90.0 <= out <= 180.0
