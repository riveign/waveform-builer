/**
 * Tests for createResource.
 *
 * This rune exists to make three bug classes unreachable (docs/notes/OBS-005/K3):
 * stale-response races, and stale reads after a write. Those are exactly the bugs
 * that are invisible in a browser unless you happen to type fast enough — so they
 * are the part of the frontend most worth testing rather than clicking.
 *
 * `createResource` uses `$effect` and `onDestroy`, so every case runs inside a real
 * component via a tiny harness.
 */

import { describe, expect, it, vi } from 'vitest';
import { flushSync, mount, unmount } from 'svelte';
import { createResource, invalidate, type Resource } from './resource.svelte';
import Harness from './resource.harness.svelte';

/** A promise you resolve by hand, so a test can control interleaving exactly. */
function deferred<T>() {
	let resolve!: (v: T) => void;
	let reject!: (e: unknown) => void;
	const promise = new Promise<T>((res, rej) => {
		resolve = res;
		reject = rej;
	});
	return { promise, resolve, reject };
}

/** Mount a resource inside a component and hand it back with a teardown. */
function mountResource<A, T>(
	source: () => A | null,
	fetcher: (a: A, signal: AbortSignal) => Promise<T>,
	options?: Parameters<typeof createResource<A, T>>[2],
) {
	const target = document.createElement('div');
	let res!: Resource<T>;
	const app = mount(Harness, {
		target,
		props: {
			build: () => {
				res = createResource(source, fetcher, options);
				return res;
			},
		},
	});
	flushSync();
	return { get res() { return res; }, destroy: () => unmount(app) };
}

const tick = () => new Promise((r) => setTimeout(r, 0));

