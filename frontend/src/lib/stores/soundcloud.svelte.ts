import type { SCPlaylist, SCTrack } from '$lib/types';
import {
	getSCStatus,
	getSCConnectUrl,
	disconnectSC,
	getSCPlaylists,
	getSCLikes,
	chasePlaylist as apiChasePlaylist,
	chaseLikes as apiChaseLikes,
} from '$lib/api/soundcloud';

let connected = $state(false);
let username = $state<string | null>(null);
let avatarUrl = $state<string | null>(null);
let playlists = $state<SCPlaylist[]>([]);
let likes = $state<SCTrack[]>([]);
let likesNextCursor = $state<string | null>(null);
let loading = $state(false);
let error = $state<string | null>(null);

async function checkStatus() {
	try {
		const status = await getSCStatus();
		connected = status.connected;
		username = status.username;
		avatarUrl = status.avatar_url;
	} catch (e) {
		error = e instanceof Error ? e.message : String(e);
	}
}

async function connect() {
	try {
		const { auth_url } = await getSCConnectUrl();
		const popup = window.open(auth_url, 'sc-auth', 'width=600,height=700');

		// Listen for postMessage from callback
		const handler = (event: MessageEvent) => {
			if (event.data === 'sc-connected') {
				window.removeEventListener('message', handler);
				checkStatus();
			}
		};
		window.addEventListener('message', handler);

		// Fallback: poll if popup is closed without postMessage
		const poll = setInterval(() => {
			if (popup && popup.closed) {
				clearInterval(poll);
				window.removeEventListener('message', handler);
				checkStatus();
			}
		}, 1000);
	} catch (e) {
		error = e instanceof Error ? e.message : String(e);
	}
}

async function disconnect() {
	try {
		await disconnectSC();
		connected = false;
		username = null;
		avatarUrl = null;
		playlists = [];
		likes = [];
		likesNextCursor = null;
	} catch (e) {
		error = e instanceof Error ? e.message : String(e);
	}
}

async function loadPlaylists() {
	loading = true;
	error = null;
	try {
		playlists = await getSCPlaylists();
	} catch (e) {
		error = e instanceof Error ? e.message : String(e);
	} finally {
		loading = false;
	}
}

async function loadLikes(reset = false) {
	if (reset) {
		likes = [];
		likesNextCursor = null;
	}
	loading = true;
	error = null;
	try {
		const result = await getSCLikes(likesNextCursor ?? undefined);
		likes = [...likes, ...result.tracks];
		likesNextCursor = result.next_cursor;
	} catch (e) {
		error = e instanceof Error ? e.message : String(e);
	} finally {
		loading = false;
	}
}

async function chasePlaylist(playlistId: number) {
	loading = true;
	error = null;
	try {
		const hunt = await apiChasePlaylist(playlistId);
		return hunt;
	} catch (e) {
		error = e instanceof Error ? e.message : String(e);
		return null;
	} finally {
		loading = false;
	}
}

async function chaseLikes(trackIds: number[]) {
	loading = true;
	error = null;
	try {
		const hunt = await apiChaseLikes(trackIds);
		return hunt;
	} catch (e) {
		error = e instanceof Error ? e.message : String(e);
		return null;
	} finally {
		loading = false;
	}
}

export function getSoundCloudStore() {
	return {
		get connected() { return connected; },
		get username() { return username; },
		get avatarUrl() { return avatarUrl; },
		get playlists() { return playlists; },
		get likes() { return likes; },
		get likesNextCursor() { return likesNextCursor; },
		get loading() { return loading; },
		get error() { return error; },
		checkStatus,
		connect,
		disconnect,
		loadPlaylists,
		loadLikes,
		chasePlaylist,
		chaseLikes,
	};
}
