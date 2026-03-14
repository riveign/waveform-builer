# DJ Set Builder

CLI toolkit for building optimized DJ sets from a Rekordbox library with waveform visualization, harmonic mixing, energy flow profiling, and intelligent track sequencing.

## Features

- **Rekordbox Sync** — Import your full library from Rekordbox's database, including BPM, key, genre, rating, and play count
- **Audio Analysis** — Extract energy, danceability, mood, spectral features, MFCCs, and waveform envelopes using Essentia and Librosa
- **Smart Set Building** — Beam search algorithm optimizes for harmonic compatibility (Camelot wheel), energy flow, BPM matching, and genre coherence
- **Waveform Visualizer** — Interactive web-based waveform viewer with track comparison, set timeline, transition detail, and cue point editing
- **Cue Point Marking** — Click on waveforms to place Mix In/Out, Drop, Loop, and Fade cue points
- **Rekordbox Export** — Export sets as Rekordbox XML playlists with cue points as POSITION_MARK entries

## Installation

```bash
# Clone
git clone git@github.com:riveign/waveform-builer.git
cd waveform-builer

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install core + visualizer
pip install -e ".[visualizer]"

# For full audio analysis (optional, requires essentia + librosa)
pip install -e ".[analysis,visualizer]"
```

## Quick Start

```bash
# 1. Import your Rekordbox library
djset sync

# 2. Analyze tracks (requires external drive with music files)
djset analyze

# 3. Extract waveforms only (faster, if already analyzed)
djset analyze --waveform-only

# 4. Build a set
djset build --duration 120 --output "Saturday Night"

# 5. Launch the waveform visualizer
djset visualize

# 6. Export to Rekordbox with cue points
djset export "Saturday Night" --with-cues
```

## CLI Commands

| Command | Description |
|---------|-------------|
| `djset sync` | Import Rekordbox library and parse directory metadata |
| `djset stats` | Show library statistics (genre, BPM, key, energy distribution) |
| `djset analyze` | Run audio analysis on tracks (essentia + librosa) |
| `djset similar <query>` | Find acoustically similar tracks by MFCC fingerprint |
| `djset suggest-next <query>` | Suggest best next tracks to mix based on harmonic/BPM/energy |
| `djset build` | Generate an optimized DJ set via beam search |
| `djset export <set>` | Export a set as Rekordbox XML playlist |
| `djset classify <query>` | Show all metadata and audio features for a track |
| `djset visualize` | Launch the waveform visualizer web app |

## Waveform Visualizer

The visualizer runs as a local web app at `http://localhost:8050`.

**Track View** — Search and load individual tracks. Interactive waveform with zoom/pan, beat markers, energy curve overlay, and cue point editing.

**Set Timeline** — View an entire set's waveforms end-to-end with transition scores. Click through transitions to see the outro/intro overlap between consecutive tracks.

**Cue Points** — Click on the waveform to mark transition points. Supports Cue, Loop, Fade In, and Fade Out types with memory or hot cue slots (A-H).

**Export** — One-click export to Rekordbox XML with all cue points included as POSITION_MARK entries.

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
src/djsetbuilder/
  cli.py                    # Click CLI (9 commands)
  config.py                 # Paths, constants, scoring weights
  db/
    models.py               # SQLAlchemy models (Track, AudioFeatures, Set, TransitionCue)
    sync.py                 # Rekordbox import via pyrekordbox
    store.py                # Query helpers
  analysis/
    essentia_ext.py         # BPM, key, energy, danceability, mood
    librosa_ext.py          # MFCC extraction
    waveform.py             # Waveform envelope + beat extraction
    analyzer.py             # Batch analysis orchestrator
    similarity.py           # MFCC cosine similarity
  setbuilder/
    camelot.py              # Camelot wheel harmonic scoring
    scoring.py              # 5-dimension transition scoring
    constraints.py          # Energy profiles, genre filters
    planner.py              # Beam search set generation
  visualization/
    app.py                  # Dash app factory
    layout.py               # UI layout components
    callbacks.py            # Interactive callbacks
    figures.py              # Plotly figure builders
    assets/style.css        # Dark theme
  export/
    rekordbox_xml.py        # Rekordbox XML with cue points
```

## Requirements

- Python 3.9+
- Rekordbox (for library sync)
- Music files on accessible drives (for analysis)

After analysis, the visualizer works offline from cached data — no drives or Rekordbox needed.

## License

MIT
