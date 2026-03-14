export interface Track {
	id: number;
	title: string | null;
	artist: string | null;
	album: string | null;
	bpm: number | null;
	key: string | null;
	rating: number | null;
	genre: string | null;
	energy: string | null;
	duration_sec: number | null;
	play_count: number | null;
	has_waveform: boolean;
	has_features: boolean;
}

export interface TrackFeatures {
	track_id: number;
	energy: number | null;
	danceability: number | null;
	loudness_lufs: number | null;
	spectral_centroid: number | null;
	spectral_complexity: number | null;
	mood_happy: number | null;
	mood_sad: number | null;
	mood_aggressive: number | null;
	mood_relaxed: number | null;
	ml_genre: string | null;
	ml_genre_confidence: number | null;
	energy_intro: number | null;
	energy_body: number | null;
	energy_outro: number | null;
	verified_bpm: number | null;
	verified_key: string | null;
}

export interface WaveformData {
	envelope: string;
	sr: number;
	hop: number;
	duration_sec: number;
}

export interface WaveformDetailData extends WaveformData {
	beats: string | null;
}

export interface WaveformBandsData {
	low: string;
	midlow: string;
	midhigh: string;
	high: string;
	sr: number;
	hop: number;
	duration_sec: number;
}

export interface DJSet {
	id: number;
	name: string | null;
	created_at: string | null;
	duration_min: number | null;
	track_count: number;
}

export interface SetDetail {
	id: number;
	name: string | null;
	created_at: string | null;
	duration_min: number | null;
	energy_profile: string | null;
	genre_filter: string | null;
	tracks: SetTrack[];
}

export interface SetTrack {
	position: number;
	track_id: number;
	title: string | null;
	artist: string | null;
	bpm: number | null;
	key: string | null;
	genre: string | null;
	energy: string | null;
	duration_sec: number | null;
	transition_score: number | null;
	has_waveform: boolean;
}

export interface SetWaveformTrack {
	position: number;
	track_id: number;
	title: string | null;
	artist: string | null;
	bpm: number | null;
	key: string | null;
	genre: string | null;
	energy: string | null;
	duration_sec: number | null;
	transition_score: number | null;
	waveform_overview: string | null;
}

export interface TransitionScoreBreakdown {
	harmonic: number;
	energy_fit: number;
	bpm_compat: number;
	genre_coherence: number;
	track_quality: number;
	total: number;
}

export interface TransitionDetail {
	position: number;
	track_a: SetTrack;
	track_b: SetTrack;
	score_breakdown: TransitionScoreBreakdown;
	bpm_a: number | null;
	bpm_b: number | null;
	key_a: string | null;
	key_b: string | null;
	waveform_a_overview: string | null;
	waveform_b_overview: string | null;
}

export interface Cue {
	id: number;
	set_id: number;
	track_id: number;
	position: number;
	name: string;
	cue_type: string;
	start_sec: number;
	end_sec: number | null;
	hot_cue_num: number;
	color: string | null;
	created_at: string | null;
}

export interface LibraryStats {
	total_tracks: number;
	analyzed_tracks: number;
	genres: Record<string, number>;
	energies: Record<string, number>;
	bpm_min: number | null;
	bpm_max: number | null;
	bpm_avg: number | null;
	keys: Record<string, number>;
	top_artists: Record<string, number>;
}

export interface BpmBin {
	bin_center: number;
	family: string;
	count: number;
}

export interface MoodPoint {
	title: string;
	artist: string;
	x: number;
	y: number;
	energy: number;
	genre_family: string;
}
