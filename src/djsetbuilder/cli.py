"""CLI entry point for DJ Set Builder."""

from __future__ import annotations

import json

import click
from rich.console import Console
from rich.table import Table

console = Console()


@click.group()
@click.version_option()
def cli():
    """DJ Set Builder — build optimized DJ sets from your Rekordbox library."""


@cli.command()
@click.option("--hashes", is_flag=True, help="Compute file hashes for change detection (slower)")
def sync(hashes: bool):
    """Import Rekordbox library and parse directory metadata."""
    from djsetbuilder.db.sync import sync_rekordbox

    sync_rekordbox(compute_hashes=hashes)


@cli.command()
def stats():
    """Show library statistics (genre, BPM, key, energy distribution)."""
    from djsetbuilder.db.models import get_session
    from djsetbuilder.db.store import library_stats

    session = get_session()
    s = library_stats(session)

    if s["total_tracks"] == 0:
        console.print("[yellow]No tracks in database. Run 'djset sync' first.[/]")
        return

    console.print(f"\n[bold]Library: {s['total_tracks']} tracks[/] ({s['analyzed_tracks']} analyzed)\n")

    # BPM
    if s["bpm_avg"]:
        console.print(f"[bold]BPM range:[/] {s['bpm_min']:.0f} – {s['bpm_max']:.0f} (avg {s['bpm_avg']})\n")

    # Genres
    if s["genres"]:
        table = Table(title="Genres (from directory)")
        table.add_column("Genre", style="cyan")
        table.add_column("Tracks", justify="right")
        table.add_column("Bar")
        max_count = max(s["genres"].values())
        for genre, count in sorted(s["genres"].items(), key=lambda x: -x[1]):
            bar_len = int(30 * count / max_count)
            table.add_row(genre, str(count), "█" * bar_len)
        console.print(table)
        console.print()

    # Energy levels
    if s["energies"]:
        table = Table(title="Energy Levels (from directory)")
        table.add_column("Energy", style="magenta")
        table.add_column("Tracks", justify="right")
        for energy, count in sorted(s["energies"].items(), key=lambda x: -x[1]):
            table.add_row(energy, str(count))
        console.print(table)
        console.print()

    # Keys
    if s["keys"]:
        table = Table(title="Key Distribution (top 15)")
        table.add_column("Key", style="green")
        table.add_column("Tracks", justify="right")
        for key, count in sorted(s["keys"].items(), key=lambda x: -x[1])[:15]:
            table.add_row(key, str(count))
        console.print(table)
        console.print()

    # Top artists
    if s["top_artists"]:
        table = Table(title="Top Artists")
        table.add_column("Artist", style="yellow")
        table.add_column("Tracks", justify="right")
        for artist, count in list(s["top_artists"].items())[:15]:
            table.add_row(artist, str(count))
        console.print(table)


@cli.command()
@click.argument("query")
@click.option("-n", "--num", default=10, help="Number of results")
def similar(query: str, num: int):
    """Find acoustically similar tracks by MFCC fingerprint."""
    from djsetbuilder.analysis.similarity import find_similar
    from djsetbuilder.db.models import get_session

    session = get_session()
    results = find_similar(session, query, n=num)

    if not results:
        console.print("[yellow]No results found. Is the track analyzed?[/]")
        return

    table = Table(title=f"Tracks similar to '{query}'")
    table.add_column("#", justify="right", style="dim")
    table.add_column("Title", style="cyan")
    table.add_column("Artist")
    table.add_column("Genre")
    table.add_column("BPM", justify="right")
    table.add_column("Similarity", justify="right", style="green")

    for i, (track, score) in enumerate(results, 1):
        table.add_row(
            str(i),
            track.title or "?",
            track.artist or "?",
            track.dir_genre or track.rb_genre or "?",
            f"{track.bpm:.0f}" if track.bpm else "?",
            f"{score:.3f}",
        )

    console.print(table)


