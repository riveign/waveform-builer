<script lang="ts">
	import type { SetComparison, TrackDeviation } from '$lib/types';

	let {
		comparison,
		onback,
	}: {
		comparison: SetComparison;
		onback: () => void;
	} = $props();

	const KIND_COLORS: Record<string, string> = {
		kept: '#66BB6A',
		moved: '#FFB74D',
		cut: '#EF5350',
		added: '#4FC3F7',
	};

	let plannedSide = $derived(
		comparison.track_deviations
			.filter((d) => d.planned_position !== null)
			.sort((a, b) => (a.planned_position ?? 0) - (b.planned_position ?? 0))
	);

	let playedSide = $derived(
		comparison.track_deviations
			.filter((d) => d.played_position !== null)
			.sort((a, b) => (a.played_position ?? 0) - (b.played_position ?? 0))
	);

	let teachingDeviations = $derived(
		comparison.track_deviations.filter((d) => d.kind !== 'kept')
	);

	function badgeLabel(d: TrackDeviation): string {
		if (d.kind === 'moved' && d.displacement !== null) {
			return d.displacement > 0 ? `moved +${d.displacement}` : `moved ${d.displacement}`;
		}
		return d.kind;
	}
</script>

<div class="comparison">
	<div class="comparison-header">
		<button class="back-btn" onclick={onback}>&larr; Timeline</button>
		<span class="title">Planned vs played</span>
		<span class="count" style="color: {KIND_COLORS.kept}">{comparison.kept_count} kept</span>
		<span class="count" style="color: {KIND_COLORS.moved}">{comparison.moved_count} moved</span>
		<span class="count" style="color: {KIND_COLORS.cut}">{comparison.cut_count} cut</span>
		<span class="count" style="color: {KIND_COLORS.added}">{comparison.added_count} added</span>
	</div>

	<div class="arc-row">
		<span class="arc-chip">arc: {comparison.arc.planned_shape} &rarr; {comparison.arc.played_shape}</span>
		<span class="arc-chip">keys: {comparison.arc.planned_key_style} &rarr; {comparison.arc.played_key_style}</span>
		<span class="arc-chip">bpm: {comparison.arc.planned_bpm_style} &rarr; {comparison.arc.played_bpm_style}</span>
	</div>

	<div class="two-col">
		<div class="col">
			<h3>Planned — {comparison.planned_name ?? 'plan'}</h3>
			{#each plannedSide as d (d.kind + '-' + d.track_id + '-' + d.planned_position)}
				<div class="dev-row" class:dimmed={d.kind === 'cut'}>
					<span class="pos">{(d.planned_position ?? 0) + 1}</span>
					<span class="track-title">{d.title ?? `Track ${d.track_id}`}</span>
					<span class="badge" style="background: {KIND_COLORS[d.kind]}22; color: {KIND_COLORS[d.kind]}">{badgeLabel(d)}</span>
				</div>
			{/each}
		</div>
		<div class="col">
			<h3>Played — {comparison.played_name ?? 'set'}</h3>
			{#each playedSide as d (d.kind + '-' + d.track_id + '-' + d.played_position)}
				<div class="dev-row">
					<span class="pos">{(d.played_position ?? 0) + 1}</span>
					<span class="track-title">{d.title ?? `Track ${d.track_id}`}</span>
					<span class="badge" style="background: {KIND_COLORS[d.kind]}22; color: {KIND_COLORS[d.kind]}">{badgeLabel(d)}</span>
				</div>
			{/each}
		</div>
	</div>

	{#if teachingDeviations.length > 0 || comparison.energy_deviations.length > 0 || comparison.deviation_patterns.length > 0}
		<div class="teaching-panel">
			<h3>What the room told you</h3>
			{#each comparison.deviation_patterns as p}
				<p class="pattern">{p}</p>
			{/each}
			{#each teachingDeviations as d}
				<p class="moment">
					<span class="badge" style="background: {KIND_COLORS[d.kind]}22; color: {KIND_COLORS[d.kind]}">{badgeLabel(d)}</span>
					{d.teaching_moment}
				</p>
			{/each}
			{#each comparison.energy_deviations as ed}
				<p class="moment">
					<span class="badge energy">energy {ed.delta > 0 ? '+' : ''}{ed.delta.toFixed(2)}</span>
					{ed.teaching_moment}
				</p>
			{/each}
		</div>
	{/if}
</div>

<style>
	.comparison {
		padding: 12px 16px;
	}

	.comparison-header {
		display: flex;
		align-items: center;
		gap: 12px;
		margin-bottom: 8px;
	}

	.back-btn {
		padding: 4px 10px;
		font-size: 12px;
		color: var(--text-primary);
		background: var(--bg-tertiary);
		border: 1px solid var(--border);
		border-radius: 4px;
	}

	.back-btn:hover {
		background: var(--accent);
		color: #000;
		border-color: var(--accent);
	}

	.title {
		font-weight: 600;
		font-size: 14px;
		margin-right: auto;
	}

	.count {
		font-size: 12px;
		font-weight: 600;
	}

	.arc-row {
		display: flex;
		gap: 8px;
		flex-wrap: wrap;
		margin-bottom: 12px;
	}

	.arc-chip {
		font-size: 11px;
		color: var(--text-secondary);
		padding: 2px 8px;
		background: var(--bg-tertiary);
		border-radius: 10px;
	}

	.two-col {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 16px;
		margin-bottom: 16px;
	}

	.col h3 {
		font-size: 12px;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.5px;
		color: var(--text-secondary);
		margin: 0 0 8px;
	}

	.dev-row {
		display: flex;
		align-items: center;
		gap: 8px;
		padding: 4px 8px;
		border-radius: 4px;
		margin-bottom: 2px;
		background: var(--bg-secondary);
	}

	.dev-row.dimmed {
		opacity: 0.55;
	}

	.pos {
		font-size: 11px;
		color: var(--text-dim);
		width: 20px;
		text-align: right;
		font-variant-numeric: tabular-nums;
	}

	.track-title {
		font-size: 13px;
		flex: 1;
		min-width: 0;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.badge {
		font-size: 10px;
		font-weight: 600;
		padding: 1px 6px;
		border-radius: 8px;
		white-space: nowrap;
	}

	.badge.energy {
		background: rgba(186, 104, 200, 0.15);
		color: #BA68C8;
	}

	.teaching-panel {
		background: var(--bg-secondary);
		border-radius: 8px;
		padding: 12px 16px;
	}

	.teaching-panel h3 {
		font-size: 12px;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.5px;
		color: var(--text-secondary);
		margin: 0 0 8px;
	}

	.pattern {
		font-size: 13px;
		font-style: italic;
		color: var(--text-primary);
		margin: 0 0 8px;
	}

	.moment {
		font-size: 12px;
		color: var(--text-secondary);
		margin: 0 0 6px;
		display: flex;
		align-items: baseline;
		gap: 8px;
	}
</style>
