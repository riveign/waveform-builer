import type { SetWaveformTrack } from '$lib/types';
import type WaveSurfer from 'wavesurfer.js';
import { API_BASE } from '$lib/api/client';

export type PlaybackMode = 'express' | 'builder';
export type PlaybackStatus = 'idle' | 'loading' | 'playing' | 'transitioning';
export type DeckId = 'A' | 'B';

/** Default snippet duration in seconds for express mode */
const EXPRESS_SNIPPET_SEC = 45;
/** Crossfade duration in seconds */
const CROSSFADE_SEC = 2;
/** Max pitch adjustment — beyond ±8% sounds unnatural */
const MAX_RATE_DELTA = 0.08;

let mode = $state<PlaybackMode | null>(null);
let status = $state<PlaybackStatus>('idle');
let setId = $state<number | null>(null);
let tracks = $state<SetWaveformTrack[]>([]);
let currentIndex = $state(0);
let activeDeck = $state<DeckId>('A');
let wsA = $state<WaveSurfer | null>(null);
let wsB = $state<WaveSurfer | null>(null);
let volume = $state(0.8);
let confirmed = $state<Set<number>>(new Set());
let currentTime = $state(0);
let bpmMatch = $state(true);

/** Per-deck listen tracking */
let deckListenedSeconds = $state(0);
let deckLastTimeUpdate = $state(0);
/** Session-scoped dedup for set playback */
const deckPlayedTrackIds = new Set<number>();

/** Persist confirmed track IDs to localStorage keyed by set ID */
function saveConfirmed(sid: number, ids: Set<number>) {
	try {
		localStorage.setItem(`kiku:confirmed:${sid}`, JSON.stringify([...ids]));
	} catch { /* quota exceeded — ignore */ }
}

/** Load confirmed track IDs from localStorage for a given set */
function loadConfirmed(sid: number): Set<number> {
	try {
		const raw = localStorage.getItem(`kiku:confirmed:${sid}`);
		if (raw) return new Set(JSON.parse(raw) as number[]);
	} catch { /* corrupted — ignore */ }
	return new Set();
}

/**
 * Calculate playback rate to pitch-match track B to track A's BPM.
 * Returns 1.0 if matching is disabled, either BPM is missing, or the
 * ratio exceeds the safe ±8% range.
 */
function calcRate(fromBpm: number | null, toBpm: number | null): number {
	if (!bpmMatch || !fromBpm || !toBpm || toBpm === 0) return 1;
	const ratio = fromBpm / toBpm;
	// Clamp: if beyond ±8%, don't force it — sounds wrong
	if (ratio < 1 - MAX_RATE_DELTA || ratio > 1 + MAX_RATE_DELTA) return 1;
	return ratio;
}

/** Audio routing for crossfade */
let audioCtx: AudioContext | null = null;
let gainNodeA: GainNode | null = null;
let gainNodeB: GainNode | null = null;
let sourceA: MediaElementAudioSourceNode | null = null;
let sourceB: MediaElementAudioSourceNode | null = null;
let connectedElA: HTMLAudioElement | null = null;
let connectedElB: HTMLAudioElement | null = null;
let crossfadeFrame: number | null = null;

function getMediaElement(ws: WaveSurfer): HTMLAudioElement | null {
	const media = ws.getMediaElement?.();
	return media instanceof HTMLAudioElement ? media : null;
}

function ensureAudioCtx(): AudioContext {
	if (!audioCtx) audioCtx = new AudioContext();
	return audioCtx;
}