@cli.command("suggest-next")
@click.argument("query")
@click.option("-n", "--num", default=10, help="Number of suggestions")
def suggest_next(query: str, num: int):
    """Suggest best next tracks to mix from a given track."""
    from djsetbuilder.db.models import get_session
    from djsetbuilder.db.store import get_track_by_title
    from djsetbuilder.setbuilder.scoring import score_transitions

    session = get_session()
    track = get_track_by_title(session, query)

    if not track:
        console.print(f"[yellow]Track '{query}' not found.[/]")
        return

    results = score_transitions(session, track, n=num)

    table = Table(title=f"Best transitions from '{track.title}'")
    table.add_column("#", justify="right", style="dim")
    table.add_column("Title", style="cyan")
    table.add_column("Artist")
    table.add_column("Key")
    table.add_column("BPM", justify="right")
    table.add_column("Genre")
    table.add_column("Score", justify="right", style="green")

    for i, (t, score) in enumerate(results, 1):
        table.add_row(
            str(i),
            t.title or "?",
            t.artist or "?",
            t.key or "?",
            f"{t.bpm:.0f}" if t.bpm else "?",
            t.dir_genre or t.rb_genre or "?",
            f"{score:.3f}",
        )

    console.print(table)


@cli.command()
@click.option("--duration", default=120, help="Set duration in minutes")
@click.option("--energy", default="warmup:30:0.3,build:20:0.6,peak:40:0.9,cooldown:20:0.4",
              help="Energy profile: name:minutes:target,...")
@click.option("--genres", default=None, help="Comma-separated genre filter")
@click.option("--bpm-min", default=None, type=float, help="Minimum BPM")
@click.option("--bpm-max", default=None, type=float, help="Maximum BPM")
@click.option("--seed", default=None, help="Seed track title")
@click.option("--output", default=None, help="Set name")
@click.option("--beam-width", default=5, help="Beam search width")
@click.option("--prefer-playlists", default=None, help="Comma-separated playlist name prefixes to boost")
def build(duration: int, energy: str, genres: str | None, bpm_min: float | None,
          bpm_max: float | None, seed: str | None, output: str | None, beam_width: int,
          prefer_playlists: str | None):
    """Generate an optimized DJ set."""
    from djsetbuilder.db.models import get_session
    from djsetbuilder.setbuilder.constraints import EnergyProfile, parse_energy_string
    from djsetbuilder.setbuilder.planner import build_set

    session = get_session()
    energy_profile = parse_energy_string(energy)
    genre_list = [g.strip() for g in genres.split(",")] if genres else None
    bpm_range = (bpm_min, bpm_max) if bpm_min is not None and bpm_max is not None else None
    playlist_list = [p.strip() for p in prefer_playlists.split(",")] if prefer_playlists else None

    result = build_set(
        session,
        duration_min=duration,
        energy_profile=energy_profile,
        genres=genre_list,
        bpm_range=bpm_range,
        seed_title=seed,
        beam_width=beam_width,
        set_name=output,
        prefer_playlists=playlist_list,
    )

    if not result:
        console.print("[yellow]Could not generate a set. Try broader filters.[/]")
        return

    console.print(f"\n[bold green]Generated set: {result.name}[/]")
    console.print(f"Duration: {result.duration_min} min | Tracks: {len(result.tracks)}\n")

    table = Table()
    table.add_column("#", justify="right", style="dim")
    table.add_column("Title", style="cyan")
    table.add_column("Artist")
    table.add_column("Key")
    table.add_column("BPM", justify="right")
    table.add_column("Energy")
    table.add_column("Genre")
    table.add_column("★", justify="right", style="yellow")
    table.add_column("▶", justify="right")
    table.add_column("Trans.", justify="right", style="green")

    for st in result.tracks:
        t = st.track
        rating_str = "★" * t.rating if t.rating else "—"
        table.add_row(
            str(st.position),
            t.title or "?",
            t.artist or "?",
            t.key or "?",
            f"{t.bpm:.0f}" if t.bpm else "?",
            t.dir_energy or "?",
            t.dir_genre or t.rb_genre or "?",
            rating_str,
            str(t.play_count or 0),
            f"{st.transition_score:.2f}" if st.transition_score else "—",
        )

    console.print(table)


@cli.command()
@click.argument("set_name")
@click.option("--format", "fmt", default="rekordbox", help="Export format")
@click.option("--output", "-o", default=None, help="Output file path")
@click.option("--with-cues", is_flag=True, help="Include transition cue points in export")
def export(set_name: str, fmt: str, output: str | None, with_cues: bool):
    """Export a generated set as Rekordbox XML playlist."""
    from djsetbuilder.db.models import Set, TransitionCue, get_session
    from djsetbuilder.export.rekordbox_xml import export_set_to_xml

    session = get_session()
    set_ = session.query(Set).filter(Set.name.ilike(f"%{set_name}%")).first()

    if not set_:
        console.print(f"[yellow]Set '{set_name}' not found.[/]")
        return

    transition_cues = None
    if with_cues:
        cues = (
            session.query(TransitionCue)
            .filter(TransitionCue.set_id == set_.id)
            .order_by(TransitionCue.track_id, TransitionCue.start_sec)
            .all()
        )
        if cues:
            transition_cues: dict[int, list[dict]] = {}
            for c in cues:
                transition_cues.setdefault(c.track_id, []).append({
                    "name": c.name, "type": c.cue_type,
                    "start": c.start_sec, "end": c.end_sec, "num": c.hot_cue_num,
                })
            console.print(f"[cyan]Including {len(cues)} cue points from {len(transition_cues)} tracks[/]")
        else:
            console.print("[dim]No cue points found for this set.[/]")

    output_path = export_set_to_xml(set_, output, transition_cues=transition_cues)
    console.print(f"[green]Exported to {output_path}[/]")


