"""Beam search set generation with energy flow planning."""

from __future__ import annotations

import json
from datetime import datetime

from rich.console import Console
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from kiku.config import ARTIST_COOLDOWN, DEFAULT_BEAM_WIDTH
from kiku.db.models import Set, SetTrack, Track
from kiku.db.store import get_track_by_title
from kiku.setbuilder.constraints import EnergyProfile, dir_energy_to_numeric
from kiku.setbuilder.scoring import transition_score

console = Console()


def _get_candidate_pool(
    session: Session,
    genres: list[str] | None = None,
    bpm_range: tuple[float, float] | None = None,
) -> list[Track]:
    """Get filtered candidate pool."""
    q = session.query(Track).filter(Track.bpm.isnot(None), Track.bpm > 0)

    if genres:
        conditions = [Track.dir_genre.ilike(f"%{g}%") for g in genres]
        q = q.filter(or_(*conditions))

    if bpm_range:
        q = q.filter(Track.bpm.between(*bpm_range))

    return q.all()


def _pick_seed(
    candidates: list[Track],
    energy_profile: EnergyProfile,
    seed_title: str | None = None,
    session: Session | None = None,
) -> Track | None:
    """Pick a seed track — user-specified or lowest-energy matching warmup."""
    if seed_title and session:
        track = get_track_by_title(session, seed_title)
        if track:
            return track

    if not candidates:
        return None

    # Pick track closest to first segment's target energy
    target = energy_profile.segments[0].target_energy if energy_profile.segments else 0.3

    def energy_diff(t: Track) -> float:
        if t.audio_features and t.audio_features.energy is not None:
            return abs(t.audio_features.energy - target)
        e = dir_energy_to_numeric(t.dir_energy)
        if e is not None:
            return abs(e - target)
        return 1.0  # Unknown — low priority

    candidates_sorted = sorted(candidates, key=energy_diff)
    return candidates_sorted[0]


def _violates_artist_cooldown(sequence: list[Track], candidate: Track) -> bool:
    """Check if adding candidate would violate same-artist cooldown."""
    if not candidate.artist:
        return False
    recent = sequence[-ARTIST_COOLDOWN:]
    return any(t.artist and t.artist.lower() == candidate.artist.lower() for t in recent)


