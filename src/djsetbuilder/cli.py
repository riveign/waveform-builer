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


@cli.group("config")
def config_group():
    """View and modify DJ Set Builder configuration."""


@config_group.command("show")
def config_show():
    """Display all configuration with override indicators."""
    from djsetbuilder.config import CONFIG_FILE, get_config

    cfg = get_config()
    has_toml = CONFIG_FILE.exists()

    table = Table(title="DJ Set Builder Configuration")
    table.add_column("Section", style="cyan")
    table.add_column("Key", style="bold")
    table.add_column("Value")
    table.add_column("Source", style="dim")

    for section, values in cfg.items():
        if isinstance(values, dict):
            for key, val in values.items():
                source = "[green]toml[/]" if has_toml else "default"
                table.add_row(section, key, str(val), source)
        else:
            source = "[green]toml[/]" if has_toml else "default"
            table.add_row("", section, str(values), source)

    console.print(table)


@config_group.command("set")
@click.argument("dotted_key")
@click.argument("value")
def config_set(dotted_key: str, value: str):
    """Set a config value (e.g., djset config set scoring.harmonic 0.30)."""
    from djsetbuilder.config import save_config_value

    parts = dotted_key.split(".", 1)
    if len(parts) != 2:
        console.print("[red]Key must be section.key (e.g., scoring.harmonic)[/]")
        raise SystemExit(1)

    section, key = parts
    save_config_value(section, key, value)
    console.print(f"[green]Set {dotted_key} = {value}[/]")


@config_group.command("path")
def config_path():
    """Print the config file location."""
    from djsetbuilder.config import CONFIG_FILE

    console.print(str(CONFIG_FILE))


@cli.command()
@click.option("--title", "-t", default=None, help="Title search (partial match)")
@click.option("--artist", "-a", default=None, help="Artist search (partial match)")
@click.option("--genre", "-g", default=None, help="Genre filter")
@click.option("--key", "-k", default=None, help="Musical key filter (e.g., 8A, 11B)")
@click.option("--bpm", default=None, help="BPM range (e.g., 124-130)")
@click.option("--energy", "-e", default=None, help="Energy level filter (e.g., Peak, Warmup)")
@click.option("--rating", "-r", default=None, type=int, help="Minimum star rating (1-5)")
@click.option("-n", "--limit", default=50, help="Max results")
def search(title: str | None, artist: str | None, genre: str | None,
           key: str | None, bpm: str | None, energy: str | None,
           rating: int | None, limit: int):
    """Search your track library with filters."""
    from djsetbuilder.db.models import get_session
    from djsetbuilder.db.store import search_tracks

    bpm_min = bpm_max = None
    if bpm:
        if "-" in bpm:
            lo, hi = bpm.split("-", 1)
            bpm_min, bpm_max = float(lo), float(hi)
        else:
            bpm_min = bpm_max = float(bpm)

    session = get_session()
    results = search_tracks(
        session, title=title, artist=artist, genre=genre,
        bpm_min=bpm_min, bpm_max=bpm_max, energy=energy,
        key=key, rating_min=rating, limit=limit,
    )

    if not results:
        console.print("[yellow]No tracks found matching your filters.[/]")
        return

    table = Table(title=f"Search Results ({len(results)} tracks)")
    table.add_column("#", justify="right", style="dim")
    table.add_column("Title", style="cyan")
    table.add_column("Artist")
    table.add_column("Key", style="green")
    table.add_column("BPM", justify="right")
    table.add_column("Energy", style="magenta")
    table.add_column("Genre")
    table.add_column("★", justify="right", style="yellow")

    for i, t in enumerate(results, 1):
        stars = "★" * t.rating if t.rating else "—"
        table.add_row(
            str(i),
            t.title or "?",
            t.artist or "?",
            t.key or "?",
            f"{t.bpm:.0f}" if t.bpm else "?",
            t.dir_energy or "?",
            t.dir_genre or t.rb_genre or "?",
            stars,
        )

    console.print(table)


@cli.command()
@click.option("--hashes", is_flag=True, help="Compute file hashes for change detection (slower)")
@click.option("--db-path", default=None, type=click.Path(exists=True),
              help="Path to Rekordbox master.db (required on Linux)")
def sync(hashes: bool, db_path: str | None):
    """Import Rekordbox library and parse directory metadata."""
    from djsetbuilder.db.sync import sync_rekordbox

    sync_rekordbox(compute_hashes=hashes, db_path=db_path)


@cli.command()
@click.option("--path", "-p", type=click.Path(exists=True), default=None,
              help="Override MUSIC_ROOTS with a specific path")
@click.option("--dry-run", is_flag=True, help="Show what would be imported without writing to DB")
@click.option("--force", is_flag=True, help="Re-import even if track already exists")
def scan(path: str | None, dry_run: bool, force: bool):
    """Import tracks from filesystem (no Rekordbox required)."""
    from pathlib import Path as P

    from djsetbuilder.db.scan import scan_filesystem

    roots = [P(path)] if path else None
    scan_filesystem(roots=roots, dry_run=dry_run, force=force)


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
@click.option("--energy", default="journey",
              help="Energy preset (warmup/peak-time/journey/afterhours) or raw format name:min:energy,...")
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
    from djsetbuilder.setbuilder.constraints import resolve_energy
    from djsetbuilder.setbuilder.planner import build_set

    session = get_session()
    energy_profile = resolve_energy(energy)
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


