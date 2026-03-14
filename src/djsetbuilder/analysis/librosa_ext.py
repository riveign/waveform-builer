"""Librosa-based MFCC extraction for acoustic similarity."""

from __future__ import annotations

from pathlib import Path

import numpy as np


def extract_mfccs(file_path: str | Path, n_mfcc: int = 13) -> dict:
    """Extract MFCC mean and variance vectors for similarity fingerprinting.

    Returns dict with mfcc_mean and mfcc_var as numpy arrays.
    """
    import librosa

    try:
        y, sr = librosa.load(str(file_path), sr=22050, mono=True, duration=180)
    except Exception:
        return {}

    if len(y) == 0:
        return {}

    mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=n_mfcc)

    return {
        "mfcc_mean": mfccs.mean(axis=1).astype(np.float32),
        "mfcc_var": mfccs.var(axis=1).astype(np.float32),
    }
