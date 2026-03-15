# Kiku (聴)

Learn why your transitions work — not just find the next track, but build the instinct to know why it's the right one.

## Features

- **Rekordbox Sync** — Import your full library from Rekordbox's database, including BPM, key, genre, rating, and play count
- **Audio Analysis** — Extract energy, danceability, mood, spectral features, MFCCs, and waveform envelopes using Essentia and Librosa
- **Smart Set Building** — Beam search algorithm optimizes for harmonic compatibility (Camelot wheel), energy flow, BPM matching, and genre coherence
- **SvelteKit UI** — Taste DNA dashboard, set timeline with drag-and-drop, transition scoring, energy flow charts
- **Waveform Visualizer** — Interactive waveform viewer with track comparison, set timeline, transition detail, and cue point editing
- **Rekordbox Export** — Export sets as Rekordbox XML playlists with cue points

## Installation

```bash
# Clone
git clone git@github.com:riveign/waveform-builer.git
cd waveform-builer

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install core + API
pip install -e ".[api]"

# For full audio analysis (optional, requires essentia + librosa)
pip install -e ".[analysis]"
```

## Quick Start

```bash
# 1. Import your Rekordbox library
kiku sync

# 2. Analyze tracks (requires external drive with music files)
kiku analyze

# 3. Build a set
kiku build --duration 120 --output "Saturday Night"

# 4. Launch the API + UI
kiku serve

# 5. Export to Rekordbox with cue points
kiku export "Saturday Night" --with-cues
```

## CLI Commands

| Command | Description |
|---------|-------------|
| `kiku sync` | Import Rekordbox library and parse directory metadata |
| `kiku scan` | Import tracks from filesystem (no Rekordbox required) |
| `kiku stats` | Show library statistics (genre, BPM, key, energy distribution) |
| `kiku gaps` | Identify gaps in your library (Camelot, BPM, energy) |
| `kiku search` | Search your track library with filters |
| `kiku analyze` | Run audio analysis on tracks (essentia + librosa) |
| `kiku similar <query>` | Find acoustically similar tracks by MFCC fingerprint |
| `kiku suggest-next <query>` | Suggest best next tracks to mix |
| `kiku build` | Generate an optimized DJ set via beam search |
| `kiku export <set>` | Export a set as Rekordbox XML playlist |
| `kiku classify <query>` | Show all metadata and audio features for a track |
| `kiku serve` | Launch the FastAPI backend for the SvelteKit UI |
| `kiku visualize` | Launch the Dash waveform visualizer |
| `kiku autotag energy` | Classify energy zones using ML trained on your tags |
| `kiku config show/set/path` | View and modify configuration |

## Scoring System

Sets are built using a 5-dimension weighted scoring system:

| Dimension | Weight | Description |
|-----------|--------|-------------|
| Harmonic (Camelot) | 25% | Key compatibility — same key, adjacent, mode switch |
| Energy fit | 20% | Distance from target energy curve |
| BPM compatibility | 20% | Within 6% tolerance, double/half time |
| Genre coherence | 15% | Same genre family matching |
| Track quality | 20% | Rating, play count, playlist membership |

## Project Structure

```
src/kiku/
  cli.py                    # Click CLI
  config.py                 # Paths, constants, scoring weights
  db/
    models.py               # SQLAlchemy models (Track, AudioFeatures, Set, TransitionCue)
    sync.py                 # Rekordbox import via pyrekordbox
    scan.py                 # Filesystem import
    store.py                # Query helpers
  analysis/
    essentia_ext.py         # BPM, key, energy, danceability, mood
    librosa_ext.py          # MFCC extraction
    waveform.py             # Waveform envelope + beat extraction
    analyzer.py             # Batch analysis orchestrator
    autotag.py              # Energy zone classifier
    similarity.py           # MFCC cosine similarity
    insights.py             # Library stats and gap analysis
  setbuilder/
    camelot.py              # Camelot wheel harmonic scoring
    scoring.py              # 5-dimension transition scoring
    constraints.py          # Energy profiles, genre filters
    planner.py              # Beam search set generation
  api/
    main.py                 # FastAPI app factory
    routes/                 # REST endpoints
  visualization/
    app.py                  # Dash app factory
    layout.py               # UI layout components
    callbacks.py            # Interactive callbacks
    figures.py              # Plotly figure builders
  export/
    rekordbox_xml.py        # Rekordbox XML with cue points
frontend/
  src/                      # SvelteKit UI
```

## Requirements

- Python 3.9+
- Rekordbox (for library sync) or music files on accessible drives
- Node.js 18+ (for frontend development)

## License

MIT
