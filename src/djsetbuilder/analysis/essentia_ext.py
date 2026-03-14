"""Essentia-based audio feature extraction."""

from __future__ import annotations

from pathlib import Path


def extract_essentia_features(file_path: str | Path) -> dict:
    """Extract audio features using Essentia.

    Returns a dict with keys matching AudioAnalysisResult fields.
    """
    import essentia.standard as es

    path = str(file_path)

    # Load audio
    loader = es.MonoLoader(filename=path, sampleRate=44100)
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

    # Energy (RMS-based, normalized)
    energy_extractor = es.Energy()
    rms = es.RMS()
    energy_val = float(rms(audio))
    # Normalize to 0-1 range (typical RMS for music: 0.01-0.3)
    results["energy"] = min(1.0, max(0.0, energy_val / 0.25))

    # Danceability
    dance = es.Danceability()
    danceability, _ = dance(audio)
    results["danceability"] = float(danceability)

    # Loudness
    loudness = es.LoudnessEBUR128(sampleRate=44100)
    try:
        import numpy as np
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

    results["energy_intro"] = min(1.0, float(rms(audio[:intro_end])) / 0.25) if intro_end > 0 else 0.0
    results["energy_body"] = min(1.0, float(rms(audio[intro_end:outro_start])) / 0.25)
    results["energy_outro"] = min(1.0, float(rms(audio[outro_start:])) / 0.25) if outro_start < total else 0.0

    return results


def extract_essentia_mood(file_path: str | Path) -> dict:
    """Extract mood features using Essentia TensorFlow models.

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
        audio = MonoLoader(filename=str(file_path), sampleRate=16000)()
        embedding_model = TensorflowPredictMusiCNN(
            graphFilename="msd-musicnn-1.pb", output="model/dense/BiasAdd"
        )
        embeddings = embedding_model(audio)

        moods = {}
        for mood_name in ["happy", "sad", "aggressive", "relaxed"]:
            try:
                model = TensorflowPredict2D(
                    graphFilename=f"mood_{mood_name}-musicnn-msd-2.pb"
                )
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
