<script lang="ts">
	import type { TransitionScoreBreakdown } from '$lib/types';
	import { getTransition } from '$lib/api/sets';
	import { createResource } from '$lib/data/resource.svelte';
	import { harmonicMove } from '$lib/utils/camelot';

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
		keyA?: string | null;
		keyB?: string | null;
		bpmA?: number | null;
		bpmB?: number | null;
		energyA?: number | null;
		energyB?: number | null;
		prevEnergyDelta?: number | null;
	}

	let {
		fromTrackId,
		toTrackId,
		score,
		analysisScore,
		teachingMoment,
		setId,
		transitionIndex,
		active = false,
		onclick,
		keyA = null,
		keyB = null,
		bpmA = null,
		bpmB = null,
		energyA = null,
		energyB = null,
		prevEnergyDelta = null,
	}: Props = $props();

	let expanded = $state(false);
	/** Latches on first expand: the breakdown stays loaded once you've asked for it,
	 *  so collapsing and re-opening doesn't refetch. */
	let everExpanded = $state(false);

	const res = createResource(
		() => (everExpanded ? { setId, transitionIndex } : null),
		({ setId: s, transitionIndex: i }, signal) => getTransition(s, i, signal),
		{ key: ({ setId: s, transitionIndex: i }) => `set:${s}:transition:${i}` },
	);
	const breakdown = $derived<TransitionScoreBreakdown | null>(res.data?.score_breakdown ?? null);
	const loading = $derived(res.loading);
	const error = $derived(res.error);

	let builderScore = $derived(breakdown?.total ?? score ?? null);
	let ctxScore = $derived(analysisScore ?? builderScore);
	let hasDualScores = $derived(analysisScore != null && builderScore != null);

	function scoreColor(s: number): string {
		if (s >= 0.8) return 'var(--score-excellent)';
		if (s >= 0.6) return 'var(--score-good)';
		if (s >= 0.4) return 'var(--score-fair)';
		return 'var(--score-poor)';
	}

	function scoreLabel(s: number): string {
		if (s >= 0.8) return 'Excellent';
		if (s >= 0.6) return 'Good';
		if (s >= 0.4) return 'Fair';
		return 'Poor';
	}

	// ── Mechanics ──
	let move = $derived(harmonicMove(keyA, keyB));
	let bpmDelta = $derived(bpmA != null && bpmB != null ? Math.round(bpmB - bpmA) : null);
	let energyDelta = $derived(energyA != null && energyB != null ? energyB - energyA : null);
	let energyArrow = $derived(
		energyDelta == null ? '→' : energyDelta > 0.05 ? '↑' : energyDelta < -0.05 ? '↓' : '→',
	);

	// Two-score copy — narrowed inside the closure so no non-null assertions are needed.
	let dualCopy = $derived.by(() => {
		if (analysisScore != null && builderScore != null) {
			return `On their own ${builderScore.toFixed(2)} · In your arc ${analysisScore.toFixed(2)}`;
		}
		return null;
	});

	// ── Noteworthy gate (Research Q4) ──
	let divergence = $derived(
		analysisScore != null && builderScore != null ? Math.abs(analysisScore - builderScore) : 0,
	);
	let energyInflection = $derived(
		energyDelta != null &&
			(Math.abs(energyDelta) >= 0.15 ||
				(prevEnergyDelta != null &&
					prevEnergyDelta !== 0 &&
					energyDelta !== 0 &&
					Math.sign(energyDelta) !== Math.sign(prevEnergyDelta))),
	);
	let noteworthy = $derived(move !== 'hold' || divergence >= 0.15 || energyInflection);
	let showNote = $derived(noteworthy && !!teachingMoment);

	function fetchBreakdown() {
		everExpanded = true;
	}

	function handleClick() {
		onclick?.(transitionIndex);
	}

	function toggleExpanded(e: MouseEvent) {
		e.stopPropagation();
		expanded = !expanded;
		if (expanded) fetchBreakdown();
	}

	// Preserve prior behavior: lazy-fetch the breakdown when no pre-computed score exists.
	$effect(() => {
		if (score == null && !breakdown && !loading && !error) {
			fetchBreakdown();
		}
	});

	type NumDim = 'harmonic' | 'energy_fit' | 'bpm_compat' | 'genre_coherence' | 'track_quality';
	const DIMS: { key: NumDim; label: string; weight: string }[] = [
		{ key: 'harmonic', label: 'Harmonic', weight: '25%' },
		{ key: 'energy_fit', label: 'Energy fit', weight: '20%' },
		{ key: 'bpm_compat', label: 'BPM', weight: '20%' },
		{ key: 'genre_coherence', label: 'Genre', weight: '15%' },
		{ key: 'track_quality', label: 'Quality', weight: '20%' },
	];
</script>

