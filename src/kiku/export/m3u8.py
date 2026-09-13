"""Export sets as M3U8 playlists for Rekordbox import.

M3U8 carries track order, duration, and display title -- exactly what
Rekordbox needs for playlist import. Tracks must already exist in
Rekordbox's collection at the file paths listed in the M3U8.
"""

from __future__ import annotations

from pathlib import Path

from kiku.config import DATA_DIR
from kiku.db.models import Set
from kiku.export.utils import (
    ExportResult,
    SkippedTrack,
    export_path,
    sanitize_filename,
    skip_reason,
)


def export_set_to_m3u8(
    set_: Set,
    output_path: str | None = None,
    *,
    target_platform: str = "macos",
    with_metadata: bool = False,
) -> ExportResult:
    """Export a Set as an M3U8 playlist file.

    Parameters
    ----------
    set_ : Set
        The set to export (with eager-loaded tracks via set_.tracks).
    output_path : str, optional
        Where to write the .m3u8 file. Default: data/<set_name>.m3u8.
    target_platform : str
        Target platform for path aliasing ("macos" or "linux").
    with_metadata : bool
        If True, include Kiku metadata as comment lines (BPM, key, energy,
        rating). These are ignored by all players but preserved for potential
        Kiku re-import.

    Returns
    -------
    ExportResult
        The written file's path, plus any tracks left out because they have no
        file — records on the shelf get a comment line naming the side instead.
    """
    tracks_in_set = sorted(set_.tracks, key=lambda st: st.position)
    set_name = set_.name or "set"

    lines: list[str] = ["#EXTM3U"]
    skipped: list[SkippedTrack] = []

    for st in tracks_in_set:
        track = st.track

        # A fileless track can't carry a path, and an #EXTINF without one
        # corrupts the playlist. M3U8 has comments, so leave a note instead —
        # Rekordbox ignores it, the DJ reading the file sees what to pull.
        reason = skip_reason(track)
        if reason:
            skipped.append(
                SkippedTrack(
                    track_id=track.id,
                    title=track.title or "Unknown Title",
                    artist=track.artist,
                    reason=reason,
                )
            )
            lines.append(
                f"# kiku:vinyl {track.artist or 'Unknown Artist'} - "
                f"{track.title or 'Unknown Title'} ({reason})"
            )
            continue

        # Duration: integer seconds, -1 if unknown
        duration = int(track.duration_sec) if track.duration_sec else -1

        # Display title: Artist - Title
        artist = track.artist or "Unknown Artist"
        title = track.title or "Unknown Title"
        display = f"{artist} - {title}"

        lines.append(f"#EXTINF:{duration},{display}")

        # Optional Kiku metadata comment
        if with_metadata:
            meta_parts: list[str] = []
            if track.bpm:
                meta_parts.append(f"bpm={round(track.bpm, 2)}")
            if track.key:
                meta_parts.append(f"key={track.key}")
            if track.energy is not None:
                meta_parts.append(f"energy={track.energy}")
            if track.rating is not None and track.rating > 0:
                meta_parts.append(f"rating={track.rating}")
            # Genre last — may contain spaces, so it's always the final field
            genre = track.dir_genre or track.rb_genre
            if genre:
                meta_parts.append(f"genre={genre}")
            if meta_parts:
                lines.append(f"# kiku:{' '.join(meta_parts)}")

        # File path: absolute, forward slashes, platform-aliased
        file_path = export_path(track.file_path, target_platform)
        file_path = file_path.replace("\\", "/")
        lines.append(file_path)

    # Write file
    if output_path is None:
        output_path = str(DATA_DIR / f"{sanitize_filename(set_name)}.m3u8")

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return ExportResult(path=str(out), skipped=skipped)
