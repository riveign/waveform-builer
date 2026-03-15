"""Essentia-based audio feature extraction."""

from __future__ import annotations

import logging
import os
from pathlib import Path

import numpy as np

# Suppress TF/CUDA warnings before any TensorFlow import
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")

logger = logging.getLogger(__name__)

# RMS normalization anchors (measured from library)
_RMS_FLOOR = 0.02   # silence / near-silent recordings
_RMS_CEIL = 0.50    # loudest mastered tracks (~-5 LUFS)


def _rms_to_energy(rms_val: float) -> float:
    """Map RMS to 0-1 energy using log scale.

    Log-scale spreads the musically relevant range (-20 to -5 LUFS)
    across 0-1 instead of cramming 90% of tracks into 1.0.
    """
    if rms_val <= _RMS_FLOOR:
        return 0.0
    if rms_val >= _RMS_CEIL:
        return 1.0
    import math
    log_val = math.log(rms_val)
    log_floor = math.log(_RMS_FLOOR)
    log_ceil = math.log(_RMS_CEIL)
    return (log_val - log_floor) / (log_ceil - log_floor)


def _resolve_model_path(filename: str) -> str | None:
    """Find an Essentia .pb model file."""
    # Project models/ directory (preferred)
    project_models = Path(__file__).resolve().parents[3] / "models" / filename
    if project_models.exists():
        return str(project_models)

    try:
        import essentia
        for base in essentia.__path__:
            candidate = Path(base) / filename
            if candidate.exists():
                return str(candidate)
            candidate = Path(base) / "models" / filename
            if candidate.exists():
                return str(candidate)
    except (ImportError, AttributeError):
        pass

    if Path(filename).exists():
        return filename
    return None


def extract_essentia_features(
    file_path: str | Path,
    audio: np.ndarray | None = None,
) -> dict:
    """Extract audio features using Essentia.

    When *audio* (float32 array at 44100 Hz) is provided, the file is
    not re-decoded from disk.

    Returns a dict with keys matching AudioAnalysisResult fields.
    """
    import essentia.standard as es

    if audio is None:
        loader = es.MonoLoader(filename=str(file_path), sampleRate=44100)
        audio = loader()

    if len(audio) == 0:
        return {}

    results = {}

    # Rhythm features
    rhythm_extractor = es.RhythmExtractor2013(method="multifeature")
    bpm, beats, beats_confidence, _, _ = rhythm_extractor(audio)
    results["verified_bpm"] = round(float(bpm), 1)

    # Key detection
    key_extractor = es.KeyExtractor()
    key, scale, key_strength = key_extractor(audio)
    camelot = _to_camelot(key, scale)
    results["verified_key"] = camelot

    # Energy (RMS-based, log-scaled)
    rms = es.RMS()
    energy_val = float(rms(audio))
    results["energy"] = _rms_to_energy(energy_val)

    # Danceability
    dance = es.Danceability()
    danceability, _ = dance(audio)
    results["danceability"] = float(danceability)

    # Loudness
    loudness = es.LoudnessEBUR128(sampleRate=44100)
    try:
        stereo = np.column_stack([audio, audio])
        momentary, short_term, integrated, loudness_range = loudness(stereo)
        results["loudness_lufs"] = float(integrated)
    except Exception:
        results["loudness_lufs"] = None

    # Spectral features
    centroid = es.SpectralCentroidTime()
    results["spectral_centroid"] = float(centroid(audio))

    # Spectral complexity via zero crossing rate as proxy
    zcr = es.ZeroCrossingRate()
    results["spectral_complexity"] = float(zcr(audio))

    # Energy curve: intro (0-15%), body (15-85%), outro (85-100%)
    total = len(audio)
    intro_end = int(total * 0.15)
    outro_start = int(total * 0.85)

    results["energy_intro"] = _rms_to_energy(float(rms(audio[:intro_end]))) if intro_end > 0 else 0.0
    results["energy_body"] = _rms_to_energy(float(rms(audio[intro_end:outro_start])))
    results["energy_outro"] = _rms_to_energy(float(rms(audio[outro_start:]))) if outro_start < total else 0.0

    return results


def extract_essentia_mood(
    file_path: str | Path,
    audio: np.ndarray | None = None,
) -> dict:
    """Extract mood features using Essentia TensorFlow models.

    When *audio* (float32 array at 16000 Hz) is provided, the file is
    not re-decoded from disk.

    Returns dict with mood_happy, mood_sad, mood_aggressive, mood_relaxed.
    """
    try:
        from essentia.standard import (
            MonoLoader,
            TensorflowPredictMusiCNN,
            TensorflowPredict2D,
        )
    except ImportError:
        return {}

    # Mood models may not be available — return empty if they fail
    try:
        embedding_pb = _resolve_model_path("msd-musicnn-1.pb")
        if not embedding_pb:
            logger.warning("Model msd-musicnn-1.pb not found — skipping mood extraction")
            return {}

        if audio is None:
            audio = MonoLoader(filename=str(file_path), sampleRate=16000)()
        embedding_model = TensorflowPredictMusiCNN(
            graphFilename=embedding_pb, output="model/dense/BiasAdd"
        )
        embeddings = embedding_model(audio)

        moods = {}
        for mood_name in ["happy", "sad", "aggressive", "relaxed"]:
            mood_pb = _resolve_model_path(f"mood_{mood_name}-msd-musicnn-1.pb")
            if not mood_pb:
                logger.warning("Model mood_%s-msd-musicnn-1.pb not found — skipping", mood_name)
                moods[f"mood_{mood_name}"] = None
                continue
            try:
                model = TensorflowPredict2D(graphFilename=mood_pb)
                pred = model(embeddings)
                moods[f"mood_{mood_name}"] = float(pred.mean())
            except Exception:
                moods[f"mood_{mood_name}"] = None

        return moods
    except Exception:
        return {}


# Camelot wheel mapping
_KEY_TO_CAMELOT = {
    ("C", "major"): "8B", ("C", "minor"): "5A",
    ("C#", "major"): "3B", ("C#", "minor"): "12A",
    ("D", "major"): "10B", ("D", "minor"): "7A",
    ("D#", "major"): "5B", ("D#", "minor"): "2A",
    ("E", "major"): "12B", ("E", "minor"): "9A",
    ("F", "major"): "7B", ("F", "minor"): "4A",
    ("F#", "major"): "2B", ("F#", "minor"): "11A",
    ("G", "major"): "9B", ("G", "minor"): "6A",
    ("G#", "major"): "4B", ("G#", "minor"): "1A",
    ("A", "major"): "11B", ("A", "minor"): "8A",
    ("A#", "major"): "6B", ("A#", "minor"): "3A",
    ("B", "major"): "1B", ("B", "minor"): "10A",
    # Enharmonic equivalents
    ("Db", "major"): "3B", ("Db", "minor"): "12A",
    ("Eb", "major"): "5B", ("Eb", "minor"): "2A",
    ("Gb", "major"): "2B", ("Gb", "minor"): "11A",
    ("Ab", "major"): "4B", ("Ab", "minor"): "1A",
    ("Bb", "major"): "6B", ("Bb", "minor"): "3A",
}


def _to_camelot(key: str, scale: str) -> str:
    """Convert key + scale to Camelot notation."""
    return _KEY_TO_CAMELOT.get((key, scale), f"{key}{scale}")
