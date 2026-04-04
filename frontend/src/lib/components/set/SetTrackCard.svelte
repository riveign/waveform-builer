<script lang="ts">
	import type { SetTrack, EnergyConflict } from '$lib/types';
	import { getCamelotColor } from '$lib/utils/camelot';
	import { getUiStore } from '$lib/stores/ui.svelte';
	import { getTrackEnergyNumeric, energyColor as getEnergyColor } from '$lib/utils/energy';
	import EnergyConflictBadge from './EnergyConflictBadge.svelte';

	let {
		track,
		position,
		isSelected = false,
		isPlaying = false,
		energyTarget,
		energyConflict = null,
		onplay,
	}: {
		track: SetTrack;
		position: number;
		isSelected?: boolean;
		isPlaying?: boolean;
		energyTarget?: number;
		energyConflict?: EnergyConflict | null;
		onplay?: (trackId: number) => void;
	} = $props();

	const ui = getUiStore();

	/** Indicator for energy vs target: match, above, below, or none */
	function energyFitIndicator(norm: number | null, target: number | undefined): { label: string; color: string } | null {
		if (norm === null || target === undefined) return null;
		const dev = norm - target;
		const absDev = Math.abs(dev);
		if (absDev <= 0.12) return { label: '', color: 'var(--energy-low)' };
		if (dev > 0) return { label: '', color: 'var(--energy-high)' };
		return { label: '', color: 'var(--accent)' };
	}

	let energyNorm = $derived(getTrackEnergyNumeric(track.energy_value, track.energy));
	let energyFit = $derived(energyFitIndicator(energyNorm, energyTarget));
	let energyColorVal = $derived(getEnergyColor(energyNorm));

	function handleClick() {
		ui.selectedTrackInSet = track.track_id;
	}

	function handlePlayClick(e: MouseEvent) {
		e.stopPropagation();
		onplay?.(track.track_id);
	}
</script>

<div
	class="set-track-card"
	class:selected={isSelected}
	class:playing={isPlaying}
	data-track-id={track.track_id}
	onclick={handleClick}
	role="button"
	tabindex="0"
	onkeydown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); handleClick(); } }}
>
	<span class="position">{position}</span>

	<button
		class="play-btn"
		class:active={isPlaying}
		onclick={handlePlayClick}
		aria-label={isPlaying ? 'Pause' : 'Play'}
	>
		{#if isPlaying}
			<svg width="12" height="12" viewBox="0 0 12 12" fill="currentColor">
				<rect x="1" y="1" width="4" height="10" rx="1" />
				<rect x="7" y="1" width="4" height="10" rx="1" />
			</svg>
		{:else}
			<svg width="12" height="12" viewBox="0 0 12 12" fill="currentColor">
				<path d="M2 1.5v9l8.5-4.5L2 1.5z" />
			</svg>
		{/if}
	</button>

	<div class="track-info">
		<div class="title-row">
			<span class="title" title={track.title ?? ''}>{track.title ?? 'Untitled'}</span>
			{#if track.genre}
				<span class="genre-badge">{track.genre}</span>
			{/if}
			{#if energyConflict}
				<EnergyConflictBadge conflict={energyConflict} />
			{/if}
		</div>
		<span class="artist" title={track.artist ?? ''}>{track.artist ?? 'Unknown'}</span>
	</div>

	<div class="meta">
		<span class="key-badge" style="color: {getCamelotColor(track.key)}">
			{track.key ?? '?'}
		</span>
		<span class="bpm">{track.bpm ? Math.round(track.bpm) : '?'}</span>
	</div>

	<div class="energy-cell">
		<div class="energy-bar-bg">
			<div
				class="energy-bar-fill"
				style="width: {energyNorm !== null ? energyNorm * 100 : 0}%; background: {energyColorVal}"
			></div>
			{#if energyTarget !== undefined}
				<div
					class="energy-target-marker"
					style="left: {energyTarget * 100}%"
				></div>
			{/if}
		</div>
		{#if energyFit}
			<span class="energy-fit-dot" style="background: {energyFit.color}" title={energyFit.label}></span>
		{/if}
	</div>
</div>

<style>
	.set-track-card {
		display: flex;
		align-items: center;
		gap: 8px;
		padding: 6px 10px;
		background: var(--bg-secondary);
		border: 1px solid transparent;
		border-radius: 4px;
		cursor: pointer;
		transition: background 0.1s, border-color 0.15s;
		user-select: none;
	}

	.set-track-card:hover {
		background: var(--bg-hover);
	}

	.set-track-card.selected {
		background: var(--bg-active);
		border-color: var(--accent);
	}

	.set-track-card.playing {
		border-color: var(--accent);
		box-shadow: 0 0 6px rgba(var(--accent-rgb, 255, 190, 11), 0.25);
	}

	.play-btn {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 22px;
		height: 22px;
		flex-shrink: 0;
		border: none;
		background: none;
		color: var(--text-dim);
		cursor: pointer;
		border-radius: 50%;
		padding: 0;
		opacity: 0;
		transition: opacity 0.15s, background 0.1s, color 0.1s;
	}

	.set-track-card:hover .play-btn,
	.play-btn.active {
		opacity: 1;
	}

	.play-btn.active {
		color: var(--accent);
	}

	.play-btn:hover {
		background: var(--bg-tertiary);
		color: var(--accent);
	}

	.position {
		width: 20px;
		flex-shrink: 0;
		font-size: 11px;
		font-weight: 600;
		color: var(--text-dim);
		text-align: center;
		font-variant-numeric: tabular-nums;
	}

	.track-info {
		flex: 1;
		min-width: 0;
		display: flex;
		flex-direction: column;
		gap: 1px;
	}

	.title-row {
		display: flex;
		align-items: center;
		gap: 6px;
		min-width: 0;
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

	.genre-badge {
		flex-shrink: 0;
		font-size: 9px;
		text-transform: uppercase;
		letter-spacing: 0.5px;
		padding: 1px 5px;
		border-radius: 3px;
		background: var(--bg-tertiary);
		color: var(--text-secondary);
	}

	.meta {
		display: flex;
		align-items: center;
		gap: 8px;
		flex-shrink: 0;
	}

	.key-badge {
		font-weight: 600;
		font-size: 11px;
		width: 28px;
		text-align: center;
	}

	.bpm {
		font-size: 11px;
		color: var(--text-secondary);
		font-variant-numeric: tabular-nums;
		width: 30px;
		text-align: right;
	}

	.energy-cell {
		display: flex;
		align-items: center;
		gap: 4px;
		flex-shrink: 0;
		width: 60px;
	}

	.energy-bar-bg {
		position: relative;
		flex: 1;
		height: 6px;
		background: var(--bg-tertiary);
		border-radius: 3px;
		overflow: visible;
	}

	.energy-bar-fill {
		height: 100%;
		border-radius: 3px;
		transition: width 0.2s;
	}

	.energy-target-marker {
		position: absolute;
		top: -2px;
		width: 2px;
		height: 10px;
		background: var(--text-dim);
		border-radius: 1px;
		transform: translateX(-1px);
	}

	.energy-fit-dot {
		width: 6px;
		height: 6px;
		border-radius: 50%;
		flex-shrink: 0;
	}
</style>
