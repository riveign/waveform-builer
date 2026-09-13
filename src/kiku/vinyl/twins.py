"""The record on the shelf and the file on the drive, when they're the same music.

Matching one side at a time by title and artist was measured against this DJ's
library and it lies: "Numb" is Portishead on the record and Linkin Park on the
drive, and a compilation's sides all say "Various", so the artist can't vouch
for anything. What does work is going record-first: find the digital album that
*is* this record, then match titles inside it. That found 20 of 86 records.

So there are two strengths of evidence, and they are treated differently:

    album   the record's title is a digital album's title, and the side's title
            is a track on it. Linked without asking.
    title   a close title (and an artist that doesn't disagree) anywhere in the
            library. Only ever offered — the DJ says "link" or "not it".

A "not it" is remembered, and an unlink counts as one, so a later pass never
quietly puts back a pairing the DJ took apart.
"""

from __future__ import annotations

import re
import unicodedata
from collections import defaultdict
from dataclasses import dataclass, field

from sqlalchemy import func
from sqlalchemy.orm import Session

from kiku.db.models import Track, VinylRelease, VinylTwinRejection

# Title similarity (0-100) for a side to count as the same track.
TITLE_MATCH = 90
# A title-only suggestion must also clear this on the artist, unless one side
# doesn't name one.
ARTIST_AGREES = 80

_FEAT_RE = re.compile(r"\s(feat\.?|ft\.?|featuring)\s.*$")
_PARENS_RE = re.compile(r"[\(\[](.*?)[\)\]]")
# A bracket naming a different version is part of the identity: "Dreams (Josh
# Hunter Remix)" is not the Fleetwood Mac record. Anything else — "(Eden)",
# "(Album Version)", "(Original Mix)" — is noise and can go.
_VERSION_RE = re.compile(r"remix|edit|rework|bootleg|dub\b|vip\b|flip|refix|live|cover|mix|version")
_SAME_VERSION_RE = re.compile(r"original|album version|extended mix|radio")
_FORMAT_WORDS = {"ep", "lp", "12", "vinyl"}
_NON_WORD_RE = re.compile(r"[^0-9a-z]+")
_UNKNOWN_ARTISTS = {"", "various", "various artists", "va", "unknown", "unknown artist"}


def norm(text: str | None) -> str:
    """Lowercase, no accents, no punctuation, no featuring credit."""
    if not text:
        return ""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c)).lower()
    text = _FEAT_RE.sub("", text)
    return _NON_WORD_RE.sub(" ", text).strip()


def _drop_bracket(m: re.Match) -> str:
    inner = m.group(1).lower()
    if _VERSION_RE.search(inner) and not _SAME_VERSION_RE.search(inner):
        return m.group(0)
    return " "


def _without_parens(text: str | None) -> str:
    return norm(_PARENS_RE.sub(_drop_bracket, text or ""))


def title_score(a: str | None, b: str | None) -> int:
    """How alike two titles are. "Quit (Eden)" and "quit(eden)" are the same
    track; so are "Mejor No Hablar…" and "…(Album Version)"."""

    return _score(norm(a), _without_parens(a), norm(b), _without_parens(b))


def _score(a: str, a_bare: str, b: str, b_bare: str) -> int:
    from thefuzz import fuzz

    return max(fuzz.ratio(a, b), fuzz.ratio(a_bare, b_bare))


def _artist_known(artist: str | None) -> bool:
    return norm(artist) not in _UNKNOWN_ARTISTS


def _artists_agree(a: str | None, b: str | None) -> bool:
    """True unless both sides name an artist and the names disagree."""
    from thefuzz import fuzz

    if not _artist_known(a) or not _artist_known(b):
        return True
    return fuzz.token_set_ratio(norm(a), norm(b)) >= ARTIST_AGREES


