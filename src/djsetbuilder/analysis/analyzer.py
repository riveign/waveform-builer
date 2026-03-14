"""Orchestration for batch audio analysis."""

from __future__ import annotations

import multiprocessing
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

import numpy as np
from rich.console import Console
from rich.progress import Progress

from djsetbuilder.db.models import AudioFeatures, Track, get_session
from djsetbuilder.db.store import get_track_by_title, get_unanalyzed_tracks, get_partially_analyzed_tracks

console = Console()


def _analyze_energy_mood(file_path: str) -> dict | None:
    """Recompute only energy + mood for a track. Much faster than full analysis."""
    from djsetbuilder.analysis.loader import _load_at_sr

    results = {}

    # Energy needs 44100 Hz audio
    try:
        audio_44100 = _load_at_sr(file_path, 44100)
        from djsetbuilder.analysis.essentia_ext import extract_essentia_features
        # We only need energy fields from the full extractor
        full = extract_essentia_features(file_path, audio=audio_44100)
        for k in ("energy", "energy_intro", "energy_body", "energy_outro"):
            if k in full:
                results[k] = full[k]
    except Exception as e:
        console.print(f"[yellow]Energy error for {Path(file_path).name}: {e}[/]")

    # Mood needs 16000 Hz audio
    try:
        audio_16000 = _load_at_sr(file_path, 16000)
        from djsetbuilder.analysis.essentia_ext import extract_essentia_mood
        results.update(extract_essentia_mood(file_path, audio=audio_16000))
    except Exception:
        pass

    return results if results else None


def _analyze_single(
    file_path: str, waveform_only: bool = False, bands_only: bool = False,
) -> dict | None:
    """Analyze a single track file. Runs in subprocess.

    Decodes the audio file **once** and resamples in-memory, then passes
    the pre-loaded buffers to each extractor.
    """
    from djsetbuilder.analysis.loader import load_audio

    try:
        buffers = load_audio(file_path, skip_44100=(waveform_only or bands_only))
    except Exception as e:
        console.print(f"[yellow]Audio load error for {Path(file_path).name}: {e}[/]")
        return None

    results = {}

    if not waveform_only and not bands_only:
        # Essentia features
        try:
            from djsetbuilder.analysis.essentia_ext import extract_essentia_features
            results.update(extract_essentia_features(file_path, audio=buffers.audio_44100))
        except ImportError:
            console.print("[yellow]essentia not installed, skipping essentia features[/]")
        except Exception as e:
            console.print(f"[yellow]Essentia error for {Path(file_path).name}: {e}[/]")

        # Essentia mood (optional)
        try:
            from djsetbuilder.analysis.essentia_ext import extract_essentia_mood
            results.update(extract_essentia_mood(file_path, audio=buffers.audio_16000))
        except Exception:
            pass

        # MFCC features
        try:
            from djsetbuilder.analysis.librosa_ext import extract_mfccs
            results.update(extract_mfccs(file_path, audio=buffers.audio_22050, sr=22050))
        except ImportError:
            console.print("[yellow]librosa not installed, skipping MFCC features[/]")
        except Exception as e:
            console.print(f"[yellow]Librosa error for {Path(file_path).name}: {e}[/]")

    # Waveform extraction (skip in bands-only mode)
    if not bands_only:
        try:
            from djsetbuilder.analysis.waveform import extract_waveform
            results.update(extract_waveform(file_path, audio=buffers.audio_22050, skip_beats=waveform_only))
        except ImportError:
            pass
        except Exception as e:
            console.print(f"[yellow]Waveform error for {Path(file_path).name}: {e}[/]")

    # Frequency band envelopes
    if bands_only or not waveform_only:
        try:
            from djsetbuilder.analysis.waveform import extract_band_envelopes
            results.update(extract_band_envelopes(file_path, audio=buffers.audio_22050))
        except ImportError:
            pass
        except Exception as e:
            console.print(f"[yellow]Band envelope error for {Path(file_path).name}: {e}[/]")

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
    for key in [
        "mfcc_mean", "mfcc_var", "waveform_overview", "waveform_detail", "beat_positions",
        "band_low", "band_midlow", "band_midhigh", "band_high",
        "band_low_overview", "band_midlow_overview", "band_midhigh_overview", "band_high_overview",
    ]:
        if key in results and results[key] is not None:
            setattr(af, key, results[key].tobytes())

    # Scalar waveform metadata
    for key in ["waveform_sr", "waveform_hop"]:
        if key in results and results[key] is not None:
            setattr(af, key, results[key])

    af.analyzed_at = datetime.now().isoformat()

    if not track.audio_features:
        session.add(af)

    # Backfill track-level fields from analysis results
    if af.verified_bpm and (not track.bpm or track.bpm == 0):
        track.bpm = af.verified_bpm
    if af.verified_key and not track.key:
        track.key = af.verified_key

    session.commit()