describe('createResource', () => {
	it('starts loading and lands the value', async () => {
		const h = mountResource(() => 1, async () => 'ok');
		expect(h.res.loading).toBe(true);

		await tick();
		flushSync();

		expect(h.res.loading).toBe(false);
		expect(h.res.data).toBe('ok');
		expect(h.res.error).toBeNull();
		h.destroy();
	});

	it('reports an error message rather than throwing', async () => {
		const h = mountResource(() => 1, async () => {
			throw new Error('the library is mid-sync');
		});

		await tick();
		flushSync();

		expect(h.res.error).toBe('the library is mid-sync');
		expect(h.res.loading).toBe(false);
		h.destroy();
	});

	it('stays idle when the source is null, and fetches nothing', async () => {
		const fetcher = vi.fn(async () => 'never');
		const h = mountResource(() => null, fetcher);

		await tick();
		flushSync();

		expect(fetcher).not.toHaveBeenCalled();
		expect(h.res.loading).toBe(false);
		expect(h.res.data).toBeUndefined();
		h.destroy();
	});

	// ── The race this rune was built to kill ──────────────────────────────

	it('discards a slow response that a newer request has superseded', async () => {
		const slow = deferred<string>();
		const fast = deferred<string>();
		let call = 0;
		let id = $state(1);

		const h = mountResource(
			() => id,
			async () => (++call === 1 ? slow.promise : fast.promise),
		);

		// Second request starts before the first has answered.
		id = 2;
		flushSync();

		// The newer one answers first, then the stale one arrives late.
		fast.resolve('second');
		await tick();
		slow.resolve('first');
		await tick();
		flushSync();

		expect(h.res.data).toBe('second');
		expect(h.res.data).not.toBe('first');
		h.destroy();
	});

	it('aborts the superseded request', async () => {
		const seen: AbortSignal[] = [];
		let id = $state(1);
		const h = mountResource(
			() => id,
			(_a, signal) => {
				seen.push(signal);
				return new Promise<string>(() => {});
			},
		);

		id = 2;
		flushSync();

		expect(seen).toHaveLength(2);
		expect(seen[0].aborted).toBe(true);
		expect(seen[1].aborted).toBe(false);
		h.destroy();
	});

	it('aborts in flight when the component goes away', async () => {
		let captured!: AbortSignal;
		const h = mountResource(() => 'unmount-case', (_a, signal) => {
			captured = signal;
			return new Promise<string>(() => {});
		});

		// Effects run in a microtask, so let the request actually start before
		// pulling the component out from under it.
		await tick();
		expect(captured.aborted).toBe(false);

		h.destroy();

		expect(captured.aborted).toBe(true);
	});

	it('does not write after the component is gone', async () => {
		const d = deferred<string>();
		const h = mountResource(() => 'late-write-case', () => d.promise);

		h.destroy();
		d.resolve('too late');
		await tick();

		// Nothing to assert on the destroyed instance beyond "this did not throw":
		// an unguarded write here is the classic post-unmount state update.
		expect(h.res.data).toBeUndefined();
	});

	// ── De-duplication ────────────────────────────────────────────────────

	it('shares one flight between concurrent resources on the same key', async () => {
		const fetcher = vi.fn(async () => 'shared');
		const opts = { key: () => 'same' };

		const a = mountResource(() => 1, fetcher, opts);
		const b = mountResource(() => 1, fetcher, opts);

		await tick();
		flushSync();

		expect(fetcher).toHaveBeenCalledTimes(1);
		expect(a.res.data).toBe('shared');
		expect(b.res.data).toBe('shared');
		a.destroy();
		b.destroy();
	});

	it('does NOT share a flight between sequential callers — the documented limit', async () => {
		// docs/notes/OBS-005/K3(b): de-duplication only merges requests in flight at
		// the same moment. Closing this needs a cache with a lifetime, which P5
		// deliberately did not add. Pinned here so the limit is a decision, not a
		// surprise.
		const fetcher = vi.fn(async () => 'x');
		const opts = { key: () => 'same' };

		const a = mountResource(() => 1, fetcher, opts);
		await tick();
		flushSync();
		a.destroy();

		const b = mountResource(() => 1, fetcher, opts);
		await tick();
		flushSync();

		expect(fetcher).toHaveBeenCalledTimes(2);
		b.destroy();
	});

	// ── Invalidation ──────────────────────────────────────────────────────

	it('refetches every live resource under an invalidated prefix', async () => {
		let n = 0;
		const fetcher = async () => `v${++n}`;
		const h = mountResource(() => 1, fetcher, { key: () => 'sets:list:active' });

		await tick();
		flushSync();
		expect(h.res.data).toBe('v1');

		invalidate('sets:list');
		await tick();
		flushSync();

		expect(h.res.data).toBe('v2');
		h.destroy();
	});

	it('leaves resources under other prefixes alone', async () => {
		const other = vi.fn(async () => 'untouched');
		const h = mountResource(() => 1, other, { key: () => 'tracks:1' });

		await tick();
		flushSync();
		invalidate('sets:list');
		await tick();
		flushSync();

		expect(other).toHaveBeenCalledTimes(1);
		h.destroy();
	});

	it('stops notifying a destroyed resource', async () => {
		const fetcher = vi.fn(async () => 'x');
		const h = mountResource(() => 1, fetcher, { key: () => 'sets:list' });
		await tick();
		flushSync();
		h.destroy();

		invalidate('sets:list');
		await tick();

		expect(fetcher).toHaveBeenCalledTimes(1);
	});

	// ── keepPrevious ──────────────────────────────────────────────────────

	it('blanks the previous value by default when the subject changes', async () => {
		let id = $state(1);
		const h = mountResource(() => id, async (n) => `value ${n}`);
		await tick();
		flushSync();
		expect(h.res.data).toBe('value 1');

		id = 2;
		flushSync();
		expect(h.res.data).toBeUndefined();
		h.destroy();
	});

	it('holds the previous value while refetching when asked', async () => {
		// What stops a list flickering as the DJ retypes a search.
		let q = $state('a');
		const h = mountResource(() => q, async (s) => `results for ${s}`, { keepPrevious: true });
		await tick();
		flushSync();

		q = 'ab';
		flushSync();

		expect(h.res.data).toBe('results for a');
		await tick();
		flushSync();
		expect(h.res.data).toBe('results for ab');
		h.destroy();
	});
});
