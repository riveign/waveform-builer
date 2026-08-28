<script lang="ts">
	/**
	 * The right rail: energy graph, KPIs, and — for the Inspector layout — the
	 * selected transition explained in full. This is the structural move the three
	 * new layouts share: reference material leaves the primary column.
	 */
	import type { SetAnalysis, SetWaveformTrack } from '$lib/types';
	import type { SetRow } from './rowModel';
	import { formatBpmDelta, scoreColor } from './rowModel';
	import EnergyFlowChart from './EnergyFlowChart.svelte';
	import SetCover from './SetCover.svelte';
	import NextKeys from './NextKeys.svelte';

	let {
		tracks,
		rows,
		analysis = null,
		energyProfile = null,
		plannedCurve = null,
		selectedIndex = -1,
		onTrackClick,
		/** Inspector layout only: which transition the rail explains. */
		inspectIndex = -1,
		showInspector = false,
	}: {
		tracks: SetWaveformTrack[];
		rows: SetRow[];
		analysis?: SetAnalysis | null;
		energyProfile?: string | null;
		plannedCurve?: number[] | null;
		selectedIndex?: number;
		onTrackClick?: (index: number) => void;
		inspectIndex?: number;
		showInspector?: boolean;
	} = $props();

	/** The five scored dimensions, in the order the scoring table documents them.
	 *  Typed off the analysis shape so a renamed score can't silently vanish. */
	type Scores = NonNullable<SetAnalysis['transitions'][number]['scores']>;
	const DIMENSIONS: { key: keyof Scores & string; label: string }[] = [
		{ key: 'harmonic', label: 'Harmonic' },
		{ key: 'energy_fit', label: 'Energy' },
		{ key: 'bpm_compat', label: 'BPM' },
		{ key: 'genre_coherence', label: 'Genre' },
		{ key: 'track_quality', label: 'Quality' },
	];

	/** Read one dimension, tolerating the non-numeric members of the score object. */
	function scoreOf(scores: Scores | null, key: keyof Scores & string): number | null {
		const v = scores?.[key];
		return typeof v === 'number' ? v : null;
	}

	let inspected = $derived(inspectIndex >= 0 && inspectIndex < rows.length ? rows[inspectIndex] : null);
	let inspectedNext = $derived(inspected ? rows[inspectIndex + 1] ?? null : null);
	let inspectedScores = $derived(
		analysis?.transitions.find((t) => t.position === inspectIndex)?.scores ?? null,
	);

	/** How many keys the set actually visits — wheel positions, not spellings. */
	let keyPositions = $derived(new Set(rows.map((r) => r.camelot).filter(Boolean)).size);
	let bpmRange = $derived.by(() => {
		const v = tracks.map((t) => t.bpm).filter((b): b is number => b != null);
		return v.length ? [Math.round(Math.min(...v)), Math.round(Math.max(...v))] : null;
	});
</script>