function connectDeck(ws: WaveSurfer, deck: DeckId): { gain: GainNode; source: MediaElementAudioSourceNode } | null {
	const el = getMediaElement(ws);
	if (!el) return null;
	const ctx = ensureAudioCtx();

	if (deck === 'A') {
		if (connectedElA !== el) {
			sourceA?.disconnect(); sourceA = null;
			gainNodeA?.disconnect(); gainNodeA = null;
			connectedElA = null;
		}
		if (!sourceA) {
			sourceA = ctx.createMediaElementSource(el);
			gainNodeA = ctx.createGain();
			sourceA.connect(gainNodeA);
			gainNodeA.connect(ctx.destination);
			connectedElA = el;
		}
		return { gain: gainNodeA!, source: sourceA };
	} else {
		if (connectedElB !== el) {
			sourceB?.disconnect(); sourceB = null;
			gainNodeB?.disconnect(); gainNodeB = null;
			connectedElB = null;
		}
		if (!sourceB) {
			sourceB = ctx.createMediaElementSource(el);
			gainNodeB = ctx.createGain();
			sourceB.connect(gainNodeB);
			gainNodeB.connect(ctx.destination);
			connectedElB = el;
		}
		return { gain: gainNodeB!, source: sourceB };
	}
}

function getActiveWs(): WaveSurfer | null {
	return activeDeck === 'A' ? wsA : wsB;
}

function getInactiveWs(): WaveSurfer | null {
	return activeDeck === 'A' ? wsB : wsA;
}

function getActiveGain(): GainNode | null {
	return activeDeck === 'A' ? gainNodeA : gainNodeB;
}

function getInactiveGain(): GainNode | null {
	return activeDeck === 'A' ? gainNodeB : gainNodeA;
}

/** Get snippet start time: use 25% into track, or cue if available */
function snippetStart(track: SetWaveformTrack): number {
	const dur = track.duration_sec ?? 0;
	return dur * 0.25;
}

function preloadNextTrack() {
	const nextIdx = currentIndex + 1;
	if (nextIdx >= tracks.length) return;
	// The inactive deck component will react to the store and load the next track
}

function cancelCrossfade() {
	if (crossfadeFrame !== null) {
		cancelAnimationFrame(crossfadeFrame);
		crossfadeFrame = null;
	}
}

/** Crossfade from active deck to inactive deck */
function doCrossfade(onComplete: () => void) {
	status = 'transitioning';
	const activeGain = getActiveGain();
	const inactiveGain = getInactiveGain();
	const inactiveWs = getInactiveWs();

	if (!activeGain || !inactiveGain || !inactiveWs) {
		onComplete();
		return;
	}

	// Pitch-match: incoming track matches outgoing track's tempo
	const currentTrackBpm = tracks[currentIndex]?.bpm ?? null;
	const nextIdx = currentIndex + 1;
	const nextTrackBpm = nextIdx < tracks.length ? (tracks[nextIdx]?.bpm ?? null) : null;
	const incomingRate = calcRate(currentTrackBpm, nextTrackBpm);
	inactiveWs.setPlaybackRate(incomingRate);

	// Start inactive deck
	inactiveGain.gain.value = 0;
	inactiveWs.play();

	const startTime = performance.now();
	const fadeMs = CROSSFADE_SEC * 1000;

	function animate() {
		const elapsed = performance.now() - startTime;
		const progress = Math.min(elapsed / fadeMs, 1);

		activeGain!.gain.value = (1 - progress) * volume;
		inactiveGain!.gain.value = progress * volume;

		if (progress < 1) {
			crossfadeFrame = requestAnimationFrame(animate);
		} else {
			// Fade done — stop old deck
			getActiveWs()?.pause();
			crossfadeFrame = null;
			onComplete();
		}
	}

	crossfadeFrame = requestAnimationFrame(animate);
}

