import type { Track } from '$lib/types';
import { searchTracks, type SearchParams } from '$lib/api/tracks';

let tracks = $state<Track[]>([]);
let total = $state(0);
let loading = $state(false);
let error = $state<string | null>(null);
let lastParams = $state<SearchParams>({});

async function search(params: SearchParams) {
	loading = true;
	error = null;
	lastParams = params;
	try {
		const result = await searchTracks(params);
		tracks = result.items;
		total = result.total;
	} catch (e) {
		error = e instanceof Error ? e.message : String(e);
		tracks = [];
		total = 0;
	} finally {
		loading = false;
	}
}

export function getTrackStore() {
	return {
		get tracks() { return tracks; },
		get total() { return total; },
		get loading() { return loading; },
		get error() { return error; },
		get lastParams() { return lastParams; },
		search,
	};
}
