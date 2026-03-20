import type { WaveformBandsData, WaveformData, WaveformDetailData } from '$lib/types';
import { fetchJson } from './client';

// ── Peaks cache: module-level singleton, survives component remounts ──
const PEAKS_CACHE_MAX = 100;
const peaksCache = new Map<number, WaveformData>();

function evictIfFull() {
	if (peaksCache.size >= PEAKS_CACHE_MAX) {
		// Delete oldest entry (first key in insertion order)
		const firstKey = peaksCache.keys().next().value;
		if (firstKey !== undefined) peaksCache.delete(firstKey);
	}
}

export async function getWaveformOverview(trackId: number): Promise<WaveformData> {
	const cached = peaksCache.get(trackId);
	if (cached) return cached;
	const data = await fetchJson<WaveformData>(`/api/waveforms/${trackId}/overview`);
	evictIfFull();
	peaksCache.set(trackId, data);
	return data;
}

/**
 * Prefetch peaks into the cache without blocking. Used by hover preload.
 * Silently ignores errors (track may not have waveform data).
 */
export function prefetchPeaks(trackId: number): void {
	if (peaksCache.has(trackId)) return;
	getWaveformOverview(trackId).catch(() => {});
}

export async function getWaveformDetail(trackId: number): Promise<WaveformDetailData> {
	return fetchJson<WaveformDetailData>(`/api/waveforms/${trackId}/detail`);
}

export async function getWaveformBands(trackId: number): Promise<WaveformBandsData> {
	return fetchJson<WaveformBandsData>(`/api/waveforms/${trackId}/bands`);
}