function advanceToNext() {
	const nextIndex = currentIndex + 1;
	if (nextIndex >= tracks.length) {
		stopPlayback();
		return;
	}

	const inactiveWs = getInactiveWs();
	if (!inactiveWs) {
		// Inactive deck not ready yet — wait a bit
		status = 'loading';
		return;
	}

	// In express mode, seek to snippet start
	if (mode === 'express') {
		const nextTrack = tracks[nextIndex];
		inactiveWs.setTime(snippetStart(nextTrack));
	}

	// Connect inactive deck to audio graph
	const inactiveDeck: DeckId = activeDeck === 'A' ? 'B' : 'A';
	connectDeck(inactiveWs, inactiveDeck);

	doCrossfade(() => {
		// Swap active deck
		activeDeck = activeDeck === 'A' ? 'B' : 'A';
		currentIndex = nextIndex;
		deckListenedSeconds = 0;
		deckLastTimeUpdate = 0;
		status = 'playing';
		preloadNextTrack();
	});
}

function advanceToPrev() {
	if (currentIndex <= 0) return;

	const prevIndex = currentIndex - 1;
	const inactiveWs = getInactiveWs();
	if (!inactiveWs) return;

	// Load previous track on inactive deck — component will react
	const inactiveDeck: DeckId = activeDeck === 'A' ? 'B' : 'A';
	connectDeck(inactiveWs, inactiveDeck);

	if (mode === 'express') {
		const prevTrack = tracks[prevIndex];
		inactiveWs.setTime(snippetStart(prevTrack));
	}

	doCrossfade(() => {
		activeDeck = activeDeck === 'A' ? 'B' : 'A';
		currentIndex = prevIndex;
		deckListenedSeconds = 0;
		deckLastTimeUpdate = 0;
		status = 'playing';
	});
}

function stopPlayback() {
	cancelCrossfade();
	wsA?.pause();
	wsB?.pause();

	if (gainNodeA) gainNodeA.gain.value = 1;
	if (gainNodeB) gainNodeB.gain.value = 1;

	// Persist confirmed tracks before clearing
	if (setId !== null && confirmed.size > 0) {
		saveConfirmed(setId, confirmed);
	}

	status = 'idle';
	mode = null;
	setId = null;
	tracks = [];
	currentIndex = 0;
	activeDeck = 'A';
	confirmed = new Set();
}

function startPlayback(playMode: PlaybackMode, newSetId: number, newTracks: SetWaveformTrack[]) {
	stopPlayback();

	mode = playMode;
	setId = newSetId;
	tracks = newTracks;
	currentIndex = 0;
	activeDeck = 'A';
	status = 'loading';
	confirmed = loadConfirmed(newSetId);
}

/** Called by PlaybackDeck when wavesurfer is ready */
function onDeckReady(deck: DeckId, ws: WaveSurfer) {
	if (deck === 'A') wsA = ws;
	else wsB = ws;

	// If this is the active deck and we're loading, start playback
	if (deck === activeDeck && status === 'loading') {
		connectDeck(ws, deck);
		const gain = deck === 'A' ? gainNodeA : gainNodeB;
		if (gain) gain.gain.value = volume;

		if (mode === 'express') {
			ws.setTime(snippetStart(tracks[currentIndex]));
		}

		ws.play();
		status = 'playing';
		preloadNextTrack();
	}
}

/** Called by PlaybackDeck on finish */
function onDeckFinish(deck: DeckId) {
	if (deck !== activeDeck) return;
	if (status === 'transitioning') return;
	advanceToNext();
}

/** Called by PlaybackDeck when audio fails to load (e.g. 404) — skip to next */
function onDeckError(deck: DeckId, trackId: number) {
	console.warn(`[playback] Audio unavailable for track ${trackId} on deck ${deck}, skipping`);
	if (deck === activeDeck) {
		// Active deck failed — skip forward
		advanceToNext();
	}
	// Inactive deck failed — it'll be handled when we try to transition to it
}

