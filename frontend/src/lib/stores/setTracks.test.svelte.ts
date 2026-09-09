/**
 * Tests for the set's running order — the store that lets an edit land on screen
 * before the server has heard about it.
 *
 * The three things worth pinning down are the three that used to go wrong: the
 * UI must move without waiting, a burst of moves must not become a burst of
 * writes, and a refused write must leave the DJ looking at the truth rather than
 * at our optimistic guess.
 */

import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { SetTrack, SetWaveformTrack } from '$lib/types';

const reorderSetTracks = vi.fn();
const removeTrackFromSet = vi.fn();
const addTrackToSet = vi.fn();

vi.mock('$lib/api/sets', () => ({
	reorderSetTracks: (...a: unknown[]) => reorderSetTracks(...a),
	removeTrackFromSet: (...a: unknown[]) => removeTrackFromSet(...a),
	addTrackToSet: (...a: unknown[]) => addTrackToSet(...a),
}));

const { getSetTracksStore } = await import('./setTracks.svelte');
const store = getSetTracksStore();

function track(id: number, position: number): SetWaveformTrack {
	return {
		track_id: id,
		position,
		title: `Track ${id}`,
		artist: `Artist ${id}`,
		bpm: 124,
		key: '8A',
		genre: 'techno',
		energy: 'build',
		duration_sec: 300,
		waveform_overview: `peaks-${id}`,
		transition_score: 0.5,
	} as unknown as SetWaveformTrack;
}

/** What the server would answer with for a given order. */
function serverList(ids: number[]): SetTrack[] {
	return ids.map((id, i) => ({
		track_id: id,
		position: i,
		title: `Track ${id}`,
		artist: `Artist ${id}`,
		has_waveform: true,
		transition_score: i === 0 ? null : 0.9,
	})) as unknown as SetTrack[];
}

const ids = () => store.tracks.map((t) => t.track_id);

beforeEach(() => {
	vi.clearAllMocks();
	vi.useRealTimers();
	store.setResync(null);
	// A different set id clears anything queued for the previous one.
	store.load(1, [track(1, 0), track(2, 1), track(3, 2)]);
});

describe('moving a track', () => {
	it('reorders on the spot, before any request is made', () => {
		expect(store.move(0, 2)).toBe(true);
		expect(ids()).toEqual([2, 3, 1]);
		expect(reorderSetTracks).not.toHaveBeenCalled();
	});

	it('renumbers positions to match the new order', () => {
		store.move(2, 0);
		expect(store.tracks.map((t) => t.position)).toEqual([0, 1, 2]);
		expect(ids()).toEqual([3, 1, 2]);
	});

	it('refuses a move that would fall off either end', () => {
		expect(store.move(0, -1)).toBe(false);
		expect(store.move(2, 3)).toBe(false);
		expect(store.move(1, 1)).toBe(false);
		expect(ids()).toEqual([1, 2, 3]);
	});

	it('coalesces a burst of moves into one write', async () => {
		reorderSetTracks.mockResolvedValue(serverList([2, 3, 1]));
		store.move(0, 1);
		store.move(1, 2);
		await store.flush();
		expect(reorderSetTracks).toHaveBeenCalledTimes(1);
		// The write carries the order as it stands after the whole burst.
		expect(reorderSetTracks).toHaveBeenCalledWith(1, [2, 3, 1]);
	});
});

describe('folding in the reply', () => {
	it('takes the server’s scores and keeps the waveforms it does not send', async () => {
		reorderSetTracks.mockResolvedValue(serverList([3, 1, 2]));
		store.move(2, 0);
		await store.flush();
		expect(ids()).toEqual([3, 1, 2]);
		// Rescored by the server...
		expect(store.tracks.map((t) => t.transition_score)).toEqual([null, 0.9, 0.9]);
		// ...while the peaks we already held travel with their track.
		expect(store.tracks.map((t) => t.waveform_overview)).toEqual([
			'peaks-3',
			'peaks-1',
			'peaks-2',
		]);
	});

	it('leaves a newly added track without peaks rather than borrowing another’s', async () => {
		addTrackToSet.mockResolvedValue(serverList([1, 2, 3, 9]));
		await store.add(9);
		expect(ids()).toEqual([1, 2, 3, 9]);
		expect(store.tracks[3].waveform_overview).toBeNull();
	});
});

describe('removing a track', () => {
	it('takes it out immediately and renumbers what is left', async () => {
		removeTrackFromSet.mockResolvedValue(serverList([1, 3]));
		await store.remove(2);
		expect(ids()).toEqual([1, 3]);
		expect(store.tracks.map((t) => t.position)).toEqual([0, 1]);
	});

	it('sends any queued move first, so the write cannot carry a dead track', async () => {
		const order: string[] = [];
		reorderSetTracks.mockImplementation(async (_id: number, list: number[]) => {
			order.push(`reorder:${list.join(',')}`);
			return serverList([2, 1, 3]);
		});
		removeTrackFromSet.mockImplementation(async () => {
			order.push('remove');
			return serverList([2, 3]);
		});

		store.move(0, 1); // queued, not yet sent
		await store.remove(1);

		expect(order).toEqual(['reorder:2,1,3', 'remove']);
		expect(ids()).toEqual([2, 3]);
	});
});

describe('when a write is refused', () => {
	it('says so and asks for the truth instead of guessing', async () => {
		const resync = vi.fn();
		store.setResync(resync);
		reorderSetTracks.mockRejectedValue(new Error('API 500'));
		vi.spyOn(console, 'error').mockImplementation(() => {});

		store.move(0, 2);
		expect(ids()).toEqual([2, 3, 1]); // shown optimistically
		await store.flush();

		expect(store.error).toMatch(/Couldn't save the new order/);
		expect(resync).toHaveBeenCalledTimes(1);
	});

	it('clears the error once the DJ dismisses it', async () => {
		store.setResync(vi.fn());
		removeTrackFromSet.mockRejectedValue(new Error('API 500'));
		vi.spyOn(console, 'error').mockImplementation(() => {});
		await store.remove(2);
		expect(store.error).not.toBeNull();
		store.clearError();
		expect(store.error).toBeNull();
	});
});

describe('switching sets', () => {
	it('drops a queued move rather than writing it to the set now on screen', async () => {
		store.move(0, 2); // queued for set 1
		store.load(2, [track(7, 0), track(8, 1)]);
		await store.flush();
		expect(reorderSetTracks).not.toHaveBeenCalled();
		expect(ids()).toEqual([7, 8]);
	});
});
