import type { SCStatus, SCPlaylist, SCLikesResponse, HuntSession } from '$lib/types';
import { fetchJson } from './client';

export async function getSCStatus(): Promise<SCStatus> {
	return fetchJson<SCStatus>('/api/soundcloud/status');
}

export async function getSCConnectUrl(): Promise<{ auth_url: string }> {
	return fetchJson<{ auth_url: string }>('/api/soundcloud/connect');
}

export async function disconnectSC(): Promise<void> {
	await fetchJson('/api/soundcloud/disconnect', { method: 'DELETE' });
}

export async function getSCPlaylists(): Promise<SCPlaylist[]> {
	return fetchJson<SCPlaylist[]>('/api/soundcloud/playlists');
}

export async function getSCLikes(cursor?: string): Promise<SCLikesResponse> {
	const params = cursor ? `?cursor=${encodeURIComponent(cursor)}` : '';
	return fetchJson<SCLikesResponse>(`/api/soundcloud/likes${params}`);
}

export async function chasePlaylist(playlistId: number): Promise<HuntSession> {
	return fetchJson<HuntSession>('/api/soundcloud/chase', {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ playlist_id: playlistId, source: 'soundcloud_playlist' }),
	});
}

export async function chaseLikes(trackIds: number[]): Promise<HuntSession> {
	return fetchJson<HuntSession>('/api/soundcloud/chase', {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ track_ids: trackIds, source: 'soundcloud_likes' }),
	});
}