/** Called by PlaybackDeck on timeupdate — used for auto-advance in express mode */
function onDeckTimeUpdate(deck: DeckId, time: number) {
	if (deck !== activeDeck) return;
	currentTime = time;

	// Listen-time accumulation (builder mode only — express is 45s, below 60s threshold)
	if (mode === 'builder' && status === 'playing') {
		const delta = time - deckLastTimeUpdate;
		if (delta > 0 && delta < 2) {
			deckListenedSeconds += delta;
		}
		const track = tracks[currentIndex];
		if (track && deckListenedSeconds >= 60 && !deckPlayedTrackIds.has(track.track_id)) {
			deckPlayedTrackIds.add(track.track_id);
			fetch(`${API_BASE}/api/tracks/${track.track_id}/played`, { method: 'POST' }).catch(() => {});
		}
	}
	deckLastTimeUpdate = time;

	if (mode !== 'express') return;
	if (status !== 'playing') return;

	const track = tracks[currentIndex];
	if (!track) return;

	const snippetEnd = snippetStart(track) + EXPRESS_SNIPPET_SEC;
	if (time >= snippetEnd) {
		advanceToNext();
	}
}

export function getPlaybackStore() {
	return {
		// State (read-only)
		get mode() { return mode; },
		get status() { return status; },
		get setId() { return setId; },
		get tracks() { return tracks; },
		get currentIndex() { return currentIndex; },
		get activeDeck() { return activeDeck; },
		get volume() { return volume; },
		set volume(v: number) {
			volume = v;
			const gain = getActiveGain();
			if (gain) gain.gain.value = v;
		},
		get confirmed() { return confirmed; },
		get isActive() { return status !== 'idle'; },
		get currentTime() { return currentTime; },
		get bpmMatch() { return bpmMatch; },
		set bpmMatch(v: boolean) { bpmMatch = v; },

		/** Current track being played */
		get currentTrack(): SetWaveformTrack | null {
			if (currentIndex < 0 || currentIndex >= tracks.length) return null;
			return tracks[currentIndex];
		},

		/** The track that should be loaded on the inactive deck (next or prev) */
		get nextTrack(): SetWaveformTrack | null {
			const idx = currentIndex + 1;
			if (idx >= tracks.length) return null;
			return tracks[idx];
		},

		/** Which track the A deck should show */
		get deckATrack(): SetWaveformTrack | null {
			if (activeDeck === 'A') return tracks[currentIndex] ?? null;
			const nextIdx = currentIndex + 1;
			return nextIdx < tracks.length ? tracks[nextIdx] : null;
		},

		/** Which track the B deck should show */
		get deckBTrack(): SetWaveformTrack | null {
			if (activeDeck === 'B') return tracks[currentIndex] ?? null;
			const nextIdx = currentIndex + 1;
			return nextIdx < tracks.length ? tracks[nextIdx] : null;
		},

		// Actions
		startExpress(newSetId: number, newTracks: SetWaveformTrack[]) {
			startPlayback('express', newSetId, newTracks);
		},

		startBuilder(newSetId: number, newTracks: SetWaveformTrack[]) {
			startPlayback('builder', newSetId, newTracks);
		},

		next() { advanceToNext(); },
		previous() { advanceToPrev(); },
		stop() { stopPlayback(); },

		pause() {
			getActiveWs()?.pause();
			status = 'idle'; // We use 'idle' loosely here — could add 'paused' state
		},

		resume() {
			getActiveWs()?.play();
			status = 'playing';
		},

		togglePlayPause() {
			if (status === 'playing') {
				getActiveWs()?.pause();
			} else if (status === 'idle' && mode !== null) {
				getActiveWs()?.play();
				status = 'playing';
			}
		},

		// Builder mode actions
		keep() {
			if (mode !== 'builder') return;
			const track = tracks[currentIndex];
			if (track) {
				confirmed = new Set([...confirmed, track.track_id]);
				if (setId !== null) saveConfirmed(setId, confirmed);
			}
			advanceToNext();
		},

		skip() {
			advanceToNext();
		},

		// Deck callbacks
		onDeckReady,
		onDeckFinish,
		onDeckTimeUpdate,
		onDeckError,
	};
}