def _is_this_record(release_title: str | None, album: str) -> bool:
    """Is a digital album the same release as the record?

    Every word of the record's title must be in the album name — digital albums
    carry noise like "[MLKL033]" or "SMILE SESSIONS 005 | …", records don't. A
    one-word album that happens to be *inside* the record's title ("Summer" in
    "Clubdance2025 (The Sound Of The Summer)") is not the record.
    """
    from thefuzz import fuzz

    have = norm(album)
    if not have:
        return False
    have_words = set(have.split()) - _FORMAT_WORDS
    for want in {norm(release_title), _without_parens(release_title)}:
        want_words = set(want.split()) - _FORMAT_WORDS
        if len(want) >= 3 and want_words and want_words <= have_words:
            return True
    want = norm(release_title)
    if len(want) < 3:
        return False
    return fuzz.ratio(want, have) >= TITLE_MATCH


@dataclass
class DigitalRow:
    id: int
    title: str | None
    artist: str | None
    album: str | None
    # Normalised once — the shelf pass compares every side against every row.
    title_norm: str = ""
    title_bare: str = ""

    def __post_init__(self):
        self.title_norm = norm(self.title)
        self.title_bare = _without_parens(self.title)


@dataclass
class Suggestion:
    vinyl_track_id: int
    digital: DigitalRow
    score: int


@dataclass
class TwinPass:
    linked: list[tuple[int, int]] = field(default_factory=list)  # (vinyl id, digital id)
    suggestions: list[Suggestion] = field(default_factory=list)


class DigitalIndex:
    """Every digital track, loaded once and grouped by album.

    ~4,300 rows is a second of fuzzy matching across the whole shelf, so a
    plain in-memory scan beats anything cleverer.
    """

    def __init__(self, session: Session):
        rows = (
            session.query(Track.id, Track.title, Track.artist, Track.album)
            .filter(
                func.coalesce(Track.medium, "digital") != "vinyl",
                Track.title.isnot(None),
            )
            .all()
        )
        self.rows = [DigitalRow(*r) for r in rows]
        self.by_album: dict[str, list[DigitalRow]] = defaultdict(list)
        for r in self.rows:
            if r.album:
                self.by_album[r.album].append(r)


def _rejected(session: Session, vinyl_ids: list[int]) -> set[tuple[int, int]]:
    if not vinyl_ids:
        return set()
    rows = (
        session.query(VinylTwinRejection.vinyl_track_id, VinylTwinRejection.digital_track_id)
        .filter(VinylTwinRejection.vinyl_track_id.in_(vinyl_ids))
        .all()
    )
    return {(v, d) for v, d in rows}


def match_release(
    session: Session, release: VinylRelease, index: DigitalIndex | None = None
) -> TwinPass:
    """Find the digital twins of a record's unlinked sides. Writes nothing."""
    index = index or DigitalIndex(session)
    sides = (
        session.query(Track)
        .filter(Track.vinyl_release_id == release.id, Track.medium == "vinyl")
        .all()
    )
    open_sides = [s for s in sides if s.duplicate_of_track_id is None]
    if not open_sides:
        return TwinPass()
    rejected = _rejected(session, [s.id for s in open_sides])
    taken = {s.duplicate_of_track_id for s in sides if s.duplicate_of_track_id}
    result = TwinPass()

    # Album first: the only evidence strong enough to act on.
    pool = [
        row
        for album, rows in index.by_album.items()
        if _is_this_record(release.title, album)
        and (
            not _artist_known(release.artist)
            or any(_artists_agree(release.artist, r.artist) for r in rows)
        )
        for row in rows
    ]
    wanted = {s.id: (norm(s.title), _without_parens(s.title)) for s in open_sides}
    pairs = sorted(
        (
            (_score(*wanted[side.id], row.title_norm, row.title_bare), side.id, row.id)
            for side in open_sides
            for row in pool
            if (side.id, row.id) not in rejected
        ),
        reverse=True,
    )
    linked_sides: set[int] = set()
    for score, side_id, row_id in pairs:
        if score < TITLE_MATCH:
            break
        if side_id in linked_sides or row_id in taken:
            continue
        result.linked.append((side_id, row_id))
        linked_sides.add(side_id)
        taken.add(row_id)

    # Then a title anywhere in the library — offered, never applied.
    for side in open_sides:
        if side.id in linked_sides:
            continue
        best: Suggestion | None = None
        for row in index.rows:
            if row.id in taken or (side.id, row.id) in rejected:
                continue
            score = _score(*wanted[side.id], row.title_norm, row.title_bare)
            if score < TITLE_MATCH or (best and score <= best.score):
                continue
            if not _artists_agree(side.artist, row.artist):
                continue
            # With no artist to vouch for it, only an exact title is worth asking about.
            if score < 100 and not (_artist_known(side.artist) and _artist_known(row.artist)):
                continue
            best = Suggestion(side.id, row, score)
        if best:
            result.suggestions.append(best)
    return result


