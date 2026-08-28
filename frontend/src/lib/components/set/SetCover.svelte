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

	let failed = $state(false);

	$effect(() => {
		trackId;
		failed = false;
	});
</script>

<!--
  Only ~17% of the library's albums have a resolved cover, so the fallback is the
  common case, not the exception. Rather than a grey blank, it carries the Camelot
  code on the key's own colour — the row stays readable at a glance, and the
  missing artwork turns into a harmonic cue instead of a hole.
-->
{#if failed || !trackId}
	<span
		class="cover fallback"
		style="width:{size}px;height:{size}px;background:{camelot ? keyColor : 'var(--surface-3)'};font-size:{Math.round(size * 0.34)}px"
		aria-hidden="true"
	>{camelot ?? ''}</span>
{:else}
	<img
		class="cover"
		style="width:{size}px;height:{size}px"
		src={getTrackArtworkUrl(trackId)}
		alt=""
		loading="lazy"
		onerror={() => { failed = true; }}
	/>
{/if}

<style>
	.cover {
		flex-shrink: 0;
		border-radius: 2px;
		object-fit: cover;
		background: var(--surface-3);
		display: block;
	}

	.fallback {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		font-family: var(--font-mono, ui-monospace, monospace);
		font-weight: var(--font-weight-semibold);
		/* The key colours are light tints, so the code sits on them in ink. */
		color: #0d0d0d;
		letter-spacing: -0.02em;
		line-height: 1;
	}
</style>
