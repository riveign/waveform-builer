import type { Track, TrackFeatures } from '$lib/types';
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
}

export async function searchTracks(params: SearchParams): Promise<Track[]> {
	const qs = new URLSearchParams();
	for (const [k, v] of Object.entries(params)) {
		if (v !== undefined && v !== null && v !== '') {
			qs.set(k, String(v));
		}
	}
	return fetchJson<Track[]>(`/api/tracks/search?${qs}`);
}

export async function getTrack(id: number): Promise<Track> {
	return fetchJson<Track>(`/api/tracks/${id}`);
}

export async function getTrackFeatures(id: number): Promise<TrackFeatures> {
	return fetchJson<TrackFeatures>(`/api/tracks/${id}/features`);
}
