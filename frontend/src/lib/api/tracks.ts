import type { Track, TrackFeatures, TrackSetAppearance, PaginatedTracks, SuggestNextResponse, ScoringWeights } from '$lib/types';
import { API_BASE, fetchJson } from './client';

export interface SearchParams {
	search?: string;
	title?: string;
	artist?: string[];
	genre?: string[];
	key?: string[];
	label?: string[];
	bpm_min?: number;
	bpm_max?: number;
	energy?: string;
	energy_zone?: string;
	rating_min?: number;
	plays_min?: number;
	plays_max?: number;
	sort?: string;
	limit?: number;
	offset?: number;
}

export async function searchTracks(params: SearchParams): Promise<PaginatedTracks> {
	const qs = new URLSearchParams();
	for (const [k, v] of Object.entries(params)) {
		if (v === undefined || v === null || v === '') continue;
		if (Array.isArray(v)) {
			for (const item of v) {
				qs.append(k, String(item));
			}
		} else {
			qs.set(k, String(v));
		}
	}
	return fetchJson<PaginatedTracks>(`/api/tracks/search?${qs}`);
}

export async function autocompleteArtists(q: string, limit = 20): Promise<string[]> {
	const qs = new URLSearchParams({ q, limit: String(limit) });
	return fetchJson<string[]>(`/api/tracks/autocomplete/artists?${qs}`);
}

export async function autocompleteLabels(q: string, limit = 20): Promise<string[]> {
	const qs = new URLSearchParams({ q, limit: String(limit) });
	return fetchJson<string[]>(`/api/tracks/autocomplete/labels?${qs}`);
}

export async function getTrack(id: number): Promise<Track> {
	return fetchJson<Track>(`/api/tracks/${id}`);
}

export async function getTrackFeatures(id: number): Promise<TrackFeatures> {
	return fetchJson<TrackFeatures>(`/api/tracks/${id}/features`);
}

export async function updateTrackRating(trackId: number, rating: number): Promise<Track> {
	return fetchJson<Track>(`/api/tracks/${trackId}/rating`, {
		method: 'PATCH',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ rating }),
	});
}

export function getTrackArtworkUrl(id: number): string {
	return `${API_BASE}/api/tracks/${id}/artwork`;
}

export async function getTrackSets(id: number): Promise<TrackSetAppearance[]> {
	return fetchJson<TrackSetAppearance[]>(`/api/tracks/${id}/sets`);
}

export async function suggestNext(
	trackId: number,
	n = 10,
	genreFilter?: string,
	weights?: ScoringWeights,
	setId?: number
): Promise<SuggestNextResponse> {
	const qs = new URLSearchParams({ n: String(n) });
	if (setId !== undefined) qs.set('set_id', String(setId));
	if (genreFilter) qs.set('genre_filter', genreFilter);
	if (weights) {
		qs.set('w_harmonic', String(weights.harmonic));
		qs.set('w_energy_fit', String(weights.energy_fit));
		qs.set('w_bpm_compat', String(weights.bpm_compat));
		qs.set('w_genre_coherence', String(weights.genre_coherence));
		qs.set('w_track_quality', String(weights.track_quality));
	}
	return fetchJson<SuggestNextResponse>(`/api/tracks/${trackId}/suggest-next?${qs}`);
}