@cli.command("import-waveforms")
@click.argument("anlz_root", type=click.Path(exists=True))
@click.option("--force", is_flag=True, help="Overwrite existing waveform data")
def import_waveforms(anlz_root: str, force: bool):
    """Import pre-computed waveforms from Rekordbox ANLZ files.

    ANLZ_ROOT is the path to the PIONEER/USBANLZ directory (or a parent
    containing it). Each ANLZ subdirectory is matched to a DB track via
    the embedded audio file path.
    """
    from datetime import datetime
    from pathlib import Path

    from djsetbuilder.analysis.waveform import (
        import_rekordbox_waveform,
        read_anlz_path,
    )
    from djsetbuilder.db.models import AudioFeatures, Track, get_session

    root = Path(anlz_root)

    # Find all hex ANLZ directories (contain ANLZ0000.DAT)
    anlz_dirs = sorted(root.rglob("ANLZ0000.DAT"))
    if not anlz_dirs:
        console.print(f"[yellow]No ANLZ0000.DAT files found under {root}[/]")
        return

    console.print(f"Found [bold]{len(anlz_dirs)}[/] ANLZ directories")

    session = get_session()

    # Build a lookup from normalized path suffixes to Track objects
    all_tracks = session.query(Track).filter(Track.file_path.isnot(None)).all()
    # Map: lowercased filename → list of tracks (handle collisions)
    path_index: dict[str, list[Track]] = {}
    for t in all_tracks:
        # Store by the relative path portion (everything after mount point)
        # e.g. /run/media/mantis/SSD/Musica/2025/... → Musica/2025/...
        fp = t.file_path
        # Try to extract the "Musica/..." portion
        parts = fp.split("/")
        for i, part in enumerate(parts):
            if part.lower() == "musica":
                rel = "/".join(parts[i:])
                path_index.setdefault(rel.lower(), []).append(t)
                break
        else:
            # Fallback: use filename
            path_index.setdefault(Path(fp).name.lower(), []).append(t)

    imported = 0
    skipped_no_match = 0
    skipped_exists = 0
    errors = 0

    for dat_path in anlz_dirs:
        anlz_dir = dat_path.parent

        # Read the embedded audio path
        anlz_path = read_anlz_path(anlz_dir)
        if not anlz_path:
            errors += 1
            continue

        # Match to DB track: strip leading / and look for "Musica/..." portion
        parts = anlz_path.strip("/").split("/")
        rel_key = None
        for i, part in enumerate(parts):
            if part.lower() == "musica":
                rel_key = "/".join(parts[i:]).lower()
                break

        if rel_key is None:
            # Fallback: match by filename
            rel_key = Path(anlz_path).name.lower()

        matches = path_index.get(rel_key, [])
        if not matches:
            skipped_no_match += 1
            console.print(f"  [dim]No match: {anlz_path}[/]")
            continue

        track = matches[0]

        # Check if waveform already exists
        if not force and track.audio_features and track.audio_features.waveform_detail:
            skipped_exists += 1
            continue

        # Need duration for time axis calculation
        if not track.duration_sec or track.duration_sec <= 0:
            console.print(f"  [yellow]No duration for: {track.title}[/]")
            errors += 1
            continue

        waveform_data = import_rekordbox_waveform(anlz_dir, track.duration_sec)
        if waveform_data is None:
            errors += 1
            continue

        # Create or update AudioFeatures
        af = track.audio_features
        if af is None:
            af = AudioFeatures(track_id=track.id)
            session.add(af)

        af.waveform_overview = waveform_data["waveform_overview"].tobytes()
        af.waveform_detail = waveform_data["waveform_detail"].tobytes()
        af.waveform_sr = waveform_data["waveform_sr"]
        af.waveform_hop = waveform_data["waveform_hop"]
        if "beat_positions" in waveform_data:
            af.beat_positions = waveform_data["beat_positions"].tobytes()
        if af.analyzed_at is None:
            af.analyzed_at = datetime.now().isoformat()

        imported += 1
        console.print(f"  [green]Imported:[/] {track.title} — {track.artist}")

    session.commit()
    session.close()

    console.print(f"\n[bold green]Done![/] Imported {imported} waveforms")
    if skipped_exists:
        console.print(f"  Skipped {skipped_exists} (already have waveforms, use --force to overwrite)")
    if skipped_no_match:
        console.print(f"  Skipped {skipped_no_match} (no matching track in DB)")
    if errors:
        console.print(f"  [yellow]Errors: {errors}[/]")


@cli.command()
@click.option("--force", is_flag=True, help="Re-analyze all tracks")
@click.option("--workers", default=0, help="Number of parallel workers (0 = auto: half of CPU cores)")
@click.option("--track", "track_name", default=None, help="Analyze a single track")
@click.option("--waveform-only", is_flag=True, help="Only extract waveforms (skip full analysis)")
@click.option("--bands", is_flag=True, help="Extract frequency band envelopes only")
@click.option("--recompute", default=None, help="Recompute specific features: energy_mood")
def analyze(force: bool, workers: int, track_name: str | None, waveform_only: bool, bands: bool, recompute: str | None):
    """Run audio analysis on tracks (requires essentia + librosa)."""
    from djsetbuilder.analysis.analyzer import run_analysis

    run_analysis(
        force=force, workers=workers, single_track=track_name,
        waveform_only=waveform_only, bands_only=bands, recompute=recompute,
    )
