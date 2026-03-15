import type { TinderQueueResponse, TinderDecision, TinderDecideResult, TinderRetrainResult, TinderStats } from '$lib/types';
import { fetchJson } from './client';

export interface TinderQueueParams {
	genre_family?: string;
	bpm_min?: number;
	bpm_max?: number;
	include_conflicts?: boolean;
	track_ids?: number[];
	limit?: number;
	offset?: number;
}

export async function getTinderQueue(params: TinderQueueParams = {}): Promise<TinderQueueResponse> {
	const qs = new URLSearchParams();
	for (const [k, v] of Object.entries(params)) {
		if (v === undefined || v === null || v === '') continue;
		if (k === 'track_ids' && Array.isArray(v)) {
			qs.set(k, v.join(','));
		} else {
			qs.set(k, String(v));
		}
	}
	return fetchJson<TinderQueueResponse>(`/api/tinder/queue?${qs}`);
}

export async function submitDecision(
	trackId: number,
	decision: TinderDecision,
	overrideZone?: string
): Promise<TinderDecideResult> {
	return fetchJson<TinderDecideResult>('/api/tinder/decide', {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ track_id: trackId, decision, override_zone: overrideZone }),
	});
}

export async function retrain(): Promise<TinderRetrainResult> {
	return fetchJson<TinderRetrainResult>('/api/tinder/retrain', { method: 'POST' });
}

export async function getTinderStats(): Promise<TinderStats> {
	return fetchJson<TinderStats>('/api/tinder/stats');
}
