<script lang="ts">
	import { tick } from 'svelte';
	import { dndzone } from 'svelte-dnd-action';
	import type { SetTrack, SetWaveformTrack, SetAnalysis } from '$lib/types';
	import { getUiStore } from '$lib/stores/ui.svelte';
	import { parseCamelot } from '$lib/utils/camelot';
	import { getSetTracksStore } from '$lib/stores/setTracks.svelte';
	import SetTrackCard from './SetTrackCard.svelte';
	import TransitionIndicator from './TransitionIndicator.svelte';
	import SetCardGrid from './SetCardGrid.svelte';
	import ReplaceTrackModal from './ReplaceTrackModal.svelte';
	import InSetTrackSearch from './InSetTrackSearch.svelte';

	let {
		tracks,
		setId,
		energyProfile,
		activeTransitionIndex = -1,
		analysis = null,
		onTransitionClick,
		onTracksChanged,
		onTrackPlay,
		focusedTrackId = null,
		viewMode = 'list',
		onFocusTrack,
	}: {
		tracks: SetWaveformTrack[];
		setId: number;
		energyProfile?: string | null;
		activeTransitionIndex?: number;
		analysis?: SetAnalysis | null;
		onTransitionClick?: (index: number) => void;
		onTracksChanged?: () => void;
		onTrackPlay?: (trackId: number) => void;
		focusedTrackId?: number | null;
		viewMode?: 'list' | 'compact' | 'grid';
		onFocusTrack?: (trackId: number) => void;
	} = $props();

	const ui = getUiStore();
	const store = getSetTracksStore();

	/** Compact = the same list, thinned down so a whole set fits on one screen. */
	let dense = $derived(viewMode === 'compact');

	/**
	 * What the rows render from. Normally this is just the store's list with the
	 * `id` svelte-dnd-action needs. While a drag is in progress the library owns
	 * the order — it hands us intermediate arrays on every hover — so we let it
	 * drive from `dragItems` and hand the result to the store on drop.
	 */
	let dragItems = $state<(SetWaveformTrack & { id: number })[] | null>(null);
	// Position (not track_id) as id — a track can appear twice in one set.
	let items = $derived(
		dragItems ?? tracks.map((t, i) => ({ ...t, id: t.position ?? i })),
	);

	let removeInFlight = $state<number | null>(null);
	let dropActive = $state(false);
	let dropAdding = $state(false);
	let replacePosition = $state<number | null>(null);

	// Keyboard move mode: a lifted track follows ↑/↓ until you drop it.
	let liftedIndex = $state<number | null>(null);
	let liftOrigin: number | null = null;
	let refocusing = false;
	let listEl = $state<HTMLElement | undefined>();

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

	// Normalized energy per position — feeds the transition energy arrow + inflection gate.
	let energyNorms = $derived(items.map((it) => getTrackEnergyNumeric(it.energy_value, it.energy)));

	function deltaOf(a: number | null, b: number | null): number | null {
		return a != null && b != null ? a - b : null;
	}

	/** Start indices of maximal runs of ≥3 consecutive tracks sharing a Camelot key. */
	let runStartIndices = $derived.by(() => {
		const starts = new Set<number>();
		let start = 0;
		for (let i = 1; i <= items.length; i++) {
			const a = parseCamelot(items[i - 1]?.key);
			const b = i < items.length ? parseCamelot(items[i]?.key) : null;
			const same = !!a && !!b && a.number === b.number && a.letter === b.letter;
			if (!same) {
				if (i - start >= 3) starts.add(start);
				start = i;
			}
		}
		return starts;
	});

	/** Map transition position → analysis data (from set analysis) */
	let analysisMap = $derived.by(() => {
		if (!analysis) return new Map<number, { score: number; teaching: string }>();
		const map = new Map<number, { score: number; teaching: string }>();
		for (const t of analysis.transitions) {
			map.set(t.position, { score: t.scores.total, teaching: t.teaching_moment });
		}
		return map;
	});

	// DnD event handlers
	function handleConsider(e: CustomEvent<{ items: (SetWaveformTrack & { id: number })[] }>) {
		dragItems = e.detail.items;
	}

	function handleFinalize(e: CustomEvent<{ items: (SetWaveformTrack & { id: number })[] }>) {
		// The store takes it from here: the new order is already on screen, and the
		// write follows it. Releasing `dragItems` hands rendering back to the store.
		store.setOrder(e.detail.items);
		dragItems = null;
	}

	// ── Nudge + keyboard reorder ──
	// Drag-and-drop is fine for a neighbouring swap; for anything further down a
	// long set it fights the scroller. These move a track without holding it, and
	// the move shows up immediately — the store coalesces the writes behind it.

	/** Keep the keyboard on the control the DJ just used, now at its new index. */
	async function refocus(selector: string, fallback?: string) {
		refocusing = true;
		await tick();
		const pick = (sel: string) => {
			const el = listEl?.querySelector<HTMLButtonElement>(sel);
			return el && !el.disabled ? el : null;
		};
		(pick(selector) ?? (fallback ? pick(fallback) : null))?.focus();
		refocusing = false;
	}

	async function nudge(index: number, dir: -1 | 1) {
		if (liftedIndex !== null || removeInFlight !== null) return;
		if (!store.move(index, index + dir)) return;
		const to = index + dir;
		const kind = dir === -1 ? 'up' : 'down';
		await refocus(
			`[data-move="${kind}"][data-idx="${to}"]`,
			`[data-move="${dir === -1 ? 'down' : 'up'}"][data-idx="${to}"]`,
		);
	}

	function dropLifted() {
		liftedIndex = null;
		liftOrigin = null;
		void store.flush();
	}

	function handleHandleKeydown(e: KeyboardEvent, index: number) {
		// Stop these from bubbling into svelte-dnd-action's own keyboard drag.
		if (e.key === ' ' || e.key === 'Enter') {
			e.preventDefault();
			e.stopPropagation();
			if (liftedIndex === null) {
				liftedIndex = index;
				liftOrigin = index;
			} else {
				dropLifted();
			}
		} else if (liftedIndex !== null && (e.key === 'ArrowUp' || e.key === 'ArrowDown')) {
			e.preventDefault();
			e.stopPropagation();
			const from = liftedIndex;
			const to = from + (e.key === 'ArrowUp' ? -1 : 1);
			if (store.move(from, to)) {
				liftedIndex = to;
				refocus(`[data-handle][data-idx="${to}"]`);
			}
		} else if (e.key === 'Escape' && liftedIndex !== null) {
			e.preventDefault();
			e.stopPropagation();
			// Walk it back where it was picked up from.
			if (liftOrigin !== null) store.move(liftedIndex, liftOrigin);
			liftedIndex = null;
			liftOrigin = null;
			void store.flush();
		}
	}

	function handleHandleBlur() {
		if (refocusing || liftedIndex === null) return;
		dropLifted();
	}

	async function handleRemoveTrack(trackId: number) {
		if (removeInFlight !== null) return;
		removeInFlight = trackId;
		try {
			await store.remove(trackId);
		} finally {
			removeInFlight = null;
		}
	}

	function handleTrackClick(trackId: number) {
		onFocusTrack?.(trackId);
	}

	function handleTransitionClickInternal(index: number) {
		onTransitionClick?.(index);
	}

	import { getTrackEnergyNumeric } from '$lib/utils/energy';

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
		const { id } = JSON.parse(raw) as { id: number };
		if (items.some((i) => i.track_id === id)) return; // already in set
		dropAdding = true;
		try {
			await store.add(id);
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
	{#if store.error}
		<div class="action-error" role="alert">
			<span>{store.error}</span>
			<button class="dismiss" onclick={() => store.clearError()} aria-label="Dismiss">×</button>
		</div>
	{/if}

	{#if items.length === 0}
		<div class="empty">
			{#if dropActive}
				Drop a track here to start your set
			{:else}
				No tracks in this set — drag one from your library
			{/if}
		</div>
	{:else}
		{#if viewMode === 'grid'}
			<SetCardGrid tracks={items} {energyTargets} {analysis} {focusedTrackId} onselect={handleTrackClick} />
		{:else}
		<div class="timeline-content">
			<!-- Track list with DnD -->
			<div
				class="track-list"
				class:dense
				bind:this={listEl}
				use:dndzone={{ items, flipDurationMs: 200, dropTargetStyle: { outline: '1px dashed var(--accent)', 'outline-offset': '-1px' } }}
				onconsider={handleConsider}
				onfinalize={handleFinalize}
			>
				{#each items as item, i (item.id)}
					<!-- Everything for one track stays INSIDE its slot. svelte-dnd-action
					     maps the zone's children to `items` by position, so an extra
					     sibling here (the run banner used to be one) shifts every index
					     and drag-to-reorder silently stops working. -->
					<div class="track-slot">
						{#if runStartIndices.has(i)}
							<div class="run-banner">The story here is energy, not key</div>
						{/if}
						<div class="card-row" class:lifted={liftedIndex === i}>
							<div class="reorder-controls" class:active={liftedIndex === i}>
								<button
									class="drag-handle"
									data-handle
									data-idx={i}
									onkeydown={(e) => handleHandleKeydown(e, i)}
									onblur={handleHandleBlur}
									title={liftedIndex === i ? 'Moving — ↑/↓ to move, Space to drop, Esc to cancel' : 'Drag to reorder, or Space to move with ↑/↓'}
									aria-label={liftedIndex === i ? 'Moving track — arrow keys to move, space to drop, escape to cancel' : 'Reorder track — drag, or press space to move with arrow keys'}
									aria-pressed={liftedIndex === i}
								>
									<svg width="12" height="18" viewBox="0 0 12 18" fill="currentColor">
										<circle cx="3" cy="3" r="1.5" /><circle cx="9" cy="3" r="1.5" />
										<circle cx="3" cy="9" r="1.5" /><circle cx="9" cy="9" r="1.5" />
										<circle cx="3" cy="15" r="1.5" /><circle cx="9" cy="15" r="1.5" />
									</svg>
								</button>
								<div class="nudge-col">
									<button
										class="move-btn"
										data-move="up"
										data-idx={i}
										onclick={() => nudge(i, -1)}
										disabled={i === 0 || liftedIndex !== null || removeInFlight !== null}
										title="Move up"
										aria-label="Move up one slot"
									>
										<svg width="10" height="10" viewBox="0 0 10 10" fill="none" stroke="currentColor" stroke-width="1.6">
											<path d="M1.5 6.5 5 3l3.5 3.5" />
										</svg>
									</button>
									<button
										class="move-btn"
										data-move="down"
										data-idx={i}
										onclick={() => nudge(i, 1)}
										disabled={i === items.length - 1 || liftedIndex !== null || removeInFlight !== null}
										title="Move down"
										aria-label="Move down one slot"
									>
										<svg width="10" height="10" viewBox="0 0 10 10" fill="none" stroke="currentColor" stroke-width="1.6">
											<path d="M1.5 3.5 5 7l3.5-3.5" />
										</svg>
									</button>
								</div>
							</div>
							<div class="card-wrapper">
								<SetTrackCard
									{dense}
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
										resolved_energy: item.resolved_energy,
										energy_source: item.energy_source,
										energy_confidence: item.energy_confidence,
										energy_value: item.energy_value,
										energy_label: item.energy_label,
										energy_conflict: item.energy_conflict,
									}}
									position={i + 1}
									isSelected={focusedTrackId === item.track_id}
									onselect={handleTrackClick}
									isPlaying={ui.playingTrackId === item.track_id}
									energyTarget={typeof energyTargets[i] === 'number' ? energyTargets[i] : undefined}
									energyConflict={item.energy_conflict}
									onplay={onTrackPlay}
								/>
							</div>
							<button
								class="action-btn replace-btn"
								onclick={() => { replacePosition = i; }}
								title="Replace track"
								aria-label="Replace track"
							>
								<svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="1.5">
									<path d="M1 5h10M8 2l3 3-3 3" /><path d="M13 9H3M6 12l-3-3 3-3" />
								</svg>
							</button>
							<button
								class="action-btn remove-btn"
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
									{dense}
									fromTrackId={item.track_id}
									toTrackId={items[i + 1].track_id}
									score={items[i + 1].transition_score ?? undefined}
									analysisScore={analysisMap.get(i)?.score}
									teachingMoment={analysisMap.get(i)?.teaching}
									keyA={item.key}
									keyB={items[i + 1].key}
									bpmA={item.bpm}
									bpmB={items[i + 1].bpm}
									energyA={energyNorms[i]}
									energyB={energyNorms[i + 1]}
									prevEnergyDelta={i > 0 ? deltaOf(energyNorms[i], energyNorms[i - 1]) : null}
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
		{/if}

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

	<InSetTrackSearch
		{setId}
		lastTrackId={items.length > 0 ? items[items.length - 1].track_id : null}
		excludeTrackIds={items.map((i) => i.track_id)}
		{energyProfile}
		positionMin={items.length > 0 ? items.reduce((sum, i) => sum + (i.duration_sec ?? 0), 0) / 60 : null}
		ontrackadded={onTracksChanged}
	/>
</div>

{#if replacePosition !== null && items[replacePosition]}
	{@const rItem = items[replacePosition]}
	<ReplaceTrackModal
		{setId}
		position={replacePosition}
		currentTrack={{
			position: rItem.position,
			track_id: rItem.track_id,
			title: rItem.title,
			artist: rItem.artist,
			bpm: rItem.bpm,
			key: rItem.key,
			genre: rItem.genre,
			energy: rItem.energy,
			duration_sec: rItem.duration_sec,
			transition_score: rItem.transition_score,
			has_waveform: rItem.waveform_overview != null,
			resolved_energy: rItem.resolved_energy,
			energy_source: rItem.energy_source,
			energy_confidence: rItem.energy_confidence,
			energy_value: rItem.energy_value,
			energy_label: rItem.energy_label,
			energy_conflict: rItem.energy_conflict,
		}}
		onclose={() => { replacePosition = null; }}
		onreplaced={() => { replacePosition = null; onTracksChanged?.(); }}
	/>
{/if}

<style>
	.set-timeline {
		width: 100%;
		overflow-y: auto;
		overflow-x: hidden;
		padding: 8px 0;
	}

	.action-error {
		display: flex;
		align-items: center;
		gap: 8px;
		margin: 0 12px 6px;
		padding: 6px 10px;
		font-size: 12px;
		color: var(--text-primary);
		background: color-mix(in srgb, var(--score-poor) 14%, transparent);
		border-left: 2px solid var(--score-poor);
		border-radius: 3px;
	}

	.action-error .dismiss {
		margin-left: auto;
		border: none;
		background: none;
		color: var(--text-dim);
		font-size: 14px;
		line-height: 1;
		cursor: pointer;
		padding: 0 2px;
	}

	.action-error .dismiss:hover {
		color: var(--text-primary);
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

	/* ── Track list ── */

	.track-list {
		flex: 1;
		min-width: 0;
		display: flex;
		flex-direction: column;
		position: relative;
	}

	/* Faint energy-ramp spine down the row gutter — the set as one continuous flow. */
	.track-list::before {
		content: '';
		position: absolute;
		left: -11px;
		top: 4px;
		bottom: 4px;
		width: 2px;
		border-radius: 1px;
		background: linear-gradient(var(--energy-low), var(--energy-mid), var(--energy-high));
		opacity: 0.18;
		pointer-events: none;
	}

	.run-banner {
		margin: 4px 0 6px;
		padding: 4px 10px;
		font-size: 11px;
		font-weight: 500;
		color: var(--text-secondary);
		background: color-mix(in srgb, var(--energy-mid) 10%, transparent);
		border-left: 2px solid var(--energy-mid);
		border-radius: 3px;
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

	/* Reorder cluster: ↑ / grab handle / ↓. The nudges are the reliable path on a
	   long set — no pointer held down, so the list scrolls normally between moves. */
	/* Handle and nudges sit side by side so the cluster is never taller than the
	   row it steers — stacking all three set a 48px floor on row height. */
	.reorder-controls {
		display: flex;
		align-items: center;
		gap: 1px;
		flex-shrink: 0;
	}

	.nudge-col {
		display: flex;
		flex-direction: column;
		gap: 1px;
	}

	.drag-handle {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 18px;
		flex-shrink: 0;
		border: none;
		background: none;
		padding: 0;
		color: var(--text-dim);
		cursor: grab;
		opacity: 0.4;
		border-radius: 3px;
		transition: opacity 0.1s, color 0.1s, background 0.1s;
	}

	.card-row:hover .drag-handle {
		opacity: 0.8;
	}

	.move-btn {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 16px;
		height: 12px;
		flex-shrink: 0;
		border: none;
		background: none;
		padding: 0;
		color: var(--text-dim);
		cursor: pointer;
		border-radius: 3px;
		opacity: 0;
		transition: opacity 0.1s, color 0.1s, background 0.1s;
	}

	.card-row:hover .move-btn,
	.reorder-controls:focus-within .move-btn {
		opacity: 0.8;
	}

	.move-btn:hover:not(:disabled) {
		background: var(--bg-tertiary);
		color: var(--accent);
	}

	.move-btn:disabled {
		cursor: default;
		opacity: 0.15;
	}

	.drag-handle:focus-visible,
	.move-btn:focus-visible {
		outline: 1px solid var(--accent);
		outline-offset: 1px;
		opacity: 1;
	}

	/* Lifted: the track is following the arrow keys until it's dropped. */
	.reorder-controls.active .drag-handle,
	.reorder-controls.active .move-btn {
		opacity: 1;
		color: var(--accent);
	}

	.reorder-controls.active .drag-handle {
		background: color-mix(in srgb, var(--accent) 18%, transparent);
		cursor: grabbing;
	}

	.card-row.lifted .card-wrapper {
		outline: 1px dashed var(--accent);
		outline-offset: 1px;
		border-radius: 4px;
	}

	.card-wrapper {
		flex: 1;
		min-width: 0;
	}

	.action-btn {
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

	.card-row:hover .action-btn {
		opacity: 1;
	}

	.action-btn:hover {
		background: var(--bg-tertiary);
	}

	.action-btn.replace-btn:hover {
		color: var(--accent);
	}

	.action-btn.remove-btn:hover {
		color: var(--energy-high, #e94560);
	}

	.action-btn:disabled {
		cursor: default;
		opacity: 0.3;
	}

	.transition-slot {
		padding: 2px 22px 2px 22px;
	}

	/* ── Compact list ── */

	.track-list.dense .transition-slot {
		padding: 1px 22px;
	}

	.track-list.dense .run-banner {
		margin: 2px 0 3px;
		padding: 2px 8px;
		font-size: 10px;
	}

	.track-list.dense .card-row {
		gap: 2px;
	}

	.track-list.dense .drag-handle {
		width: 12px;
	}

	.track-list.dense .drag-handle svg {
		width: 9px;
		height: 14px;
	}

	.track-list.dense .move-btn {
		width: 14px;
		height: 11px;
	}

	.track-list.dense .action-btn {
		width: 20px;
		height: 20px;
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
