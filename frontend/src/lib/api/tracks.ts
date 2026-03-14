import type { Track, TrackFeatures, PaginatedTracks, SuggestNextResponse } from '$lib/types';
import { fetchJson } from './client';

export interface SearchParams {
	title?: string;
	artist?: string;
	genre?: string;
	key?: string;
	bpm_min?: number;
	bpm_max?: number;
	energy?: string;
	rating_min?: number;
	limit?: number;
	offset?: number;
}

export async function searchTracks(params: SearchParams): Promise<PaginatedTracks> {
	const qs = new URLSearchParams();
	for (const [k, v] of Object.entries(params)) {
		if (v !== undefined && v !== null && v !== '') {
			qs.set(k, String(v));
		}
	}
	return fetchJson<PaginatedTracks>(`/api/tracks/search?${qs}`);
}

export async function getTrack(id: number): Promise<Track> {
	return fetchJson<Track>(`/api/tracks/${id}`);
}

export async function getTrackFeatures(id: number): Promise<TrackFeatures> {
	return fetchJson<TrackFeatures>(`/api/tracks/${id}/features`);
}

export async function suggestNext(
	trackId: number,
	n = 10,
	genreFilter?: string
): Promise<SuggestNextResponse> {
	const qs = new URLSearchParams({ n: String(n) });
	if (genreFilter) qs.set('genre_filter', genreFilter);
	return fetchJson<SuggestNextResponse>(`/api/tracks/${trackId}/suggest-next?${qs}`);
}
