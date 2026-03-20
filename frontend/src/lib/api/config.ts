import type { ScoringWeights } from '$lib/types';
import { fetchJson } from './client';

export async function getScoringWeights(): Promise<ScoringWeights> {
	return fetchJson<ScoringWeights>('/api/config/scoring-weights');
}

export async function updateScoringWeights(weights: ScoringWeights): Promise<ScoringWeights> {
	return fetchJson<ScoringWeights>('/api/config/scoring-weights', {
		method: 'PUT',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(weights),
	});
}
