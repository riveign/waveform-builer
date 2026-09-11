import type { components } from './schema';
import { fetchJson, fetchVoid } from './client';

type S = components['schemas'];
export type VinylSearchResponse = S['VinylSearchResponse'];
export type VinylSearchResult = S['VinylSearchResult'];
export type VinylPreview = S['VinylPreviewResponse'];
export type VinylPreviewRow = S['VinylPreviewRow'];
export type VinylImportResponse = S['VinylImportResponse'];
export type VinylReleaseSummary = S['VinylReleaseSummary'];

export async function searchPressings(
	q: string,
	opts: { vinylOnly?: boolean; limit?: number } = {},
	signal?: AbortSignal,
): Promise<VinylSearchResponse> {
	const qs = new URLSearchParams({ q });
	if (opts.vinylOnly === false) qs.set('vinyl_only', 'false');
	if (opts.limit) qs.set('limit', String(opts.limit));
	return fetchJson<VinylSearchResponse>(`/api/vinyl/search?${qs}`, { signal });
}

/** The tracklist, plus every BPM Kiku could work out. Takes a second or so per
 *  side when it has to listen to a preview, so callers should show progress. */
export async function previewRelease(
	target: { releaseId?: string; url?: string },
	signal?: AbortSignal,
): Promise<VinylPreview> {
	const qs = new URLSearchParams();
	if (target.releaseId) qs.set('release_id', target.releaseId);
	if (target.url) qs.set('url', target.url);
	return fetchJson<VinylPreview>(`/api/vinyl/preview?${qs}`, { signal });
}

export async function importRelease(body: {
	release_id?: string;
	url?: string;
	acquired_on?: string;
	notes?: string;
	force?: boolean;
	sides?: { position: string; bpm?: number | null; key?: string | null; source?: string }[];
}): Promise<VinylImportResponse> {
	return fetchJson<VinylImportResponse>('/api/vinyl/import', {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(body),
	});
}

export async function listReleases(signal?: AbortSignal): Promise<VinylReleaseSummary[]> {
	return fetchJson<VinylReleaseSummary[]>('/api/vinyl/releases', { signal });
}

export async function removeRelease(id: number): Promise<void> {
	await fetchVoid(`/api/vinyl/releases/${id}`, { method: 'DELETE' });
}

/** The API explains itself in `detail`; the transport wrapper wraps that in
 *  "API 503: {...}". Dig the sentence back out so the DJ reads what happened
 *  rather than a status code. */
export function apiMessage(err: unknown): string {
	const raw = err instanceof Error ? err.message : String(err);
	const m = raw.match(/^API \d+: (.*)$/s);
	if (!m) return raw;
	try {
		const parsed = JSON.parse(m[1]);
		if (typeof parsed?.detail === 'string') return parsed.detail;
	} catch {
		/* not JSON — fall through to the raw body */
	}
	return m[1] || raw;
}
