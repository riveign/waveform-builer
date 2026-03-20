"""Parse descriptions, comments, and chapters into structured tracklists."""

from __future__ import annotations

from dataclasses import dataclass

from kiku.hunting.parsers.common import (
    NUMBERED_LINE_RE,
    TIMESTAMPED_LINE_RE,
    YT_MUSIC_SECTION_RE,
    parse_artist_title,
    parse_remix,
)


@dataclass
class ParsedTrack:
    """A single track extracted from text."""
    position: int
    artist: str
    title: str
    remix_info: str | None = None
    original_title: str | None = None
    timestamp_sec: float | None = None
    raw_text: str = ""
    source: str = "description"  # "description", "comment", "chapter", "copyright"
    confidence: float = 0.8


def parse_description(text: str | None) -> list[ParsedTrack]:
    """Parse a set description for tracklist entries.

    Handles formats:
    - Numbered lists: "1. Artist - Title"
    - Timestamped lists: "01:23 Artist - Title"
    - Plain lists: "Artist - Title" (one per line)
    - YouTube "Music in this video" sections
    """
    if not text:
        return []

    tracks: list[ParsedTrack] = []
    lines = text.strip().split("\n")
    position = 1
    in_tracklist_section = False

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Detect tracklist section headers
        if YT_MUSIC_SECTION_RE.search(line) and len(line) < 80:
            in_tracklist_section = True
            continue

        # Try timestamped line: "01:23:45 Artist - Title"
        ts_match = TIMESTAMPED_LINE_RE.match(line)
        if ts_match:
            hours = int(ts_match.group(1) or 0)
            minutes = int(ts_match.group(2))
            seconds = int(ts_match.group(3))
            timestamp = hours * 3600 + minutes * 60 + seconds
            track_text = ts_match.group(4).strip()

            parsed = _parse_track_text(track_text)
            if parsed:
                artist, title, remix = parsed
                tracks.append(ParsedTrack(
                    position=position,
                    artist=artist,
                    title=title,
                    remix_info=remix,
                    original_title=title if remix else None,
                    timestamp_sec=timestamp,
                    raw_text=line,
                    source="description",
                    confidence=0.9,
                ))
                position += 1
                continue

        # Try numbered line: "1. Artist - Title" or "01) Artist - Title"
        num_match = NUMBERED_LINE_RE.match(line)
        if num_match:
            track_text = num_match.group(2).strip()
            parsed = _parse_track_text(track_text)
            if parsed:
                artist, title, remix = parsed
                tracks.append(ParsedTrack(
                    position=position,
                    artist=artist,
                    title=title,
                    remix_info=remix,
                    original_title=title if remix else None,
                    raw_text=line,
                    source="description",
                    confidence=0.85,
                ))
                position += 1
                continue

        # Try plain "Artist - Title" line (only if we're in a tracklist section or many such lines exist)
        parsed = _parse_track_text(line)
        if parsed and (in_tracklist_section or _looks_like_tracklist_line(line)):
            artist, title, remix = parsed
            tracks.append(ParsedTrack(
                position=position,
                artist=artist,
                title=title,
                remix_info=remix,
                original_title=title if remix else None,
                raw_text=line,
                source="description",
                confidence=0.7,
            ))
            position += 1

    return tracks


def parse_chapters(chapters: list[dict] | None) -> list[ParsedTrack]:
    """Parse YouTube chapters (auto-detected from timestamps) into tracks."""
    if not chapters:
        return []

    tracks: list[ParsedTrack] = []
    for i, ch in enumerate(chapters, 1):
        title_text = ch.get("title", "").strip()
        if not title_text:
            continue

        parsed = _parse_track_text(title_text)
        if parsed:
            artist, title, remix = parsed
            tracks.append(ParsedTrack(
                position=i,
                artist=artist,
                title=title,
                remix_info=remix,
                original_title=title if remix else None,
                timestamp_sec=ch.get("start_time"),
                raw_text=title_text,
                source="chapter",
                confidence=0.95,
            ))

    return tracks


