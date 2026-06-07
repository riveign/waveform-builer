import type { Track } from '$lib/types';
import { fetchJson } from './client';

export interface Album {
	album_key: string;
	album: string;
	artist: string;
	year: number | null;
	label: string | null;
	track_count: number;
	cover_track_id: number | null;
	is_compilation: boolean;
	mb_release_id: string | null;
	match_status: string | null;
}

export interface PaginatedAlbums {
	items: Album[];
	total: number;
	offset: number;
	limit: number;
}

export interface AlbumTracks {
	album: Album;
	tracks: Track[];
}

export interface MBRecording {
	position: number;
	disc: number;
	title: string;
	length_ms: number | null;
}

export interface MBMappingPreviewItem {
	track_id: number;
	track_title: string | null;
	mb_position: number | null;
	mb_disc: number | null;
	mb_title: string | null;
	confidence: number;
}

export interface MBCandidate {
	mb_release_id: string;
	title: string;
	artist: string;
	year: number | null;
	country: string | null;
	label: string | null;
	track_count: number;
	recordings: MBRecording[];
	score: number;
	mapping_preview: MBMappingPreviewItem[];
}

export interface MBMatchResponse {
	candidates: MBCandidate[];
}

export interface MBMappingItem {
	track_id: number;
	disc_number: number | null;
	track_number: number | null;
	mb_position: number | null;
	confidence: number;
}

export interface MBApplyRequest {
	mb_release_id: string;
	mappings: MBMappingItem[];
}

export interface MBApplyResponse {
	updated_count: number;
	album_key: string;
	mb_release_id: string;
}

export interface ListAlbumsParams {
	search?: string;
	artist?: string[];
	label?: string[];
	year_min?: number;
	year_max?: number;
	sort?: 'artist' | 'year' | 'recent';
	limit?: number;
	offset?: number;
}

export function getAlbumCoverUrl(albumKey: string): string {
	return `/api/albums/${albumKey}/cover`;
}

// ── Multi-source metadata correction (spec 016) ──────────────────────────

export interface SourceInfo {
	name: string;
	lookup_mode: 'url' | 'search' | 'files';
	available: boolean;
}

export interface CorrectionFieldChange {
	field: string;
	old: string | number | null;
	new: string | number | null;
	changed: boolean;
}

export interface CorrectionTrackItem {
	track_id: number;
	track_title: string | null;
	matched_title: string | null;
	confidence: number;
	changes: CorrectionFieldChange[];
}

export interface CorrectionPreview {
	source: string;
	source_ref: string | null;
	album: string | null;
	artist: string | null;
	label: string | null;
	year: number | null;
	track_count: number;
	items: CorrectionTrackItem[];
}

export interface CorrectionMatchRequest {
	url?: string;
	query?: string;
	artist?: string;
	candidate_index?: number;
	fields?: string[];
}

export interface ApplyCorrectionItem {
	track_id: number;
	values: Record<string, string | number | null>;
}

export interface ApplyCorrectionRequest {
	source: string;
	source_ref: string | null;
	fields: string[];
	items: ApplyCorrectionItem[];
}

export interface ApplyCorrectionResponse {
	updated_count: number;
	album_key: string;
}

export async function listMetadataSources(): Promise<{ sources: SourceInfo[] }> {
	return fetchJson<{ sources: SourceInfo[] }>(`/api/albums/sources`);
}

export async function matchAlbumSource(
	albumKey: string,
	source: string,
	body: CorrectionMatchRequest,
): Promise<CorrectionPreview> {
	return fetchJson<CorrectionPreview>(
		`/api/albums/${albumKey}/match-source?source=${encodeURIComponent(source)}`,
		{
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify(body),
		},
	);
}

export async function applyAlbumCorrection(
	albumKey: string,
	body: ApplyCorrectionRequest,
): Promise<ApplyCorrectionResponse> {
	return fetchJson<ApplyCorrectionResponse>(`/api/albums/${albumKey}/apply-correction`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(body),
	});
}

export async function listAlbums(params: ListAlbumsParams = {}): Promise<PaginatedAlbums> {
	const qs = new URLSearchParams();
	for (const [k, v] of Object.entries(params)) {
		if (v === undefined || v === null || v === '') continue;
		if (Array.isArray(v)) {
			for (const item of v) qs.append(k, String(item));
		} else {
			qs.set(k, String(v));
		}
	}
	return fetchJson<PaginatedAlbums>(`/api/albums?${qs}`);
}

export async function getAlbumTracks(albumKey: string): Promise<AlbumTracks> {
	return fetchJson<AlbumTracks>(`/api/albums/${albumKey}/tracks`);
}

export async function matchAlbumMusicBrainz(albumKey: string): Promise<MBMatchResponse> {
	return fetchJson<MBMatchResponse>(`/api/albums/${albumKey}/match-musicbrainz`, {
		method: 'POST',
	});
}

export async function applyAlbumMusicBrainz(
	albumKey: string,
	body: MBApplyRequest,
): Promise<MBApplyResponse> {
	return fetchJson<MBApplyResponse>(`/api/albums/${albumKey}/apply-mb-mapping`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(body),
	});
}