@cli.command()
@click.option("--track", "track_query", default=None, help="Pre-load a specific track")
@click.option("--set", "set_name", default=None, help="Pre-load a specific set")
@click.option("--port", default=8050, help="HTTP port for the web server")
@click.option("--debug", is_flag=True, help="Enable debug mode with hot reload")
def visualize(track_query: str | None, set_name: str | None, port: int, debug: bool):
    """Launch the waveform visualizer web app."""
    try:
        from djsetbuilder.visualization import run_visualizer
    except ImportError:
        console.print("[red]Visualizer dependencies not installed.[/]")
        console.print("Install with: [cyan]pip install '.[visualizer]'[/]")
        return

    run_visualizer(port=port, debug=debug, track_query=track_query, set_name=set_name)


@cli.command()
@click.argument("query")
def classify(query: str):
    """Show all features for a track."""
    from djsetbuilder.db.models import get_session
    from djsetbuilder.db.store import get_track_by_title

    session = get_session()
    track = get_track_by_title(session, query)

    if not track:
        console.print(f"[yellow]Track '{query}' not found.[/]")
        return

    console.print(f"\n[bold]{track.title}[/] — {track.artist}")
    console.print(f"  BPM: {track.bpm or '?'} | Key: {track.key or '?'} | Rating: {track.rating or '?'}")
    console.print(f"  Rekordbox genre: {track.rb_genre or '?'}")
    console.print(f"  Directory genre: {track.dir_genre or '?'} | Energy: {track.dir_energy or '?'}")
    console.print(f"  Duration: {track.duration_sec:.0f}s" if track.duration_sec else "")
    console.print(f"  Play count: {track.play_count or 0}")
    console.print(f"  File: {track.file_path or '?'}")

    af = track.audio_features
    if af:
        console.print(f"\n[bold]Audio Features:[/]")
        console.print(f"  Energy: {af.energy:.3f}" if af.energy else "")
        console.print(f"  Danceability: {af.danceability:.3f}" if af.danceability else "")
        console.print(f"  Loudness: {af.loudness_lufs:.1f} LUFS" if af.loudness_lufs else "")
        console.print(f"  Brightness: {af.spectral_centroid:.0f}" if af.spectral_centroid else "")
        console.print(f"  Mood: happy={af.mood_happy:.2f} sad={af.mood_sad:.2f} "
                       f"aggressive={af.mood_aggressive:.2f} relaxed={af.mood_relaxed:.2f}"
                       if af.mood_happy is not None else "")
        console.print(f"  ML Genre: {af.ml_genre} ({af.ml_genre_confidence:.2f})"
                       if af.ml_genre else "")
        console.print(f"  Energy curve: intro={af.energy_intro:.2f} body={af.energy_body:.2f} "
                       f"outro={af.energy_outro:.2f}"
                       if af.energy_intro is not None else "")
        console.print(f"  Verified BPM: {af.verified_bpm}" if af.verified_bpm else "")
        console.print(f"  Verified Key: {af.verified_key}" if af.verified_key else "")
    else:
        console.print("\n[dim]No audio features. Run 'djset analyze' first.[/]")


@cli.command()
@click.option("--force", is_flag=True, help="Re-analyze all tracks")
@click.option("--workers", default=1, help="Number of parallel workers")
@click.option("--track", "track_name", default=None, help="Analyze a single track")
@click.option("--waveform-only", is_flag=True, help="Only extract waveforms (skip full analysis)")
def analyze(force: bool, workers: int, track_name: str | None, waveform_only: bool):
    """Run audio analysis on tracks (requires essentia + librosa)."""
    from djsetbuilder.analysis.analyzer import run_analysis

    run_analysis(force=force, workers=workers, single_track=track_name, waveform_only=waveform_only)
