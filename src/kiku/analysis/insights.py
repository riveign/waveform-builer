"""Library intelligence queries — pure data, no rendering."""

from __future__ import annotations

from collections import defaultdict

from sqlalchemy import func
from sqlalchemy.orm import Session

from kiku.db.models import AudioFeatures, Track
from kiku.setbuilder.camelot import parse_camelot
from kiku.setbuilder.constraints import ENERGY_TAG_VALUES
from kiku.setbuilder.scoring import GENRE_FAMILIES, genre_to_family


def camelot_distribution(session: Session) -> dict[int, dict[str, int]]:
    """Count tracks per Camelot position (1-12) and mode (A/B).

    Returns: {1: {"A": 45, "B": 32}, 2: {...}, ...}
    """
    tracks = session.query(Track.key).filter(Track.key.isnot(None)).all()
    dist: dict[int, dict[str, int]] = {
        n: {"A": 0, "B": 0} for n in range(1, 13)
    }
    for (key,) in tracks:
        parsed = parse_camelot(key)
        if parsed:
            num, letter = parsed
            dist[num][letter] += 1
    return dist


def bpm_histogram(
    session: Session,
    bin_width: float = 2.0,
    bpm_min: float = 90.0,
    bpm_max: float = 200.0,
) -> list[dict]:
    """BPM histogram binned by genre family.

    Returns: [{"bin_center": 124.0, "family": "Techno", "count": 12}, ...]
    """
    tracks = (
        session.query(Track.bpm, Track.dir_genre, Track.rb_genre)
        .filter(Track.bpm.isnot(None), Track.bpm >= bpm_min, Track.bpm <= bpm_max)
        .all()
    )

    bins: dict[tuple[float, str], int] = defaultdict(int)
    for bpm, dir_genre, rb_genre in tracks:
        genre = dir_genre or rb_genre
        family = genre_to_family(genre).capitalize()
        center = round((bpm // bin_width) * bin_width + bin_width / 2, 1)
        bins[(center, family)] += 1

    return [
        {"bin_center": center, "family": family, "count": count}
        for (center, family), count in sorted(bins.items())
    ]


def energy_genre_heatmap(session: Session) -> dict[str, dict[str, int]]:
    """Energy level x genre family matrix.

    Returns: {"Techno": {"low": 5, "warmup": 12, ...}, ...}
    """
    tracks = (
        session.query(Track.dir_genre, Track.rb_genre, Track.dir_energy)
        .filter(Track.dir_energy.isnot(None))
        .all()
    )

    matrix: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for dir_genre, rb_genre, energy in tracks:
        genre = dir_genre or rb_genre
        family = genre_to_family(genre).capitalize()
        matrix[family][energy.lower()] += 1

    return {k: dict(v) for k, v in matrix.items()}


def mood_quadrant(session: Session) -> list[dict]:
    """Mood scatter data: happy-sad (x) vs aggressive-relaxed (y).

    Returns: [{"title": ..., "artist": ..., "x": float, "y": float,
               "energy": float, "genre_family": str}, ...]
    """
    tracks = (
        session.query(Track, AudioFeatures)
        .join(AudioFeatures)
        .filter(
            AudioFeatures.mood_happy.isnot(None),
            AudioFeatures.mood_sad.isnot(None),
            AudioFeatures.mood_aggressive.isnot(None),
            AudioFeatures.mood_relaxed.isnot(None),
        )
        .all()
    )

    results = []
    for track, af in tracks:
        genre = track.dir_genre or track.rb_genre
        results.append({
            "title": track.title or "?",
            "artist": track.artist or "?",
            "x": af.mood_happy - af.mood_sad,
            "y": af.mood_aggressive - af.mood_relaxed,
            "energy": af.energy or 0.5,
            "genre_family": genre_to_family(genre).capitalize(),
        })

    return results


def library_gaps(session: Session) -> dict[str, list[dict]]:
    """Identify gaps in the library ranked by impact.

    Returns: {
        "camelot_gaps": [{"position": "3A", "count": 2, "impact": 85,
                          "explanation": "..."}],
        "bpm_gaps": [{"range": "138-142", "count": 3}],
        "energy_gaps": [{"level": "warmup", "count": 5}],
    }
    """
    # ── Camelot gaps ──
    cam_dist = camelot_distribution(session)

    # Flatten to totals per position
    totals: dict[str, int] = {}
    for num in range(1, 13):
        for letter in ("A", "B"):
            totals[f"{num}{letter}"] = cam_dist[num][letter]

    # Impact = number of tracks in adjacent positions that would gain a mix partner
    def _adjacent_keys(pos: str) -> list[str]:
        parsed = parse_camelot(pos)
        if not parsed:
            return []
        num, letter = parsed
        adj = []
        # Same letter, +/-1
        for d in (-1, 1):
            n = ((num - 1 + d) % 12) + 1
            adj.append(f"{n}{letter}")
        # Mode switch at same number
        other = "B" if letter == "A" else "A"
        adj.append(f"{num}{other}")
        return adj

    camelot_gaps = []
    for pos, count in sorted(totals.items(), key=lambda x: x[1]):
        if count >= 10:
            continue
        adjacent_count = sum(totals.get(a, 0) for a in _adjacent_keys(pos))
        impact = adjacent_count  # more neighbors wanting this key = higher impact
        explanation = (
            f"{count} tracks in {pos}, but {adjacent_count} tracks in adjacent keys "
            f"({', '.join(_adjacent_keys(pos))}) would benefit from more {pos} options"
        )
        camelot_gaps.append({
            "position": pos,
            "count": count,
            "impact": impact,
            "explanation": explanation,
        })

    camelot_gaps.sort(key=lambda g: g["impact"], reverse=True)

    # ── BPM gaps ──
    bpm_rows = (
        session.query(Track.bpm)
        .filter(Track.bpm.isnot(None), Track.bpm > 0)
        .order_by(Track.bpm)
        .all()
    )
    bpms = [r[0] for r in bpm_rows]

    bpm_gaps = []
    if bpms:
        bin_width = 4.0
        lo = int(min(bpms) // bin_width * bin_width)
        hi = int(max(bpms) // bin_width * bin_width) + int(bin_width)
        for start in range(lo, hi, int(bin_width)):
            end = start + int(bin_width)
            count = sum(1 for b in bpms if start <= b < end)
            if count < 5:
                bpm_gaps.append({
                    "range": f"{start}-{end}",
                    "count": count,
                })
    bpm_gaps.sort(key=lambda g: g["count"])

    # ── Energy gaps ──
    energy_counts: dict[str, int] = defaultdict(int)
    energy_rows = (
        session.query(Track.dir_energy)
        .filter(Track.dir_energy.isnot(None))
        .all()
    )
    for (e,) in energy_rows:
        energy_counts[e.lower()] += 1

    energy_gaps = []
    for level in ENERGY_TAG_VALUES:
        count = energy_counts.get(level, 0)
        if count < 20:
            energy_gaps.append({"level": level, "count": count})
    energy_gaps.sort(key=lambda g: g["count"])

    return {
        "camelot_gaps": camelot_gaps[:15],
        "bpm_gaps": bpm_gaps[:10],
        "energy_gaps": energy_gaps,
    }


def enhanced_stats(session: Session) -> dict:
    """Extended statistics beyond the basic library_stats.

    Returns dict with: bpm_per_genre, energy_zones, most_played,
    hidden_gems, coverage.
    """
    # ── BPM per genre family ──
    genre_bpm_rows = (
        session.query(Track.dir_genre, Track.rb_genre, Track.bpm)
        .filter(Track.bpm.isnot(None), Track.bpm > 0)
        .all()
    )
    family_bpms: dict[str, list[float]] = defaultdict(list)
    for dir_g, rb_g, bpm in genre_bpm_rows:
        family = genre_to_family(dir_g or rb_g).capitalize()
        family_bpms[family].append(bpm)

    bpm_per_genre = {}
    for family, bpms_list in sorted(family_bpms.items()):
        bpm_per_genre[family] = {
            "avg": round(sum(bpms_list) / len(bpms_list), 1),
            "min": round(min(bpms_list), 1),
            "max": round(max(bpms_list), 1),
            "count": len(bpms_list),
        }

    # ── Energy zones ──
    energy_rows = (
        session.query(Track.dir_energy, Track.dir_genre, Track.rb_genre)
        .filter(Track.dir_energy.isnot(None))
        .all()
    )

    zones: dict[str, dict] = {
        "warmup": {"levels": {"low", "warmup", "closing"}, "tracks": [], "families": defaultdict(int)},
        "build": {"levels": {"mid", "dance", "up"}, "tracks": [], "families": defaultdict(int)},
        "peak": {"levels": {"high", "fast", "peak"}, "tracks": [], "families": defaultdict(int)},
    }
    for energy, dir_g, rb_g in energy_rows:
        el = energy.lower()
        family = genre_to_family(dir_g or rb_g).capitalize()
        for zone_name, zone in zones.items():
            if el in zone["levels"]:
                zone["tracks"].append(el)
                zone["families"][family] += 1

    energy_zones = {}
    for zone_name, zone in zones.items():
        top_families = sorted(zone["families"].items(), key=lambda x: -x[1])[:3]
        energy_zones[zone_name] = {
            "count": len(zone["tracks"]),
            "top_genres": [{"family": f, "count": c} for f, c in top_families],
        }

    # ── Most played ──
    most_played = (
        session.query(Track)
        .filter(Track.play_count.isnot(None), Track.play_count > 0)
        .order_by(Track.play_count.desc())
        .limit(10)
        .all()
    )
    most_played_list = [
        {"title": t.title, "artist": t.artist, "plays": t.play_count,
         "genre": t.dir_genre or t.rb_genre or "?"}
        for t in most_played
    ]

    # ── Hidden gems: rated >= 3 stars, 0 plays ──
    hidden_gems = (
        session.query(Track)
        .filter(
            Track.rating >= 3,
            (Track.play_count == 0) | (Track.play_count.is_(None)),
        )
        .order_by(Track.rating.desc())
        .limit(10)
        .all()
    )
    hidden_gems_list = [
        {"title": t.title, "artist": t.artist, "rating": t.rating,
         "genre": t.dir_genre or t.rb_genre or "?"}
        for t in hidden_gems
    ]

    # ── Coverage percentages ──
    total = session.query(func.count(Track.id)).scalar() or 0
    if total > 0:
        has_key = session.query(func.count(Track.id)).filter(Track.key.isnot(None)).scalar()
        has_bpm = session.query(func.count(Track.id)).filter(Track.bpm.isnot(None), Track.bpm > 0).scalar()
        has_rating = session.query(func.count(Track.id)).filter(Track.rating.isnot(None), Track.rating > 0).scalar()
        has_features = (
            session.query(func.count(AudioFeatures.track_id))
            .filter(AudioFeatures.energy.isnot(None))
            .scalar()
        )
        coverage = {
            "key": round(100 * has_key / total, 1),
            "bpm": round(100 * has_bpm / total, 1),
            "rating": round(100 * has_rating / total, 1),
            "features": round(100 * has_features / total, 1),
            "total": total,
        }
    else:
        coverage = {"key": 0, "bpm": 0, "rating": 0, "features": 0, "total": 0}

    return {
        "bpm_per_genre": bpm_per_genre,
        "energy_zones": energy_zones,
        "most_played": most_played_list,
        "hidden_gems": hidden_gems_list,
        "coverage": coverage,
    }
