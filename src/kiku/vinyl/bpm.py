"""Find a BPM for a record before asking the DJ to type one.

Four rungs, in order of how much they can be trusted. Every number carries the
rung it came from, because a wrong BPM that looks certain is worse than a blank
(spec 030, Risk 2 — and it happened in testing: "Lost In Time" matched a
different record's "Lost in Lima" at 0.898 and would have written 145 onto it).

    1. library    the DJ's own analysed file. Same Essentia run as everything
                  else they own, so it is on the same measuring stick. Exact
                  title match only.
    2. preview    Deezer finds ~92% of this DJ's vinyl but its own `bpm` field
                  is 0 for all of it (it works for chart pop, not for techno).
                  So we fetch the 30-second preview and listen to it. Measured
                  against 10 already-analysed tracks: 9 within 5 BPM.
    3. suggestion a near-match in the library that is probably a different
                  track. Shown, never applied.
    4. none       the DJ types it. Outranks everything above, forever.

The octave is chosen using the DJ's own tempo distribution. Without that, a
120 BPM track read as 234.9 and a 139 as 184.6; with it, 117.5 and 138.4.
"""

from __future__ import annotations

import logging
import os
import tempfile
from collections import Counter
from dataclasses import dataclass

import httpx
from sqlalchemy.orm import Session

from kiku.db.models import Track

logger = logging.getLogger(__name__)

DEEZER_API = "https://api.deezer.com"
USER_AGENT = "Kiku/0.1 ( riveign@gmail.com )"
TIMEOUT_S = 30.0

# An exact title match is the only one trusted enough to apply. Below this a
# match is offered as a suggestion the DJ resolves; "Lost In Time" vs
# "Lost in Lima" scores 0.898, which is why the bar is this high.
APPLY_THRESHOLD = 0.97
SUGGEST_THRESHOLD = 0.75

# Tempo folding never leaves this band — beyond it nothing is danceable.
_MIN_BPM, _MAX_BPM = 60.0, 220.0

# How plausible each mis-reading is, before the library gets a say. A beat
# tracker's own answer is evidence and starts ahead; hearing double or half is
# its commonest error; hearing a 3:2 or 4:3 metre is rarer; anything wilder is
# rare enough that the library should have to argue hard for it.
#
# Without this weighting the library simply outvoted the detector: a correct
# 103 BPM blues reading became 154.5, because 155 is a tempo this collection
# recognises and 103 is not.
# Calibrated against every reading measured while building this: the two Doors
# tempos the old code broke, the half-time and doubled readings it fixed, the
# 4:3 metre error, and two already-correct readings it had to leave alone.
# 8/8, and stable across metre 0.02-0.15 — these sit in the middle of that.
_MULTIPLE_PRIOR: tuple[tuple[float, float], ...] = (
    (1.0, 1.00),  # the detector's own answer
    (2.0, 0.70),  # heard half the beat
    (0.5, 0.70),  # heard twice the beat
    (1.5, 0.10),  # 3:2 metre
    (2 / 3, 0.10),
    (4 / 3, 0.10),  # 4:3 metre
    (0.75, 0.10),
    (3.0, 0.03),
    (1 / 3, 0.03),
    (4.0, 0.03),
    (0.25, 0.03),
)

# Where to fold when the library can't advise — a new library, or one too thin
# to mean anything. Detectors habitually report half-time, so without this a
# 143 BPM record lands as 71.8 and reads as broken rather than as an estimate.
_DEFAULT_BAND = (90.0, 180.0)
_PRIOR_MIN_TRACKS = 25


@dataclass
class BpmFinding:
    """A BPM and, more importantly, where it came from."""

    bpm: float | None = None
    key: str | None = None
    source: str = "none"  # library | preview | suggestion | none
    note: str | None = None  # what to show the DJ
    matched_track_id: int | None = None
    confidence: float | None = None

    @property
    def is_certain(self) -> bool:
        return self.source == "library"

    @property
    def needs_a_look(self) -> bool:
        return self.source == "suggestion"


def library_tempo_prior(session: Session, genre: str | None = None) -> Counter:
    """How often each whole BPM shows up in the DJ's analysed library.

    `genre` narrows it to the part of the library that's actually like this
    record. That matters more than it sounds: a techno library's taste for 140s
    will happily push a correct 103 BPM blues reading up to 154.5, because 155
    is a tempo it recognises and 103 isn't. Measured on a 1971 rock LP, that
    turned four right answers into wrong ones.
    """
    q = session.query(Track.bpm).filter(
        Track.bpm.isnot(None), Track.bpm > 0, Track.medium != "vinyl"
    )
    if genre:
        from kiku.setbuilder.scoring import genre_to_family

        family = genre_to_family(genre)
        rows = (
            session.query(Track.bpm, Track.dir_genre, Track.rb_genre)
            .filter(Track.bpm.isnot(None), Track.bpm > 0, Track.medium != "vinyl")
            .all()
        )
        return Counter(
            round(bpm)
            for bpm, dir_g, rb_g in rows
            if bpm and genre_to_family(dir_g or rb_g or "") == family
        )
    return Counter(round(b[0]) for b in q.all() if b[0])


