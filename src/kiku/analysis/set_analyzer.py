"""Set analysis engine — scores transitions, computes arcs, generates teaching moments."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime

from sqlalchemy.orm import Session

from kiku.analysis.autotag import resolve_energy
from kiku.analysis.teaching import detect_set_patterns, transition_teaching_moment
from kiku.config import SCORING_WEIGHTS
from kiku.db.models import Set, SetTrack, Track
from kiku.setbuilder.camelot import harmonic_score
from kiku.setbuilder.constraints import zone_to_numeric
from kiku.setbuilder.scoring import (
    bpm_compatibility,
    energy_fit,
    genre_coherence,
    genre_to_family,
    track_quality,
)


# ── Data Structures ─────────────────────────────────────────────────────


@dataclass
class TransitionAnalysis:
    position: int
    track_a_id: int
    track_b_id: int
    scores: dict
    teaching_moment: str
    suggestion: str | None


@dataclass
class ArcAnalysis:
    energy_curve: list[float]
    energy_shape: str
    key_journey: list[str | None]
    key_style: str
    bpm_range: tuple[float, float]
    bpm_drift: float
    bpm_style: str
    genre_segments: list[dict]


@dataclass
class SetAnalysisResult:
    set_id: int
    track_count: int
    transition_count: int
    transitions: list[TransitionAnalysis]
    arc: ArcAnalysis
    overall_score: float
    set_patterns: list[str]
    analyzed_at: str


# ── Core Analyzer ───────────────────────────────────────────────────────


def analyze_set(db: Session, set_id: int) -> SetAnalysisResult:
    """Run full analysis on a set: score transitions, compute arc, generate teaching moments.

    Also infers energy for untagged tracks and caches the result.
    """
    s = db.get(Set, set_id)
    if not s:
        raise ValueError(f"Set {set_id} not found")

    set_tracks = sorted(s.tracks, key=lambda st: st.position)
    tracks = [st.track for st in set_tracks]

    if len(tracks) < 2:
        raise ValueError(f"Set {set_id} needs at least 2 tracks for analysis")

    # 1. Infer energy for untagged tracks
    _infer_energy(db, set_tracks, tracks)

    # 2. Score all transitions
    transitions = _score_transitions(tracks, set_tracks)

    # 3. Compute arc analysis
    arc = _compute_arc(tracks)

    # 4. Detect set-level patterns
    score_dicts = [t.scores for t in transitions]
    set_patterns = detect_set_patterns(
        score_dicts,
        arc.energy_curve,
        arc.key_journey,
        [t.bpm for t in tracks],
    )

    # 5. Overall score
    totals = [t.scores["total"] for t in transitions]
    overall_score = round(sum(totals) / len(totals), 3) if totals else 0.0

    result = SetAnalysisResult(
        set_id=set_id,
        track_count=len(tracks),
        transition_count=len(transitions),
        transitions=transitions,
        arc=arc,
        overall_score=overall_score,
        set_patterns=set_patterns,
        analyzed_at=datetime.now().isoformat(),
    )

    # 6. Cache result
    cache_data = asdict(result)
    # Convert tuple to list for JSON serialization
    cache_data["arc"]["bpm_range"] = list(cache_data["arc"]["bpm_range"])
    s.analysis_cache = json.dumps(cache_data)
    s.is_analyzed = 1
    db.commit()

    return result


# ── Energy Inference ────────────────────────────────────────────────────


def _get_track_energy(track: Track) -> float | None:
    """Get energy value from existing sources (not inferred)."""
    if track.audio_features and track.audio_features.energy is not None:
        return track.audio_features.energy
    zone, source, _conf = resolve_energy(track)
    if zone and source != "none":
        return zone_to_numeric(zone)
    return None


def _infer_energy(db: Session, set_tracks: list[SetTrack], tracks: list[Track]) -> None:
    """Infer energy for tracks that lack energy data, based on position and neighbors."""
    energies: list[float | None] = [_get_track_energy(t) for t in tracks]
    n = len(tracks)

    for i, (st, e) in enumerate(zip(set_tracks, energies)):
        if e is not None:
            continue  # Already has energy — skip

        # Try neighbor interpolation
        prev_e = energies[i - 1] if i > 0 else None
        next_e = energies[i + 1] if i < n - 1 else None

        if prev_e is not None and next_e is not None:
            inferred = round((prev_e + next_e) / 2, 3)
            source = "interpolation"
        elif prev_e is not None:
            inferred = prev_e
            source = "interpolation"
        elif next_e is not None:
            inferred = next_e
            source = "interpolation"
        else:
            # Position-based fallback
            ratio = i / max(n - 1, 1)
            if ratio < 0.2:
                inferred = 0.3  # warmup
            elif ratio < 0.4:
                inferred = 0.55  # build
            elif ratio < 0.7:
                inferred = 0.75  # drive/peak
            elif ratio < 0.85:
                inferred = 0.9  # peak
            else:
                inferred = 0.4  # close
            source = "position"

        st.inferred_energy = inferred
        st.inference_source = source
        energies[i] = inferred  # Update for next neighbor lookups

    db.flush()


# ── Transition Scoring ──────────────────────────────────────────────────


def _score_transitions(tracks: list[Track], set_tracks: list[SetTrack]) -> list[TransitionAnalysis]:
    """Score all adjacent transitions in the set."""
    w = SCORING_WEIGHTS
    results = []

    for i in range(len(tracks) - 1):
        t_a, t_b = tracks[i], tracks[i + 1]

        h = harmonic_score(t_a.key, t_b.key)
        # Use inferred energy if available for target
        st_b = set_tracks[i + 1]
        target_e = st_b.inferred_energy if st_b.inferred_energy is not None else 0.5
        e = energy_fit(t_b, target_e)
        b = bpm_compatibility(t_a.bpm, t_b.bpm)
        g = genre_coherence(
            t_a.dir_genre or t_a.rb_genre,
            t_b.dir_genre or t_b.rb_genre,
        )
        q, _ = track_quality(t_b)

        total = (w["harmonic"] * h + w["energy_fit"] * e + w["bpm_compat"] * b
                 + w["genre_coherence"] * g + w["track_quality"] * q)

        scores = {
            "harmonic": round(h, 3),
            "energy_fit": round(e, 3),
            "bpm_compat": round(b, 3),
            "genre_coherence": round(g, 3),
            "track_quality": round(q, 3),
            "total": round(total, 3),
        }

        teaching, suggestion = transition_teaching_moment(
            scores,
            t_a.key, t_b.key,
            t_a.bpm, t_b.bpm,
            t_a.dir_genre or t_a.rb_genre,
            t_b.dir_genre or t_b.rb_genre,
        )

        results.append(TransitionAnalysis(
            position=i,
            track_a_id=t_a.id,
            track_b_id=t_b.id,
            scores=scores,
            teaching_moment=teaching,
            suggestion=suggestion,
        ))

    return results


# ── Arc Analysis ────────────────────────────────────────────────────────


def _compute_arc(tracks: list[Track]) -> ArcAnalysis:
    """Compute arc-level analysis across the full set."""
    # Energy curve
    energy_curve = []
    for t in tracks:
        e = _get_track_energy(t)
        energy_curve.append(e if e is not None else 0.5)

    energy_shape = _classify_energy_shape(energy_curve)

    # Key journey
    key_journey: list[str | None] = [t.key for t in tracks]
    key_style = _classify_key_style(key_journey)

    # BPM
    bpms = [t.bpm for t in tracks if t.bpm and t.bpm > 0]
    bpm_range = (min(bpms), max(bpms)) if bpms else (0.0, 0.0)
    bpm_drift = round(bpms[-1] - bpms[0], 1) if len(bpms) >= 2 else 0.0
    bpm_style = _classify_bpm_style(bpms)

    # Genre segments
    genre_segments = _detect_genre_segments(tracks)

    return ArcAnalysis(
        energy_curve=[round(e, 3) for e in energy_curve],
        energy_shape=energy_shape,
        key_journey=key_journey,
        key_style=key_style,
        bpm_range=bpm_range,
        bpm_drift=bpm_drift,
        bpm_style=bpm_style,
        genre_segments=genre_segments,
    )


def _classify_energy_shape(curve: list[float]) -> str:
    if len(curve) < 2:
        return "too-short"
    mid = len(curve) // 2
    first_half = sum(curve[:mid]) / mid if mid > 0 else 0
    second_half = sum(curve[mid:]) / (len(curve) - mid)
    peak_pos = curve.index(max(curve))
    valley_pos = curve.index(min(curve))
    spread = max(curve) - min(curve)

    if spread < 0.15:
        return "flat"
    if peak_pos < len(curve) * 0.4 and valley_pos > len(curve) * 0.6:
        return "peak-valley"
    if second_half > first_half + 0.1:
        return "ramp-up"
    if first_half > second_half + 0.1:
        return "wind-down"
    # Check for multiple peaks
    peaks = sum(1 for i in range(1, len(curve) - 1)
                if curve[i] > curve[i - 1] and curve[i] > curve[i + 1])
    if peaks >= 3:
        return "roller-coaster"
    return "journey"


def _classify_key_style(keys: list[str | None]) -> str:
    valid = [k for k in keys if k]
    if len(valid) < 2:
        return "unknown"
    unique = len(set(valid))
    ratio = unique / len(valid)
    if ratio <= 0.3:
        return "home-key"
    if ratio >= 0.7:
        return "adventurous"
    return "chromatic-walk"


def _classify_bpm_style(bpms: list[float]) -> str:
    if len(bpms) < 2:
        return "unknown"
    spread = max(bpms) - min(bpms)
    if spread < 3:
        return "steady"
    drift = abs(bpms[-1] - bpms[0])
    if drift > 10:
        return "gradual-build" if bpms[-1] > bpms[0] else "gradual-drop"
    if spread > 15:
        return "volatile"
    return "gentle-drift"


def _detect_genre_segments(tracks: list[Track]) -> list[dict]:
    """Detect contiguous genre family segments."""
    segments: list[dict] = []
    current_family = None
    start_pos = 0

    for i, t in enumerate(tracks):
        family = genre_to_family(t.dir_genre or t.rb_genre)
        if family != current_family:
            if current_family is not None:
                segments.append({"genre_family": current_family, "start_pos": start_pos, "end_pos": i - 1})
            current_family = family
            start_pos = i

    if current_family is not None:
        segments.append({"genre_family": current_family, "start_pos": start_pos, "end_pos": len(tracks) - 1})

    return segments
