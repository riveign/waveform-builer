import type { Track, SetAnalysis } from '$lib/types';

/**
 * Cross-surface UI state that is *not* navigation.
 *
 * Anything that identifies what you are looking at — which surface, which track,
 * which set, which row inside it, list vs grid — lives in the URL instead, so it
 * survives a refresh and can be shared. See $lib/nav.
 *
 * What remains here is genuinely ambient: the track you were last looking at
 * (offered as a build seed), what the player is on, and two hand-off channels.
 */

/** The last track opened in Track view. Written by the track route; read by the
 *  build dialog, which offers it as a seed or tail. Not navigation — a memory. */
let selectedTrack = $state<Track | null>(null);
let playingTrackId = $state<number | null>(null);
/** Analysis computed during a build, handed to the set view so it need not re-run. */
let pendingAnalysis = $state<SetAnalysis | null>(null);
/** Bumped to ask the shell to open the Build a Set dialog. */
let buildRequested = $state(0);

/** The library sidebar folds to a rail. A layout preference, not navigation —
 *  so it's remembered per browser, never put in the URL. */
const SIDEBAR_KEY = 'kiku:sidebar-collapsed';
let sidebarCollapsed = $state(
	typeof localStorage !== 'undefined' && localStorage.getItem(SIDEBAR_KEY) === '1',
);
/** A collapsed library floated over the content for a quick search. */
let sidebarPeeking = $state(false);
/** Whether the library is narrowed by anything but its sort — the rail shows a dot. */
let libraryFiltered = $state(false);
/** Bumped to ask the library to focus its search box. */
let searchFocusRequested = $state(0);

function setSidebarCollapsed(v: boolean) {
	sidebarCollapsed = v;
	sidebarPeeking = false;
	if (typeof localStorage !== 'undefined') localStorage.setItem(SIDEBAR_KEY, v ? '1' : '0');
}

export function getUiStore() {
	return {
		get selectedTrack() { return selectedTrack; },
		set selectedTrack(v: Track | null) { selectedTrack = v; },
		get playingTrackId() { return playingTrackId; },
		set playingTrackId(v: number | null) { playingTrackId = v; },
		get pendingAnalysis() { return pendingAnalysis; },
		set pendingAnalysis(v: SetAnalysis | null) { pendingAnalysis = v; },
		get buildRequested() { return buildRequested; },
		/** Ask the shell to open the Build a Set dialog. */
		requestBuild() { buildRequested += 1; },

		get sidebarCollapsed() { return sidebarCollapsed; },
		get sidebarPeeking() { return sidebarPeeking; },
		/** The library is on screen — expanded, or peeking over the content. */
		get libraryOpen() { return !sidebarCollapsed || sidebarPeeking; },
		get libraryFiltered() { return libraryFiltered; },
		set libraryFiltered(v: boolean) { libraryFiltered = v; },
		get searchFocusRequested() { return searchFocusRequested; },
		setSidebarCollapsed,
		toggleSidebar() { setSidebarCollapsed(!sidebarCollapsed); },
		/** Jump to search. A collapsed library peeks rather than unfolding, so the
		 *  content pane never reflows for a quick look. */
		focusSearch() {
			if (sidebarCollapsed) sidebarPeeking = true;
			searchFocusRequested += 1;
		},
		closePeek() { sidebarPeeking = false; },
	};
}
