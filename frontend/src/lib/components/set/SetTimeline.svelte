<script lang="ts">
	import { dndzone } from 'svelte-dnd-action';
	import type { SetTrack, SetWaveformTrack } from '$lib/types';
	import { getUiStore } from '$lib/stores/ui.svelte';
	import { reorderSetTracks, removeTrackFromSet, addTrackToSet } from '$lib/api/sets';
	import SetTrackCard from './SetTrackCard.svelte';
	import TransitionIndicator from './TransitionIndicator.svelte';

	let {
		tracks,
		setId,
		energyProfile,
		activeTransitionIndex = -1,
		onTransitionClick,
		onTracksChanged,
		onTrackPlay,
	}: {
		tracks: SetWaveformTrack[];
		setId: number;
		energyProfile?: string | null;
		activeTransitionIndex?: number;
		onTransitionClick?: (index: number) => void;
		onTracksChanged?: () => void;
		onTrackPlay?: (trackId: number) => void;
	} = $props();

	const ui = getUiStore();

	// DnD items — need `id` field for svelte-dnd-action
	let items = $state<(SetWaveformTrack & { id: number })[]>([]);
	let reordering = $state(false);
	let removeInFlight = $state<number | null>(null);
	let dropActive = $state(false);
	let dropAdding = $state(false);

	// Sync items when tracks prop changes (but not during drag)
	$effect(() => {
		if (!reordering) {
			items = tracks.map((t) => ({ ...t, id: t.track_id }));
		}
	});

	/** Parse energy profile string like "warmup(0.3)->build(0.6)->peak(0.9)->cooldown(0.4)"
	 *  into interpolated target values per track position. */
	function computeEnergyTargets(profile: string | null | undefined, count: number): (number | undefined)[] {
		if (!profile || count === 0) return new Array(count).fill(undefined);

		const segments: { name: string; value: number }[] = [];
		const re = /(\w+)\(([0-9.]+)\)/g;
		let match: RegExpExecArray | null;
		while ((match = re.exec(profile)) !== null) {
			segments.push({ name: match[1], value: parseFloat(match[2]) });
		}

		if (segments.length === 0) return new Array(count).fill(undefined);
		if (segments.length === 1) return new Array(count).fill(segments[0].value);

		// Linear interpolation across track positions
		const targets: number[] = [];
		for (let i = 0; i < count; i++) {
			const t = count === 1 ? 0 : i / (count - 1);
			const segIdx = t * (segments.length - 1);
			const lo = Math.floor(segIdx);
			const hi = Math.min(lo + 1, segments.length - 1);
			const frac = segIdx - lo;
			targets.push(segments[lo].value * (1 - frac) + segments[hi].value * frac);
		}
		return targets;
	}

	let energyTargets = $derived(computeEnergyTargets(energyProfile, items.length));

	// DnD event handlers
	function handleConsider(e: CustomEvent<{ items: (SetWaveformTrack & { id: number })[] }>) {
		reordering = true;
		items = e.detail.items;
	}

	async function handleFinalize(e: CustomEvent<{ items: (SetWaveformTrack & { id: number })[] }>) {
		items = e.detail.items;
		reordering = false;

		// Persist the new order
		const trackIds = items.map((i) => i.track_id);
		try {
			await reorderSetTracks(setId, trackIds);
			onTracksChanged?.();
		} catch (err) {
			// Revert on failure — re-sync from props
			items = tracks.map((t) => ({ ...t, id: t.track_id }));
			console.error('Failed to reorder tracks:', err);
		}
	}

	async function handleRemoveTrack(trackId: number) {
		if (removeInFlight !== null) return;
		removeInFlight = trackId;
		try {
			await removeTrackFromSet(setId, trackId);
			onTracksChanged?.();
		} catch (err) {
			console.error('Failed to remove track:', err);
		} finally {
			removeInFlight = null;
		}
	}

	function handleTrackClick(trackId: number) {
		ui.selectedTrackInSet = trackId;
	}

	function handleTransitionClickInternal(index: number) {
		onTransitionClick?.(index);
	}

	// Energy bar sidebar data: normalized energy for each track (0-1)
	const ENERGY_LABEL_MAP: Record<string, number> = {
		low: 0.15, warmup: 0.3, close: 0.35, closing: 0.35, mid: 0.5,
		build: 0.55, dance: 0.6, up: 0.7, drive: 0.75, high: 0.8, fast: 0.85, peak: 0.95,
	};

	function parseTrackEnergy(energy: string | null): number | null {
		if (!energy) return null;
		const n = parseInt(energy, 10);
		if (!isNaN(n)) return (n - 1) / 8;
		return ENERGY_LABEL_MAP[energy.toLowerCase()] ?? null;
	}

	function handleDragOver(e: DragEvent) {
		if (!e.dataTransfer?.types.includes('application/x-kiku-track')) return;
		e.preventDefault();
		e.dataTransfer.dropEffect = 'copy';
		dropActive = true;
	}

	function handleDragLeave() {
		dropActive = false;
	}

	async function handleDrop(e: DragEvent) {
		e.preventDefault();
		dropActive = false;
		const raw = e.dataTransfer?.getData('application/x-kiku-track');
		if (!raw) return;
		try {
			const { id } = JSON.parse(raw) as { id: number };
			if (items.some((i) => i.track_id === id)) return; // already in set
			dropAdding = true;
			await addTrackToSet(setId, id);
			onTracksChanged?.();
		} catch (err) {
			console.error('Failed to add track to set:', err);
		} finally {
			dropAdding = false;
		}
	}
