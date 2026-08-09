/**
 * Types shared across the app.
 *
 * Everything the API returns is *generated* from its OpenAPI schema — see
 * `npm run gen:api`, and `schema.d.ts` next door. These aliases exist so call
 * sites keep importing `Track` rather than
 * `components['schemas']['TrackResponse']`, and so a renamed Pydantic field
 * breaks the build instead of quietly producing undefined at runtime
 * (docs/notes/OBS-005/K4).
 *
 * Below the aliases are the types the API cannot describe: responses from
 * endpoints declared without a `response_model`, plus a few genuinely
 * client-side shapes. Every one of those is a small gap in the contract.
 */

import type { components } from '$lib/api/schema';

type S = components['schemas'];

export type ArcAnalysis = S['ArcAnalysisResponse'];
export type ArcComparison = S['ArcComparisonResponse'];
export type ArtistPick = S['ArtistPickItem'];
export type ArtistPicksResponse = S['ArtistPicksResponse'];
export type BpmBin = S['BpmBin'];
export type Cue = S['CueResponse'];
export type DJSet = S['SetResponse'];
export type EnergyConflict = S['EnergyConflictResponse'];
export type EnergyDeviation = S['EnergyDeviationResponse'];
export type HuntListResponse = S['HuntListResponse'];
export type HuntSession = S['HuntSessionResponse'];
export type HuntSessionSummary = S['HuntSessionSummary'];
export type HuntTrack = S['HuntTrackResponse'];
export type ImportResult = S['ImportResultResponse'];
export type LibraryStats = S['LibraryStatsResponse'];
export type MoodPoint = S['MoodPoint'];
export type PaginatedTracks = S['PaginatedTracksResponse'];
export type PlannedSetCandidate = S['PlannedSetCandidate'];
export type ReplacementBreakdown = S['ReplacementBreakdown'];
export type ReplacementCandidate = S['ReplacementCandidate'];
export type ReplacementContext = S['ReplacementContext'];
export type ReplacementSuggestionsResponse = S['ReplacementSuggestionsResponse'];
export type SCLikesResponse = S['SCLikesResponse'];
export type SCPlaylist = S['SCPlaylistResponse'];
export type SCStatus = S['SCStatusResponse'];
export type SCTrack = S['SCTrackResponse'];
export type ScoringWeights = S['ScoringWeightsResponse'];
export type SetAnalysis = S['SetAnalysisResponse'];
/** Request body. Fields with server-side defaults are optional for callers —
 *  the generator marks them required because the server always fills them. */
export type SetBuildParams = Partial<S['SetBuildRequest']> & Pick<S['SetBuildRequest'], 'name'>;
export type SetComparison = S['SetComparisonResponse'];
export type SetCreateParams = Partial<S['SetCreateRequest']> & Pick<S['SetCreateRequest'], 'name'>;
export type SetDetail = S['SetDetailResponse'];
export type SetTrack = S['SetTrackResponse'];
export type SetUpdateParams = Partial<S['SetUpdateRequest']>;
export type SetWaveformTrack = S['SetWaveformTrackResponse'];
export type SlotSuggestion = S['SlotSuggestionItem'];
export type SlotSuggestionsResponse = S['SlotSuggestionsResponse'];
export type SuggestNextItem = S['SuggestNextItem'];
export type SuggestNextResponse = S['SuggestNextResponse'];
export type TinderBatchDecision = S['TinderDecideRequest'];
export type TinderBatchResult = S['TinderBatchDecideResponse'];
export type TinderDecideResult = S['TinderDecideResponse'];
export type TinderQueueItem = S['TinderQueueItem'];
export type TinderQueueResponse = S['TinderQueueResponse'];
export type TinderRetrainResult = S['TinderRetrainResponse'];
export type TinderStats = S['TinderStatsResponse'];
export type Track = S['TrackResponse'];
export type TrackDeviation = S['TrackDeviationResponse'];
export type TrackFeatures = S['TrackFeaturesResponse'];
export type TrackSetAppearance = S['TrackSetAppearance'];
export type TrackSummary = S['TrackSummary'];
export type TransitionAnalysis = S['TransitionAnalysisResponse'];
export type TransitionDetail = S['TransitionResponse'];
export type TransitionScoreBreakdown = S['TransitionScoreBreakdown'];
export type UnmatchedTrack = S['UnmatchedTrack'];
export type WaveformBandsData = S['WaveformBandsResponse'];
export type WaveformData = S['WaveformResponse'];
export type WaveformDetailData = S['WaveformDetailResponse'];

// ── Not in the OpenAPI schema ──

export interface CamelotGap {
	position: string;
	count: number;
	impact: number;
	explanation: string;
}

export interface BpmGap {
	range: string;
	count: number;
}

export interface EnergyGap {
	level: string;
	count: number;
}

export interface LibraryGapsResponse {
	camelot_gaps: CamelotGap[];
	bpm_gaps: BpmGap[];
	energy_gaps: EnergyGap[];
}

export interface GenreBpmStats {
	avg: number;
	min: number;
	max: number;
	count: number;
}

export interface EnergyZoneStats {
	count: number;
	top_genres: { family: string; count: number }[];
}

export interface PlayedTrack {
	title: string | null;
	artist: string | null;
	plays: number;
	genre: string;
}

export interface HiddenGem {
	title: string | null;
	artist: string | null;
	rating: number;
	genre: string;
}

export interface CoverageStats {
	key: number;
	bpm: number;
	rating: number;
	features: number;
	total: number;
}

export interface EnhancedStatsResponse {
	bpm_per_genre: Record<string, GenreBpmStats>;
	energy_zones: Record<string, EnergyZoneStats>;
	most_played: PlayedTrack[];
	hidden_gems: HiddenGem[];
	coverage: CoverageStats;
}

// ── Scoring weights ──

export interface VibePreset {
	name: string;
	brightness: number;
	density: number;
	label: string;
}

export interface SetBuildComplete {
	set_id: number;
	name: string;
	track_count: number;
	duration_min: number;
}

export type TinderDecision = 'confirm' | 'override' | 'skip';