def link(session: Session, vinyl: Track, digital: Track) -> Track:
    """Pair a side with its file, and let the file's analysis speak for the side.

    Your own analysed file is the best number Kiku has — better than a preview
    estimate — but a BPM or key the DJ typed stays theirs.
    """
    if vinyl.medium != "vinyl":
        raise ValueError("Only a side on the shelf can be linked to a file.")
    if (digital.medium or "digital") == "vinyl":
        raise ValueError("That's another record, not a file — pick a digital track.")

    vinyl.duplicate_of_track_id = digital.id
    session.query(VinylTwinRejection).filter(
        VinylTwinRejection.vinyl_track_id == vinyl.id,
        VinylTwinRejection.digital_track_id == digital.id,
    ).delete()

    if digital.bpm and vinyl.bpm_source != "manual":
        vinyl.bpm = digital.bpm
        vinyl.bpm_source = "library"
    if digital.key and vinyl.key_source != "manual":
        vinyl.key = digital.key
        vinyl.key_source = "library"
    if not vinyl.duration_sec and digital.duration_sec:
        vinyl.duration_sec = digital.duration_sec
    if vinyl.bpm and vinyl.enrichment_status != "manual":
        vinyl.enrichment_status = "enriched"
    return vinyl


def reject(session: Session, vinyl: Track, digital_track_id: int) -> Track:
    """ "Not it" — for a suggestion, or for a link that was wrong.

    Unlinking keeps the side's BPM, because a side with none can't be planned
    with, but stops claiming it came from your file.
    """
    if vinyl.duplicate_of_track_id == digital_track_id:
        vinyl.duplicate_of_track_id = None
        if vinyl.bpm_source == "library":
            vinyl.bpm_source = "unlinked"
        if vinyl.key_source == "library":
            vinyl.key_source = "unlinked"
    exists = (
        session.query(VinylTwinRejection.id)
        .filter(
            VinylTwinRejection.vinyl_track_id == vinyl.id,
            VinylTwinRejection.digital_track_id == digital_track_id,
        )
        .first()
    )
    if not exists:
        session.add(VinylTwinRejection(vinyl_track_id=vinyl.id, digital_track_id=digital_track_id))
    return vinyl


def link_release(
    session: Session, release: VinylRelease, index: DigitalIndex | None = None
) -> TwinPass:
    """Apply a record's album-level matches. The caller commits."""
    found = match_release(session, release, index)
    for vinyl_id, digital_id in found.linked:
        link(session, session.get(Track, vinyl_id), session.get(Track, digital_id))
    return found


def link_shelf(session: Session, *, apply: bool = True) -> dict[int, TwinPass]:
    """Run the album-level pass over every record. Commits when `apply`."""
    index = DigitalIndex(session)
    results: dict[int, TwinPass] = {}
    for release in session.query(VinylRelease).order_by(VinylRelease.artist, VinylRelease.title):
        results[release.id] = (
            link_release(session, release, index)
            if apply
            else match_release(session, release, index)
        )
    if apply:
        session.commit()
    return results