def run_analysis(
    force: bool = False,
    workers: int = 1,
    single_track: str | None = None,
    waveform_only: bool = False,
    bands_only: bool = False,
    recompute: str | None = None,
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
        results = _analyze_single(
            track.file_path, waveform_only=waveform_only, bands_only=bands_only,
        )
        if results:
            _save_features(session, track, results)
            console.print("[green]Analysis complete![/]")
        else:
            console.print("[yellow]No features extracted.[/]")
        return

    # Targeted recompute mode
    if recompute:
        targets = [t.strip().lower() for t in recompute.split(",")]
        if "energy_mood" not in targets and "energy" not in targets and "mood" not in targets:
            console.print(f"[red]Unknown recompute target: {recompute}. Use: energy, mood, energy_mood[/]")
            return

        # Get all tracks with existing audio_features
        tracks = (
            session.query(Track)
            .join(AudioFeatures)
            .all()
        )
        available = [t for t in tracks if t.file_path and Path(t.file_path).exists()]
        if not available:
            console.print("[yellow]No tracks to recompute.[/]")
            return

        console.print(f"Recomputing {recompute} for {len(available)} tracks (workers={workers})...")

        if workers <= 0:
            workers = max(1, multiprocessing.cpu_count() // 2)

        label = f"[cyan]Recomputing {recompute}..."
        if workers <= 1:
            with Progress() as progress:
                task = progress.add_task(label, total=len(available))
                for track in available:
                    results = _analyze_energy_mood(track.file_path)
                    if results:
                        _save_features(session, track, results)
                    progress.advance(task)
        else:
            with Progress() as progress:
                task = progress.add_task(label, total=len(available))
                mp_ctx = multiprocessing.get_context("spawn")
                with ProcessPoolExecutor(max_workers=workers, mp_context=mp_ctx) as executor:
                    futures = {
                        executor.submit(_analyze_energy_mood, t.file_path): t
                        for t in available
                    }
                    for future in as_completed(futures):
                        track = futures[future]
                        try:
                            results = future.result()
                            if results:
                                _save_features(session, track, results)
                        except Exception as e:
                            console.print(f"[red]Error: {track.title}: {e}[/]")
                        progress.advance(task)

        console.print(f"[green]Recompute complete! {len(available)} tracks updated.[/]")
        return

    # Batch analysis
    if bands_only:
        # Get tracks missing band envelope data
        tracks = (
            session.query(Track)
            .outerjoin(AudioFeatures)
            .filter(
                (AudioFeatures.band_low.is_(None))
                | (AudioFeatures.track_id.is_(None))
            )
            .all()
        )
        if force:
            tracks = session.query(Track).all()
    elif waveform_only:
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
        unanalyzed = get_unanalyzed_tracks(session)
        partial = get_partially_analyzed_tracks(session)
        tracks = unanalyzed + partial
        if partial:
            console.print(f"[dim]Found {len(partial)} partially analyzed tracks (waveform-only).[/]")

    # Auto-detect worker count
    if workers <= 0:
        workers = max(1, multiprocessing.cpu_count() // 2)

    # Filter to tracks with accessible files
    available = [t for t in tracks if t.file_path and Path(t.file_path).exists()]

    if not available:
        console.print("[yellow]No tracks to analyze (files may not be mounted).[/]")
        total_missing = len([t for t in tracks if t.file_path and not Path(t.file_path).exists()])
        if total_missing:
            console.print(f"[dim]{total_missing} tracks have inaccessible files. Mount external drives?[/]")
        return

    console.print(f"Analyzing {len(available)} tracks (workers={workers})...")

    if bands_only:
        label = "[cyan]Extracting frequency bands..."
    elif waveform_only:
        label = "[cyan]Extracting waveforms..."
    else:
        label = "[cyan]Analyzing..."

    if workers <= 1:
        # Sequential
        with Progress() as progress:
            task = progress.add_task(label, total=len(available))
            for track in available:
                results = _analyze_single(
                    track.file_path, waveform_only=waveform_only, bands_only=bands_only,
                )
                if results:
                    _save_features(session, track, results)
                progress.advance(task)
    else:
        # Parallel — need to handle session per process
        with Progress() as progress:
            task = progress.add_task(label, total=len(available))
            mp_ctx = multiprocessing.get_context("spawn")
            with ProcessPoolExecutor(max_workers=workers, mp_context=mp_ctx) as executor:
                futures = {
                    executor.submit(_analyze_single, t.file_path, waveform_only, bands_only): t
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