def fold_to_library(tempo: float, prior: Counter) -> float:
    """Pick the octave/metre the DJ's own library says is most likely.

    A tempo detector is reliable about the beat grid and unreliable about which
    multiple of it you meant. The library settles that argument: if this DJ
    plays 140s, a reading of 234.9 is a doubled 117.
    """
    if not tempo or tempo <= 0:
        return tempo

    total = sum(prior.values())
    if total < _PRIOR_MIN_TRACKS:
        # Nothing to learn from yet — fold into the band most dance music lives
        # in, so a half-time reading still lands somewhere usable.
        return _fold_into_band(tempo, *_DEFAULT_BAND)

    def likelihood(b: float) -> float:
        return sum(prior.get(x, 0) for x in range(round(b) - 2, round(b) + 3)) / total

    scored = [
        (tempo * m, likelihood(tempo * m) * weight)
        for m, weight in _MULTIPLE_PRIOR
        if _MIN_BPM <= tempo * m <= _MAX_BPM
    ]
    if not scored:
        return tempo

    best, best_score = max(scored, key=lambda pair: pair[1])
    if best_score == 0:
        # The library has opinions, but none about this tempo or any multiple of
        # it. Don't let an arbitrary tie-break pick a wild octave.
        return _fold_into_band(tempo, *_DEFAULT_BAND)
    return best


def _fold_into_band(tempo: float, lo: float, hi: float) -> float:
    """Double or halve until the tempo sits in the band, if it can."""
    out = tempo
    for _ in range(7):
        if out < lo:
            out *= 2
        elif out > hi:
            out /= 2
        else:
            break
    return out


def from_library(
    session: Session, artist: str | None, title: str, prior_ids: set[int] | None = None
) -> BpmFinding:
    """Does the DJ already own this track as an analysed file?

    Only digital rows with a BPM count — matching a vinyl row against itself
    would be circular, and a row with no BPM teaches nothing.
    """
    try:
        from thefuzz import fuzz
    except ImportError:
        logger.warning("thefuzz not installed — skipping library matching")
        return BpmFinding()

    from kiku.hunting.parsers.common import normalize_name

    want_artist = normalize_name(artist or "")
    want_title = normalize_name(title or "")
    if not want_title:
        return BpmFinding()

    rows = (
        session.query(Track.id, Track.artist, Track.title, Track.bpm, Track.key)
        .filter(
            Track.bpm.isnot(None),
            Track.bpm > 0,
            Track.title.isnot(None),
            Track.medium != "vinyl",
        )
        .all()
    )

    best = None
    best_score = 0.0
    for tid, r_artist, r_title, r_bpm, r_key in rows:
        if prior_ids and tid in prior_ids:
            continue
        title_score = fuzz.ratio(want_title, normalize_name(r_title or "")) / 100.0
        artist_score = fuzz.ratio(want_artist, normalize_name(r_artist or "")) / 100.0
        # Title carries the identity; the artist is corroboration. A record's
        # own artist is on every side, so it cannot discriminate between them.
        score = title_score * 0.75 + artist_score * 0.25
        if score > best_score:
            best_score, best = score, (tid, r_artist, r_title, r_bpm, r_key)

    if best is None or best_score < SUGGEST_THRESHOLD:
        return BpmFinding()

    tid, r_artist, r_title, r_bpm, r_key = best
    if best_score >= APPLY_THRESHOLD:
        return BpmFinding(
            bpm=r_bpm,
            key=r_key,
            source="library",
            note=f"from your file — {r_title}",
            matched_track_id=tid,
            confidence=round(best_score, 3),
        )
    return BpmFinding(
        bpm=r_bpm,
        key=r_key,
        source="suggestion",
        note=f"looks like your “{r_title}” — check it's the same track",
        matched_track_id=tid,
        confidence=round(best_score, 3),
    )


