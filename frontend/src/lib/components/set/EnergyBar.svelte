<script lang="ts">
	/**
	 * Energy as a filled bar — the one way every set-list layout draws it.
	 *
	 * The Spine used to render the zone *word* here while the Ledger and Inspector
	 * drew a bar, so the same fact looked like two different things depending on
	 * which layout you were in. `rowModel` already made the three agree about the
	 * numbers; this makes them agree about the mark.
	 */
	import { energyColor } from '$lib/utils/energy';

	let {
		energy,
		zone = null,
	}: {
		/** 0–1, or null when the track has no resolved energy. */
		energy: number | null;
		/** Zone name ("peak") — carried as the tooltip, not as the mark. */
		zone?: string | null;
	} = $props();

	let pct = $derived(energy == null ? 0 : Math.round(energy * 100));
	let title = $derived(
		energy == null ? 'No energy read for this track' : zone ? `${zone} · ${pct}%` : `${pct}%`,
	);
</script>

<span class="ebar" {title}>
	{#if energy != null}
		<i style="width:{pct}%;background:{energyColor(energy)}"></i>
	{/if}
</span>

<style>
	.ebar {
		height: 3px;
		border-radius: 2px;
		background: var(--surface-3);
		position: relative;
		overflow: hidden;
		display: block;
		width: 100%;
	}
	.ebar i {
		position: absolute;
		inset: 0 auto 0 0;
		display: block;
		border-radius: 2px;
	}
</style>
