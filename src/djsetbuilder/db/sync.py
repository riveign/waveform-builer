"""Sync Rekordbox library to local SQLite database."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.progress import Progress
from sqlalchemy.orm import Session

from djsetbuilder.db.models import Track, get_session
from djsetbuilder.parsing.directory import parse_track_path

console = Console()


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


def sync_rekordbox(compute_hashes: bool = False) -> dict:
    """Import tracks from Rekordbox master.db into local database.

    Returns dict with sync stats.
    """
    try:
        from pyrekordbox import Rekordbox6Database
    except ImportError:
        console.print("[red]pyrekordbox not installed. Run: pip install pyrekordbox[/]")
        return {"error": "pyrekordbox not installed"}

    console.print("[bold]Opening Rekordbox database...[/]")
    try:
        db = Rekordbox6Database()
    except Exception as e:
        console.print(f"[red]Failed to open Rekordbox database: {e}[/]")
        return {"error": str(e)}

    session = get_session()
    content = db.get_content()

    added = 0
    updated = 0
    skipped = 0
    total = 0

    with Progress() as progress:
        # Count total first
        all_tracks = list(content)
        total = len(all_tracks)
        task = progress.add_task("[cyan]Syncing tracks...", total=total)

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

            # Check if track exists
            existing = session.query(Track).filter_by(rb_id=rb_id).first()

            track_data = dict(
                title=rb_track.Title,
                artist=rb_track.ArtistName,
                album=rb_track.AlbumName,
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
                for k, v in track_data.items():
                    setattr(existing, k, v)
                updated += 1
            else:
                track = Track(rb_id=rb_id, **track_data)
                session.add(track)
                added += 1

    session.commit()

    # Sync playlist membership
    console.print("[bold]Syncing playlist tags...[/]")
    _sync_playlist_tags(db, session)

    session.commit()
    db.close()

    stats = {
        "total": total,
        "added": added,
        "updated": updated,
        "skipped": skipped,
    }

    console.print(f"\n[green]Sync complete![/] {total} tracks processed")
    console.print(f"  Added: {added}, Updated: {updated}, Skipped: {skipped}")

    return stats
