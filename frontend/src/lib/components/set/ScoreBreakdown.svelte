<script lang="ts">
	import type { TransitionScoreBreakdown } from '$lib/types';

	let { breakdown }: { breakdown: TransitionScoreBreakdown } = $props();

	const dimensions = [
		{ key: 'harmonic' as const, label: 'Harmonic', weight: 0.25, color: '#9b59b6' },
		{ key: 'energy_fit' as const, label: 'Energy Fit', weight: 0.20, color: '#e94560' },
		{ key: 'bpm_compat' as const, label: 'BPM', weight: 0.20, color: '#00bcd4' },
		{ key: 'genre_coherence' as const, label: 'Genre', weight: 0.15, color: '#2ecc71' },
		{ key: 'track_quality' as const, label: 'Quality', weight: 0.20, color: '#f39c12' },
	];
</script>

<div class="score-breakdown">
	<div class="total-score">
		<span class="total-label">Score</span>
		<span class="total-value">{breakdown.total.toFixed(3)}</span>
	</div>
	<div class="dimensions">
		{#each dimensions as dim}
			{@const value = breakdown[dim.key]}
			<div class="dim-row">
				<span class="dim-label">{dim.label}</span>
				<div class="dim-bar">
					<div
						class="dim-fill"
						style="width: {value * 100}%; background: {dim.color}"
					></div>
				</div>
				<span class="dim-value">{value.toFixed(2)}</span>
				<span class="dim-weight">x{dim.weight}</span>
			</div>
		{/each}
	</div>
</div>

<style>
	.score-breakdown {
		background: var(--bg-secondary);
		border-radius: 6px;
		padding: 12px;
	}

	.total-score {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 10px;
		padding-bottom: 8px;
		border-bottom: 1px solid var(--border);
	}

	.total-label {
		font-size: 12px;
		text-transform: uppercase;
		letter-spacing: 0.5px;
		color: var(--text-secondary);
	}

	.total-value {
		font-size: 20px;
		font-weight: 700;
		color: var(--accent);
		font-variant-numeric: tabular-nums;
	}

	.dimensions {
		display: flex;
		flex-direction: column;
		gap: 6px;
	}

	.dim-row {
		display: flex;
		align-items: center;
		gap: 8px;
	}

	.dim-label {
		width: 70px;
		font-size: 11px;
		color: var(--text-secondary);
		flex-shrink: 0;
	}

	.dim-bar {
		flex: 1;
		height: 6px;
		background: var(--bg-tertiary);
		border-radius: 3px;
		overflow: hidden;
	}

	.dim-fill {
		height: 100%;
		border-radius: 3px;
		transition: width 0.3s;
	}

	.dim-value {
		width: 32px;
		text-align: right;
		font-size: 11px;
		font-variant-numeric: tabular-nums;
		color: var(--text-primary);
	}

	.dim-weight {
		width: 28px;
		text-align: right;
		font-size: 10px;
		color: var(--text-dim);
	}
</style>
