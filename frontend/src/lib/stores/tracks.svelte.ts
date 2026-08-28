import type { Track } from '$lib/types';
import { searchTracks, type SearchParams } from '$lib/api/tracks';

let tracks = $state<Track[]>([]);
let total = $state(0);
let loading = $state(false);
let error = $state<string | null>(null);
let lastParams = $state<SearchParams>({});
let fuzzy = $state(false);

/** How many tracks one page holds, and where the current page starts. */
let pageSize = $state(50);
let offset = $state(0);

/** Only the newest request may write. Paging invites fast repeat clicks, and
 *  without this the slower of two overlapping searches would win. */
let generation = 0;

async function run() {
	const mine = ++generation;
	loading = true;
	error = null;
	try {
		const result = await searchTracks({ ...lastParams, limit: pageSize, offset });
		if (mine !== generation) return;
		tracks = result.items;
		total = result.total;
		fuzzy = result.fuzzy ?? false;
	} catch (e) {
		if (mine !== generation) return;
		error = e instanceof Error ? e.message : String(e);
		tracks = [];
		total = 0;
		fuzzy = false;
	} finally {
		if (mine === generation) loading = false;
	}
}

/** New filters mean a new result set — always land back on the first page. */
async function search(params: SearchParams) {
	lastParams = params;
	offset = 0;
	await run();
}

/** Jump to a 1-based page, clamped to what actually exists. */
async function goToPage(page: number) {
	const last = Math.max(1, Math.ceil(total / pageSize));
	const clamped = Math.min(Math.max(1, page), last);
	const next = (clamped - 1) * pageSize;
	if (next === offset) return;
	offset = next;
	await run();
}

/** Change page size, keeping the first track you were looking at in view. */
async function setPageSize(size: number) {
	if (size === pageSize) return;
	const anchor = offset;
	pageSize = size;
	offset = Math.floor(anchor / size) * size;
	await run();
}

export function getTrackStore() {
	return {
		get tracks() { return tracks; },
		get total() { return total; },
		get loading() { return loading; },
		get error() { return error; },
		get lastParams() { return lastParams; },
		get fuzzy() { return fuzzy; },
		get offset() { return offset; },
		get pageSize() { return pageSize; },
		/** 1-based, so it reads the way the pager shows it. */
		get page() { return Math.floor(offset / pageSize) + 1; },
		get pageCount() { return Math.max(1, Math.ceil(total / pageSize)); },
		search,
		goToPage,
		setPageSize,
	};
}
