"""Analyze trance vs non-trance tracks to identify distinguishing audio characteristics."""

from __future__ import annotations

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from pathlib import Path
from datetime import datetime
import numpy as np
from rich.console import Console
from rich.table import Table
from rich.progress import Progress

from kiku.db.models import AudioFeatures, Track, get_session
from kiku.analysis.essentia_ext import extract_essentia_features
from kiku.analysis.librosa_ext import extract_mfccs

console = Console()

def analyze_track(file_path: str) -> dict | None:
    results = {}
    try:
        results.update(extract_essentia_features(file_path))
    except Exception as e:
        console.print(f"[yellow]Essentia error: {e}[/]")
    try:
        results.update(extract_mfccs(file_path))
    except Exception as e:
        console.print(f"[yellow]MFCC error: {e}[/]")
    return results if results else None


def save_features(session, track, results):
    af = track.audio_features or AudioFeatures(track_id=track.id)
    for key in [
        "energy", "danceability", "loudness_lufs", "spectral_centroid",
        "spectral_complexity", "mood_happy", "mood_sad", "mood_aggressive",
        "mood_relaxed", "ml_genre", "ml_genre_confidence", "energy_intro",
        "energy_body", "energy_outro", "verified_bpm", "verified_key",
    ]:
        if key in results and results[key] is not None:
            setattr(af, key, results[key])
    if "mfcc_mean" in results and results["mfcc_mean"] is not None:
        af.mfcc_mean = results["mfcc_mean"].tobytes()
    if "mfcc_var" in results and results["mfcc_var"] is not None:
        af.mfcc_var = results["mfcc_var"].tobytes()
    af.analyzed_at = datetime.now().isoformat()
    if not track.audio_features:
        session.add(af)
    session.commit()


