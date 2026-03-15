"""Single-decode audio loader with in-memory resampling."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass(frozen=True, slots=True)
class AudioBuffers:
    """Pre-loaded audio at the three sample rates used by extractors."""

    audio_44100: np.ndarray  # For essentia features
    audio_22050: np.ndarray  # For librosa MFCCs + waveform
    audio_16000: np.ndarray  # For essentia mood/TF models


def _load_with_ffmpeg(path: str, sr: int) -> np.ndarray:
    """Decode audio via ffmpeg subprocess (handles M4A/AAC and any format)."""
    cmd = [
        "ffmpeg", "-i", path,
        "-f", "f32le",      # raw 32-bit float PCM
        "-acodec", "pcm_f32le",
        "-ac", "1",          # mono
        "-ar", str(sr),      # target sample rate
        "-v", "quiet",
        "pipe:1",
    ]
    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed for {Path(path).name}")
    return np.frombuffer(result.stdout, dtype=np.float32)


def _load_at_sr(path: str, sr: int) -> np.ndarray:
    """Load audio at a target sample rate. Uses soundfile, falls back to ffmpeg."""
    import soundfile as sf

    try:
        data, native_sr = sf.read(path, dtype="float32", always_2d=False)
    except Exception:
        return _load_with_ffmpeg(path, sr)

    if data.ndim > 1:
        data = data.mean(axis=1)

    if native_sr != sr:
        import librosa

        data = librosa.resample(data, orig_sr=native_sr, target_sr=sr)

    return data


def load_audio(file_path: str | Path, *, skip_44100: bool = False) -> AudioBuffers:
    """Decode an audio file once and resample to all needed rates.

    When *skip_44100* is True (waveform-only mode), the file is loaded
    directly at 22050 Hz and no 44100/16000 buffers are produced —
    empty arrays are returned for those slots.
    """
    import librosa

    path = str(file_path)

    if skip_44100:
        audio_22050 = _load_at_sr(path, 22050)
        return AudioBuffers(
            audio_44100=np.empty(0, dtype=np.float32),
            audio_22050=audio_22050,
            audio_16000=np.empty(0, dtype=np.float32),
        )

    audio_44100 = _load_at_sr(path, 44100)
    audio_22050 = librosa.resample(audio_44100, orig_sr=44100, target_sr=22050)
    audio_16000 = librosa.resample(audio_44100, orig_sr=44100, target_sr=16000)

    return AudioBuffers(
        audio_44100=audio_44100,
        audio_22050=audio_22050,
        audio_16000=audio_16000,
    )
