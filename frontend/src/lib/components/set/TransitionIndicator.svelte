<script lang="ts">
	import type { TransitionScoreBreakdown } from '$lib/types';
	import { getTransition } from '$lib/api/sets';

	interface Props {
		fromTrackId: number;
		toTrackId: number;
		score?: number;
		analysisScore?: number;
		teachingMoment?: string;
		setId: number;
		transitionIndex: number;
		active?: boolean;
		onclick?: (index: number) => void;
	}

	let { fromTrackId, toTrackId, score, analysisScore, teachingMoment, setId, transitionIndex, active = false, onclick }: Props = $props();

	let loading = $state(false);
	let breakdown = $state<TransitionScoreBreakdown | null>(null);
	let error = $state<string | null>(null);
	let builderScore = $derived(breakdown?.total ?? score ?? null);
	let displayScore = $derived(analysisScore ?? builderScore);
	let hasDualScores = $derived(analysisScore != null && builderScore != null);

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
		onclick?.(transitionIndex);
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

<div class="transition-indicator" class:active>
	<button
		class="indicator-bar"
		style="--score-color: {displayScore != null ? scoreColor(displayScore) : 'var(--border)'}"
		onclick={handleClick}
		title={tooltipDimensions ?? (loading ? 'Loading...' : 'Click to inspect transition')}
	>
		<div class="score-fill"></div>
		<span class="score-text">
			{#if loading && displayScore == null}
				...
			{:else if displayScore != null}
				{#if hasDualScores}
					<span class="builder-score" style="color: {scoreColor(builderScore!)}">
						<span class="score-label">build</span>{builderScore!.toFixed(2)}
					</span>
					<span class="score-separator">/</span>
					<span class="analysis-score" style="color: {scoreColor(analysisScore!)}">
						{analysisScore!.toFixed(2)}<span class="score-label">ctx</span>
					</span>
				{:else}
					<span>{displayScore.toFixed(2)}</span>
				{/if}
				<span class="score-quality">{scoreLabel(displayScore)}</span>
				{#if teachingMoment}
					<span class="teaching-moment">{teachingMoment}</span>
				{/if}
			{:else if error}
				--
			{/if}
		</span>
	</button>
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

	.active .indicator-bar {
		box-shadow: 0 0 0 2px var(--accent, var(--score-color));
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

	.builder-score,
	.analysis-score {
		display: flex;
		align-items: center;
		gap: 3px;
		font-size: 11px;
		font-weight: 600;
		font-variant-numeric: tabular-nums;
	}

	.score-label {
		font-size: 8px;
		font-weight: 500;
		text-transform: uppercase;
		letter-spacing: 0.3px;
		opacity: 0.6;
	}

	.score-separator {
		font-size: 9px;
		color: var(--text-dim);
		opacity: 0.3;
		margin: 0 1px;
	}

	.score-quality {
		font-size: 10px;
		font-weight: 400;
		color: var(--text-secondary);
		text-transform: uppercase;
		letter-spacing: 0.5px;
	}

	.teaching-moment {
		font-size: 10px;
		font-weight: 400;
		color: var(--text-dim);
		margin-left: 4px;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
		max-width: 300px;
	}
</style>
