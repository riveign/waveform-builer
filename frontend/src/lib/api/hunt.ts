import type { HuntSession, HuntListResponse } from '$lib/types';
import { fetchJson } from './client';

export async function startHunt(url: string, includeComments = true): Promise<HuntSession> {
	return fetchJson<HuntSession>('/api/hunt', {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ url, include_comments: includeComments }),
	});
}

export async function getHunt(huntId: number): Promise<HuntSession> {
	return fetchJson<HuntSession>(`/api/hunt/${huntId}`);
}

export async function listHunts(limit = 20, offset = 0): Promise<HuntListResponse> {
	return fetchJson<HuntListResponse>(`/api/hunts?limit=${limit}&offset=${offset}`);
}

export async function updateHuntTrackStatus(
	trackId: number,
	status: 'wanted' | 'owned' | 'unowned'
): Promise<void> {
	await fetchJson(`/api/hunt/tracks/${trackId}`, {
		method: 'PATCH',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ acquisition_status: status }),
	});
}