def main():
    session = get_session()

    # Get all trance tracks
    trance_tracks = session.query(Track).filter(Track.dir_genre.like('%Trance%')).all()
    trance_available = [t for t in trance_tracks if t.file_path and Path(t.file_path).exists()]

    # Get non-trance tracks for comparison (sample across genres)
    non_trance = session.query(Track).filter(
        ~Track.dir_genre.like('%Trance%'),
        Track.dir_genre.isnot(None),
        Track.dir_genre != '',
    ).all()
    non_trance_available = [t for t in non_trance if t.file_path and Path(t.file_path).exists()]

    # Sample up to 150 non-trance tracks for comparison
    import random
    random.seed(42)
    if len(non_trance_available) > 150:
        non_trance_sample = random.sample(non_trance_available, 150)
    else:
        non_trance_sample = non_trance_available

    all_tracks = trance_available + non_trance_sample
    console.print(f"[bold]Analyzing {len(trance_available)} trance + {len(non_trance_sample)} non-trance tracks[/]\n")

    # Analyze tracks that don't have features yet
    to_analyze = [t for t in all_tracks if not t.audio_features or t.audio_features.energy is None]
    console.print(f"Need to analyze: {len(to_analyze)} tracks\n")

    if to_analyze:
        with Progress() as progress:
            task = progress.add_task("[cyan]Analyzing...", total=len(to_analyze))
            for track in to_analyze:
                try:
                    results = analyze_track(track.file_path)
                    if results:
                        save_features(session, track, results)
                except Exception as e:
                    console.print(f"[red]Error {track.title}: {e}[/]")
                progress.advance(task)

    # Now compare features
    session.expire_all()  # refresh

    features = {"trance": [], "non_trance": []}
    for track in all_tracks:
        af = track.audio_features
        if not af or af.energy is None:
            continue
        label = "trance" if "Trance" in (track.dir_genre or "") else "non_trance"
        features[label].append({
            "title": track.title,
            "artist": track.artist,
            "genre": track.dir_genre,
            "bpm": track.bpm,
            "energy": af.energy,
            "danceability": af.danceability,
            "loudness": af.loudness_lufs,
            "spectral_centroid": af.spectral_centroid,
            "spectral_complexity": af.spectral_complexity,
            "energy_intro": af.energy_intro,
            "energy_body": af.energy_body,
            "energy_outro": af.energy_outro,
            "verified_bpm": af.verified_bpm,
        })

    console.print(f"\n[bold]Results: {len(features['trance'])} trance, {len(features['non_trance'])} non-trance analyzed[/]\n")

    # Compare averages
    metrics = ["bpm", "energy", "danceability", "loudness", "spectral_centroid",
               "spectral_complexity", "energy_intro", "energy_body", "energy_outro"]

    table = Table(title="Trance vs Non-Trance Audio Characteristics")
    table.add_column("Feature", style="cyan")
    table.add_column("Trance (avg)", justify="right")
    table.add_column("Trance (std)", justify="right", style="dim")
    table.add_column("Non-Trance (avg)", justify="right")
    table.add_column("Non-Trance (std)", justify="right", style="dim")
    table.add_column("Diff", justify="right", style="bold")
    table.add_column("Separability", justify="right", style="green")

    for metric in metrics:
        t_vals = [f[metric] for f in features["trance"] if f[metric] is not None]
        nt_vals = [f[metric] for f in features["non_trance"] if f[metric] is not None]

        if not t_vals or not nt_vals:
            continue

        t_mean = np.mean(t_vals)
        t_std = np.std(t_vals)
        nt_mean = np.mean(nt_vals)
        nt_std = np.std(nt_vals)

        diff = t_mean - nt_mean
        # Cohen's d for effect size
        pooled_std = np.sqrt((t_std**2 + nt_std**2) / 2)
        cohens_d = abs(diff / pooled_std) if pooled_std > 0 else 0

        if cohens_d > 0.8:
            sep = "[bold green]STRONG[/]"
        elif cohens_d > 0.5:
            sep = "[yellow]MODERATE[/]"
        elif cohens_d > 0.2:
            sep = "[dim]weak[/]"
        else:
            sep = "[dim red]none[/]"

        table.add_row(
            metric,
            f"{t_mean:.3f}",
            f"{t_std:.3f}",
            f"{nt_mean:.3f}",
            f"{nt_std:.3f}",
            f"{diff:+.3f}",
            sep,
        )

    console.print(table)

    # Show non-trance genre breakdown
    console.print("\n[bold]Non-Trance genres in comparison set:[/]")
    genre_counts = {}
    for f in features["non_trance"]:
        g = f["genre"]
        genre_counts[g] = genre_counts.get(g, 0) + 1
    for g, c in sorted(genre_counts.items(), key=lambda x: -x[1]):
        console.print(f"  {g}: {c}")

    # Trance subgenre comparison
    console.print("\n")
    sub_table = Table(title="Trance Subgenre Breakdown")
    sub_table.add_column("Subgenre", style="cyan")
    sub_table.add_column("Count", justify="right")
    sub_table.add_column("BPM", justify="right")
    sub_table.add_column("Energy", justify="right")
    sub_table.add_column("Danceability", justify="right")
    sub_table.add_column("Brightness", justify="right")
    sub_table.add_column("Loudness", justify="right")

    subgenres = {}
    for f in features["trance"]:
        g = f["genre"]
        if g not in subgenres:
            subgenres[g] = []
        subgenres[g].append(f)

    for genre, tracks in sorted(subgenres.items(), key=lambda x: -len(x[1])):
        bpms = [t["bpm"] for t in tracks if t["bpm"]]
        energies = [t["energy"] for t in tracks if t["energy"] is not None]
        dances = [t["danceability"] for t in tracks if t["danceability"] is not None]
        brights = [t["spectral_centroid"] for t in tracks if t["spectral_centroid"] is not None]
        louds = [t["loudness"] for t in tracks if t["loudness"] is not None]

        sub_table.add_row(
            genre,
            str(len(tracks)),
            f"{np.mean(bpms):.1f}" if bpms else "?",
            f"{np.mean(energies):.3f}" if energies else "?",
            f"{np.mean(dances):.3f}" if dances else "?",
            f"{np.mean(brights):.0f}" if brights else "?",
            f"{np.mean(louds):.1f}" if louds else "?",
        )

    console.print(sub_table)


if __name__ == "__main__":
    main()
