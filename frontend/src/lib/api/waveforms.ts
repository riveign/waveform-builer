import type { WaveformBandsData, WaveformData, WaveformDetailData } from '$lib/types';
import { fetchJson } from './client';

export async function getWaveformOverview(trackId: number): Promise<WaveformData> {
	return fetchJson<WaveformData>(`/api/waveforms/${trackId}/overview`);
}

export async function getWaveformDetail(trackId: number): Promise<WaveformDetailData> {
	return fetchJson<WaveformDetailData>(`/api/waveforms/${trackId}/detail`);
}

export async function getWaveformBands(trackId: number): Promise<WaveformBandsData> {
	return fetchJson<WaveformBandsData>(`/api/waveforms/${trackId}/bands`);
}
