import type { LibraryStats, BpmBin, MoodPoint } from '$lib/types';
import { fetchJson } from './client';

export async function getLibraryStats(): Promise<LibraryStats> {
	return fetchJson<LibraryStats>('/api/stats/library');
}

export async function getCamelotStats(): Promise<Record<string, { A: number; B: number }>> {
	return fetchJson<Record<string, { A: number; B: number }>>('/api/stats/camelot');
}

export async function getBpmHistogram(): Promise<BpmBin[]> {
	return fetchJson<BpmBin[]>('/api/stats/bpm-histogram');
}

export async function getEnergyGenre(): Promise<Record<string, Record<string, number>>> {
	return fetchJson<Record<string, Record<string, number>>>('/api/stats/energy-genre');
}

export async function getMoodScatter(): Promise<MoodPoint[]> {
	return fetchJson<MoodPoint[]>('/api/stats/mood-scatter');
}
