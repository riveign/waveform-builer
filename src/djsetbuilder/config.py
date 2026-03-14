"""Configuration and constants for DJ Set Builder.

Loads user overrides from ~/.djsetbuilder/config.toml, falls back to hardcoded defaults.
"""

import os
import sys
import tomllib
from pathlib import Path

# Config file location
CONFIG_DIR = Path.home() / ".djsetbuilder"
CONFIG_FILE = CONFIG_DIR / "config.toml"

# Project paths (defaults)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DB_PATH = DATA_DIR / "dj_library.db"


def _load_toml() -> dict:
    """Load user config from TOML file. Returns empty dict if missing."""
    if not CONFIG_FILE.exists():
        return {}
    with open(CONFIG_FILE, "rb") as f:
        return tomllib.load(f)


def _get(section: str, key: str, default):
    """Get a config value: TOML override > hardcoded default."""
    toml = _load_toml()
    return toml.get(section, {}).get(key, default)


# ── Paths ──────────────────────────────────────────────────────────────

def _resolve_db_path() -> Path:
    custom = _get("paths", "db_path", None)
    if custom:
        return Path(custom)
    return DB_PATH


def _resolve_music_roots() -> list[Path]:
    custom = _get("paths", "music_roots", None)
    if custom:
        return [Path(p) for p in custom]
    env_roots = os.environ.get("DJSET_MUSIC_ROOTS")
    if env_roots:
        return [Path(p) for p in env_roots.split(":") if p]
    if sys.platform == "darwin":
        return [
            Path("/Volumes/SSD/Musica"),
            Path("/Volumes/My Passport/Musica"),
        ]
    return [
        Path("/run/media/mantis/SSD/Musica"),
    ]


MUSIC_ROOTS = _resolve_music_roots()

# Known energy tags from directory names (order matters for regex alternation)
ENERGY_TAGS = [
    "Warmup", "Closing", "Dance",
    "Peak", "High", "Up", "Mid", "Low", "Fast",
]

# ── Scoring weights ────────────────────────────────────────────────────

def _resolve_scoring_weights() -> dict[str, float]:
    defaults = {
        "harmonic": 0.25,
        "energy_fit": 0.20,
        "bpm_compat": 0.20,
        "genre_coherence": 0.15,
        "track_quality": 0.20,
    }
    toml = _load_toml()
    overrides = toml.get("scoring", {})
    return {k: overrides.get(k, v) for k, v in defaults.items()}


SCORING_WEIGHTS = _resolve_scoring_weights()

# ── Search defaults ────────────────────────────────────────────────────

BPM_TOLERANCE = _get("search", "bpm_tolerance", 0.06)
ARTIST_COOLDOWN = _get("search", "artist_cooldown", 5)
DEFAULT_BEAM_WIDTH = _get("search", "default_beam_width", 5)

# ── Visualizer ─────────────────────────────────────────────────────────

VISUALIZER_PORT = 8050
WAVEFORM_OVERVIEW_POINTS = 1000
WAVEFORM_DETAIL_HOP = 512
WAVEFORM_SR = 22050


# ── Public API ─────────────────────────────────────────────────────────

def get_db_url() -> str:
    db = _resolve_db_path()
    db.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{db}"


def get_config() -> dict:
    """Return full merged config (defaults + TOML overrides)."""
    defaults = {
        "paths": {
            "db_path": str(_resolve_db_path()),
            "music_roots": [str(p) for p in _resolve_music_roots()],
        },
        "scoring": _resolve_scoring_weights(),
        "search": {
            "bpm_tolerance": BPM_TOLERANCE,
            "artist_cooldown": ARTIST_COOLDOWN,
            "default_beam_width": DEFAULT_BEAM_WIDTH,
        },
        "energy_tags": {tag.lower(): _get("energy_tags", tag.lower(), None) for tag in ENERGY_TAGS},
        "energy_presets": _get("energy_presets", None, None) or {},
        "genre_aliases": _get("genre_aliases", None, None) or {},
    }
    # Merge TOML on top
    toml = _load_toml()
    for section, section_defaults in defaults.items():
        if isinstance(section_defaults, dict):
            toml_section = toml.get(section, {})
            if isinstance(toml_section, dict):
                defaults[section] = {**section_defaults, **toml_section}
    return defaults


def save_config_value(section: str, key: str, value) -> None:
    """Set a single config value in the TOML file."""
    import tomli_w

    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    config = _load_toml()
    if section not in config:
        config[section] = {}
    # Coerce numeric strings
    if isinstance(value, str):
        try:
            value = int(value)
        except ValueError:
            try:
                value = float(value)
            except ValueError:
                pass
    config[section][key] = value
    with open(CONFIG_FILE, "wb") as f:
        tomli_w.dump(config, f)
