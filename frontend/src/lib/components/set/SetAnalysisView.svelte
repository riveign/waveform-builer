<script lang="ts">
	import type { SetAnalysis } from '$lib/types';
	import ScoreBreakdown from './ScoreBreakdown.svelte';

	interface Props {
		analysis: SetAnalysis;
	}

	let { analysis }: Props = $props();

	function scoreColor(score: number): string {
		if (score >= 0.7) return 'var(--color-success, #66BB6A)';
		if (score >= 0.5) return 'var(--color-warning, #FFA726)';
		return 'var(--color-error, #EF5350)';
	}

	const shapeLabels: Record<string, string> = {
		'flat': 'Steady energy \u2014 hypnotic vibe',
		'ramp-up': 'Building energy \u2014 classic journey',
		'wind-down': 'Front-loaded energy \u2014 bold opener',
		'peak-valley': 'Peak then valley \u2014 dramatic arc',
		'roller-coaster': 'Multiple peaks \u2014 dynamic ride',
		'journey': 'Natural flow \u2014 organic energy',
		'too-short': 'Too short to classify',
	};

	const keyLabels: Record<string, string> = {
		'home-key': 'Staying close \u2014 deep harmonic focus',
		'adventurous': 'Exploring the wheel \u2014 wide key range',
		'chromatic-walk': 'Gradual movement \u2014 chromatic walk',
		'unknown': 'Not enough key data',
	};

	const bpmLabels: Record<string, string> = {
		'steady': 'Locked tempo \u2014 consistent groove',
		'gradual-build': 'Building tempo \u2014 rising energy',
		'gradual-drop': 'Dropping tempo \u2014 winding down',
		'volatile': 'Tempo jumps \u2014 dynamic pacing',
		'gentle-drift': 'Gentle tempo drift',
		'unknown': 'Not enough BPM data',
	};

	let expandedTransition = $state<number | null>(null);

	function toggleTransition(pos: number) {
		expandedTransition = expandedTransition === pos ? null : pos;
	}
</script>

