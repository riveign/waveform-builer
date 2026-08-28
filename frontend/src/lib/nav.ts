/**
 * The route table, in one place.
 *
 * Every surface Kiku shows is a URL, so a transition you want to study can be
 * bookmarked, shared, and returned to with the back button. The tab strip reads
 * this list; so does the 1–6 keyboard shortcut map.
 */

import { goto } from '$app/navigation';

export type Tab = 'track' | 'set' | 'dna' | 'tinder' | 'hunt' | 'albums';

export interface TabDef {
	value: Tab;
	label: string;
	/** Number key that jumps here. Also shown in the tab strip. */
	shortcut: string;
	path: string;
}

export const TABS: TabDef[] = [
	{ value: 'track', label: 'Track view', shortcut: '1', path: '/track' },
	{ value: 'set', label: 'Set timeline', shortcut: '2', path: '/set' },
	{ value: 'dna', label: 'Taste DNA', shortcut: '3', path: '/dna' },
	{ value: 'tinder', label: 'Energy tinder', shortcut: '4', path: '/tinder' },
	{ value: 'hunt', label: 'Track hunter', shortcut: '5', path: '/hunt' },
	{ value: 'albums', label: 'Albums', shortcut: '6', path: '/albums' },
];

/** Which tab a pathname belongs to, for highlighting the active segment. */
export function tabFromPath(pathname: string): Tab | null {
	const seg = pathname.split('/')[1] ?? '';
	return TABS.find((t) => t.value === seg)?.value ?? null;
}

/** Deep link to a track's detail view. */
export function trackHref(trackId: number): string {
	return `/track/${trackId}`;
}

/**
 * Deep link to a set, optionally focused on one track within it.
 * The focused track rides in a query param because it selects *within* the set
 * rather than identifying a different resource.
 */
export function setHref(setId: number, opts?: { trackId?: number | null }): string {
	const t = opts?.trackId;
	return t == null ? `/set/${setId}` : `/set/${setId}?t=${t}`;
}

/**
 * Update one query parameter without adding a history entry.
 *
 * Selecting a row inside a set, or flipping list/grid, should survive a refresh
 * and a share — but pressing Back should leave the *set*, not step through every
 * row you clicked on the way. Hence `replaceState: true`.
 *
 * This goes through `goto` rather than `$app/navigation`'s `replaceState`: that
 * one is shallow routing, so it rewrites the address bar without republishing
 * `page.url`. Anything derived from a query param — the view toggle, the focused
 * row — then only caught up on a manual refresh.
 *
 * Pass null to drop the parameter.
 */
export function setQueryParam(url: URL, key: string, value: string | number | null): void {
	const next = new URL(url);
	if (value === null) next.searchParams.delete(key);
	else next.searchParams.set(key, String(value));
	if (next.href === url.href) return;
	// Keep the page where it is and the segment you just clicked focused —
	// this is a state change within the view, not a trip to a new one.
	void goto(next, { replaceState: true, noScroll: true, keepFocus: true });
}

/** Read a numeric query parameter, or null when absent or malformed. */
export function numParam(url: URL, key: string): number | null {
	const raw = url.searchParams.get(key);
	if (raw === null) return null;
	const n = Number(raw);
	return Number.isFinite(n) ? n : null;
}
