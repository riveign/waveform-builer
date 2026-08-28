import type { SetTrack, SetWaveformTrack } from '$lib/types';
import { addTrackToSet, removeTrackFromSet, reorderSetTracks } from '$lib/api/sets';

/**
 * The loaded set's running order — one copy, owned here.
 *
 * Before this, the same list lived in three places (the resource, `SetView`'s
 * `waveformTracks`, `SetTimeline`'s `items`) and every edit re-read the whole set
 * to put them back in agreement. That re-read cost three requests, blanked the
 * resource mid-flight — which unmounted the timeline under in-flight handlers —
 * and still showed the DJ a stale list for as long as it took.
 *
 * So: the edit lands in the UI immediately, and the request follows. Every
 * mutation endpoint already answers with the set's new state (positions
 * compacted, transitions rescored), so the reply is folded straight in — there is
 * nothing left to go and ask for. A DJ moving a track should see it move, not
 * watch the set reload around them.
 *
 * When a write fails we do NOT guess: the list is reset from the server, because
 * after a failed write the only thing we know for certain is that we don't know.
 */

let setId = $state<number | null>(null);
let tracks = $state<SetWaveformTrack[]>([]);
let error = $state<string | null>(null);
/** How to re-read the set when a write fails and local state can't be trusted. */
let resync: (() => void) | null = null;

/** Reorders coalesce: five taps of ↓ are one write, and the UI never waits. */
const REORDER_DEBOUNCE_MS = 400;
let reorderTimer: ReturnType<typeof setTimeout> | null = null;
let reorderPending = false;

/** Writes run one at a time — a reorder must not race the delete before it. */
let queue: Promise<unknown> = Promise.resolve();

function enqueue<T>(fn: () => Promise<T>): Promise<T> {
	const run = queue.then(fn, fn);
	queue = run.then(
		() => {},
		() => {},
	);
	return run;
}

/**
 * Fold a mutation's reply into the list. It carries everything the list renders
 * except `waveform_overview`, which is only served by the waveforms read — so
 * that one field is carried across by track id from what we already hold.
 */
function reconcile(server: SetTrack[]): void {
	const peaks = new Map<number, string | null | undefined>();
	for (const t of tracks) peaks.set(t.track_id, t.waveform_overview);
	tracks = server.map(({ has_waveform, ...rest }) => ({
		...rest,
		// A track added just now has no entry here; it renders fine without one.
		waveform_overview: peaks.get(rest.track_id) ?? null,
	}));
}

function fail(message: string, err: unknown): void {
	error = message;
	console.error(message, err);
	// The optimistic list may now disagree with the server. Go and find out.
	resync?.();
}

/** Send any coalesced reorder now, before another write reads the list. */
async function flushReorder(): Promise<void> {
	if (reorderTimer) {
		clearTimeout(reorderTimer);
		reorderTimer = null;
	}
	if (!reorderPending) return;
	reorderPending = false;
	const sid = setId;
	if (sid === null) return;
	await enqueue(async () => {
		try {
			// Read the ids at send time: the list may have moved on since the tap.
			reconcile(await reorderSetTracks(sid, tracks.map((t) => t.track_id)));
			error = null;
		} catch (err) {
			fail("Couldn't save the new order — reloading the set.", err);
		}
	});
}

function scheduleReorder(): void {
	reorderPending = true;
	if (reorderTimer) clearTimeout(reorderTimer);
	reorderTimer = setTimeout(() => void flushReorder(), REORDER_DEBOUNCE_MS);
}

export function getSetTracksStore() {
	return {
		get tracks() {
			return tracks;
		},
		get error() {
			return error;
		},
		get setId() {
			return setId;
		},

		/** Seed from an authoritative read. Clears anything queued for the old set. */
		load(id: number | null, next: SetWaveformTrack[]) {
			if (id !== setId) {
				if (reorderTimer) clearTimeout(reorderTimer);
				reorderTimer = null;
				reorderPending = false;
				error = null;
			}
			setId = id;
			tracks = next;
		},

		/** Tell the store how to re-read the set after a failed write. */
		setResync(fn: (() => void) | null) {
			resync = fn;
		},

		clearError() {
			error = null;
		},

		/** Replace the list wholesale — for panels that return the set's new state. */
		applyServer(server: SetTrack[]) {
			reconcile(server);
		},

		/** Move a track. Lands in the UI now; the write follows, coalesced. */
		move(from: number, to: number): boolean {
			if (to < 0 || to >= tracks.length || from === to) return false;
			const next = [...tracks];
			const [moved] = next.splice(from, 1);
			next.splice(to, 0, moved);
			// Positions are the list's own order until the server answers with its.
			tracks = next.map((t, i) => ({ ...t, position: i }));
			scheduleReorder();
			return true;
		},

		/** Commit an order arrived at some other way (a drag). */
		setOrder(next: SetWaveformTrack[]) {
			tracks = next.map((t, i) => ({ ...t, position: i }));
			scheduleReorder();
		},

		flush: flushReorder,

		async remove(trackId: number) {
			const sid = setId;
			if (sid === null) return;
			await flushReorder();
			tracks = tracks
				.filter((t) => t.track_id !== trackId)
				.map((t, i) => ({ ...t, position: i }));
			await enqueue(async () => {
				try {
					reconcile(await removeTrackFromSet(sid, trackId));
					error = null;
				} catch (err) {
					fail("Couldn't take that track out — reloading the set.", err);
				}
			});
		},

		async add(trackId: number, position?: number) {
			const sid = setId;
			if (sid === null) return;
			await flushReorder();
			await enqueue(async () => {
				try {
					reconcile(await addTrackToSet(sid, trackId, position));
					error = null;
				} catch (err) {
					fail("Couldn't add that track — reloading the set.", err);
				}
			});
		},
	};
}
