<script module lang="ts">
	/**
	 * Track ids the server has already answered 404 for, for this page load.
	 *
	 * Only ~17% of the library's albums resolve to a cover, so most of these
	 * requests are asking a question we already know the answer to. Worse, the
	 * three set-list layouts remount every cover when the DJ toggles between
	 * them, so without this a flick through Ledger → Spine → Inspect re-asks the
	 * same 47 questions three times.
	 *
	 * Module scope, not per-component: the point is that it outlives the row.
	 * Deliberately not persisted — a cover the DJ resolves in another tab should
	 * appear on the next load, not stay hidden by yesterday's answer.
	 */
	const noArtwork = new Set<number>();
</script>

<script lang="ts">
	import { getTrackArtworkUrl } from '$lib/api/tracks';

	let {
		trackId,
		camelot = null,
		keyColor = 'var(--surface-3)',
		size = 26,
	}: {
		trackId: number;
		/** Camelot code shown when there is no cover — see the fallback note below. */
		camelot?: string | null;
		keyColor?: string;
		size?: number;
	} = $props();

	let el = $state<HTMLElement | undefined>();
	/** The row has scrolled close enough to be worth asking about. */
	let near = $state(false);
	let loaded = $state(false);
	/** This mount's own 404. `noArtwork` is a plain Set and so not reactive — it
	    is how the NEXT mount skips the request; this is how this one stops. */
	let errored = $state(false);
	let skip = $derived(errored || noArtwork.has(trackId));

	$effect(() => {
		trackId;
		loaded = false;
		errored = false;
	});

	/**
	 * Ask for a cover only once its row approaches the viewport.
	 *
	 * `loading="lazy"` alone was not enough: it defers by proximity, but a set
	 * view renders every row at once, so a long set still fired dozens of
	 * requests. Each miss walks CoverArtArchive → iTunes → Deezer before the
	 * server can stamp its "no cover" sentinel, and six-connections-per-origin
	 * turns that into a queue — a cold headless load stalled past 30s. Warm it is
	 * 2–9ms. So: observe, and ask only for what the DJ is actually looking at.
	 */
	$effect(() => {
		if (!el || near) return;
		// No IntersectionObserver (older browsers, some test environments) means
		// falling back to eager loading rather than never showing a cover at all.
		if (typeof IntersectionObserver === 'undefined') {
			near = true;
			return;
		}
		const io = new IntersectionObserver(
			(entries) => {
				if (entries.some((e) => e.isIntersecting)) {
					near = true;
					io.disconnect();
				}
			},
			// A screen's worth of lead time, so covers are there by the time the
			// row is — scrolling should not look like it is waiting for the network.
			{ rootMargin: '400px 0px' },
		);
		io.observe(el);
		return () => io.disconnect();
	});
</script>

<!--
  Only ~17% of the library's albums have a resolved cover, so the fallback is the
  common case, not the exception. Rather than a grey blank, it carries the Camelot
  code on the key's own colour — the row stays readable at a glance, and the
  missing artwork turns into a harmonic cue instead of a hole.

  The fallback is therefore what renders first and always; a cover that resolves
  fades in over it. That way the row never flashes empty waiting for a request
  that will most likely 404.
-->
<span
	bind:this={el}
	class="cover"
	class:covered={loaded}
	style="width:{size}px;height:{size}px;background:{camelot ? keyColor : 'var(--surface-3)'};font-size:{Math.round(size * 0.34)}px"
>
	<span class="code" aria-hidden="true">{camelot ?? ''}</span>
	{#if near && !skip && trackId}
		<img
			class="art"
			class:shown={loaded}
			src={getTrackArtworkUrl(trackId)}
			alt=""
			loading="lazy"
			onload={() => { loaded = true; }}
			onerror={() => { noArtwork.add(trackId); errored = true; loaded = false; }}
		/>
	{/if}
</span>

<style>
	.cover {
		position: relative;
		flex-shrink: 0;
		border-radius: 2px;
		display: inline-flex;
		align-items: center;
		justify-content: center;
		overflow: hidden;
	}

	.code {
		font-family: var(--font-mono, ui-monospace, monospace);
		font-weight: var(--font-weight-semibold);
		/* The key colours are light tints, so the code sits on them in ink. */
		color: #0d0d0d;
		letter-spacing: -0.02em;
		line-height: 1;
	}

	.art {
		position: absolute;
		inset: 0;
		width: 100%;
		height: 100%;
		object-fit: cover;
		opacity: 0;
		transition: opacity 0.15s;
	}
	.art.shown { opacity: 1; }

	/* Once a cover is up, the code beneath it must not bleed through its edges. */
	.covered .code { visibility: hidden; }
</style>
