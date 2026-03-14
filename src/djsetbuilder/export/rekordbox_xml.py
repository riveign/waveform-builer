"""Export sets as Rekordbox-compatible XML playlists with optional cue points."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

from djsetbuilder.config import DATA_DIR
from djsetbuilder.db.models import Set

# Cue type mapping: internal name -> Rekordbox POSITION_MARK Type attribute
CUE_TYPE_MAP = {
    "cue": "0",
    "fadein": "1",
    "fadeout": "2",
    "load": "3",
    "loop": "4",
}


def _track_to_xml(
    track,
    position: int,
    cue_points: list[dict] | None = None,
) -> ET.Element:
    """Convert a Track to a Rekordbox XML TRACK element with optional cue points."""
    attrs = {
        "TrackID": str(track.id),
        "Name": track.title or "",
        "Artist": track.artist or "",
        "Album": track.album or "",
        "Genre": track.dir_genre or track.rb_genre or "",
        "Kind": "MP3 File",
        "TotalTime": str(int(track.duration_sec)) if track.duration_sec else "0",
        "AverageBpm": f"{track.bpm:.2f}" if track.bpm else "0.00",
        "Tonality": track.key or "",
        "Rating": str(track.rating or 0),
    }

    if track.file_path:
        attrs["Location"] = Path(track.file_path).as_uri()

    elem = ET.Element("TRACK", attrs)

    # Add cue points as POSITION_MARK child elements
    if cue_points:
        for cue in cue_points:
            mark_attrs = {
                "Name": cue.get("name", ""),
                "Type": CUE_TYPE_MAP.get(cue.get("type", "cue"), "0"),
                "Start": f"{cue.get('start', 0):.3f}",
                "Num": str(cue.get("num", -1)),
            }
            if cue.get("end") is not None:
                mark_attrs["End"] = f"{cue['end']:.3f}"
            ET.SubElement(elem, "POSITION_MARK", mark_attrs)

    return elem


def export_set_to_xml(
    set_: Set,
    output_path: str | None = None,
    transition_cues: dict[int, list[dict]] | None = None,
) -> str:
    """Export a Set as Rekordbox XML, optionally with cue points.

    Parameters
    ----------
    set_ : Set
        The set to export
    output_path : str, optional
        Output file path (default: data/<set_name>.xml)
    transition_cues : dict, optional
        Cue points per track: {track_id: [{"name", "type", "start", "end", "num"}]}
        When None, exports tracks without cue points (backward compatible).

    Returns
    -------
    str
        Path to the written XML file
    """
    root = ET.Element("DJ_PLAYLISTS", Version="1.0.0")

    # Product info
    ET.SubElement(root, "PRODUCT", Name="DJ Set Builder", Version="0.1.0")

    # Collection: all tracks in the set
    collection = ET.SubElement(root, "COLLECTION")
    tracks_in_set = sorted(set_.tracks, key=lambda st: st.position)

    for st in tracks_in_set:
        track = st.track
        cues = transition_cues.get(track.id) if transition_cues else None
        collection.append(_track_to_xml(track, st.position, cue_points=cues))

    collection.set("Entries", str(len(tracks_in_set)))

    # Playlists
    playlists = ET.SubElement(root, "PLAYLISTS")
    root_node = ET.SubElement(playlists, "NODE", Type="0", Name="ROOT", Count="1")

    playlist_node = ET.SubElement(root_node, "NODE", **{
        "Name": set_.name or "DJ Set",
        "Type": "1",
        "KeyType": "0",
        "Entries": str(len(tracks_in_set)),
    })

    for st in tracks_in_set:
        ET.SubElement(playlist_node, "TRACK", Key=str(st.track.id))

    # Write XML
    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ")

    if output_path is None:
        output_path = str(DATA_DIR / f"{set_.name or 'set'}.xml")

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    tree.write(output_path, encoding="unicode", xml_declaration=True)

    return output_path
