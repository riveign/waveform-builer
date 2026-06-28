<script lang="ts">
	import type { SetComparison, TrackDeviation } from '$lib/types';
	import Chip from '$lib/components/primitives/Chip.svelte';
	import Button from '$lib/components/primitives/Button.svelte';

	let {
		comparison,
		onback,
	}: {
		comparison: SetComparison;
		onback: () => void;
	} = $props();

	const KIND_COLORS: Record<string, string> = {
		kept: 'var(--score-excellent)',
		moved: 'var(--score-good)',
		cut: 'var(--score-poor)',
		added: 'var(--zone-intro)',
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

	/** A soft tinted background for a deviation badge — the kind color at low alpha. */
	function badgeTint(kind: string): string {
		return `color-mix(in srgb, ${KIND_COLORS[kind]} 13%, transparent)`;
	}
</script>

<div class="comparison">
	<div class="comparison-header">
		<Button variant="secondary" size="sm" onclick={onback}>&larr; Timeline</Button>
		<span class="title">Planned vs played</span>
		<span class="count" style="color: {KIND_COLORS.kept}">{comparison.kept_count} kept</span>
		<span class="count" style="color: {KIND_COLORS.moved}">{comparison.moved_count} moved</span>
		<span class="count" style="color: {KIND_COLORS.cut}">{comparison.cut_count} cut</span>
		<span class="count" style="color: {KIND_COLORS.added}">{comparison.added_count} added</span>
	</div>

	<div class="arc-row">
		<Chip variant="neutral" size="sm">arc: {comparison.arc.planned_shape} &rarr; {comparison.arc.played_shape}</Chip>
		<Chip variant="neutral" size="sm">keys: {comparison.arc.planned_key_style} &rarr; {comparison.arc.played_key_style}</Chip>
		<Chip variant="neutral" size="sm">bpm: {comparison.arc.planned_bpm_style} &rarr; {comparison.arc.played_bpm_style}</Chip>
	</div>

	<div class="two-col">
		<div class="col">
			<h3>Planned — {comparison.planned_name ?? 'plan'}</h3>
			{#each plannedSide as d (d.kind + '-' + d.track_id + '-' + d.planned_position)}
				<div class="dev-row" class:dimmed={d.kind === 'cut'}>
					<span class="pos">{(d.planned_position ?? 0) + 1}</span>
					<span class="track-title">{d.title ?? `Track ${d.track_id}`}</span>
					<span class="badge" style="background: {badgeTint(d.kind)}; color: {KIND_COLORS[d.kind]}">{badgeLabel(d)}</span>
				</div>
			{/each}
		</div>
		<div class="col">
			<h3>Played — {comparison.played_name ?? 'set'}</h3>
			{#each playedSide as d (d.kind + '-' + d.track_id + '-' + d.played_position)}
				<div class="dev-row">
					<span class="pos">{(d.played_position ?? 0) + 1}</span>
					<span class="track-title">{d.title ?? `Track ${d.track_id}`}</span>
					<span class="badge" style="background: {badgeTint(d.kind)}; color: {KIND_COLORS[d.kind]}">{badgeLabel(d)}</span>
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
					<span class="badge" style="background: {badgeTint(d.kind)}; color: {KIND_COLORS[d.kind]}">{badgeLabel(d)}</span>
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
		padding: var(--space-lg) var(--space-xl);
	}

	.comparison-header {
		display: flex;
		align-items: center;
		gap: var(--space-lg);
		margin-bottom: var(--space-md);
	}

	.title {
		font-weight: var(--font-weight-semibold);
		font-size: var(--text-md);
		margin-right: auto;
	}

	.count {
		font-size: var(--text-sm);
		font-weight: var(--font-weight-semibold);
	}

	.arc-row {
		display: flex;
		gap: var(--space-md);
		flex-wrap: wrap;
		margin-bottom: var(--space-lg);
	}

	.two-col {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: var(--space-xl);
		margin-bottom: var(--space-xl);
	}

	.col h3 {
		font-size: var(--text-sm);
		font-weight: var(--font-weight-semibold);
		text-transform: uppercase;
		letter-spacing: 0.5px;
		color: var(--text-secondary);
		margin: 0 0 var(--space-md);
	}

	.dev-row {
		display: flex;
		align-items: center;
		gap: var(--space-md);
		padding: var(--space-xs) var(--space-md);
		border-radius: var(--radius-sm);
		margin-bottom: var(--space-2xs);
		background: var(--bg-secondary);
	}

	.dev-row.dimmed {
		opacity: 0.55;
	}

	.pos {
		font-size: var(--text-xs);
		color: var(--text-dim);
		width: 20px;
		text-align: right;
		font-variant-numeric: tabular-nums;
	}

	.track-title {
		font-size: var(--text-base);
		flex: 1;
		min-width: 0;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.badge {
		font-size: var(--text-2xs);
		font-weight: var(--font-weight-semibold);
		padding: var(--space-px) var(--space-sm);
		border-radius: var(--radius-lg);
		white-space: nowrap;
	}

	.badge.energy {
		background: color-mix(in srgb, var(--zone-close) 15%, transparent);
		color: var(--zone-close);
	}

	.teaching-panel {
		background: var(--bg-secondary);
		border-radius: var(--radius-lg);
		padding: var(--space-lg) var(--space-xl);
	}

	.teaching-panel h3 {
		font-size: var(--text-sm);
		font-weight: var(--font-weight-semibold);
		text-transform: uppercase;
		letter-spacing: 0.5px;
		color: var(--text-secondary);
		margin: 0 0 var(--space-md);
	}

	.pattern {
		font-size: var(--text-base);
		font-style: italic;
		color: var(--text-primary);
		margin: 0 0 var(--space-md);
	}

	.moment {
		font-size: var(--text-sm);
		color: var(--text-secondary);
		margin: 0 0 var(--space-sm);
		display: flex;
		align-items: baseline;
		gap: var(--space-md);
	}
</style>
