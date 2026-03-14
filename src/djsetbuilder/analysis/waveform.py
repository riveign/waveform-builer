"""Waveform envelope extraction for visualization."""

from __future__ import annotations

import numpy as np


def extract_waveform(
    file_path: str,
    sr: int = 22050,
    hop_length: int = 512,
    overview_points: int = 1000,
) -> dict:
    """Extract waveform envelope and beat positions from an audio file.

    Returns dict with waveform_overview, waveform_detail, waveform_sr,
    waveform_hop, and beat_positions.
    """
    import librosa

    y, sr_actual = librosa.load(str(file_path), sr=sr, mono=True)

    if len(y) == 0:
        return {}

    # RMS envelope (detail resolution)
    rms = librosa.feature.rms(y=y, frame_length=2048, hop_length=hop_length)[0]
    detail = rms.astype(np.float32)

    # Peak-downsampled overview
    overview = peak_downsample(detail, overview_points).astype(np.float32)

    # Beat positions
    _tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr_actual, hop_length=hop_length)
    beat_times = librosa.frames_to_time(beat_frames, sr=sr_actual, hop_length=hop_length)

    return {
        "waveform_overview": overview,
        "waveform_detail": detail,
        "waveform_sr": sr_actual,
        "waveform_hop": hop_length,
        "beat_positions": beat_times.astype(np.float32),
    }


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


def envelope_to_time_axis(
    n_frames: int, sr: int, hop_length: int
) -> np.ndarray:
    """Convert frame indices to time values in seconds."""
    return np.arange(n_frames) * hop_length / sr