def parse_comments(comments: list[dict] | None) -> list[ParsedTrack]:
    """Parse user comments for track identifications.

    Looks for patterns like:
    - "Track at 32:15 is Artist - Title"
    - "01:23 Artist - Title"
    - Replies with "ID?" followed by track names
    """
    if not comments:
        return []

    tracks: list[ParsedTrack] = []
    seen: set[tuple[str, str]] = set()
    position = 1

    for comment in comments:
        text = comment.get("text", "").strip()
        if not text:
            continue

        # Check each line of multi-line comments
        for line in text.split("\n"):
            line = line.strip()
            if not line or len(line) < 5:
                continue

            # Try timestamped format
            ts_match = TIMESTAMPED_LINE_RE.match(line)
            if ts_match:
                hours = int(ts_match.group(1) or 0)
                minutes = int(ts_match.group(2))
                seconds = int(ts_match.group(3))
                timestamp = hours * 3600 + minutes * 60 + seconds
                track_text = ts_match.group(4).strip()

                parsed = _parse_track_text(track_text)
                if parsed:
                    artist, title, remix = parsed
                    key = (artist.lower(), title.lower())
                    if key not in seen:
                        seen.add(key)
                        tracks.append(ParsedTrack(
                            position=position,
                            artist=artist,
                            title=title,
                            remix_info=remix,
                            original_title=title if remix else None,
                            timestamp_sec=timestamp,
                            raw_text=line,
                            source="comment",
                            confidence=0.6,
                        ))
                        position += 1

    return tracks


def parse_music_credits(credits: list[dict] | None) -> list[ParsedTrack]:
    """Parse YouTube Content ID music credits into tracks.

    Each credit is a dict with {title, artist, album} from YouTube's
    auto-detected "Music in this video" section.
    """
    if not credits:
        return []

    tracks: list[ParsedTrack] = []
    for i, credit in enumerate(credits, 1):
        title_raw = credit.get("title", "").strip()
        artist = credit.get("artist", "").strip()
        if not title_raw or not artist:
            continue

        title, remix = parse_remix(title_raw)
        tracks.append(ParsedTrack(
            position=i,
            artist=artist,
            title=title,
            remix_info=remix,
            original_title=title if remix else None,
            raw_text=f"{artist} - {title_raw}",
            source="content_id",
            confidence=0.95,
        ))

    return tracks


def _track_signature(track: ParsedTrack) -> str:
    """Full artist+title string for fuzzy comparison."""
    return f"{track.artist} {track.title}".lower().strip()


def merge_tracklists(*tracklists: list[ParsedTrack]) -> list[ParsedTrack]:
    """Merge multiple tracklists, deduplicating by artist+title.

    Uses fuzzy matching (>=85% similarity) to catch variants like
    "Matrixxman - Hong Kong (Night)" vs "Matrixxman Hong Kong - Night".
    Higher confidence sources take priority. Position is renumbered.
    """
    from thefuzz import fuzz

    FUZZY_THRESHOLD = 85

    merged_tracks: list[ParsedTrack] = []
    signatures: list[str] = []

    for tracks in tracklists:
        for track in tracks:
            sig = _track_signature(track)

            # Check for fuzzy match against existing entries
            matched_idx = None
            for i, existing_sig in enumerate(signatures):
                if fuzz.ratio(sig, existing_sig) >= FUZZY_THRESHOLD:
                    matched_idx = i
                    break

            if matched_idx is not None:
                existing = merged_tracks[matched_idx]
                # Replace if higher confidence, but preserve timestamp from either source
                if track.confidence > existing.confidence:
                    if track.timestamp_sec is None and existing.timestamp_sec is not None:
                        track.timestamp_sec = existing.timestamp_sec
                    merged_tracks[matched_idx] = track
                    signatures[matched_idx] = sig
                elif existing.timestamp_sec is None and track.timestamp_sec is not None:
                    existing.timestamp_sec = track.timestamp_sec
            else:
                merged_tracks.append(track)
                signatures.append(sig)

    # Sort by timestamp if available, otherwise by original position
    merged_tracks.sort(
        key=lambda t: (t.timestamp_sec if t.timestamp_sec is not None else float("inf"), t.position),
    )

    # Renumber
    for i, track in enumerate(merged_tracks, 1):
        track.position = i

    return merged_tracks


def _parse_track_text(text: str) -> tuple[str, str, str | None] | None:
    """Parse a track string into (artist, title, remix_info).
    Returns None if the text doesn't look like a track.
    """
    at = parse_artist_title(text)
    if not at:
        return None

    artist, title_raw = at

    # Skip if artist or title is too short or looks like a URL/header
    if len(artist) < 2 or len(title_raw) < 2:
        return None
    if artist.startswith("http") or title_raw.startswith("http"):
        return None

    title, remix = parse_remix(title_raw)
    return artist, title, remix


def _looks_like_tracklist_line(line: str) -> bool:
    """Heuristic: does this line look like a track entry?"""
    # Must contain " - " separator
    if " - " not in line and " – " not in line and " — " not in line:
        return False
    # Not too long (URLs, paragraphs, prose sentences)
    if len(line) > 120:
        return False
    # Not a URL
    if line.startswith("http"):
        return False
    # Reject lines with too many words (prose, not track names)
    word_count = len(line.split())
    if word_count > 15:
        return False
    return True