def build_set(
    session: Session,
    duration_min: int = 120,
    energy_profile: EnergyProfile | None = None,
    genres: list[str] | None = None,
    bpm_range: tuple[float, float] | None = None,
    seed_title: str | None = None,
    beam_width: int = DEFAULT_BEAM_WIDTH,
    set_name: str | None = None,
    prefer_playlists: list[str] | None = None,
    weights: dict[str, float] | None = None,
    discovery_density: float = 0.0,
) -> Set | None:
    """Generate a DJ set using beam search.

    Returns a saved Set object with SetTrack entries, or None on failure.
    """
    if not energy_profile:
        from kiku.setbuilder.constraints import parse_energy_string
        energy_profile = parse_energy_string(
            "warmup:30:0.3,build:20:0.6,peak:40:0.9,cooldown:20:0.4"
        )

    candidates = _get_candidate_pool(session, genres=genres, bpm_range=bpm_range)

    # Batch query: how many sets each track appears in (for density signal)
    set_appearance_counts: dict[int, int] = {}
    if discovery_density != 0.0:
        rows = session.query(SetTrack.track_id, func.count(SetTrack.set_id.distinct())).group_by(SetTrack.track_id).all()
        set_appearance_counts = {track_id: cnt for track_id, cnt in rows}

    if not candidates:
        console.print("[yellow]No tracks match the genre filter.[/]")
        return None

    console.print(f"Candidate pool: {len(candidates)} tracks")

    seed = _pick_seed(candidates, energy_profile, seed_title, session)
    if not seed:
        console.print("[yellow]Could not find a seed track.[/]")
        return None

    console.print(f"Seed: [cyan]{seed.title}[/] — {seed.artist}")

    # Beam search
    # Each beam is (track_sequence, cumulative_score, elapsed_minutes)
    avg_track_min = 6.0  # Assume ~6 min average track length
    target_duration = float(duration_min)

    beams: list[tuple[list[Track], float, float]] = [
        ([seed], 0.0, seed.duration_sec / 60.0 if seed.duration_sec else avg_track_min)
    ]

    candidate_set = {t.id: t for t in candidates}

    iteration = 0
    while True:
        iteration += 1
        new_beams = []

        for seq, cum_score, elapsed in beams:
            if elapsed >= target_duration:
                new_beams.append((seq, cum_score, elapsed))
                continue

            used_ids = {t.id for t in seq}
            current = seq[-1]
            target_e = energy_profile.target_energy_at(elapsed)

            # Compute target BPM at this point if BPM range given
            target_bpm = None
            if bpm_range:
                progress = min(elapsed / target_duration, 1.0)
                target_bpm = bpm_range[0] + (bpm_range[1] - bpm_range[0]) * progress

            # Score all candidates not yet in sequence
            scored_candidates = []
            for cand_id, cand in candidate_set.items():
                if cand_id in used_ids:
                    continue
                if _violates_artist_cooldown(seq, cand):
                    continue

                # BPM pre-filter (±12% to allow some flexibility)
                if current.bpm and cand.bpm:
                    ratio = cand.bpm / current.bpm
                    if ratio < 0.88 or ratio > 1.12:
                        # Also allow double/half time
                        if not (0.47 < ratio < 0.53 or 1.88 < ratio < 2.12):
                            continue

                score = transition_score(current, cand, target_energy=target_e, prefer_playlists=prefer_playlists, weights=weights, discovery_density=discovery_density, set_appearance_counts=set_appearance_counts)

                # BPM progression bonus: reward tracks closer to target BPM at this point
                if target_bpm and cand.bpm:
                    bpm_diff = abs(cand.bpm - target_bpm)
                    bpm_range_span = bpm_range[1] - bpm_range[0]
                    bpm_prog_score = max(0.0, 1.0 - bpm_diff / max(bpm_range_span, 1.0))
                    score += 0.15 * bpm_prog_score

                scored_candidates.append((cand, score))

            # Take top candidates for each beam
            scored_candidates.sort(key=lambda x: x[1], reverse=True)
            top = scored_candidates[:beam_width]

            if not top:
                # Dead end — keep current beam
                new_beams.append((seq, cum_score, target_duration))
                continue

            for cand, score in top:
                cand_dur = cand.duration_sec / 60.0 if cand.duration_sec else avg_track_min
                new_beams.append((
                    seq + [cand],
                    cum_score + score,
                    elapsed + cand_dur,
                ))

        # Keep top beam_width beams by average score
        new_beams.sort(key=lambda b: b[1] / max(len(b[0]), 1), reverse=True)
        beams = new_beams[:beam_width]

        # Check if all beams have reached target duration
        if all(elapsed >= target_duration for _, _, elapsed in beams):
            break

        # Safety: max iterations
        if iteration > 200:
            break

    if not beams:
        return None

    # Pick best beam
    best_seq, best_score, best_elapsed = beams[0]

    # Save to database
    name = set_name or f"set_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    set_ = Set(
        name=name,
        duration_min=int(best_elapsed),
        energy_profile=json.dumps([
            {"name": s.name, "duration_min": s.duration_min, "target_energy": s.target_energy}
            for s in energy_profile.segments
        ]),
        genre_filter=json.dumps(genres) if genres else None,
    )
    session.add(set_)
    session.flush()

    prev_track = None
    for i, track in enumerate(best_seq):
        t_score = transition_score(prev_track, track, prefer_playlists=prefer_playlists, weights=weights, discovery_density=discovery_density, set_appearance_counts=set_appearance_counts) if prev_track else None
        st = SetTrack(
            set_id=set_.id,
            position=i + 1,
            track_id=track.id,
            transition_score=t_score,
        )
        session.add(st)
        prev_track = track

    session.commit()

    # Reload with relationships
    set_ = session.get(Set, set_.id)
    return set_