def find_preview_url(artist: str | None, title: str, client: httpx.Client) -> str | None:
    """A 30-second clip of this track, if Deezer has one.

    Deezer's own `bpm` field is not used: it is populated for chart catalogue
    and 0 for every underground techno track measured, which is the same skew
    that made AcousticBrainz useless here.
    """
    query = " ".join(x for x in (artist, title) if x).strip()
    if not query:
        return None
    try:
        res = (
            client.get(f"{DEEZER_API}/search", params={"q": query, "limit": 3})
            .json()
            .get("data", [])
        )
    except Exception:
        logger.warning("Deezer search failed for %r", query, exc_info=True)
        return None

    wanted = (title or "").lower().strip()
    for hit in res:
        # Identity has to be exact. A near-miss here attaches another track's
        # tempo, which is the failure this whole module is shaped to avoid.
        if (hit.get("title") or "").lower().strip() != wanted:
            continue
        try:
            full = client.get(f"{DEEZER_API}/track/{hit['id']}").json()
        except Exception:
            logger.warning("Deezer track fetch failed for %s", hit.get("id"), exc_info=True)
            continue
        if full.get("preview"):
            return full["preview"]
    return None


# Krumhansl-Schmuckler key profiles — the standard correlation templates.
_MAJOR_PROFILE = (6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88)
_MINOR_PROFILE = (6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17)
_PITCH_NAMES = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")


def key_from_audio(path: str) -> str | None:
    """Estimate a key from a clip, in the notation the library already uses.

    Measured against 7 of the DJ's own analysed tracks: 4 exact, and every one
    of the rest landed within a step on the Camelot wheel (a relative mode or a
    neighbour), which still mixes. Good enough to offer, not to assert.
    """
    try:
        import librosa
        import numpy as np
    except ImportError:
        return None

    try:
        y, sr = librosa.load(path, sr=22050, mono=True)
        chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
        profile = chroma.mean(axis=1)
        profile = (profile - profile.mean()) / (profile.std() or 1)

        best_key, best_r = None, -2.0
        for i in range(12):
            for suffix, template in (("", _MAJOR_PROFILE), ("m", _MINOR_PROFILE)):
                rolled = np.roll(np.array(template), i)
                rolled = (rolled - rolled.mean()) / (rolled.std() or 1)
                r = float(np.corrcoef(profile, rolled)[0, 1])
                if r > best_r:
                    best_r, best_key = r, f"{_PITCH_NAMES[i]}{suffix}"
        return best_key
    except Exception:
        logger.warning("key detection failed for %s", path, exc_info=True)
        return None


def analyse_preview(
    url: str, prior: Counter, client: httpx.Client
) -> tuple[float | None, str | None]:
    """Fetch the clip once and take both readings off it.

    Downloading and decoding is the expensive part, so BPM and key share a pass.
    """
    try:
        audio = client.get(url).content
    except Exception:
        logger.warning("preview fetch failed", exc_info=True)
        return None, None

    path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            f.write(audio)
            path = f.name
        return _tempo_from_file(path, prior), key_from_audio(path)
    finally:
        if path and os.path.exists(path):
            os.unlink(path)


def _tempo_from_file(path: str, prior: Counter) -> float | None:
    try:
        import librosa
        import numpy as np
    except ImportError:
        logger.warning("librosa not installed — preview analysis unavailable")
        return None
    try:
        y, sr = librosa.load(path, sr=22050, mono=True)
        tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
        raw = float(np.atleast_1d(tempo)[0])
    except Exception:
        logger.warning("tempo detection failed for %s", path, exc_info=True)
        return None
    if not raw or raw <= 0:
        return None
    return round(fold_to_library(raw, prior), 1)


def find_bpm(
    session: Session,
    artist: str | None,
    title: str,
    *,
    prior: Counter | None = None,
    genre: str | None = None,
    client: httpx.Client | None = None,
    allow_preview: bool = True,
) -> BpmFinding:
    """Walk the rungs until one of them answers."""
    found = from_library(session, artist, title)
    if found.source == "library":
        return found

    if not allow_preview:
        return found

    owned = client is not None
    c = client or httpx.Client(
        timeout=TIMEOUT_S, headers={"User-Agent": USER_AGENT}, follow_redirects=True
    )
    try:
        url = find_preview_url(artist, title, c)
        if url:
            if prior is None:
                prior = library_tempo_prior(session, genre=genre)
            bpm, key = analyse_preview(url, prior, c)
            if bpm:
                # A suggestion is a maybe about identity; a preview reading is a
                # real measurement of the right track. Prefer the measurement,
                # but keep the suggestion visible so the DJ can still act on it.
                return BpmFinding(
                    bpm=bpm,
                    key=key,
                    source="preview",
                    note="estimated from a 30-second preview",
                    confidence=None,
                )
    finally:
        if not owned:
            c.close()

    return found
