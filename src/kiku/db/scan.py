"""Scan filesystem for audio files and import into the local SQLite database.

This is the Rekordbox-free alternative to `kiku sync`. It walks MUSIC_ROOTS,
reads embedded tags via mutagen, and parses genre/energy from folder names.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from sqlalchemy.orm import Session

from kiku.config import MUSIC_ROOTS
from kiku.db.models import Track, get_session
from kiku.db.paths import normalize_path
from kiku.parsing.directory import parse_track_path

console = Console()

# Supported audio extensions (lowercase, with dot)
AUDIO_EXTENSIONS = frozenset({
    ".mp3", ".flac", ".wav", ".aiff", ".aif", ".m4a", ".ogg", ".wma",
})


def _read_tags(file_path: Path) -> dict:
    """Extract metadata from audio file tags via mutagen.

    Returns a dict with available fields: title, artist, album, genre, bpm,
    key, duration_sec, bitrate, date/year.
    """
    from mutagen import File as MutagenFile

    result: dict = {}

    try:
        audio = MutagenFile(file_path, easy=False)
    except Exception:
        return result

    if audio is None:
        return result

    # Duration is available on most formats
    if audio.info and hasattr(audio.info, "length"):
        result["duration_sec"] = audio.info.length
    if audio.info and hasattr(audio.info, "bitrate"):
        result["bitrate"] = audio.info.bitrate

    # Try easy tags first for uniform access
    try:
        from mutagen import File as MutagenFile
        easy = MutagenFile(file_path, easy=True)
        if easy and easy.tags:
            tags = easy.tags
            result["title"] = _first_tag(tags, "title")
            result["artist"] = _first_tag(tags, "artist")
            result["album"] = _first_tag(tags, "album")
            result["genre"] = _first_tag(tags, "genre")
            result["date"] = _first_tag(tags, "date")
            result["bpm"] = _parse_float(_first_tag(tags, "bpm"))
            return result
    except Exception:
        pass

    # Fallback: read raw tags for formats that don't support easy mode well
    if audio.tags is None:
        return result

    tags = audio.tags

    # ID3 tags (MP3, AIFF)
    if hasattr(tags, "getall"):
        result["title"] = _id3_text(tags, "TIT2")
        result["artist"] = _id3_text(tags, "TPE1")
        result["album"] = _id3_text(tags, "TALB")
        result["genre"] = _id3_text(tags, "TCON")
        result["bpm"] = _parse_float(_id3_text(tags, "TBPM"))
        result["key"] = _id3_text(tags, "TKEY")
        result["date"] = _id3_text(tags, "TDRC") or _id3_text(tags, "TYER")
    else:
        # Vorbis/FLAC/Ogg style
        result["title"] = _vorbis_tag(tags, "title")
        result["artist"] = _vorbis_tag(tags, "artist")
        result["album"] = _vorbis_tag(tags, "album")
        result["genre"] = _vorbis_tag(tags, "genre")
        result["bpm"] = _parse_float(_vorbis_tag(tags, "bpm") or _vorbis_tag(tags, "TBPM"))
        result["key"] = _vorbis_tag(tags, "TKEY") or _vorbis_tag(tags, "initialkey")
        result["date"] = _vorbis_tag(tags, "date")

    return result


def _first_tag(tags, key: str) -> str | None:
    """Get the first value for a tag key (easy mode)."""
    vals = tags.get(key)
    if vals and isinstance(vals, list) and len(vals) > 0:
        return str(vals[0]).strip() or None
    return None


def _id3_text(tags, frame_id: str) -> str | None:
    """Get text from an ID3 frame."""
    frames = tags.getall(frame_id)
    if frames:
        val = str(frames[0])
        return val.strip() or None
    return None


def _vorbis_tag(tags, key: str) -> str | None:
    """Get a tag value from Vorbis-style tags."""
    vals = tags.get(key)
    if vals and isinstance(vals, list) and len(vals) > 0:
        return str(vals[0]).strip() or None
    if isinstance(vals, str):
        return vals.strip() or None
    return None


def _parse_float(val: str | None) -> float | None:
    """Parse a string to float, returning None on failure."""
    if val is None:
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def _parse_year(val: str | None) -> int | None:
    """Extract a 4-digit year from a date string."""
    if val is None:
        return None
    import re
    m = re.search(r"\d{4}", val)
    if m:
        return int(m.group())
    return None


def discover_audio_files(roots: list[Path]) -> list[Path]:
    """Recursively find all audio files under the given root directories."""
    files: list[Path] = []
    for root in roots:
        if not root.exists():
            console.print(f"[yellow]Warning: {root} does not exist, skipping[/]")
            continue
        for path in root.rglob("*"):
            if path.is_file() and path.suffix.lower() in AUDIO_EXTENSIONS:
                # Skip macOS resource fork files
                if path.name.startswith("._"):
                    continue
                files.append(path)
    return files


def _build_path_index(session: Session) -> dict[str, Track]:
    """Build a normalized-path -> Track lookup for existing tracks.

    This allows scan to match files against tracks that were imported via
    Rekordbox sync (which stores macOS /Volumes/... paths) even when scanning
    on Linux (which sees /run/media/mantis/... paths).
    """
    index: dict[str, Track] = {}
    for track in session.query(Track).all():
        if track.file_path:
            norm = normalize_path(track.file_path)
            index[norm] = track
    return index


def _process_files(
    audio_files: list[Path],
    session: Session,
    path_index: dict[str, Track],
    force: bool = False,
    dry_run: bool = False,
) -> dict:
    """Core scan loop -- reads files, matches to existing tracks, imports new ones.

    When *dry_run* is True the session is rolled back and no writes happen.

    Returns dict with scan stats.
    """
    added = 0
    updated = 0
    skipped = 0
    errors = 0
    total = len(audio_files)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        label = "[cyan]Reading tracks..." if dry_run else "[cyan]Scanning tracks..."
        task = progress.add_task(label, total=total)

        for file_path in audio_files:
            progress.advance(task)

            try:
                file_path_str = str(file_path)
                norm_path = normalize_path(file_path_str)

                # Check for existing track by normalized path
                existing = path_index.get(norm_path)

                if existing and not force:
                    skipped += 1
                    continue

                # Read audio tags
                tags = _read_tags(file_path)

                # Parse directory metadata
                dir_meta = parse_track_path(file_path)

                # Use tag title or fall back to filename parsing
                title = tags.get("title")
                artist = tags.get("artist")

                # Parse "Artist - Title [Label]" from filename when tags are missing
                if not artist and " - " in file_path.stem:
                    parts = file_path.stem.split(" - ", 1)
                    artist = parts[0].strip()
                    if not title:
                        title = parts[1].strip()

                if not title:
                    title = file_path.stem
                album = tags.get("album")
                tag_genre = tags.get("genre")
                bpm = tags.get("bpm")
                key = tags.get("key")
                duration_sec = tags.get("duration_sec")
                release_year = _parse_year(tags.get("date"))

                now = datetime.now().isoformat()

                track_data = dict(
                    title=title,
                    artist=artist,
                    album=album,
                    rb_genre=tag_genre,  # Use rb_genre for file-embedded genre
                    dir_genre=dir_meta.genre,
                    dir_energy=dir_meta.energy,
                    bpm=bpm,
                    key=key,
                    duration_sec=duration_sec,
                    file_path=file_path_str,
                    release_year=release_year,
                    acquired_month=dir_meta.acquired_month,
                    last_synced=now,
                )

                if existing:
                    if not dry_run:
                        for k, v in track_data.items():
                            setattr(existing, k, v)
                    updated += 1
                else:
                    if not dry_run:
                        track = Track(**track_data)
                        session.add(track)
                    added += 1

            except Exception as e:
                errors += 1
                console.print(f"[red]Error processing {file_path.name}: {e}[/]")

    if dry_run:
        session.rollback()
    else:
        session.commit()

    return {
        "total": total,
        "added": added,
        "updated": updated,
        "skipped": skipped,
        "errors": errors,
    }


def _print_preview(stats: dict) -> None:
    """Display a human-friendly scan preview."""
    console.print()
    console.print("[bold]Scan preview:[/]")
    console.print(f"  New tracks:   {stats['added']:>6,}")
    console.print(f"  Updated:      {stats['updated']:>6,}")
    console.print(f"  Already here: {stats['skipped']:>6,}")
    if stats["errors"]:
        console.print(f"  Errors:       {stats['errors']:>6,}")
    console.print()


def scan_filesystem(
    roots: list[Path] | None = None,
    dry_run: bool = False,
    force: bool = False,
    yes: bool = False,
) -> dict:
    """Scan filesystem for audio files and import into the database.

    When *dry_run* is True, shows what would change without writing.
    When *yes* is False (default), a preview is shown and the DJ must
    confirm before any writes happen.

    Args:
        roots: Directories to scan. Defaults to MUSIC_ROOTS from config.
        dry_run: If True, show what would be imported without writing to DB.
        force: If True, re-import tracks that already exist (update metadata).
        yes: If True, skip confirmation prompt.

    Returns:
        Dict with scan stats: total, added, updated, skipped, errors.
    """
    if roots is None:
        roots = MUSIC_ROOTS

    console.print(f"[bold]Exploring your music folders...[/]")
    for root in roots:
        console.print(f"  [dim]{root}[/]")

    # Discover files
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        progress.add_task("[cyan]Discovering audio files...", total=None)
        audio_files = discover_audio_files(roots)

    console.print(f"[bold]Found {len(audio_files)} audio files[/]\n")

    if not audio_files:
        return {"total": 0, "added": 0, "updated": 0, "skipped": 0, "errors": 0}

    session = get_session()

    # Build normalized path index for cross-platform matching
    path_index = _build_path_index(session)

    # --- Preview pass (unless --yes) ---
    if not yes:
        stats = _process_files(
            audio_files, session, path_index, force=force, dry_run=True,
        )
        _print_preview(stats)

        if dry_run:
            console.print("[dim]Dry run — nothing was written.[/]")
            return stats

        if not click.confirm("Ready to scan?", default=False):
            console.print("[dim]Scan cancelled — your library is untouched.[/]")
            return {**stats, "cancelled": True}

    # --- Write pass ---
    stats = _process_files(
        audio_files, session, path_index, force=force, dry_run=False,
    )

    console.print()
    console.print(f"[bold green]Scan complete![/] {stats['total']:,} files processed")
    console.print(
        f"  Added: {stats['added']:,}, Updated: {stats['updated']:,}, "
        f"Skipped: {stats['skipped']:,}, Errors: {stats['errors']}"
    )

    return stats
