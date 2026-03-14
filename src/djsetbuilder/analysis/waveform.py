"""Waveform envelope extraction for visualization."""

from __future__ import annotations

from pathlib import Path

import numpy as np


def extract_waveform(
    file_path: str,
    sr: int = 22050,
    hop_length: int = 512,
    overview_points: int = 1000,
    audio: np.ndarray | None = None,
    skip_beats: bool = False,
) -> dict:
    """Extract waveform envelope and beat positions from an audio file.

    When *audio* (float32 array at 22050 Hz) is provided, the file is
    not re-decoded from disk.

    When *skip_beats* is True, beat tracking is skipped for faster
    waveform-only extraction.

    Returns dict with waveform_overview, waveform_detail, waveform_sr,
    waveform_hop, and optionally beat_positions.
    """
    import librosa

    if audio is not None:
        y = audio
        sr_actual = sr
    else:
        y, sr_actual = librosa.load(str(file_path), sr=sr, mono=True)

    if len(y) == 0:
        return {}

    # RMS envelope (detail resolution)
    rms = librosa.feature.rms(y=y, frame_length=2048, hop_length=hop_length)[0]
    detail = rms.astype(np.float32)

    # Peak-downsampled overview
    overview = peak_downsample(detail, overview_points).astype(np.float32)

    result = {
        "waveform_overview": overview,
        "waveform_detail": detail,
        "waveform_sr": sr_actual,
        "waveform_hop": hop_length,
    }

    # Beat positions (expensive — skip in waveform-only mode)
    if not skip_beats:
        _tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr_actual, hop_length=hop_length)
        beat_times = librosa.frames_to_time(beat_frames, sr=sr_actual, hop_length=hop_length)
        result["beat_positions"] = beat_times.astype(np.float32)

    return result


def peak_downsample(data: np.ndarray, target_points: int) -> np.ndarray:
    """Downsample by taking max absolute value per window.

    Preserves peaks for visual fidelity in overview display.
    """
    if len(data) <= target_points:
        return data.copy()

    window_size = len(data) // target_points
    n_complete = window_size * target_points
    reshaped = data[:n_complete].reshape(target_points, window_size)
    return np.max(np.abs(reshaped), axis=1)


def extract_band_envelopes(
    file_path: str,
    sr: int = 22050,
    hop_length: int = 512,
    overview_points: int = 1000,
    audio: np.ndarray | None = None,
) -> dict:
    """Extract per-frequency-band RMS envelopes for colored waveform display.

    Splits signal into 4 bands using Butterworth bandpass filters:
      Low (20–250 Hz), Mid-low (250–1000 Hz),
      Mid-high (1000–4000 Hz), High (4000–nyquist Hz).

    Returns dict with band_low, band_midlow, band_midhigh, band_high
    (detail arrays) and *_overview variants (peak-downsampled).
    """
    import librosa
    from scipy.signal import butter, sosfilt

    if audio is not None:
        y = audio
    else:
        y, sr = librosa.load(str(file_path), sr=sr, mono=True)

    if len(y) == 0:
        return {}

    nyquist = sr / 2
    # Band definitions: (low_hz, high_hz, name)
    bands = [
        (20, 250, "band_low"),
        (250, 1000, "band_midlow"),
        (1000, 4000, "band_midhigh"),
        (4000, nyquist - 1, "band_high"),
    ]

    result = {}
    for low_hz, high_hz, name in bands:
        # Normalize frequencies to [0, 1] relative to Nyquist
        low_n = low_hz / nyquist
        high_n = min(high_hz / nyquist, 0.9999)

        sos = butter(4, [low_n, high_n], btype="bandpass", output="sos")
        filtered = sosfilt(sos, y).astype(np.float32)

        rms = librosa.feature.rms(
            y=filtered, frame_length=2048, hop_length=hop_length
        )[0].astype(np.float32)

        overview = peak_downsample(rms, overview_points).astype(np.float32)

        result[name] = rms
        result[f"{name}_overview"] = overview

    return result