def vinyl_twins_of(session: Session, digital_ids: list[int]) -> dict[int, Track]:
    """For each digital track, the first record side that is the same recording."""
    if not digital_ids:
        return {}
    rows = (
        session.query(Track)
        .filter(Track.duplicate_of_track_id.in_(digital_ids), Track.medium == "vinyl")
        .order_by(Track.id)
        .all()
    )
    out: dict[int, Track] = {}
    for r in rows:
        out.setdefault(r.duplicate_of_track_id, r)
    return out


@dataclass
class Pairing:
    vinyl_track_id: int
    digital_track_id: int | None
    reason: str | None  # linked | title | order | None


def pair_with_album(
    session: Session, release: VinylRelease, digital_ids: list[int]
) -> list[Pairing]:
    """Propose which file is which side, when the DJ has said which album it is.

    The DJ chose the album, so the album-name test is skipped — that's the whole
    point, the names in the library can be wrong. Titles still pair what they
    can; if titles fail but the counts line up, pressing order pairs the rest
    and says so, because a tagging mistake usually keeps the running order.
    Nothing is written.
    """
    sides = (
        session.query(Track)
        .filter(Track.vinyl_release_id == release.id, Track.medium == "vinyl")
        .order_by(Track.disc_number, Track.track_number, Track.id)
        .all()
    )
    files = (
        session.query(Track)
        .filter(Track.id.in_(digital_ids), func.coalesce(Track.medium, "digital") != "vinyl")
        .order_by(Track.disc_number, Track.track_number, Track.file_path, Track.id)
        .all()
        if digital_ids
        else []
    )
    file_ids = {f.id for f in files}
    chosen: dict[int, tuple[int, str]] = {}
    used: set[int] = set()

    for s in sides:
        if s.duplicate_of_track_id in file_ids:
            chosen[s.id] = (s.duplicate_of_track_id, "linked")
            used.add(s.duplicate_of_track_id)

    rejected = _rejected(session, [s.id for s in sides])
    pairs = sorted(
        (
            (title_score(s.title, f.title), s.id, f.id)
            for s in sides
            if s.id not in chosen
            for f in files
            if f.id not in used and (s.id, f.id) not in rejected
        ),
        reverse=True,
    )
    for score, sid, fid in pairs:
        if score < TITLE_MATCH:
            break
        if sid in chosen or fid in used:
            continue
        chosen[sid] = (fid, "title")
        used.add(fid)

    open_sides = [s for s in sides if s.id not in chosen]
    open_files = [f for f in files if f.id not in used]
    if open_sides and len(open_sides) == len(open_files):
        for s, f in zip(open_sides, open_files):
            chosen[s.id] = (f.id, "order")

    return [
        Pairing(s.id, *chosen[s.id]) if s.id in chosen else Pairing(s.id, None, None) for s in sides
    ]


def apply_pairings(session: Session, release: VinylRelease, pairs: dict[int, int | None]) -> None:
    """Set each side's file as the DJ confirmed it. The caller commits.

    Replacing or clearing a link counts as "not it" for the old file, so no
    later automatic pass puts the wrong one back.
    """
    sides = {
        s.id: s
        for s in session.query(Track).filter(
            Track.vinyl_release_id == release.id, Track.medium == "vinyl"
        )
    }
    unknown = set(pairs) - set(sides)
    if unknown:
        raise ValueError("Some of those tracks aren't on this record.")
    wanted = [d for d in pairs.values() if d]
    if len(wanted) != len(set(wanted)):
        raise ValueError("One file is paired with two sides — each file can only be one side.")

    for sid, digital_id in pairs.items():
        side = sides[sid]
        current = side.duplicate_of_track_id
        if current == digital_id:
            continue
        if current:
            reject(session, side, current)
        if digital_id:
            digital = session.get(Track, digital_id)
            if digital is None:
                raise ValueError("One of those files isn't in your library any more.")
            link(session, side, digital)
