"""Import M3U8 playlists into Kiku sets with batch track matching."""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from pathlib import PurePosixPath

from sqlalchemy.orm import Session

from kiku.db.models import Set, SetTrack, Track
from kiku.db.paths import normalize_path
from kiku.import_playlist.m3u8 import M3U8ParseResult, M3U8Track


@dataclass
class TrackMatchResult:
    m3u8_track: M3U8Track
    matched_track: Track | None
    match_method: str  # "exact_path", "nocase_path", "fuzzy_filename", "unmatched"


@dataclass
class ImportResult:
    set_id: int
    name: str
    source: str
    total_tracks: int
    matched_count: int
    unmatched_count: int
    unmatched: list[dict]  # [{path, title, line}]
    match_methods: dict[str, int]
    warnings: list[str]
    duplicate_set_id: int | None = None  # Set if source_ref already exists


def _build_path_index(
    session: Session,
) -> tuple[dict[str, Track], dict[str, Track], dict[str, list[Track]]]:
    """Load all tracks and build in-memory lookup dicts.

    Returns
    -------
    exact_index : dict mapping normalized file_path -> Track
    nocase_index : dict mapping lowercased normalized file_path -> Track
    stem_index : dict mapping lowercased filename stem -> [Track, ...]
    """
    all_tracks = session.query(Track).filter(Track.file_path.isnot(None)).all()

    exact_index: dict[str, Track] = {}
    nocase_index: dict[str, Track] = {}
    stem_index: dict[str, list[Track]] = {}

    for t in all_tracks:
        norm = normalize_path(t.file_path)
        norm_nfc = unicodedata.normalize("NFC", norm)
        exact_index[norm_nfc] = t
        nocase_index[norm_nfc.lower()] = t

        stem = PurePosixPath(norm_nfc).stem.lower()
        stem_index.setdefault(stem, []).append(t)

    return exact_index, nocase_index, stem_index


def match_tracks(
    parse_result: M3U8ParseResult,
    session: Session,
) -> list[TrackMatchResult]:
    """Match parsed M3U8 tracks to library using batch approach.

    Cascade: exact normalized path -> case-insensitive -> fuzzy filename +/-10s.
    """
    exact_idx, nocase_idx, stem_idx = _build_path_index(session)
    results: list[TrackMatchResult] = []

    for mt in parse_result.tracks:
        # Level 1: exact normalized path
        track = exact_idx.get(mt.normalized_path)
        if track:
            results.append(TrackMatchResult(mt, track, "exact_path"))
            continue

        # Level 2: case-insensitive
        track = nocase_idx.get(mt.normalized_path.lower())
        if track:
            results.append(TrackMatchResult(mt, track, "nocase_path"))
            continue

        # Level 3: fuzzy filename + duration +/-10s
        stem = PurePosixPath(mt.normalized_path).stem.lower()
        candidates = stem_idx.get(stem, [])
        matched = None
        if candidates and mt.duration_sec > 0:
            for cand in candidates:
                if cand.duration_sec and abs(cand.duration_sec - mt.duration_sec) <= 10:
                    matched = cand
                    break
        elif candidates:
            # No duration info — take first stem match
            matched = candidates[0]

        if matched:
            results.append(TrackMatchResult(mt, matched, "fuzzy_filename"))
        else:
            results.append(TrackMatchResult(mt, None, "unmatched"))

    return results


def import_playlist(
    session: Session,
    parse_result: M3U8ParseResult,
    *,
    name: str | None = None,
    force: bool = False,
) -> ImportResult:
    """Import parsed M3U8 into a new set.

    Parameters
    ----------
    session : Session
        SQLAlchemy session.
    parse_result : M3U8ParseResult
        Parsed M3U8 data.
    name : str, optional
        Set name override (defaults to playlist_name from parse result).
    force : bool
        If True, create set even if source_ref already exists.
    """
    set_name = name or parse_result.playlist_name or "Imported Set"
    source_ref = parse_result.source_path or set_name

    # Check for duplicate set
    existing = session.query(Set).filter(Set.source_ref == source_ref).first()
    if existing and not force:
        return ImportResult(
            set_id=existing.id,
            name=existing.name or "",
            source="m3u8",
            total_tracks=len(parse_result.tracks),
            matched_count=0,
            unmatched_count=0,
            unmatched=[],
            match_methods={},
            warnings=[],
            duplicate_set_id=existing.id,
        )

    # Match tracks
    matches = match_tracks(parse_result, session)

    matched = [m for m in matches if m.matched_track is not None]
    unmatched = [m for m in matches if m.matched_track is None]

    if not matched:
        return ImportResult(
            set_id=0,
            name=set_name,
            source="m3u8",
            total_tracks=len(parse_result.tracks),
            matched_count=0,
            unmatched_count=len(unmatched),
            unmatched=[
                {"path": m.m3u8_track.path, "title": m.m3u8_track.title, "line": m.m3u8_track.line_number}
                for m in unmatched
            ],
            match_methods={},
            warnings=parse_result.warnings,
        )

    # Compute total duration from matched tracks
    total_dur_sec = sum(
        m.matched_track.duration_sec for m in matched
        if m.matched_track and m.matched_track.duration_sec
    )
    duration_min = int(total_dur_sec / 60) if total_dur_sec else None

    # Create set
    new_set = Set(
        name=set_name,
        duration_min=duration_min,
        source="m3u8",
        source_ref=source_ref,
    )
    session.add(new_set)
    session.flush()  # Get the ID

    # Add tracks at 0-based positions
    for position, m in enumerate(matched):
        session.add(SetTrack(
            set_id=new_set.id,
            position=position,
            track_id=m.matched_track.id,
        ))

    session.commit()

    # Count match methods
    method_counts: dict[str, int] = {}
    for m in matched:
        method_counts[m.match_method] = method_counts.get(m.match_method, 0) + 1

    return ImportResult(
        set_id=new_set.id,
        name=set_name,
        source="m3u8",
        total_tracks=len(parse_result.tracks),
        matched_count=len(matched),
        unmatched_count=len(unmatched),
        unmatched=[
            {"path": m.m3u8_track.path, "title": m.m3u8_track.title, "line": m.m3u8_track.line_number}
            for m in unmatched
        ],
        match_methods=method_counts,
        warnings=parse_result.warnings,
    )
