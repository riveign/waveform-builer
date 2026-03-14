import type { Cue, DJSet, SetDetail, SetWaveformTrack, TransitionDetail } from '$lib/types';
import { fetchJson } from './client';

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

export async function exportRekordbox(setId: number): Promise<Blob> {
	const res = await fetch(`/api/sets/${setId}/export/rekordbox`, { method: 'POST' });
	if (!res.ok) {
		const text = await res.text().catch(() => 'Export failed');
		throw new Error(text);
	}
	return res.blob();
}
