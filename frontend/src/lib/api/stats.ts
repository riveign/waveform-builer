import type { LibraryStats, BpmBin, MoodPoint, LibraryGapsResponse, EnhancedStatsResponse } from '$lib/types';
import { fetchJson } from './client';

// Every read takes an optional AbortSignal so callers (createResource) can cancel
// a request the moment its answer stops being wanted.

export async function getLibraryStats(signal?: AbortSignal): Promise<LibraryStats> {
	return fetchJson<LibraryStats>('/api/stats/library', { signal });
}

export async function getCamelotStats(signal?: AbortSignal): Promise<Record<string, { A: number; B: number }>> {
	return fetchJson<Record<string, { A: number; B: number }>>('/api/stats/camelot', { signal });
}

export async function getBpmHistogram(signal?: AbortSignal): Promise<BpmBin[]> {
	return fetchJson<BpmBin[]>('/api/stats/bpm-histogram', { signal });
}

export async function getEnergyGenre(signal?: AbortSignal): Promise<Record<string, Record<string, number>>> {
	return fetchJson<Record<string, Record<string, number>>>('/api/stats/energy-genre', { signal });
}

export async function getMoodScatter(signal?: AbortSignal): Promise<MoodPoint[]> {
	return fetchJson<MoodPoint[]>('/api/stats/mood-scatter', { signal });
}

export async function getLibraryGaps(signal?: AbortSignal): Promise<LibraryGapsResponse> {
	return fetchJson<LibraryGapsResponse>('/api/stats/gaps', { signal });
}

export async function getEnhancedStats(signal?: AbortSignal): Promise<EnhancedStatsResponse> {
	return fetchJson<EnhancedStatsResponse>('/api/stats/enhanced', { signal });
}
