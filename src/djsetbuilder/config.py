"""Configuration and constants for DJ Set Builder."""

from pathlib import Path

# Project paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DB_PATH = DATA_DIR / "dj_library.db"

# Rekordbox music roots (external drives)
MUSIC_ROOTS = [
    Path("/Volumes/SSD/Musica"),
    Path("/Volumes/My Passport/Musica"),
]

# Known energy tags from directory names (order matters for regex alternation)
ENERGY_TAGS = [
    "Warmup", "Closing", "Dance",
    "Peak", "High", "Up", "Mid", "Low", "Fast",
]

# BPM compatibility threshold for transitions (±6%)
BPM_TOLERANCE = 0.06

# Beam search parameters
DEFAULT_BEAM_WIDTH = 5

# Transition scoring weights
SCORING_WEIGHTS = {
    "harmonic": 0.25,
    "energy_fit": 0.20,
    "bpm_compat": 0.20,
    "genre_coherence": 0.15,
    "track_quality": 0.20,  # rating + play count + playlist membership
}

# Same-artist cooldown (tracks)
ARTIST_COOLDOWN = 5

# Visualizer settings
VISUALIZER_PORT = 8050
WAVEFORM_OVERVIEW_POINTS = 1000
WAVEFORM_DETAIL_HOP = 512
WAVEFORM_SR = 22050

# Database URL
def get_db_url() -> str:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{DB_PATH}"
