/**
 * One place that knows how to fetch something and how to say so.
 *
 * Before this, 26 components each hand-rolled the same four lines of loading /
 * error state, and none of them cancelled anything. That made three bugs
 * unpreventable rather than merely unfixed (docs/notes/OBS-005/K3):
 *
 *   a) stale-response races  — the slower of two searches wins
 *   b) redundant refetches   — the same track re-fetched on every remount
 *   c) stale reads after writes — a mutation leaves other copies wrong
 *
 * `createResource` closes (a) and (c): superseded requests are aborted *and* their
 * results discarded, and `invalidate()` tells every live resource under a key to
 * refetch.
 *
 * It does NOT close (b), and measuring proved it. De-duplication only merges
 * requests genuinely in flight at the same moment; two components that want the
 * same data *sequentially* — a parent gating its children behind its own load,
 * say — still make two requests. Fixing that needs a cache with a lifetime, which
 * is the line P5 agreed not to cross (docs/notes/PLN-001/P5). If (b) starts to
 * hurt, that is the signal to take a real query library rather than grow this one.
 *
 * Also not here: pagination and eviction. Those belong to the caller.
 */

import { onDestroy, untrack } from 'svelte';

export type Fetcher<A, T> = (args: A, signal: AbortSignal) => Promise<T>;

export interface ResourceOptions<A, T> {
	/**
	 * Stable identity for this request, used for de-duplication and invalidation.
	 * Defaults to the JSON of the args. Give resources that should invalidate
	 * together a shared prefix, e.g. `sets:${id}`.
	 */
	key?: (args: A) => string;
	/** Value exposed before the first load resolves. */
	initial?: T;
	/**
	 * Keep the previous value visible while a new one loads, instead of blanking.
	 * Right for a list being re-filtered; wrong when the subject itself changed.
	 */
	keepPrevious?: boolean;
}

export interface Resource<T> {
	readonly data: T | undefined;
	readonly loading: boolean;
	readonly error: string | null;
	/** Refetch now, bypassing de-duplication. */
	refresh(): void;
}

/** In-flight requests by key, so N components asking at once make one request. */
const inFlight = new Map<string, Promise<unknown>>();
/** Live resources by key, so invalidate() can reach them. */
const live = new Map<string, Set<() => void>>();

/** Tell every live resource whose key starts with `prefix` to refetch. */
export function invalidate(prefix: string): void {
	for (const [key, fns] of live) {
		if (key.startsWith(prefix)) for (const fn of fns) fn();
	}
}

export function createResource<A, T>(
	/** Reactive args. Return `null` to stay idle — nothing is fetched. */
	source: () => A | null,
	fetcher: Fetcher<A, T>,
	options: ResourceOptions<A, T> = {},
): Resource<T> {
	const { key: keyOf = (a: A) => JSON.stringify(a), initial, keepPrevious = false } = options;

	let data = $state<T | undefined>(initial);
	let loading = $state(false);
	let error = $state<string | null>(null);

	let controller: AbortController | null = null;
	/** Only the newest request may write. Guards (a) even when abort is ignored. */
	let generation = 0;
	let currentKey: string | null = null;
	let registered: { key: string; fn: () => void } | null = null;
	/** The flight this resource put into the shared map, if it started one. */
	let ownedFlight: { key: string; promise: Promise<unknown> } | null = null;

	function unregister() {
		if (!registered) return;
		const set = live.get(registered.key);
		set?.delete(registered.fn);
		if (set && set.size === 0) live.delete(registered.key);
		registered = null;
	}

	async function run(args: A, key: string, { dedupe }: { dedupe: boolean }) {
		abandonInFlight();
		controller = new AbortController();
		const mine = ++generation;
		const signal = controller.signal;

		loading = true;
		error = null;
		if (!keepPrevious) data = initial;

		try {
			// Share a flight with any identical request already running.
			const existing = dedupe ? (inFlight.get(key) as Promise<T> | undefined) : undefined;
			const promise = existing ?? fetcher(args, signal);
			if (!existing) {
				inFlight.set(key, promise);
				ownedFlight = { key, promise };
				// The entry clears itself when the request settles, however it settles.
				// Doing this in a `finally` block below instead would leak the entry
				// whenever the awaiting resource returned early — and a stale entry is
				// worse than no de-duplication, because the next caller on that key
				// would await a promise nobody is going to resolve.
				void promise.then(
					() => releaseFlight(key, promise),
					() => releaseFlight(key, promise),
				);
			}

			const result = await promise;
			if (mine !== generation) return; // superseded — discard
			data = result;
		} catch (e) {
			if (signal.aborted || mine !== generation) return;
			error = e instanceof Error ? e.message : String(e);
			if (!keepPrevious) data = initial;
		} finally {
			if (mine === generation) loading = false;
		}
	}

	/** Drop a flight entry, but only if it is still the one we registered. */
	function releaseFlight(key: string, promise: Promise<unknown>) {
		if (inFlight.get(key) === promise) inFlight.delete(key);
		if (ownedFlight?.promise === promise) ownedFlight = null;
	}

	/**
	 * Abort whatever is running and stop advertising its flight.
	 *
	 * A fetcher that honours its signal rejects on abort and releases the entry
	 * itself; one that ignores it never settles at all. Releasing here covers both,
	 * so an abandoned request can never strand its key — the next caller would
	 * otherwise await a promise nobody will resolve, and sit loading forever.
	 */
	function abandonInFlight() {
		controller?.abort();
		if (ownedFlight) {
			releaseFlight(ownedFlight.key, ownedFlight.promise);
			ownedFlight = null;
		}
	}

	$effect(() => {
		const args = source();

		untrack(() => {
			unregister();

			if (args === null) {
				abandonInFlight();
				generation++;
				loading = false;
				error = null;
				data = initial;
				currentKey = null;
				return;
			}

			const key = keyOf(args);
			currentKey = key;

			const fn = () => void run(args, key, { dedupe: false });
			registered = { key, fn };
			if (!live.has(key)) live.set(key, new Set());
			live.get(key)!.add(fn);

			void run(args, key, { dedupe: true });
		});
	});

	onDestroy(() => {
		abandonInFlight();
		generation++;
		unregister();
	});

	return {
		get data() { return data; },
		get loading() { return loading; },
		get error() { return error; },
		refresh() {
			const args = untrack(source);
			if (args !== null && currentKey !== null) void run(args, currentKey, { dedupe: false });
		},
	};
}
