<script lang="ts">
	import type { TransitionScoreBreakdown } from '$lib/types';
	import { getTransition } from '$lib/api/sets';
	import ScoreBreakdown from './ScoreBreakdown.svelte';

	interface Props {
		fromTrackId: number;
		toTrackId: number;
		score?: number;
		setId: number;
		transitionIndex: number;
	}

	let { fromTrackId, toTrackId, score, setId, transitionIndex }: Props = $props();

	let expanded = $state(false);
	let loading = $state(false);
	let breakdown = $state<TransitionScoreBreakdown | null>(null);
	let error = $state<string | null>(null);
	let displayScore = $derived(breakdown?.total ?? score ?? null);

	function scoreColor(s: number): string {
		if (s >= 0.8) return '#66BB6A';
		if (s >= 0.6) return '#FFB74D';
		if (s >= 0.4) return '#FF9800';
		return '#FF6B6B';
	}

	function scoreLabel(s: number): string {
		if (s >= 0.8) return 'Excellent';
		if (s >= 0.6) return 'Good';
		if (s >= 0.4) return 'Fair';
		return 'Poor';
	}

	async function fetchBreakdown() {
		if (breakdown || loading) return;
		loading = true;
		error = null;
		try {
			const detail = await getTransition(setId, transitionIndex);
			breakdown = detail.score_breakdown;
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load transition';
		} finally {
			loading = false;
		}
	}

	function handleClick() {
		expanded = !expanded;
		if (expanded && !breakdown) {
			fetchBreakdown();
		}
	}

	// Lazy-fetch breakdown if no pre-computed score is provided
	$effect(() => {
		if (score == null && !breakdown && !loading && !error) {
			fetchBreakdown();
		}
	});

	let tooltipDimensions = $derived(
		breakdown
			? [
					`Harmonic: ${breakdown.harmonic.toFixed(2)}`,
					`Energy: ${breakdown.energy_fit.toFixed(2)}`,
					`BPM: ${breakdown.bpm_compat.toFixed(2)}`,
					`Genre: ${breakdown.genre_coherence.toFixed(2)}`,
					`Quality: ${breakdown.track_quality.toFixed(2)}`,
				].join(' | ')
			: null
	);
</script>

<div class="transition-indicator" class:expanded>
	<button
		class="indicator-bar"
		style="--score-color: {displayScore != null ? scoreColor(displayScore) : 'var(--border)'}"
		onclick={handleClick}
		title={tooltipDimensions ?? (loading ? 'Loading...' : 'Click to expand')}
	>
		<div class="score-fill"></div>
		<span class="score-text">
			{#if loading && displayScore == null}
				...
			{:else if displayScore != null}
				{displayScore.toFixed(2)}
				<span class="score-quality">{scoreLabel(displayScore)}</span>
			{:else if error}
				--
			{/if}
		</span>
	</button>

	{#if expanded}
		<div class="breakdown-panel">
			{#if loading}
				<div class="breakdown-loading">Loading breakdown...</div>
			{:else if error}
				<div class="breakdown-error">{error}</div>
			{:else if breakdown}
				<ScoreBreakdown {breakdown} />
			{/if}
		</div>
	{/if}
</div>

<style>
	.transition-indicator {
		padding: 2px 0;
		display: flex;
		flex-direction: column;
		align-items: stretch;
	}

	.indicator-bar {
		display: flex;
		align-items: center;
		justify-content: center;
		position: relative;
		height: 24px;
		border: none;
		border-radius: 12px;
		background: var(--bg-tertiary);
		cursor: pointer;
		overflow: hidden;
		transition: box-shadow 0.15s;
		padding: 0;
	}

	.indicator-bar:hover {
		box-shadow: 0 0 0 1px var(--score-color);
	}

	.score-fill {
		position: absolute;
		inset: 0;
		background: var(--score-color);
		opacity: 0.2;
	}

	.score-text {
		position: relative;
		z-index: 1;
		font-size: 11px;
		font-weight: 600;
		font-variant-numeric: tabular-nums;
		color: var(--text-primary);
		display: flex;
		align-items: center;
		gap: 6px;
	}

	.score-quality {
		font-size: 10px;
		font-weight: 400;
		color: var(--text-secondary);
		text-transform: uppercase;
		letter-spacing: 0.5px;
	}

	.breakdown-panel {
		margin-top: 4px;
		animation: slide-down 0.15s ease-out;
	}

	.breakdown-loading,
	.breakdown-error {
		font-size: 11px;
		color: var(--text-dim);
		text-align: center;
		padding: 8px;
	}

	.breakdown-error {
		color: #FF6B6B;
	}

	@keyframes slide-down {
		from {
			opacity: 0;
			transform: translateY(-4px);
		}
		to {
			opacity: 1;
			transform: translateY(0);
		}
	}
</style>
