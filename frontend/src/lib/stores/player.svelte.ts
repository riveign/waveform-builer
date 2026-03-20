import type { Track } from '$lib/types';
import type WaveSurfer from 'wavesurfer.js';
import { API_BASE } from '$lib/api/client';

export type PlayerMode = 'single' | 'set';
export type PlayerStatus = 'idle' | 'loading' | 'playing' | 'paused';

/** Minimal track info needed for queue display when full Track isn't available */
export interface QueueTrack {
	id: number;
	title: string | null;
	artist: string | null;
	duration_sec: number | null;
	bpm: number | null;
	key: string | null;
	genre: string | null;
}

/**
 * Global player store — single source of truth for all playback state in Kiku.
 *
 * Design:
 * - Store does NOT own the WaveSurfer instance. The NowPlayingBar (or any persistent
 *   audio component) calls `registerPlayer(ws)` after mounting its WaveSurfer.
 * - All state is Svelte 5 $state/$derived — reactive across any importing component.
 * - Calling `play(track)` stops any current playback, updates state, and tells the
 *   registered WaveSurfer to load the new audio URL.
 * - Set mode uses a queue with next/previous navigation.
 */

let currentTrack = $state<Track | null>(null);
let status = $state<PlayerStatus>('idle');
let currentTime = $state(0);
let duration = $state(0);
let volume = $state(0.8);
let isMuted = $state(false);
let mode = $state<PlayerMode>('single');
let queue = $state<Track[]>([]);
let queueIndex = $state(0);
let setId = $state<number | null>(null);

/** The registered WaveSurfer instance — set by the persistent audio component */
let ws = $state<WaveSurfer | null>(null);

/** Volume before mute, for unmute restore */
let preMuteVolume = 0.8;

/**
 * Build the audio URL for a track.
 */
function audioUrl(trackId: number): string {
	return `${API_BASE}/api/audio/${trackId}`;
}

/**
 * Load a track into the registered WaveSurfer instance.
 * Sets status to 'loading', then plays once ready.
 */
function loadAndPlay(track: Track) {
	currentTrack = track;
	duration = track.duration_sec ?? 0;
	currentTime = 0;
	status = 'loading';

	if (!ws) {
		// No player registered yet — state is set, player will pick it up on register
		return;
	}

	ws.load(audioUrl(track.id));
	// 'ready' handler (bound in registerPlayer) will call ws.play()
}

/**
 * Register the WaveSurfer instance from the persistent player component.
 * Binds event listeners to keep store state in sync.
 * Returns a cleanup function to call on unmount.
 */
function registerPlayer(instance: WaveSurfer): () => void {
	ws = instance;

	const onTimeUpdate = (time: number) => {
		currentTime = time;
	};

	const onPlay = () => {
		status = 'playing';
	};

	const onPause = () => {
		// Only set paused if we didn't explicitly stop
		if (status === 'playing') {
			status = 'paused';
		}
	};

	const onFinish = () => {
		if (mode === 'set') {
			// Auto-advance in set mode
			const nextIdx = queueIndex + 1;
			if (nextIdx < queue.length) {
				queueIndex = nextIdx;
				loadAndPlay(queue[nextIdx]);
				return;
			}
		}
		// Single mode or end of queue — go idle
		status = 'idle';
		currentTime = 0;
	};

	const onReady = () => {
		duration = instance.getDuration();
		// Apply current volume
		instance.setVolume(isMuted ? 0 : volume);
		// Auto-play after load
		if (status === 'loading') {
			instance.play();
		}
	};

	instance.on('timeupdate', onTimeUpdate);
	instance.on('play', onPlay);
	instance.on('pause', onPause);
	instance.on('finish', onFinish);
	instance.on('ready', onReady);

	// If there's a pending track to load (set before player was registered)
	if (currentTrack && status === 'loading') {
		instance.load(audioUrl(currentTrack.id));
	}

	return () => {
		instance.un('timeupdate', onTimeUpdate);
		instance.un('play', onPlay);
		instance.un('pause', onPause);
		instance.un('finish', onFinish);
		instance.un('ready', onReady);
		if (ws === instance) {
			ws = null;
		}
	};
}