<div class="transition-indicator" class:active>
	<div class="strip-row">
		<button
			class="strip"
			style="--score-color: {ctxScore != null ? scoreColor(ctxScore) : 'var(--border)'}"
			onclick={handleClick}
		>
			<span class="score-fill"></span>
			{#if ctxScore != null}
				<span class="verdict" style="color: {scoreColor(ctxScore)}; border-color: {scoreColor(ctxScore)}">
					{scoreLabel(ctxScore)}
				</span>
				<span class="scores">
					{#if dualCopy}{dualCopy}{:else}{ctxScore.toFixed(2)}{/if}
				</span>
			{:else if loading}
				<span class="scores">...</span>
			{:else}
				<span class="scores">--</span>
			{/if}

			<span class="mechanics">
				<span class="mech mech-move" data-move={move}>{move}</span>
				{#if bpmDelta != null}
					<span class="mech mech-bpm">{bpmDelta > 0 ? '+' : bpmDelta < 0 ? '−' : ''}{Math.abs(bpmDelta)} BPM</span>
				{/if}
				<span class="mech mech-energy">{energyArrow}</span>
			</span>
		</button>
		<button
			class="expand-btn"
			onclick={toggleExpanded}
			aria-expanded={expanded}
			aria-label={expanded ? 'Hide the math' : 'Show the math'}
		>
			{expanded ? '▴' : '▾'}
		</button>
	</div>

	{#if showNote}
		<div class="note">{teachingMoment}</div>
	{/if}

	{#if expanded}
		<div class="breakdown">
			{#if loading}
				<span class="breakdown-status">Reading the math...</span>
			{:else if error}
				<span class="breakdown-status">Couldn't load the breakdown — try again.</span>
			{:else if breakdown}
				{#each DIMS as dim (dim.key)}
					{@const v = breakdown[dim.key]}
					<div class="dim-row">
						<span class="dim-label">{dim.label}</span>
						<span class="dim-weight">{dim.weight}</span>
						<span class="dim-bar"><span class="dim-fill" style="width: {v * 100}%; background: {scoreColor(v)}"></span></span>
						<span class="dim-val">{v.toFixed(2)}</span>
					</div>
				{/each}
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
		gap: 3px;
	}

	.strip-row {
		display: flex;
		align-items: stretch;
		gap: 4px;
	}

	.strip {
		flex: 1;
		display: flex;
		align-items: center;
		gap: 8px;
		position: relative;
		height: 26px;
		padding: 0 10px;
		border: none;
		border-radius: 13px;
		background: var(--bg-tertiary);
		cursor: pointer;
		overflow: hidden;
		transition: box-shadow 0.15s;
	}

	.strip:hover {
		box-shadow: 0 0 0 1px var(--score-color);
	}

	.active .strip {
		box-shadow: 0 0 0 2px var(--accent, var(--score-color));
	}

	.score-fill {
		position: absolute;
		inset: 0;
		background: var(--score-color);
		opacity: 0.12;
		pointer-events: none;
	}

	.verdict {
		position: relative;
		z-index: 1;
		font-size: 9px;
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0.4px;
		padding: 1px 6px;
		border: 1px solid;
		border-radius: 8px;
		flex-shrink: 0;
	}

	.scores {
		position: relative;
		z-index: 1;
		font-size: 11px;
		font-weight: 500;
		color: var(--text-secondary);
		font-variant-numeric: tabular-nums;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.mechanics {
		position: relative;
		z-index: 1;
		margin-left: auto;
		display: flex;
		align-items: center;
		gap: 8px;
		flex-shrink: 0;
	}

	.mech {
		font-size: 10px;
		font-weight: 600;
		color: var(--text-secondary);
		font-variant-numeric: tabular-nums;
	}

	.mech-move {
		text-transform: uppercase;
		letter-spacing: 0.3px;
	}

	.mech-move[data-move='lift'] { color: var(--energy-mid); }
	.mech-move[data-move='switch'] { color: var(--energy-high); }
	.mech-move[data-move='clash'] { color: var(--score-poor); }

	.mech-energy {
		font-size: 12px;
	}

	.expand-btn {
		flex-shrink: 0;
		width: 22px;
		border: none;
		background: var(--bg-tertiary);
		color: var(--text-dim);
		border-radius: 11px;
		cursor: pointer;
		font-size: 10px;
	}

	.expand-btn:hover {
		color: var(--text-primary);
		background: var(--bg-hover);
	}

	.note {
		font-size: 11px;
		line-height: 1.35;
		color: var(--text-secondary);
		padding: 2px 10px;
	}

	.breakdown {
		display: flex;
		flex-direction: column;
		gap: 4px;
		padding: 6px 10px;
		background: var(--bg-secondary);
		border-radius: 8px;
	}

	.breakdown-status {
		font-size: 11px;
		color: var(--text-dim);
	}

	.dim-row {
		display: grid;
		grid-template-columns: 72px 34px 1fr 34px;
		align-items: center;
		gap: 6px;
	}

	.dim-label {
		font-size: 11px;
		color: var(--text-secondary);
	}

	.dim-weight {
		font-size: 9px;
		color: var(--text-dim);
		text-align: right;
	}

	.dim-bar {
		height: 5px;
		background: var(--bg-tertiary);
		border-radius: 3px;
		overflow: hidden;
	}

	.dim-fill {
		display: block;
		height: 100%;
		border-radius: 3px;
	}

	.dim-val {
		font-size: 11px;
		font-weight: 600;
		text-align: right;
		font-variant-numeric: tabular-nums;
		color: var(--text-primary);
	}
</style>
