<script lang="ts">
	import type { SetWaveformTrack, SetAnalysis } from '$lib/types';
	import { formatKey, getCamelotColor, harmonicMove } from '$lib/utils/camelot';
	import { getTrackEnergyNumeric, energyColor } from '$lib/utils/energy';
	import Chip from '$lib/components/primitives/Chip.svelte';

	let {
		tracks,
		energyTargets = [],
		analysis = null,
		focusedTrackId = null,
		onselect,
	}: {
		tracks: SetWaveformTrack[];
		energyTargets?: (number | undefined)[];
		analysis?: SetAnalysis | null;
		focusedTrackId?: number | null;
		onselect?: (trackId: number) => void;
	} = $props();


	// Incoming-transition CTX score keyed by transition position (i-1 lands on card i).
	let ctxMap = $derived.by(() => {
		const map = new Map<number, number>();
		if (analysis) for (const t of analysis.transitions) map.set(t.position, t.scores.total);
		return map;
	});

	function scoreColor(s: number): string {
		if (s >= 0.8) return 'var(--score-excellent)';
		if (s >= 0.6) return 'var(--score-good)';
		if (s >= 0.4) return 'var(--score-fair)';
		return 'var(--score-poor)';
	}

	function selectTrack(trackId: number) {
		onselect?.(trackId);
	}
</script>

<div class="card-grid" role="group" aria-label="Set at a glance">
	{#each tracks as track, i (track.position ?? i)}
		{@const prevKey = i > 0 ? tracks[i - 1].key : null}
		{@const move = i > 0 ? harmonicMove(prevKey, track.key) : null}
		{@const ctx = ctxMap.get(i - 1)}
		{@const stripe = ctx != null ? scoreColor(ctx) : getCamelotColor(track.key)}
		{@const energyNorm = getTrackEnergyNumeric(track.energy_value, track.energy)}
		{@const target = energyTargets[i]}
		<div
			class="grid-card"
			class:selected={focusedTrackId === track.track_id}
			role="button"
				aria-label="Select {track.title ?? 'Untitled'} by {track.artist ?? 'Unknown'}"
			tabindex="0"
			onclick={() => selectTrack(track.track_id)}
			onkeydown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); selectTrack(track.track_id); } }}
		>
			<div class="stripe" style="background: {stripe}" aria-hidden="true"></div>
			<div class="card-header">
				<span class="pos-badge">{i + 1}</span>
				{#if move}
					<span class="from-caption">from {formatKey(prevKey) || '?'} · {move}</span>
				{:else}
					<span class="from-caption from-start">set opener</span>
				{/if}
				{#if ctx != null}
					<span class="ctx" style="color: {scoreColor(ctx)}">{ctx.toFixed(2)}</span>
				{/if}
			</div>
			<span class="title" title={track.title ?? ''}>{track.title ?? 'Untitled'}</span>
			<span class="artist" title={track.artist ?? ''}>{track.artist ?? 'Unknown'}</span>
			<div class="meta">
				<span class="key-badge" style="color: {getCamelotColor(track.key)}">{formatKey(track.key) || '?'}</span>
				<span class="bpm">{track.bpm ? Math.round(track.bpm) : '?'}</span>
				{#if track.genre}
					<Chip variant="genre" value={track.genre} size="sm" title={track.genre} />
				{/if}
			</div>
			<div class="energy-bar-bg">
				<div
					class="energy-bar-fill"
					style="width: {energyNorm !== null ? energyNorm * 100 : 0}%; background: {energyNorm !== null ? energyColor(energyNorm) : 'transparent'}"
				></div>
				{#if target !== undefined}
					<div class="energy-target-marker" style="left: {target * 100}%"></div>
				{/if}
			</div>
		</div>
	{/each}
</div>

<style>
	.card-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
		gap: 8px;
		padding: 8px 12px;
	}

	.grid-card {
		position: relative;
		display: flex;
		flex-direction: column;
		gap: 3px;
		padding: 8px 10px 10px;
		background: var(--bg-secondary);
		border: 1px solid transparent;
		border-radius: 6px;
		cursor: pointer;
		overflow: hidden;
		transition: background 0.1s, border-color 0.15s;
	}

	.grid-card:hover {
		background: var(--bg-hover);
	}

	.grid-card.selected {
		background: var(--bg-active);
		border-color: var(--accent);
	}

	.stripe {
		position: absolute;
		top: 0;
		left: 0;
		right: 0;
		height: 3px;
	}

	.card-header {
		display: flex;
		align-items: center;
		gap: 6px;
		margin-top: 2px;
	}

	.pos-badge {
		flex-shrink: 0;
		min-width: 18px;
		height: 18px;
		padding: 0 5px;
		display: inline-flex;
		align-items: center;
		justify-content: center;
		font-size: 10px;
		font-weight: 700;
		font-variant-numeric: tabular-nums;
		color: var(--text-secondary);
		background: var(--bg-tertiary);
		border-radius: 9px;
	}

	.from-caption {
		font-size: 10px;
		color: var(--text-dim);
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.from-start {
		font-style: italic;
	}

	.ctx {
		margin-left: auto;
		font-size: 11px;
		font-weight: 600;
		font-variant-numeric: tabular-nums;
	}

	.title {
		font-size: 12px;
		font-weight: 500;
		color: var(--text-primary);
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.artist {
		font-size: 11px;
		color: var(--text-secondary);
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.meta {
		display: flex;
		align-items: center;
		gap: 8px;
		margin-top: 2px;
	}

	.key-badge {
		font-weight: 600;
		font-size: 11px;
	}

	.bpm {
		font-size: 11px;
		color: var(--text-secondary);
		font-variant-numeric: tabular-nums;
	}

	.energy-bar-bg {
		position: relative;
		height: 6px;
		margin-top: 4px;
		background: linear-gradient(
			90deg,
			color-mix(in srgb, var(--energy-low) 22%, var(--bg-tertiary)),
			color-mix(in srgb, var(--energy-mid) 22%, var(--bg-tertiary)),
			color-mix(in srgb, var(--energy-high) 22%, var(--bg-tertiary))
		);
		border-radius: 3px;
		overflow: visible;
	}

	.energy-bar-fill {
		height: 100%;
		border-radius: 3px;
	}

	.energy-target-marker {
		position: absolute;
		top: -2px;
		width: 2px;
		height: 10px;
		background: var(--text-secondary);
		border-radius: 1px;
		transform: translateX(-1px);
	}
</style>
