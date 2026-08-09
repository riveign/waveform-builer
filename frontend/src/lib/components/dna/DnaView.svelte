<script lang="ts">
	import TasteRadar from './TasteRadar.svelte';
	import CamelotWheel from './CamelotWheel.svelte';
	import BpmHistogram from './BpmHistogram.svelte';
	import GenreDistribution from './GenreDistribution.svelte';
	import EnergyGenreHeatmap from './EnergyGenreHeatmap.svelte';
	import MoodScatter from './MoodScatter.svelte';
	import LibraryGaps from './LibraryGaps.svelte';
	import Spinner from '$lib/components/Spinner.svelte';
	import { getLibraryStats } from '$lib/api/stats';
	import { createResource } from '$lib/data/resource.svelte';

	// A fingerprint needs enough analyzed tracks to mean anything — below this
	// the charts would read as noise, so we show a warm "too quiet" empty state.
	const MIN_ANALYZED = 20;

	// Same key as GenreDistribution, but they do not actually share a flight: this
	// view gates its children behind its own load, and de-duplication cannot help
	// sequential callers. See resource.svelte.ts.
	const res = createResource(() => ({}), (_a, signal) => getLibraryStats(signal), {
		key: () => 'stats:library',
	});
	const loading = $derived(res.loading);
	const error = $derived(
		res.error
			? "Couldn't read your library to draw its fingerprint. The library may be mid-sync — give it a moment and try again."
			: null,
	);
	const analyzed = $derived(res.data?.analyzed_tracks ?? 0);

</script>

<div class="dna-view">
	<div class="dna-header">
		<h2 class="dna-title">Taste DNA</h2>
		<p class="dna-subtitle">Your library's musical fingerprint</p>
	</div>

	{#if loading}
		<div class="dna-state">
			<Spinner label="Reading your library's fingerprint..." />
		</div>
	{:else if error}
		<div class="dna-state" role="alert">
			<p class="dna-state-msg dna-state-error">{error}</p>
		</div>
	{:else if analyzed < MIN_ANALYZED}
		<div class="dna-state">
			<p class="dna-state-msg">
				Your library's still too quiet to read a fingerprint. Analyze more tracks and the
				shape of your taste will start to show.
			</p>
		</div>
	{:else}
		<div class="dna-scroll">
			<div class="dna-hero">
				<TasteRadar />
			</div>

			<div class="dna-grid grid-12 grid-12--content">
				<div class="dna-card">
					<CamelotWheel />
				</div>
				<div class="dna-card">
					<BpmHistogram />
				</div>
				<div class="dna-card">
					<GenreDistribution />
				</div>
				<div class="dna-card">
					<EnergyGenreHeatmap />
				</div>
				<div class="dna-card">
					<MoodScatter />
				</div>
				<div class="dna-card">
					<LibraryGaps />
				</div>
			</div>
		</div>
	{/if}
</div>

<style>
	.dna-view {
		display: flex;
		flex-direction: column;
		flex: 1;
		min-height: 0;
		overflow: hidden;
	}

	/* Sticky toolbar band — matches the Set tab's band rhythm (audit 003 §2.1).
	   Stays pinned beneath the navbar while the chart grid scrolls under it. */
	.dna-header {
		display: flex;
		flex-direction: column;
		justify-content: center;
		height: var(--band-toolbar-h);
		padding: 0 var(--space-xl);
		border-bottom: 1px solid var(--border);
		position: sticky;
		top: 0;
		z-index: 5;
		background: var(--bg-primary);
	}

	/* Sole scroller — the chart grid scrolls inside the bounded frame. */
	.dna-scroll {
		flex: 1;
		min-height: 0;
		overflow-y: auto;
		padding: var(--space-xl);
		container-type: inline-size; /* query container for the chart card grid reflow */
	}

	.dna-title {
		font-size: 16px;
		font-weight: 700;
		color: var(--text-primary);
	}

	.dna-subtitle {
		font-size: 12px;
		color: var(--text-secondary);
	}

	/* Full-pane loading / empty / error states, centered in the scroll area. */
	.dna-state {
		flex: 1;
		min-height: 0;
		display: flex;
		align-items: center;
		justify-content: center;
		padding: var(--space-2xl);
	}

	.dna-state-msg {
		max-width: 42ch;
		text-align: center;
		font-size: 14px;
		line-height: 1.5;
		color: var(--text-secondary);
	}

	.dna-state-error {
		color: var(--text-secondary);
	}

	.dna-hero {
		margin-bottom: 16px;
	}

	/* 12-col content grid: secondary chart cards span 6 (2-up) at full width,
	   reflowing to 1-up via container query. The hero radar sits in .dna-hero
	   above, full width. */
	.dna-card {
		min-width: 0;
		grid-column: span 6; /* 2-up */
	}

	@container (max-width: 640px) {
		.dna-card {
			grid-column: span 12; /* 1-up */
		}
	}
</style>