</script>

<div
	class="set-timeline"
	class:drop-active={dropActive}
	ondragover={handleDragOver}
	ondragleave={handleDragLeave}
	ondrop={handleDrop}
	role="region"
	aria-label="Set timeline"
>
	{#if items.length === 0}
		<div class="empty">
			{#if dropActive}
				Drop a track here to start your set
			{:else}
				No tracks in this set — drag one from your library
			{/if}
		</div>
	{:else}
		<div class="timeline-content">
			<!-- Energy sidebar -->
			<div class="energy-sidebar" aria-label="Energy profile">
				{#each items as item, i (item.id)}
					{@const norm = parseTrackEnergy(item.energy)}
					{@const target = energyTargets[i]}
					<div class="energy-row">
						<div class="energy-bar-track">
							{#if norm !== null}
								<div
									class="energy-fill"
									class:low={norm < 0.35}
									class:mid={norm >= 0.35 && norm < 0.7}
									class:high={norm >= 0.7}
									style="height: {norm * 100}%"
								></div>
							{/if}
							{#if target !== undefined}
								<div class="energy-target-line" style="bottom: {target * 100}%"></div>
							{/if}
						</div>
					</div>
					{#if i < items.length - 1}
						<div class="energy-gap"></div>
					{/if}
				{/each}
			</div>

			<!-- Track list with DnD -->
			<div
				class="track-list"
				use:dndzone={{ items, flipDurationMs: 200, dropTargetStyle: { outline: '1px dashed var(--accent)', 'outline-offset': '-1px' } }}
				onconsider={handleConsider}
				onfinalize={handleFinalize}
			>
				{#each items as item, i (item.id)}
					<div class="track-slot">
						<div class="card-row">
							<div class="drag-handle" aria-label="Drag to reorder">
								<svg width="12" height="18" viewBox="0 0 12 18" fill="currentColor">
									<circle cx="3" cy="3" r="1.5" /><circle cx="9" cy="3" r="1.5" />
									<circle cx="3" cy="9" r="1.5" /><circle cx="9" cy="9" r="1.5" />
									<circle cx="3" cy="15" r="1.5" /><circle cx="9" cy="15" r="1.5" />
								</svg>
							</div>
							<div class="card-wrapper">
								<SetTrackCard
									track={{
										position: item.position,
										track_id: item.track_id,
										title: item.title,
										artist: item.artist,
										bpm: item.bpm,
										key: item.key,
										genre: item.genre,
										energy: item.energy,
										duration_sec: item.duration_sec,
										transition_score: item.transition_score,
										has_waveform: item.waveform_overview != null,
										energy_source: item.energy_source,
										energy_conflict: item.energy_conflict,
									}}
									position={i + 1}
									isSelected={ui.selectedTrackInSet === item.track_id}
									isPlaying={ui.playingTrackId === item.track_id}
									energyTarget={typeof energyTargets[i] === 'number' ? energyTargets[i] : undefined}
									energyConflict={item.energy_conflict}
									onplay={onTrackPlay}
								/>
							</div>
							<button
								class="remove-btn"
								onclick={() => handleRemoveTrack(item.track_id)}
								disabled={removeInFlight !== null}
								title="Remove from set"
								aria-label="Remove track"
							>
								{#if removeInFlight === item.track_id}
									<span class="spinner"></span>
								{:else}
									<svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="1.5">
										<line x1="3" y1="3" x2="11" y2="11" /><line x1="11" y1="3" x2="3" y2="11" />
									</svg>
								{/if}
							</button>
						</div>

						{#if i < items.length - 1}
							<div class="transition-slot">
								<TransitionIndicator
									fromTrackId={item.track_id}
									toTrackId={items[i + 1].track_id}
									score={items[i + 1].transition_score ?? undefined}
									{setId}
									transitionIndex={i}
								active={activeTransitionIndex === i}
									onclick={handleTransitionClickInternal}
								/>
							</div>
						{/if}
					</div>
				{/each}
			</div>
		</div>

		{#if dropActive || dropAdding}
			<div class="drop-indicator">
				{#if dropAdding}
					Adding track...
				{:else}
					Drop here to add to set
				{/if}
			</div>
		{/if}
	{/if}
</div>

<style>
	.set-timeline {
		width: 100%;
		overflow-y: auto;
		overflow-x: hidden;
		padding: 8px 0;
	}

	.empty {
		display: flex;
		align-items: center;
		justify-content: center;
		padding: 40px 16px;
		color: var(--text-dim);
		font-size: 13px;
	}

	.timeline-content {
		display: flex;
		gap: 0;
		padding: 0 12px;
	}

	/* ── Energy sidebar ── */

	.energy-sidebar {
		display: flex;
		flex-direction: column;
		align-items: center;
		width: 20px;
		flex-shrink: 0;
		padding-top: 4px;
	}

	.energy-row {
		height: 44px;
		display: flex;
		align-items: center;
	}

	.energy-gap {
		height: 32px;
	}

	.energy-bar-track {
		position: relative;
		width: 8px;
		height: 32px;
		background: var(--bg-tertiary);
		border-radius: 4px;
		overflow: visible;
		display: flex;
		flex-direction: column;
		justify-content: flex-end;
	}

	.energy-fill {
		width: 100%;
		border-radius: 4px;
		transition: height 0.2s;
	}

	.energy-fill.low {
		background: var(--energy-low, #2ecc71);
	}

	.energy-fill.mid {
		background: var(--energy-mid, #f39c12);
	}

	.energy-fill.high {
		background: var(--energy-high, #e94560);
	}

	.energy-target-line {
		position: absolute;
		left: -2px;
		right: -2px;
		height: 2px;
		background: var(--text-dim);
		border-radius: 1px;
	}

	/* ── Track list ── */

	.track-list {
		flex: 1;
		min-width: 0;
		display: flex;
		flex-direction: column;
	}

	.track-slot {
		display: flex;
		flex-direction: column;
	}

	.card-row {
		display: flex;
		align-items: center;
		gap: 4px;
	}

	.drag-handle {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 18px;
		flex-shrink: 0;
		color: var(--text-dim);
		cursor: grab;
		opacity: 0.4;
		transition: opacity 0.1s;
	}

	.card-row:hover .drag-handle {
		opacity: 0.8;
	}

	.card-wrapper {
		flex: 1;
		min-width: 0;
	}

	.remove-btn {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 24px;
		height: 24px;
		flex-shrink: 0;
		border: none;
		background: none;
		color: var(--text-dim);
		cursor: pointer;
		border-radius: 4px;
		opacity: 0;
		transition: opacity 0.1s, background 0.1s, color 0.1s;
		padding: 0;
	}

	.card-row:hover .remove-btn {
		opacity: 1;
	}

	.remove-btn:hover {
		background: var(--bg-tertiary);
		color: var(--energy-high, #e94560);
	}

	.remove-btn:disabled {
		cursor: default;
		opacity: 0.3;
	}

	.transition-slot {
		padding: 2px 22px 2px 22px;
	}

	/* ── Spinner ── */

	.spinner {
		display: inline-block;
		width: 12px;
		height: 12px;
		border: 1.5px solid var(--text-dim);
		border-top-color: transparent;
		border-radius: 50%;
		animation: spin 0.6s linear infinite;
	}

	@keyframes spin {
		to { transform: rotate(360deg); }
	}

	/* ── Drop zone ── */

	.set-timeline.drop-active {
		outline: 2px dashed var(--accent);
		outline-offset: -2px;
		background: color-mix(in srgb, var(--accent) 5%, transparent);
	}

	.drop-indicator {
		display: flex;
		align-items: center;
		justify-content: center;
		padding: 12px;
		margin: 4px 22px 8px;
		border: 1px dashed var(--accent);
		border-radius: 6px;
		color: var(--accent);
		font-size: 12px;
		font-weight: 500;
	}
</style>