def import_rekordbox_waveform(
    anlz_dir: str | Path,
    duration_sec: float,
    overview_points: int = 1000,
) -> dict | None:
    """Import pre-computed waveform data from Rekordbox ANLZ files.

    Reads ANLZ0000.DAT (preview waveform, beat grid) and ANLZ0000.EXT
    (color detail waveform) to produce the same dict format as
    extract_waveform().

    Args:
        anlz_dir: Path to the ANLZ hex directory containing .DAT/.EXT files.
        duration_sec: Track duration in seconds (needed for time axis).
        overview_points: Target number of overview points (default 1000).

    Returns:
        Dict with waveform_overview, waveform_detail, waveform_sr,
        waveform_hop, beat_positions — or None if files are unreadable.
    """
    from pyrekordbox import AnlzFile

    anlz_dir = Path(anlz_dir)
    dat_path = anlz_dir / "ANLZ0000.DAT"
    ext_path = anlz_dir / "ANLZ0000.EXT"

    if not dat_path.exists():
        return None

    try:
        dat = AnlzFile.parse_file(str(dat_path))
    except Exception:
        return None

    result = {}

    # --- Detail waveform from PWV5 (color detail, float64 heights 0–1) ---
    detail = None
    if ext_path.exists():
        try:
            ext = AnlzFile.parse_file(str(ext_path))
            pwv5 = ext.get("PWV5")
            if pwv5 is not None:
                # pwv5[0] = heights (float64, 0–1), pwv5[1] = RGB colors
                detail = pwv5[0].astype(np.float32)
        except Exception:
            pass

    # Fallback: use PWAV preview from DAT (400 int8 heights)
    pwav = dat.get("PWAV")
    if pwav is not None:
        # pwav[0] = heights (int8, 0–31), pwav[1] = whiteness
        preview_heights = pwav[0].astype(np.float32) / 31.0
    else:
        preview_heights = None

    if detail is None and preview_heights is None:
        return None

    if detail is not None:
        result["waveform_detail"] = detail
        result["waveform_overview"] = peak_downsample(detail, overview_points).astype(np.float32)
    else:
        # Only preview available — use as both
        result["waveform_detail"] = preview_heights
        result["waveform_overview"] = peak_downsample(preview_heights, overview_points).astype(np.float32)

    # --- SR/hop to produce correct time axis ---
    # envelope_to_time_axis computes: arange(n) * hop / sr
    # We want n * hop / sr = duration_sec, with hop=1:
    #   sr = n / duration_sec
    n_detail = len(result["waveform_detail"])
    if duration_sec > 0:
        result["waveform_sr"] = round(n_detail / duration_sec)
        result["waveform_hop"] = 1
    else:
        result["waveform_sr"] = n_detail
        result["waveform_hop"] = 1

    # --- Beat grid from PQTZ ---
    pqtz = dat.get("PQTZ")
    if pqtz is not None:
        # pqtz[2] = beat times in seconds
        result["beat_positions"] = pqtz[2].astype(np.float32)

    return result


def read_anlz_path(anlz_dir: str | Path) -> str | None:
    """Read the PPTH (audio file path) tag from an ANLZ directory.

    Returns the relative path string (e.g. '/Musica/2025/09/track.aiff')
    or None if unreadable.
    """
    from pyrekordbox import AnlzFile

    dat_path = Path(anlz_dir) / "ANLZ0000.DAT"
    if not dat_path.exists():
        return None
    try:
        dat = AnlzFile.parse_file(str(dat_path))
        ppth = dat.get("PPTH")
        return ppth if isinstance(ppth, str) else None
    except Exception:
        return None


def envelope_to_time_axis(
    n_frames: int, sr: int, hop_length: int
) -> np.ndarray:
    """Convert frame indices to time values in seconds."""
    return np.arange(n_frames) * hop_length / sr
