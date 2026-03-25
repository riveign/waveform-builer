"""Export sets as Rekordbox-compatible XML playlists with optional cue points.

Uses pyrekordbox's RekordboxXml class for proper path encoding, rating
mapping, and validated attribute types.
"""

from __future__ import annotations

from pathlib import Path

from pyrekordbox.rbxml import RekordboxXml

from kiku.config import DATA_DIR
from kiku.db.models import Set
from kiku.export.utils import export_path

# File extension -> Rekordbox Kind string
_KIND_MAP: dict[str, str] = {
    ".mp3": "MP3 File",
    ".flac": "FLAC File",
    ".wav": "WAV File",
    ".aiff": "AIFF File",
    ".aif": "AIFF File",
    ".m4a": "M4A File",
    ".ogg": "OGG File",
    ".wma": "WMA File",
    ".alac": "ALAC File",
}



def _detect_kind(file_path: str) -> str:
    """Return the Rekordbox ``Kind`` string based on file extension."""
    ext = Path(file_path).suffix.lower()
    return _KIND_MAP.get(ext, "MP3 File")


def export_set_to_xml(
    set_: Set,
    output_path: str | None = None,
    transition_cues: dict[int, list[dict]] | None = None,
) -> str:
    """Export a Set as Rekordbox XML, optionally with cue points.

    Parameters
    ----------
    set_ : Set
        The set to export (with eager-loaded tracks).
    output_path : str, optional
        Output file path (default: data/<set_name>.xml).
    transition_cues : dict, optional
        Cue points per track: ``{track_id: [{"name", "type", "start", "end", "num"}]}``.
        When None, exports tracks without cue points (backward compatible).

    Returns
    -------
    str
        Path to the written XML file.
    """
    xml = RekordboxXml(name="Kiku", version="0.1.0", company="")

    tracks_in_set = sorted(set_.tracks, key=lambda st: st.position)
    playlist = xml.add_playlist(set_.name or "DJ Set")

    for st in tracks_in_set:
        track = st.track

        # --- Gap 2: reverse path alias for macOS ---
        location = export_path(track.file_path, "macos") if track.file_path else ""

        # --- Gap 1: use rb_id when available ---
        track_id = int(track.rb_id) if track.rb_id else track.id

        # --- Gap 3: detect file format ---
        kind = _detect_kind(track.file_path) if track.file_path else "MP3 File"

        # Build kwargs — only include non-None values to avoid serialisation
        # errors from pyrekordbox (None values crash xml.etree).
        kwargs: dict = {
            "TrackID": track_id,
            "Name": track.title or "",
            "Artist": track.artist or "",
            "Kind": kind,
            "TotalTime": int(track.duration_sec) if track.duration_sec else 0,
            "AverageBpm": round(track.bpm, 2) if track.bpm else 0.0,
            "Tonality": track.key or "",
        }

        # --- Gap 4: add missing fields ---
        if track.album:
            kwargs["Album"] = track.album
        if track.label:
            kwargs["Label"] = track.label

        genre = track.dir_genre or track.rb_genre
        if genre:
            kwargs["Genre"] = genre

        if track.play_count:
            kwargs["PlayCount"] = track.play_count
        if track.comment:
            kwargs["Comments"] = track.comment

        # --- Gap 5: use pyrekordbox's add_track for proper encoding ---
        rb_track = xml.add_track(location, **kwargs)

        # Rating must go through set() to trigger the SETTER mapping (0-5 → 0/51/102/153/204/255).
        # add_track kwargs bypass the setter and store the raw value.
        if track.rating is not None and track.rating > 0:
            rb_track.set("Rating", track.rating)

        # Add cue points
        if transition_cues and track.id in transition_cues:
            for cue in transition_cues[track.id]:
                mark_kwargs: dict = {
                    "Name": cue.get("name", ""),
                    "Type": cue.get("type", "cue"),
                    "Start": cue.get("start", 0.0),
                    "Num": cue.get("num", -1),
                }
                if cue.get("end") is not None:
                    mark_kwargs["End"] = cue["end"]
                rb_track.add_mark(**mark_kwargs)

        # Add track to playlist
        playlist.add_track(rb_track.TrackID)

    # Write XML
    if output_path is None:
        output_path = str(DATA_DIR / f"{set_.name or 'set'}.xml")

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    xml.save(output_path)

    return output_path
