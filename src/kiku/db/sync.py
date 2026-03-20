"""Sync Rekordbox library to local SQLite database."""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path

import click
from rich.console import Console
from rich.progress import Progress
from sqlalchemy.orm import Session

from kiku.db.models import Track, get_session
from kiku.parsing.directory import parse_track_path

console = Console()

# Known mount-point mappings between macOS and Linux.
# Rekordbox stores macOS paths; on Linux the same drive mounts differently.
_PATH_ALIASES: list[tuple[str, str]] = [
    ("/Volumes/", "/run/media/mantis/"),
]


def _normalize_path(path: str) -> str:
    """Return a canonical form of *path* for cross-platform matching.

    Replaces known macOS mount prefixes with their Linux equivalents so that
    a track stored under ``/Volumes/SSD/…`` matches ``/run/media/mantis/SSD/…``.
    """
    for mac_prefix, linux_prefix in _PATH_ALIASES:
        if path.startswith(mac_prefix):
            return linux_prefix + path[len(mac_prefix):]
        if path.startswith(linux_prefix):
            return linux_prefix + path[len(linux_prefix):]
    return path


def _file_hash(path: str, chunk_size: int = 1024 * 1024) -> str | None:
    """MD5 hash of first 1MB for change detection."""
    try:
        h = hashlib.md5()
        with open(path, "rb") as f:
            h.update(f.read(chunk_size))
        return h.hexdigest()
    except (OSError, IOError):
        return None


def _safe_int(val) -> int | None:
    """Convert a possibly-string value to int."""
    if val is None:
        return None
    try:
        return int(val)
    except (ValueError, TypeError):
        return None


def _parse_artist_from_title(title: str) -> tuple[str, str] | None:
    """Try to extract artist from an 'Artist - Title' pattern.

    Returns (artist, clean_title) or None if no separator found.
    Only splits on the first ' - ' to handle titles with dashes.
    """
    if not title or " - " not in title:
        return None
    parts = title.split(" - ", 1)
    artist = parts[0].strip()
    clean_title = parts[1].strip()
    if not artist or not clean_title:
        return None
    return artist, clean_title


def _sync_playlist_tags(db, session: Session) -> None:
    """Sync Rekordbox playlist membership as tags on tracks."""
    playlists = list(db.get_playlist())
    playlist_names = {pl.ID: pl.Name for pl in playlists if pl.Name}

    # Build content_id -> list of playlist names
    content_playlists: dict[str, list[str]] = {}
    for song in db.get_playlist_songs():
        pl_name = playlist_names.get(song.PlaylistID)
        if pl_name:
            cid = str(song.ContentID)
            content_playlists.setdefault(cid, []).append(pl_name)

    # Update tracks
    updated = 0
    for rb_id_str, pl_names in content_playlists.items():
        track = session.query(Track).filter_by(rb_id=rb_id_str).first()
        if track:
            track.playlist_tags = json.dumps(pl_names)
            updated += 1

    console.print(f"  Tagged {updated} tracks with playlist membership")


def _open_rekordbox(db_path: str | None = None):
    """Open Rekordbox database, returning the db object or None on failure."""
    try:
        from pyrekordbox import Rekordbox6Database
    except ImportError:
        console.print("[red]pyrekordbox not installed. Run: pip install 'kiku[rekordbox]'[/]")
        return None

    console.print("[bold]Listening to your Rekordbox library...[/]")
    try:
        kwargs = {"path": db_path} if db_path else {}
        if not db_path and sys.platform != "darwin":
            console.print(
                "[yellow]Rekordbox auto-discovery only works on macOS.\n"
                "Use --db-path to specify the master.db location.[/]"
            )
            return None
        return Rekordbox6Database(**kwargs)
    except Exception as e:
        console.print(f"[red]Couldn't open Rekordbox: {e}[/]")
        return None


