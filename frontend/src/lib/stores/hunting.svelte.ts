import type { HuntSession, HuntSessionSummary } from '$lib/types';
import { startHunt, getHunt, listHunts, updateHuntTrackStatus } from '$lib/api/hunt';

let currentHunt = $state<HuntSession | null>(null);
let history = $state<HuntSessionSummary[]>([]);
let historyTotal = $state(0);
let loading = $state(false);
let error = $state<string | null>(null);

async function hunt(url: string) {
	loading = true;
	error = null;
	currentHunt = null;
	try {
		currentHunt = await startHunt(url);
	} catch (e) {
		error = e instanceof Error ? e.message : String(e);
	} finally {
		loading = false;
	}
}

async function loadHunt(huntId: number) {
	loading = true;
	error = null;
	try {
		currentHunt = await getHunt(huntId);
	} catch (e) {
		error = e instanceof Error ? e.message : String(e);
	} finally {
		loading = false;
	}
}

async function loadHistory() {
	try {
		const result = await listHunts();
		history = result.items;
		historyTotal = result.total;
	} catch (e) {
		error = e instanceof Error ? e.message : String(e);
	}
}

async function markWanted(huntTrackId: number) {
	try {
		await updateHuntTrackStatus(huntTrackId, 'wanted');
		if (currentHunt) {
			const track = currentHunt.tracks.find((t) => t.id === huntTrackId);
			if (track) track.acquisition_status = 'wanted';
			currentHunt = { ...currentHunt };
		}
	} catch (e) {
		error = e instanceof Error ? e.message : String(e);
	}
}

export function getHuntingStore() {
	return {
		get currentHunt() { return currentHunt; },
		get history() { return history; },
		get historyTotal() { return historyTotal; },
		get loading() { return loading; },
		get error() { return error; },
		get ownedCount() { return currentHunt?.owned_count ?? 0; },
		get unownedCount() { return (currentHunt?.track_count ?? 0) - (currentHunt?.owned_count ?? 0); },
		hunt,
		loadHunt,
		loadHistory,
		markWanted,
	};
}
