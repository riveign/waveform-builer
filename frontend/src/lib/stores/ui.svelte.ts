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
	};
}
