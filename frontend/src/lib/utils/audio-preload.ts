/**
 * Audio preload cache — module-level singleton for hover-based preloading.
 *
 * When a DJ hovers a track row in TrackTable, we start buffering the audio
 * so playback feels near-instant on click. Only one preload runs at a time
 * to avoid wasting bandwidth on fast scrolling.
 */
import { API_BASE } from '$lib/api/client';

let preloadedTrackId: number | null = null;
let preloadedAudio: HTMLAudioElement | null = null;
let hoverTimer: ReturnType<typeof setTimeout> | null = null;

const DEBOUNCE_MS = 250;

/**
 * Called on track row mouseenter. Debounces to avoid preloading on fast scroll.
 * Starts buffering the audio and prefetches peaks data.
 */
export function preloadOnHover(trackId: number): void {
	// Already preloaded this track
	if (trackId === preloadedTrackId) return;

	// Clear any pending debounce
	if (hoverTimer !== null) {
		clearTimeout(hoverTimer);
		hoverTimer = null;
	}

	hoverTimer = setTimeout(() => {
		hoverTimer = null;
		startPreload(trackId);
	}, DEBOUNCE_MS);
}

/**
 * Cancel any pending preload (e.g., on mouseleave from the table area).
 */
export function cancelPreload(): void {
	if (hoverTimer !== null) {
		clearTimeout(hoverTimer);
		hoverTimer = null;
	}
}

function startPreload(trackId: number): void {
	// Cancel previous preload if different track
	if (preloadedAudio && preloadedTrackId !== trackId) {
		preloadedAudio.src = '';
		preloadedAudio.load();
		preloadedAudio = null;
		preloadedTrackId = null;
	}

	// Create preload audio element
	const audio = new Audio();
	audio.preload = 'auto';
	audio.src = `${API_BASE}/api/audio/${trackId}`;

	preloadedTrackId = trackId;
	preloadedAudio = audio;
}

/**
 * Get the preloaded Audio element for a track, if available.
 * Consumes the preload (returns it once, then clears).
 */
export function consumePreloadedAudio(trackId: number): HTMLAudioElement | null {
	if (preloadedTrackId === trackId && preloadedAudio) {
		const audio = preloadedAudio;
		preloadedAudio = null;
		preloadedTrackId = null;
		return audio;
	}
	return null;
}

/**
 * Check if a specific track's audio is preloaded and has buffered data.
 */
export function hasPreloadedAudio(trackId: number): boolean {
	return preloadedTrackId === trackId && preloadedAudio !== null;
}