<div class="analysis-view">
	<!-- Overall Score -->
	<div class="overall-section">
		<div class="overall-score" style="color: {scoreColor(analysis.overall_score)}">
			{analysis.overall_score.toFixed(3)}
		</div>
		<div class="overall-label">
			{analysis.track_count} tracks &middot; {analysis.transition_count} transitions
		</div>
	</div>

	<!-- Arc Summary -->
	<div class="arc-section">
		<h3>Set Arc</h3>
		<div class="arc-grid">
			<div class="arc-item">
				<span class="arc-label">Energy</span>
				<span class="arc-value">{shapeLabels[analysis.arc.energy_shape] ?? analysis.arc.energy_shape}</span>
			</div>
			<div class="arc-item">
				<span class="arc-label">Keys</span>
				<span class="arc-value">{keyLabels[analysis.arc.key_style] ?? analysis.arc.key_style}</span>
			</div>
			<div class="arc-item">
				<span class="arc-label">BPM</span>
				<span class="arc-value">
					{bpmLabels[analysis.arc.bpm_style] ?? analysis.arc.bpm_style}
					{#if analysis.arc.bpm_range[0] > 0}
						({analysis.arc.bpm_range[0].toFixed(0)}\u2013{analysis.arc.bpm_range[1].toFixed(0)})
					{/if}
				</span>
			</div>
			{#if analysis.arc.genre_segments.length > 1}
				<div class="arc-item">
					<span class="arc-label">Genre Flow</span>
					<span class="arc-value">
						{analysis.arc.genre_segments.map((s) => s.genre_family).join(' \u2192 ')}
					</span>
				</div>
			{/if}
		</div>
	</div>

	<!-- Set Patterns -->
	{#if analysis.set_patterns.length > 0}
		<div class="patterns-section">
			<h3>What your ear tells us</h3>
			{#each analysis.set_patterns as pattern}
				<p class="pattern">{pattern}</p>
			{/each}
		</div>
	{/if}

	<!-- Transitions -->
	<div class="transitions-section">
		<h3>Transitions</h3>
		{#each analysis.transitions as t}
			<button
				class="transition-row"
				class:weak={t.scores.total < 0.5}
				class:strong={t.scores.total >= 0.7}
				onclick={() => toggleTransition(t.position)}
			>
				<span class="t-pos">{t.position + 1}</span>
				<span class="t-score" style="color: {scoreColor(t.scores.total)}">
					{t.scores.total.toFixed(3)}
				</span>
				<span class="t-teaching">{t.teaching_moment}</span>
			</button>
			{#if expandedTransition === t.position}
				<div class="transition-detail">
					<ScoreBreakdown breakdown={t.scores} />
					{#if t.suggestion}
						<div class="suggestion">{t.suggestion}</div>
					{/if}
				</div>
			{/if}
		{/each}
	</div>

	<div class="analyzed-at">
		Analyzed {new Date(analysis.analyzed_at).toLocaleString()}
	</div>
</div>

<style>
	.analysis-view {
		display: flex;
		flex-direction: column;
		gap: 20px;
		padding: 16px;
	}

	.overall-section {
		text-align: center;
		padding: 16px;
		background: var(--bg-secondary);
		border-radius: 8px;
	}

	.overall-score {
		font-size: 36px;
		font-weight: 700;
		font-variant-numeric: tabular-nums;
	}

	.overall-label {
		font-size: 13px;
		color: var(--text-secondary);
		margin-top: 4px;
	}

	h3 {
		font-size: 14px;
		text-transform: uppercase;
		letter-spacing: 0.5px;
		color: var(--text-secondary);
		margin: 0 0 12px;
	}

	.arc-section {
		background: var(--bg-secondary);
		border-radius: 8px;
		padding: 16px;
	}

	.arc-grid {
		display: flex;
		flex-direction: column;
		gap: 8px;
	}

	.arc-item {
		display: flex;
		justify-content: space-between;
		align-items: center;
	}

	.arc-label {
		font-size: 12px;
		color: var(--text-secondary);
		min-width: 60px;
	}

	.arc-value {
		font-size: 12px;
		color: var(--text-primary);
		text-align: right;
	}

	.patterns-section {
		background: var(--bg-secondary);
		border-radius: 8px;
		padding: 16px;
	}

	.pattern {
		font-size: 13px;
		color: var(--text-primary);
		margin: 6px 0;
		line-height: 1.5;
		font-style: italic;
	}

	.transitions-section {
		display: flex;
		flex-direction: column;
		gap: 2px;
	}

	.transition-row {
		display: flex;
		align-items: center;
		gap: 10px;
		padding: 8px 12px;
		background: var(--bg-secondary);
		border: 1px solid transparent;
		border-radius: 4px;
		cursor: pointer;
		text-align: left;
		width: 100%;
		font-family: inherit;
		font-size: inherit;
		color: inherit;
	}

	.transition-row:hover {
		border-color: var(--border);
	}

	.transition-row.weak {
		border-left: 3px solid var(--color-error, #EF5350);
	}

	.transition-row.strong {
		border-left: 3px solid var(--color-success, #66BB6A);
	}

	.t-pos {
		width: 24px;
		font-size: 11px;
		color: var(--text-dim);
		text-align: right;
		flex-shrink: 0;
	}

	.t-score {
		width: 48px;
		font-weight: 600;
		font-variant-numeric: tabular-nums;
		flex-shrink: 0;
	}

	.t-teaching {
		font-size: 12px;
		color: var(--text-primary);
		flex: 1;
	}

	.transition-detail {
		padding: 12px 12px 12px 46px;
		background: var(--bg-tertiary);
		border-radius: 0 0 4px 4px;
		margin-top: -2px;
	}

	.suggestion {
		margin-top: 10px;
		padding: 8px 12px;
		background: var(--bg-secondary);
		border-left: 3px solid var(--accent);
		border-radius: 2px;
		font-size: 12px;
		color: var(--text-secondary);
		font-style: italic;
	}

	.analyzed-at {
		font-size: 11px;
		color: var(--text-dim);
		text-align: right;
	}
</style>
