"""Feature dataclasses for audio analysis results."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class AudioAnalysisResult:
    """Result of analyzing a single audio track."""

    energy: float | None = None
    danceability: float | None = None
    loudness_lufs: float | None = None
    spectral_centroid: float | None = None
    spectral_complexity: float | None = None
    mood_happy: float | None = None
    mood_sad: float | None = None
    mood_aggressive: float | None = None
    mood_relaxed: float | None = None
    ml_genre: str | None = None
    ml_genre_confidence: float | None = None
    energy_intro: float | None = None
    energy_body: float | None = None
    energy_outro: float | None = None
    mfcc_mean: np.ndarray | None = None
    mfcc_var: np.ndarray | None = None
    verified_bpm: float | None = None
    verified_key: str | None = None
    # Waveform data
    waveform_overview: np.ndarray | None = None
    waveform_detail: np.ndarray | None = None
    waveform_sr: int | None = None
    waveform_hop: int | None = None
    beat_positions: np.ndarray | None = None
