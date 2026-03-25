<script lang="ts">
	import type { TransitionScoreBreakdown } from '$lib/types';
	import { harmonicRelationship } from '$lib/utils/camelot';

	let {
		breakdown,
		keyA = null,
		keyB = null,
	}: {
		breakdown: TransitionScoreBreakdown;
		keyA?: string | null;
		keyB?: string | null;
	} = $props();

	const TEACHING: Record<string, [string, string, string]> = {
		harmonic:        ["Keys align naturally", "Some harmonic tension", "Clashing keys — bold move"],
		energy_fit:      ["Right on the energy curve", "Drifting from your target", "Sharp energy jump"],
		bpm_compat:      ["Seamless tempo", "Slight tempo shift", "Big tempo change"],
		genre_coherence: ["Same sonic world", "Crossing genre boundaries", "Genre clash — make it count"],
		track_quality:   ["Well-curated pick", "Decent selection", "Under-played — give it a chance"],
	};

	function getTeachingNote(key: string, value: number): string {
		// For harmonic, use the richer relationship description if keys are available
		if (key === 'harmonic' && (keyA || keyB)) {
			return harmonicRelationship(keyA, keyB).description;
		}
		const [high, mid, low] = TEACHING[key] ?? ["", "", ""];
		if (value >= 0.8) return high;
		if (value >= 0.5) return mid;
		return low;
	}

	const dimensions = [
		{ key: 'harmonic' as const, label: 'Harmonic', weight: 0.25, color: '#9575CD' },
		{ key: 'energy_fit' as const, label: 'Energy Fit', weight: 0.20, color: '#FF7F50' },
		{ key: 'bpm_compat' as const, label: 'BPM', weight: 0.20, color: '#40E0D0' },
		{ key: 'genre_coherence' as const, label: 'Genre', weight: 0.15, color: '#66BB6A' },
		{ key: 'track_quality' as const, label: 'Quality', weight: 0.20, color: '#FFB74D' },
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
			<div class="dim-group">
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
				<div class="dim-note">{getTeachingNote(dim.key, value)}</div>
			</div>
		{/each}
	</div>
	{#if breakdown.discovery_label}
		<div class="discovery-badge">
			<span class="discovery-icon">&#9679;</span>
			<span class="discovery-text">{breakdown.discovery_label}</span>
			{#if breakdown.set_appearances != null && breakdown.set_appearances > 0}
				<span class="discovery-detail">&middot; in {breakdown.set_appearances} set{breakdown.set_appearances > 1 ? 's' : ''}</span>
			{/if}
		</div>
	{/if}
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
		gap: 10px;
	}

	.dim-group {
		display: flex;
		flex-direction: column;
		gap: 2px;
	}

	.dim-note {
		font-size: 10px;
		color: var(--text-dim);
		padding-left: 78px;
		font-style: italic;
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

	.discovery-badge {
		display: flex;
		align-items: center;
		gap: 5px;
		margin-top: 8px;
		padding: 6px 10px;
		background: var(--bg-tertiary);
		border-radius: 4px;
		font-size: 11px;
	}

	.discovery-icon {
		color: var(--accent);
		font-size: 8px;
	}

	.discovery-text {
		color: var(--accent);
		font-weight: 500;
		text-transform: capitalize;
	}

	.discovery-detail {
		color: var(--text-dim);
	}
</style>
