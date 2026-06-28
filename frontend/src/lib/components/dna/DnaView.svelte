<script lang="ts">
	import TasteRadar from './TasteRadar.svelte';
	import CamelotWheel from './CamelotWheel.svelte';
	import BpmHistogram from './BpmHistogram.svelte';
	import GenreDistribution from './GenreDistribution.svelte';
	import EnergyGenreHeatmap from './EnergyGenreHeatmap.svelte';
	import MoodScatter from './MoodScatter.svelte';
	import LibraryGaps from './LibraryGaps.svelte';
</script>

<div class="dna-view">
	<div class="dna-header">
		<h2 class="dna-title">Taste DNA</h2>
		<p class="dna-subtitle">Your library's musical fingerprint</p>
	</div>

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
</div>

<style>
	.dna-view {
		display: flex;
		flex-direction: column;
		flex: 1;
		min-height: 0;
		overflow: hidden;
	}

	/* Pinned top band — title/subtitle stay put while charts scroll beneath. */
	.dna-header {
		flex-shrink: 0;
		padding: var(--space-lg) 20px;
		border-bottom: 1px solid var(--border);
		background: var(--surface-1);
	}

	/* Sole scroller — the chart grid scrolls inside the bounded frame. */
	.dna-scroll {
		flex: 1;
		min-height: 0;
		overflow-y: auto;
		padding: 20px;
		container-type: inline-size; /* query container for the chart card grid reflow */
	}

	.dna-title {
		font-size: 20px;
		font-weight: 700;
		color: var(--text-primary);
		margin-bottom: 4px;
	}

	.dna-subtitle {
		font-size: 13px;
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