/**
 * Play a single track. Stops any current playback first.
 */
function play(track: Track) {
	mode = 'single';
	queue = [];
	queueIndex = 0;
	setId = null;
	loadAndPlay(track);
}

/**
 * Pause the current track.
 */
function pause() {
	if (ws && status === 'playing') {
		ws.pause();
		status = 'paused';
	}
}

/**
 * Resume the current track from where it was paused.
 */
function resume() {
	if (ws && status === 'paused') {
		ws.play();
		status = 'playing';
	}
}

/**
 * Toggle between play and pause.
 */
function togglePlay() {
	if (status === 'playing') {
		pause();
	} else if (status === 'paused') {
		resume();
	}
}

/**
 * Seek to a specific time in seconds.
 */
function seek(time: number) {
	if (!ws) return;
	const d = ws.getDuration();
	if (d > 0) {
		ws.seekTo(time / d);
		currentTime = time;
	}
}

/**
 * Set the playback volume (0-1).
 */
function setVolume(v: number) {
	volume = Math.max(0, Math.min(1, v));
	if (!isMuted && ws) {
		ws.setVolume(volume);
	}
}

/**
 * Toggle mute state. Preserves previous volume for unmute.
 */
function toggleMute() {
	if (isMuted) {
		isMuted = false;
		if (ws) ws.setVolume(volume);
	} else {
		preMuteVolume = volume;
		isMuted = true;
		if (ws) ws.setVolume(0);
	}
}

/**
 * Start playing a set — loads the queue and begins from the given index.
 */
function playSet(newSetId: number, tracks: Track[], startIndex = 0) {
	mode = 'set';
	setId = newSetId;
	queue = tracks;
	queueIndex = Math.max(0, Math.min(startIndex, tracks.length - 1));

	if (tracks.length > 0) {
		loadAndPlay(tracks[queueIndex]);
	}
}

/**
 * Advance to the next track in the queue (set mode).
 */
function next() {
	if (mode !== 'set' || queueIndex >= queue.length - 1) return;
	queueIndex++;
	loadAndPlay(queue[queueIndex]);
}

/**
 * Go to the previous track in the queue (set mode).
 */
function previous() {
	if (mode !== 'set') return;

	// If more than 3 seconds in, restart current track instead
	if (currentTime > 3 && ws) {
		ws.seekTo(0);
		currentTime = 0;
		return;
	}

	if (queueIndex <= 0) return;
	queueIndex--;
	loadAndPlay(queue[queueIndex]);
}

/**
 * Stop playback and clear all state.
 */
function stop() {
	if (ws) {
		ws.pause();
		ws.seekTo(0);
	}
	currentTrack = null;
	status = 'idle';
	currentTime = 0;
	duration = 0;
	mode = 'single';
	queue = [];
	queueIndex = 0;
	setId = null;
}

export function getPlayerStore() {
	return {
		// ── Read-only state ──
		get currentTrack() { return currentTrack; },
		get isPlaying() { return status === 'playing'; },
		get status() { return status; },
		get currentTime() { return currentTime; },
		get duration() { return duration; },
		get volume() { return volume; },
		get isMuted() { return isMuted; },
		get mode() { return mode; },
		get queue() { return queue; },
		get queueIndex() { return queueIndex; },
		get setId() { return setId; },

		/** True when any track is loaded (playing, paused, or loading) */
		get hasTrack() { return currentTrack !== null; },

		/** True when in set mode with tracks remaining after current */
		get hasNext() { return mode === 'set' && queueIndex < queue.length - 1; },

		/** True when in set mode with tracks before current */
		get hasPrevious() { return mode === 'set' && queueIndex > 0; },

		/** Progress as 0-1 ratio */
		get progress() { return duration > 0 ? currentTime / duration : 0; },

		// ── Actions ──
		play,
		pause,
		resume,
		togglePlay,
		seek,
		setVolume,
		toggleMute,
		playSet,
		next,
		previous,
		stop,

		// ── Player registration ──
		registerPlayer,
	};
}