def _process_tracks(
    db,
    session: Session,
    compute_hashes: bool = False,
    dry_run: bool = False,
) -> dict:
    """Core sync loop — reads Rekordbox, writes to session.

    When *dry_run* is True the session is rolled back instead of committed
    and extra detail counters are returned for the preview summary.

    Returns dict with sync stats.
    """
    content = db.get_content()

    added = 0
    updated = 0
    skipped = 0
    total = 0
    artists_parsed = 0
    labels_added = 0

    progress_label = "[cyan]Reading tracks..." if dry_run else "[cyan]Syncing tracks..."

    with Progress() as progress:
        all_tracks = list(content)
        total = len(all_tracks)
        task = progress.add_task(progress_label, total=total)

        for rb_track in all_tracks:
            progress.advance(task)

            rb_id = str(rb_track.ID)
            if not rb_id:
                skipped += 1
                continue

            # Build file path — FolderPath is already the full path including filename
            file_path = rb_track.FolderPath or rb_track.FileNameL or ""

            # Parse directory metadata
            dir_meta = parse_track_path(file_path) if file_path else None

            # Compute file hash if requested and file exists
            file_hash = None
            if compute_hashes and file_path:
                file_hash = _file_hash(file_path)

            now = datetime.now().isoformat()

            # Check if track exists — first by rb_id, then by normalised file path
            existing = session.query(Track).filter_by(rb_id=rb_id).first()

            if not existing and file_path:
                # Fallback: match by normalised file path (handles macOS ↔ Linux mounts)
                norm = _normalize_path(file_path)
                for candidate in (file_path, norm):
                    existing = session.query(Track).filter_by(file_path=candidate).first()
                    if existing:
                        break

            # Parse artist from title when Rekordbox has no artist
            title = rb_track.Title
            artist = rb_track.ArtistName
            if not artist and title:
                parsed = _parse_artist_from_title(title)
                if parsed:
                    artist, title = parsed
                    artists_parsed += 1

            # Track label additions
            if rb_track.LabelName and (not existing or not getattr(existing, "label", None)):
                labels_added += 1

            track_data = dict(
                title=title,
                artist=artist,
                album=rb_track.AlbumName,
                label=rb_track.LabelName,
                rb_genre=rb_track.GenreName,
                dir_genre=dir_meta.genre if dir_meta else None,
                dir_energy=dir_meta.energy if dir_meta else None,
                bpm=rb_track.BPM / 100.0 if rb_track.BPM else None,  # Rekordbox stores BPM * 100
                key=rb_track.KeyName,
                rating=rb_track.Rating,
                color=rb_track.ColorName,
                comment=rb_track.Commnt,
                duration_sec=rb_track.Length,
                file_path=file_path,
                file_hash=file_hash,
                date_added=rb_track.DateCreated,
                play_count=_safe_int(rb_track.DJPlayCount),
                release_year=rb_track.ReleaseYear,
                acquired_month=dir_meta.acquired_month if dir_meta else None,
                last_synced=now,
            )

            if existing:
                # Always set rb_id (may be missing on tracks matched by path)
                existing.rb_id = rb_id
                for k, v in track_data.items():
                    setattr(existing, k, v)
                updated += 1
            else:
                track = Track(rb_id=rb_id, **track_data)
                session.add(track)
                added += 1

    if dry_run:
        session.rollback()
    else:
        session.commit()
        # Sync playlist membership
        console.print("[bold]Syncing playlist tags...[/]")
        _sync_playlist_tags(db, session)
        session.commit()

    return {
        "total": total,
        "added": added,
        "updated": updated,
        "skipped": skipped,
        "artists_parsed": artists_parsed,
        "labels_added": labels_added,
    }


def _print_preview(stats: dict) -> None:
    """Display a human-friendly sync preview."""
    console.print()
    console.print("[bold]Sync preview:[/]")
    console.print(f"  New tracks:   {stats['added']:>6,}")
    console.print(f"  Updated:      {stats['updated']:>6,}")
    console.print(f"  Unchanged:    {stats['skipped']:>6,}")

    details = []
    if stats["added"]:
        details.append(f"  - {stats['added']:,} new tracks from Rekordbox")
    if stats["artists_parsed"]:
        details.append(f"  - {stats['artists_parsed']:,} artist names parsed from titles")
    if stats["labels_added"]:
        details.append(f"  - {stats['labels_added']:,} labels added")

    if details:
        console.print()
        console.print("[bold]Changes include:[/]")
        for line in details:
            console.print(line)
    console.print()


def sync_rekordbox(
    compute_hashes: bool = False,
    db_path: str | None = None,
    dry_run: bool = False,
    yes: bool = False,
) -> dict:
    """Import tracks from Rekordbox master.db into local database.

    When *dry_run* is True, shows what would change without writing.
    When *yes* is False (default), a preview is shown and the DJ must
    confirm before any writes happen.

    Returns dict with sync stats.
    """
    db = _open_rekordbox(db_path=db_path)
    if db is None:
        return {"error": "Could not open Rekordbox database"}

    session = get_session()

    # --- Dry-run / preview pass ---
    if not yes:
        stats = _process_tracks(
            db, session, compute_hashes=compute_hashes, dry_run=True
        )
        _print_preview(stats)

        if dry_run:
            db.close()
            console.print("[dim]Dry run — nothing was written.[/]")
            return stats

        if not click.confirm("Ready to sync?", default=False):
            db.close()
            console.print("[dim]Sync cancelled — your library is untouched.[/]")
            return {**stats, "cancelled": True}

    # --- Write pass ---
    stats = _process_tracks(
        db, session, compute_hashes=compute_hashes, dry_run=False
    )
    db.close()

    console.print(f"\n[green]Sync complete![/] {stats['total']:,} tracks processed")
    console.print(
        f"  Added: {stats['added']:,}, Updated: {stats['updated']:,}, "
        f"Skipped: {stats['skipped']:,}"
    )

    return stats
