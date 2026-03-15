import type {
	Cue,
	DJSet,
	SetBuildComplete,
	SetBuildParams,
	SetCreateParams,
	SetDetail,
	SetTrack,
	SetUpdateParams,
	SetWaveformTrack,
	TransitionDetail,
} from '$lib/types';
import { API_BASE, fetchJson } from './client';

export async function listSets(search?: string, limit = 20): Promise<DJSet[]> {
	const qs = new URLSearchParams();
	if (search) qs.set('search', search);
	qs.set('limit', String(limit));
	return fetchJson<DJSet[]>(`/api/sets?${qs}`);
}

export async function getSet(id: number): Promise<SetDetail> {
	return fetchJson<SetDetail>(`/api/sets/${id}`);
}

export async function getSetWaveforms(id: number): Promise<SetWaveformTrack[]> {
	return fetchJson<SetWaveformTrack[]>(`/api/sets/${id}/waveforms`);
}

export async function getTransition(setId: number, index: number): Promise<TransitionDetail> {
	return fetchJson<TransitionDetail>(`/api/sets/${setId}/transition/${index}`);
}

export async function getCues(setId: number, trackId: number): Promise<Cue[]> {
	return fetchJson<Cue[]>(`/api/sets/${setId}/tracks/${trackId}/cues`);
}

export async function createCue(
	setId: number,
	trackId: number,
	body: { position: number; name: string; cue_type?: string; start_sec: number; end_sec?: number; hot_cue_num?: number }
): Promise<Cue> {
	return fetchJson<Cue>(`/api/sets/${setId}/tracks/${trackId}/cues`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(body)
	});
}

export async function deleteCue(cueId: number): Promise<void> {
	await fetchJson(`/api/sets/cues/${cueId}`, { method: 'DELETE' });
}

export async function createSet(params: SetCreateParams): Promise<DJSet> {
	return fetchJson<DJSet>('/api/sets', {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(params),
	});
}

export async function updateSet(id: number, params: SetUpdateParams): Promise<DJSet> {
	return fetchJson<DJSet>(`/api/sets/${id}`, {
		method: 'PUT',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(params),
	});
}

export async function deleteSet(id: number): Promise<void> {
	await fetch(`${API_BASE}/api/sets/${id}`, { method: 'DELETE' });
}

/**
 * Build a set via SSE. Calls onEvent for each SSE event.
 * Returns a promise that resolves with the completed set info, or rejects on error.
 */
export function buildSet(
	params: SetBuildParams,
	onEvent?: (event: string, data: unknown) => void
): Promise<SetBuildComplete> {
	return new Promise((resolve, reject) => {
		fetch(`${API_BASE}/api/sets/build`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify(params),
		})
			.then((res) => {
				if (!res.ok || !res.body) {
					reject(new Error(`Build request failed: ${res.status}`));
					return;
				}

				const reader = res.body.getReader();
				const decoder = new TextDecoder();
				let buffer = '';
				let settled = false;

				function processChunk(chunk: string) {
					buffer += chunk;
					const lines = buffer.split('\n');
					buffer = lines.pop() ?? '';

					let currentEvent = '';
					for (const line of lines) {
						if (line.startsWith('event: ')) {
							currentEvent = line.slice(7).trim();
						} else if (line.startsWith('data: ')) {
							const data = JSON.parse(line.slice(6));
							onEvent?.(currentEvent, data);

							if (currentEvent === 'complete') {
								settled = true;
								resolve(data as SetBuildComplete);
							} else if (currentEvent === 'error') {
								settled = true;
								reject(new Error((data as { detail: string }).detail));
							}
						}
					}
				}

				function read(): void {
					reader
						.read()
						.then(({ done, value }) => {
							if (done) {
								if (!settled) {
									reject(new Error('SSE stream closed before build completed'));
								}
								return;
							}
							processChunk(decoder.decode(value, { stream: true }));
							read();
						})
						.catch(reject);
				}

				read();
			})
			.catch(reject);
	});
}

export async function addTrackToSet(
	setId: number,
	trackId: number,
	position?: number
): Promise<SetTrack[]> {
	return fetchJson<SetTrack[]>(`/api/sets/${setId}/tracks`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ track_id: trackId, position }),
	});
}

export async function removeTrackFromSet(setId: number, trackId: number): Promise<void> {
	await fetch(`${API_BASE}/api/sets/${setId}/tracks/${trackId}`, { method: 'DELETE' });
}

export async function reorderSetTracks(setId: number, trackIds: number[]): Promise<SetTrack[]> {
	return fetchJson<SetTrack[]>(`/api/sets/${setId}/tracks/reorder`, {
		method: 'PUT',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ track_ids: trackIds }),
	});
}

export async function exportRekordbox(setId: number): Promise<Blob> {
	const res = await fetch(`${API_BASE}/api/sets/${setId}/export/rekordbox`, { method: 'POST' });
	if (!res.ok) {
		const text = await res.text().catch(() => 'Export failed');
		throw new Error(text);
	}
	return res.blob();
}