<aside class="rail">
	<!-- The chart draws its own header, so the rail doesn't add a second one. -->
	<div class="block chart">
		<EnergyFlowChart
			dense
			{tracks}
			{energyProfile}
			{plannedCurve}
			{selectedIndex}
			{onTrackClick}
		/>
	</div>

	<div class="block">
		<div class="label"><span>How it scores</span></div>
		<div class="kpis">
			<div class="kpi">
				<span class="v" style="color:{scoreColor(analysis?.overall_score ?? null)}">
					{analysis ? analysis.overall_score.toFixed(3) : '—'}
				</span>
				<span class="l">Overall</span>
			</div>
			<div class="kpi">
				<span class="v">{bpmRange ? `${bpmRange[0]}–${bpmRange[1]}` : '—'}</span>
				<span class="l">BPM range</span>
			</div>
			<div class="kpi">
				<span class="v">{keyPositions}</span>
				<span class="l">Keys visited</span>
			</div>
			<div class="kpi">
				<span class="v">{tracks.length}</span>
				<span class="l">Tracks</span>
			</div>
		</div>
	</div>

	{#if analysis}
		<div class="block">
			<div class="label"><span>Shape</span></div>
			<div class="tags">
				<span class="tag">{analysis.arc.energy_shape}</span>
				<span class="tag">{analysis.arc.key_style}</span>
				<span class="tag">{analysis.arc.bpm_style}</span>
			</div>
			{#each analysis.set_patterns as pattern}
				<p class="note">{pattern}</p>
			{/each}
		</div>
	{/if}

	{#if showInspector}
		{#if inspected && inspectedNext && inspected.moveOut}
			<div class="block">
				<div class="label">
					<span>Transition {inspected.position} → {inspectedNext.position}</span>
					<span class="mv {inspected.moveOut.kind}">{inspected.moveOut.label}</span>
				</div>

				<div class="pair">
					<SetCover trackId={inspected.track.track_id} camelot={inspected.camelot} keyColor={inspected.keyColor} size={38} />
					<span class="arrow" aria-hidden="true">→</span>
					<SetCover trackId={inspectedNext.track.track_id} camelot={inspectedNext.camelot} keyColor={inspectedNext.keyColor} size={38} />
					<span class="pairtext">
						<span class="ttl">{inspected.track.title} → {inspectedNext.track.title}</span>
						<span class="sub">
							{inspected.keyName} → {inspectedNext.keyName}
							{#if inspected.moveOut.bpmDelta != null}· {formatBpmDelta(inspected.moveOut.bpmDelta)} BPM{/if}
						</span>
					</span>
				</div>

				{#if inspectedScores}
					<div class="breakdown">
						{#each DIMENSIONS as dim}
							{@const v = scoreOf(inspectedScores, dim.key)}
							{#if v != null}
								<div class="brow">
									<span class="bl">{dim.label}</span>
									<span class="bar"><i style="width:{Math.round(v * 100)}%;background:{scoreColor(v)}"></i></span>
									<span class="bv">{v.toFixed(2)}</span>
								</div>
							{/if}
						{/each}
					</div>
				{/if}

				{#if inspected.moveOut.teaching}
					<p class="note">{inspected.moveOut.teaching}</p>
				{/if}
			</div>

			<div class="block">
				<div class="label"><span>What can follow {inspectedNext.keyName}</span></div>
				<NextKeys keys={inspectedNext.nextKeys} verbose />
				<p class="note">Three clean ways out of {inspectedNext.keyName}. Anything else is a jump.</p>
			</div>
		{:else}
			<div class="block">
				<p class="note">Pick a track to see the move into it — the score behind it, and where it can go next.</p>
			</div>
		{/if}
	{/if}
</aside>

<style>
	.rail {
		display: flex;
		flex-direction: column;
		background: var(--surface-2);
		border-left: 1px solid var(--border-default);
		overflow-y: auto;
		min-width: 0;
	}

	.block { padding: var(--space-lg); border-bottom: 1px solid var(--border-default); }

	/* The chart brings its own padding and header. `dense` was tuned for the
	   full-width band; in a 320px rail the axis labels and legend eat a 96px plot
	   until nothing is left, so the rail buys back the height it needs. */
	.block.chart { padding: 0; flex-shrink: 0; }
	.block.chart :global(.chart-container) { height: 148px; }

	.label {
		display: flex;
		justify-content: space-between;
		align-items: center;
		gap: var(--space-sm);
		font-family: var(--font-mono, ui-monospace, monospace);
		font-size: var(--text-2xs);
		letter-spacing: 0.11em;
		text-transform: uppercase;
		color: var(--text-4);
		margin-bottom: var(--space-md);
	}
	.kpis { display: grid; grid-template-columns: 1fr 1fr; gap: var(--space-md); }
	.kpi { background: var(--surface-3); border-radius: 3px; padding: var(--space-md); }
	.v {
		display: block;
		font-family: var(--font-mono, ui-monospace, monospace);
		font-size: var(--text-lg);
		font-weight: var(--font-weight-semibold);
		font-variant-numeric: tabular-nums;
		letter-spacing: -0.02em;
		line-height: 1.15;
	}
	.l {
		display: block;
		font-family: var(--font-mono, ui-monospace, monospace);
		font-size: 9px;
		letter-spacing: 0.08em;
		text-transform: uppercase;
		color: var(--text-4);
		margin-top: 3px;
	}

	.tags { display: flex; flex-wrap: wrap; gap: var(--space-xs); }
	.tag {
		font-size: var(--text-2xs);
		padding: 3px 7px;
		border-radius: 9px;
		background: var(--surface-3);
		color: var(--text-2);
	}

	.note { font-size: var(--text-xs); color: var(--text-3); line-height: 1.5; margin: var(--space-md) 0 0; }

	.pair { display: flex; align-items: center; gap: var(--space-md); min-width: 0; }
	.arrow { color: var(--text-4); flex-shrink: 0; }
	.pairtext { flex: 1; min-width: 0; }
	.ttl {
		display: block;
		font-size: var(--text-xs);
		font-weight: var(--font-weight-medium);
		white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
	}
	.sub {
		display: block;
		font-family: var(--font-mono, ui-monospace, monospace);
		font-size: var(--text-2xs);
		color: var(--text-3);
	}

	.breakdown { display: grid; gap: var(--space-sm); margin: var(--space-lg) 0 0; }
	.brow { display: grid; grid-template-columns: 60px 1fr 30px; gap: var(--space-md); align-items: center; }
	.bl {
		font-family: var(--font-mono, ui-monospace, monospace);
		font-size: var(--text-2xs);
		letter-spacing: 0.05em;
		text-transform: uppercase;
		color: var(--text-3);
	}
	.bar { height: 3px; border-radius: 2px; background: var(--surface-3); position: relative; overflow: hidden; }
	.bar i { position: absolute; inset: 0 auto 0 0; display: block; border-radius: 2px; }
	.bv {
		font-family: var(--font-mono, ui-monospace, monospace);
		font-size: var(--text-2xs);
		color: var(--text-2);
		text-align: right;
		font-variant-numeric: tabular-nums;
	}

	.mv {
		font-family: var(--font-mono, ui-monospace, monospace);
		font-size: var(--text-2xs);
		font-weight: var(--font-weight-semibold);
		letter-spacing: 0.04em;
		padding: 2px 6px;
		border-radius: 2px;
	}
	.mv.hold { background: color-mix(in srgb, var(--score-excellent) 16%, transparent); color: var(--score-excellent); }
	.mv.lift { background: color-mix(in srgb, var(--energy-high) 16%, transparent); color: var(--energy-high); }
	.mv.switch { background: color-mix(in srgb, var(--role) 16%, transparent); color: var(--role); }
	.mv.clash { background: color-mix(in srgb, var(--score-poor) 16%, transparent); color: var(--score-poor); }
</style>
