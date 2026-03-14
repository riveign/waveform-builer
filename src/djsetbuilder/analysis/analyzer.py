"""Orchestration for batch audio analysis."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

import numpy as np
from rich.console import Console
from rich.progress import Progress

from djsetbuilder.db.models import AudioFeatures, Track, get_session
from djsetbuilder.db.store import get_track_by_title, get_unanalyzed_tracks

console = Console()


def _analyze_single(file_path: str, waveform_only: bool = False) -> dict | None:
    """Analyze a single track file. Runs in subprocess."""
    results = {}

    if not waveform_only:
        # Essentia features
        try:
            from djsetbuilder.analysis.essentia_ext import extract_essentia_features
            results.update(extract_essentia_features(file_path))
        except ImportError:
            console.print("[yellow]essentia not installed, skipping essentia features[/]")
        except Exception as e:
            console.print(f"[yellow]Essentia error for {Path(file_path).name}: {e}[/]")

        # Essentia mood (optional)
        try:
            from djsetbuilder.analysis.essentia_ext import extract_essentia_mood
            results.update(extract_essentia_mood(file_path))
        except Exception:
            pass

        # MFCC features
        try:
            from djsetbuilder.analysis.librosa_ext import extract_mfccs
            results.update(extract_mfccs(file_path))
        except ImportError:
            console.print("[yellow]librosa not installed, skipping MFCC features[/]")
        except Exception as e:
            console.print(f"[yellow]Librosa error for {Path(file_path).name}: {e}[/]")

    # Waveform extraction
    try:
        from djsetbuilder.analysis.waveform import extract_waveform
        results.update(extract_waveform(file_path))
    except ImportError:
        pass
    except Exception as e:
        console.print(f"[yellow]Waveform error for {Path(file_path).name}: {e}[/]")

    return results if results else None


def _save_features(session, track: Track, results: dict):
    """Save analysis results to database."""
    af = track.audio_features or AudioFeatures(track_id=track.id)

    for key in [
        "energy", "danceability", "loudness_lufs", "spectral_centroid",
        "spectral_complexity", "mood_happy", "mood_sad", "mood_aggressive",
        "mood_relaxed", "ml_genre", "ml_genre_confidence", "energy_intro",
        "energy_body", "energy_outro", "verified_bpm", "verified_key",
    ]:
        if key in results and results[key] is not None:
            setattr(af, key, results[key])

    # Serialize numpy arrays to bytes
    for key in ["mfcc_mean", "mfcc_var", "waveform_overview", "waveform_detail", "beat_positions"]:
        if key in results and results[key] is not None:
            setattr(af, key, results[key].tobytes())

    # Scalar waveform metadata
    for key in ["waveform_sr", "waveform_hop"]:
        if key in results and results[key] is not None:
            setattr(af, key, results[key])

    af.analyzed_at = datetime.now().isoformat()

    if not track.audio_features:
        session.add(af)

    session.commit()


def run_analysis(
    force: bool = False,
    workers: int = 1,
    single_track: str | None = None,
    waveform_only: bool = False,
):
    """Run audio analysis on library tracks."""
    session = get_session()

    if single_track:
        track = get_track_by_title(session, single_track)
        if not track:
            console.print(f"[yellow]Track '{single_track}' not found.[/]")
            return

        if not track.file_path or not Path(track.file_path).exists():
            console.print(f"[red]File not found: {track.file_path}[/]")
            return

        console.print(f"Analyzing: [cyan]{track.title}[/] — {track.artist}")
        results = _analyze_single(track.file_path, waveform_only=waveform_only)
        if results:
            _save_features(session, track, results)
            console.print("[green]Analysis complete![/]")
        else:
            console.print("[yellow]No features extracted.[/]")
        return

    # Batch analysis
    if waveform_only:
        # For waveform-only, get all tracks missing waveform data
        tracks = (
            session.query(Track)
            .outerjoin(AudioFeatures)
            .filter(
                (AudioFeatures.waveform_overview.is_(None))
                | (AudioFeatures.track_id.is_(None))
            )
            .all()
        )
        if force:
            tracks = session.query(Track).all()
    elif force:
        tracks = session.query(Track).all()
    else:
        tracks = get_unanalyzed_tracks(session)

    # Filter to tracks with accessible files
    available = [t for t in tracks if t.file_path and Path(t.file_path).exists()]

    if not available:
        console.print("[yellow]No tracks to analyze (files may not be mounted).[/]")
        total_missing = len([t for t in tracks if t.file_path and not Path(t.file_path).exists()])
        if total_missing:
            console.print(f"[dim]{total_missing} tracks have inaccessible files. Mount external drives?[/]")
        return

    console.print(f"Analyzing {len(available)} tracks (workers={workers})...")

    label = "[cyan]Extracting waveforms..." if waveform_only else "[cyan]Analyzing..."

    if workers <= 1:
        # Sequential
        with Progress() as progress:
            task = progress.add_task(label, total=len(available))
            for track in available:
                results = _analyze_single(track.file_path, waveform_only=waveform_only)
                if results:
                    _save_features(session, track, results)
                progress.advance(task)
    else:
        # Parallel — need to handle session per process
        with Progress() as progress:
            task = progress.add_task(label, total=len(available))
            with ProcessPoolExecutor(max_workers=workers) as executor:
                futures = {
                    executor.submit(_analyze_single, t.file_path, waveform_only): t
                    for t in available
                }
                for future in as_completed(futures):
                    track = futures[future]
                    try:
                        results = future.result()
                        if results:
                            _save_features(session, track, results)
                    except Exception as e:
                        console.print(f"[red]Error analyzing {track.title}: {e}[/]")
                    progress.advance(task)

    analyzed_count = len([t for t in available if t.audio_features])
    console.print(f"[green]Analysis complete! {analyzed_count} tracks analyzed.[/]")
