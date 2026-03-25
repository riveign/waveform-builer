"""Pydantic response models for the API."""

from __future__ import annotations

from pydantic import BaseModel


class EnergyConflictResponse(BaseModel):
    dir_energy: str
    predicted: str
    message: str


class TrackResponse(BaseModel):
    id: int
    title: str | None = None
    artist: str | None = None
    album: str | None = None
    label: str | None = None
    bpm: float | None = None
    key: str | None = None
    rating: int | None = None
    genre: str | None = None
    energy: str | None = None
    duration_sec: float | None = None
    play_count: int | None = None
    kiku_play_count: int | None = None
    has_waveform: bool = False
    has_features: bool = False
    resolved_energy: str | None = None
    energy_source: str | None = None
    energy_confidence: float | None = None
    energy_conflict: EnergyConflictResponse | None = None

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
    source: str | None = None

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
    energy_source: str | None = None
    energy_conflict: EnergyConflictResponse | None = None


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
    energy_source: str | None = None
    energy_conflict: EnergyConflictResponse | None = None


class TransitionScoreBreakdown(BaseModel):
    harmonic: float
    energy_fit: float
    bpm_compat: float
    genre_coherence: float
    track_quality: float
    total: float
    discovery_label: str | None = None
    set_appearances: int | None = None


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
    beats_a: str | None = None  # base64 float32 beat timestamps
    beats_b: str | None = None  # base64 float32 beat timestamps


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


# ── Set mutation request models ──


class SetBuildRequest(BaseModel):
    name: str
    duration_min: int = 120
    energy_preset: str = "journey"
    genre_filter: list[str] | None = None
    bpm_min: float | None = None
    bpm_max: float | None = None
    seed_track_id: int | None = None
    beam_width: int = 5
    playlist_preference: list[str] | None = None
    weights: ScoringWeightsRequest | None = None
    discovery_density: float = 0.0


class SetCreateRequest(BaseModel):
    name: str
    energy_profile: str | None = None
    genre_filter: list[str] | None = None


class SetUpdateRequest(BaseModel):
    name: str | None = None
    energy_profile: str | None = None
    genre_filter: list[str] | None = None


class SetAddTrackRequest(BaseModel):
    track_id: int
    position: int | None = None  # defaults to end


class SetReorderTracksRequest(BaseModel):
    track_ids: list[int]


# ── Suggest-next response models ──


class SuggestNextItem(BaseModel):
    track: TrackResponse
    score: float
    breakdown: TransitionScoreBreakdown


class SuggestNextResponse(BaseModel):
    source_track_id: int
    suggestions: list[SuggestNextItem]


# ── Paginated tracks response ──


class PaginatedTracksResponse(BaseModel):
    items: list[TrackResponse]
    total: int
    offset: int
    limit: int


# ── Energy Tinder models ──


class TinderQueueItem(BaseModel):
    track: TrackResponse
    energy_predicted: str | None = None
    energy_confidence: float | None = None
    mood_happy: float | None = None
    mood_sad: float | None = None
    mood_aggressive: float | None = None
    mood_relaxed: float | None = None
    has_waveform: bool = False


class TinderQueueResponse(BaseModel):
    items: list[TinderQueueItem]
    total: int
    offset: int
    limit: int


class TinderDecideRequest(BaseModel):
    track_id: int
    decision: str  # "confirm", "override", "skip"
    override_zone: str | None = None  # required if decision == "override"


class TinderDecideResponse(BaseModel):
    track_id: int
    decision: str
    applied_zone: str | None = None
    teaching_moment: str | None = None  # one-sentence explanation on override


class TinderStatsResponse(BaseModel):
    total_reviewed: int
    confirmed: int
    overridden: int
    skipped: int
    queue_remaining: int
    confirmed_pct: float
    overridden_pct: float
    skip_pct: float


class TinderRetrainResponse(BaseModel):
    accuracy: float | None = None
    class_counts: dict[str, int] = {}
    feature_importance: list[tuple[str, float]] = []
    training_samples: int = 0


# ── Config endpoint response models ──


class ScoringWeightsResponse(BaseModel):
    harmonic: float
    energy_fit: float
    bpm_compat: float
    genre_coherence: float
    track_quality: float


class ScoringWeightsRequest(BaseModel):
    harmonic: float
    energy_fit: float
    bpm_compat: float
    genre_coherence: float
    track_quality: float


class EnergySegmentResponse(BaseModel):
    name: str
    target_energy: float
    duration_pct: float


class EnergyPresetResponse(BaseModel):
    name: str
    description: str
    segments: list[EnergySegmentResponse]


class GenreFamilyResponse(BaseModel):
    family_name: str
    genres: list[str]
    compatible_with: list[str]


# ── Track Hunter models ──


class HuntRequest(BaseModel):
    url: str
    include_comments: bool = True


class HuntTrackResponse(BaseModel):
    id: int
    position: int
    artist: str | None = None
    title: str | None = None
    remix_info: str | None = None
    original_title: str | None = None
    confidence: float = 0.0
    source: str | None = None
    timestamp_sec: float | None = None
    matched_track_id: int | None = None
    match_score: float | None = None
    acquisition_status: str = "unowned"
    purchase_links: dict[str, str] = {}
    raw_text: str | None = None

    model_config = {"from_attributes": True}


class HuntSessionResponse(BaseModel):
    id: int
    url: str
    platform: str | None = None
    title: str | None = None
    uploader: str | None = None
    status: str = "pending"
    track_count: int = 0
    owned_count: int = 0
    created_at: str | None = None
    tracks: list[HuntTrackResponse] = []

    model_config = {"from_attributes": True}


class HuntSessionSummary(BaseModel):
    id: int
    url: str
    platform: str | None = None
    title: str | None = None
    uploader: str | None = None
    status: str = "pending"
    track_count: int = 0
    owned_count: int = 0
    created_at: str | None = None

    model_config = {"from_attributes": True}


class HuntListResponse(BaseModel):
    items: list[HuntSessionSummary]
    total: int
    offset: int
    limit: int


class HuntTrackUpdateRequest(BaseModel):
    acquisition_status: str  # "wanted", "owned", "unowned"


# ── Replace Track models ──


class ReplacementBreakdown(BaseModel):
    harmonic: float
    energy_fit: float
    bpm_compat: float
    genre_coherence: float
    track_quality: float
    total: float
    discovery_label: str | None = None
    set_appearances: int | None = None


class ReplacementCandidate(BaseModel):
    track: TrackResponse
    combined_score: float
    incoming_breakdown: ReplacementBreakdown | None = None
    outgoing_breakdown: ReplacementBreakdown | None = None


class TrackSummary(BaseModel):
    track_id: int
    title: str | None = None
    artist: str | None = None
    bpm: float | None = None
    key: str | None = None
    genre: str | None = None


class ReplacementContext(BaseModel):
    prev_track: TrackSummary | None = None
    next_track: TrackSummary | None = None
    energy_target: float
    position: int


class ReplacementSuggestionsResponse(BaseModel):
    context: ReplacementContext
    candidates: list[ReplacementCandidate]


class ReplaceTrackRequest(BaseModel):
    new_track_id: int


# ── Import playlist models ──


class UnmatchedTrack(BaseModel):
    path: str
    title: str | None = None
    line: int


class ImportResultResponse(BaseModel):
    set_id: int
    name: str
    source: str
    total_tracks: int
    matched_count: int
    unmatched_count: int
    unmatched_paths: list[UnmatchedTrack] = []
    match_methods: dict[str, int] = {}
    warnings: list[str] = []
    duplicate_set_id: int | None = None
