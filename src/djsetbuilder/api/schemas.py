"""Pydantic response models for the API."""

from __future__ import annotations

from pydantic import BaseModel


class TrackResponse(BaseModel):
    id: int
    title: str | None = None
    artist: str | None = None
    album: str | None = None
    bpm: float | None = None
    key: str | None = None
    rating: int | None = None
    genre: str | None = None
    energy: str | None = None
    duration_sec: float | None = None
    play_count: int | None = None
    has_waveform: bool = False
    has_features: bool = False

    model_config = {"from_attributes": True}


class TrackFeaturesResponse(BaseModel):
    track_id: int
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
    verified_bpm: float | None = None
    verified_key: str | None = None

    model_config = {"from_attributes": True}


class WaveformResponse(BaseModel):
    envelope: str  # base64 float32
    sr: int
    hop: int
    duration_sec: float


class WaveformDetailResponse(WaveformResponse):
    beats: str | None = None  # base64 float32


class WaveformBandsResponse(BaseModel):
    low: str  # base64 float32
    midlow: str
    midhigh: str
    high: str
    sr: int
    hop: int
    duration_sec: float


class SetResponse(BaseModel):
    id: int
    name: str | None = None
    created_at: str | None = None
    duration_min: int | None = None
    track_count: int = 0

    model_config = {"from_attributes": True}


class SetTrackResponse(BaseModel):
    position: int
    track_id: int
    title: str | None = None
    artist: str | None = None
    bpm: float | None = None
    key: str | None = None
    genre: str | None = None
    energy: str | None = None
    duration_sec: float | None = None
    transition_score: float | None = None
    has_waveform: bool = False


class SetDetailResponse(BaseModel):
    id: int
    name: str | None = None
    created_at: str | None = None
    duration_min: int | None = None
    energy_profile: str | None = None
    genre_filter: str | None = None
    tracks: list[SetTrackResponse] = []

    model_config = {"from_attributes": True}


class CueResponse(BaseModel):
    id: int
    set_id: int
    track_id: int
    position: int
    name: str
    cue_type: str
    start_sec: float
    end_sec: float | None = None
    hot_cue_num: int = -1
    color: str | None = None
    created_at: str | None = None

    model_config = {"from_attributes": True}


class CueCreateRequest(BaseModel):
    position: int
    name: str
    cue_type: str = "cue"
    start_sec: float
    end_sec: float | None = None
    hot_cue_num: int = -1
    color: str | None = None


class SetWaveformTrackResponse(BaseModel):
    position: int
    track_id: int
    title: str | None = None
    artist: str | None = None
    bpm: float | None = None
    key: str | None = None
    genre: str | None = None
    energy: str | None = None
    duration_sec: float | None = None
    transition_score: float | None = None
    waveform_overview: str | None = None  # base64 float32


class TransitionScoreBreakdown(BaseModel):
    harmonic: float
    energy_fit: float
    bpm_compat: float
    genre_coherence: float
    track_quality: float
    total: float


class TransitionResponse(BaseModel):
    position: int
    track_a: SetTrackResponse
    track_b: SetTrackResponse
    score_breakdown: TransitionScoreBreakdown
    bpm_a: float | None = None
    bpm_b: float | None = None
    key_a: str | None = None
    key_b: str | None = None
    waveform_a_overview: str | None = None  # base64 float32
    waveform_b_overview: str | None = None  # base64 float32


class LibraryStatsResponse(BaseModel):
    total_tracks: int
    analyzed_tracks: int
    genres: dict[str, int] = {}
    energies: dict[str, int] = {}
    bpm_min: float | None = None
    bpm_max: float | None = None
    bpm_avg: float | None = None
    keys: dict[str, int] = {}
    top_artists: dict[str, int] = {}


# ── Taste DNA stats responses ──


class BpmBin(BaseModel):
    bin_center: float
    family: str
    count: int


class MoodPoint(BaseModel):
    title: str
    artist: str
    x: float
    y: float
    energy: float
    genre_family: str
