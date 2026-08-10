/**
 * Tests for the dual-deck playback store — 465 lines and, until now, the largest
 * untested thing in the frontend (docs/notes/PLN-001/P8).
 *
 * These cover the state machine only: which track is current, which deck is
 * active, and how builder mode records keeps. Audio itself is not exercised —
 * `AudioContext` and WaveSurfer only appear once a real deck reports ready, and
 * a fake one would test the fake.
 */

import { beforeEach, describe, expect, it } from 'vitest';
import { getPlaybackStore } from './playback.svelte';
import type { SetWaveformTrack } from '$lib/types';

const pb = getPlaybackStore();

function track(id: number): SetWaveformTrack {
	return {
		track_id: id,
		position: id - 1,
		title: `Track ${id}`,
		artist: `Artist ${id}`,
		bpm: 124,
		key: '8A',
		genre: 'techno',
		energy: 'build',
		duration_sec: 300,
		waveform_overview: null,
		energy_source: 'tag',
		energy_confidence: null,
		energy_value: 0.5,
		energy_label: 'build',
		energy_conflict: null,
	} as unknown as SetWaveformTrack;
}

const three = [track(1), track(2), track(3)];

/**
 * A stand-in for a WaveSurfer deck.
 *
 * `getMediaElement()` returns null on purpose: `connectDeck` bails before it
 * touches `AudioContext`, and `doCrossfade` completes synchronously when there
 * are no gain nodes. That lets the whole state machine run under jsdom without
 * a Web Audio stub — the audio graph is the one part these tests do not cover.
 */
function fakeDeck() {
	return {
		getMediaElement: () => null,
		setTime: () => {},
		play: () => {},
		pause: () => {},
		getDuration: () => 300,
		setPlaybackRate: () => {},
	} as unknown as Parameters<typeof pb.onDeckReady>[1];
}

/** Start a session with both decks reported ready, as the UI does on mount. */
function startWithDecks(mode: 'express' | 'builder', setId: number, list = three) {
	if (mode === 'express') pb.startExpress(setId, list);
	else pb.startBuilder(setId, list);
	pb.onDeckReady('A', fakeDeck());
	pb.onDeckReady('B', fakeDeck());
}

beforeEach(() => {
	// The store is a module-level singleton, so each test starts from a stop.
	pb.stop();
	localStorage.clear();
});

describe('playback store', () => {
	it('is idle before anything starts', () => {
		expect(pb.isActive).toBe(false);
		expect(pb.mode).toBeNull();
		expect(pb.currentTrack).toBeNull();
	});

	it('starts express mode on the first track', () => {
		pb.startExpress(12, three);

		expect(pb.isActive).toBe(true);
		expect(pb.mode).toBe('express');
		expect(pb.setId).toBe(12);
		expect(pb.currentIndex).toBe(0);
		expect(pb.currentTrack?.track_id).toBe(1);
		expect(pb.activeDeck).toBe('A');
	});

	it('starting again resets rather than resuming', () => {
		startWithDecks('express', 12);
		pb.next();
		expect(pb.currentIndex).toBe(1);

		startWithDecks('express', 13);

		expect(pb.currentIndex).toBe(0);
		expect(pb.setId).toBe(13);
	});

	// ── Moving through the set ────────────────────────────────────────────

	it('advances and goes back', () => {
		startWithDecks('express', 1);

		pb.next();
		expect(pb.currentTrack?.track_id).toBe(2);

		pb.previous();
		expect(pb.currentTrack?.track_id).toBe(1);
	});

	it('does not step before the first track', () => {
		startWithDecks('express', 1);

		pb.previous();

		expect(pb.currentIndex).toBe(0);
	});

	it('stops at the end rather than running past it', () => {
		startWithDecks('express', 1);
		pb.next();
		pb.next();
		expect(pb.currentTrack?.track_id).toBe(3);

		pb.next();

		// Either it stops the session or it stays put — never index 3.
		expect(pb.currentIndex).toBeLessThanOrEqual(2);
		expect(pb.currentTrack?.track_id === 3 || pb.currentTrack === null).toBe(true);
	});

	it('alternates decks as it advances, so the next track can preload', () => {
		startWithDecks('express', 1);
		const first = pb.activeDeck;

		pb.next();

		expect(pb.activeDeck).not.toBe(first);
	});

	it('shows the current track on the active deck and the next on the other', () => {
		startWithDecks('express', 1);

		const active = pb.activeDeck;
		const onActive = active === 'A' ? pb.deckATrack : pb.deckBTrack;
		const onIdle = active === 'A' ? pb.deckBTrack : pb.deckATrack;

		expect(onActive?.track_id).toBe(1);
		// The idle deck holds the next track so it can preload during playback.
		expect(onIdle?.track_id).toBe(2);
	});

	it('has no next track on the last one', () => {
		startWithDecks('express', 1);
		pb.next();
		pb.next();

		expect(pb.nextTrack).toBeNull();
	});

	it('survives being started with an empty set', () => {
		pb.startExpress(1, []);

		expect(pb.currentTrack).toBeNull();
		expect(pb.nextTrack).toBeNull();
		expect(() => pb.next()).not.toThrow();
	});

	// ── Builder mode ──────────────────────────────────────────────────────

	it('records a keep and moves on', () => {
		startWithDecks('builder', 7);

		pb.keep();

		expect(pb.confirmed.has(1)).toBe(true);
		expect(pb.currentTrack?.track_id).toBe(2);
	});

	it('skipping advances without confirming', () => {
		startWithDecks('builder', 7);

		pb.skip();

		expect(pb.confirmed.has(1)).toBe(false);
		expect(pb.currentTrack?.track_id).toBe(2);
	});

	it('ignores keep outside builder mode', () => {
		startWithDecks('express', 7);

		pb.keep();

		expect(pb.confirmed.size).toBe(0);
	});

	it('remembers keeps for a set across sessions', () => {
		startWithDecks('builder', 42);
		pb.keep();
		pb.stop();

		pb.startBuilder(42, three);

		expect(pb.confirmed.has(1)).toBe(true);
	});

	it('does not carry keeps between different sets', () => {
		startWithDecks('builder', 42);
		pb.keep();
		pb.stop();

		pb.startBuilder(43, three);

		expect(pb.confirmed.has(1)).toBe(false);
	});

	// ── Stopping ──────────────────────────────────────────────────────────

	it('stop clears the session', () => {
		startWithDecks('express', 1);
		pb.stop();

		expect(pb.isActive).toBe(false);
		expect(pb.currentTrack).toBeNull();
	});

	it('stop is safe when nothing is playing', () => {
		expect(() => pb.stop()).not.toThrow();
	});

	it('volume is settable and readable', () => {
		startWithDecks('express', 1);
		pb.volume = 0.42;

		expect(pb.volume).toBeCloseTo(0.42);
	});
});
