<script lang="ts">
	import type { Track, SuggestNextItem } from '$lib/types';
	import { getTrackArtworkUrl, setTrackAffinity, removeTrackAffinity } from '$lib/api/tracks';
	import StarRating from './StarRating.svelte';
	import ContextMenu from '../ContextMenu.svelte';
	import AddToSetPicker from '../set/AddToSetPicker.svelte';
	import { getPlayerStore } from '$lib/stores/player.svelte';
	import { getUiStore } from '$lib/stores/ui.svelte';
	import { getCamelotColor, formatKey, keyMoveLabel, harmonyColor } from '$lib/utils/camelot';
	import HarmonyIcon, { toHarmonyRelation, HARMONY_RELATION_LABEL } from '$lib/components/primitives/HarmonyIcon.svelte';

	let {
		item,
		parentTrackId,
		parentBpm = null,
		parentKey = null,
		affinity = null,
		onaffinitychange,
	}: {
		item: SuggestNextItem;
		parentTrackId: number;
		parentBpm?: number | null;
		parentKey?: string | null;
		affinity?: string | null;
		onaffinitychange?: (trackId: number, newAffinity: string | null) => void;
	} = $props();

	const player = getPlayerStore();
	const ui = getUiStore();

	let artworkFailed = $state(false);
	let menuOpen = $state(false);
	let menuX = $state(0);
	let menuY = $state(0);
	let isSelected = $state(false);
	let showAddPicker = $state(false);

	// Reset artwork error when item changes
	$effect(() => {
		item.track.id;
		artworkFailed = false;
	});

	const track = $derived(item.track);
	const energyZone = $derived(track.resolved_energy ?? null);
	const genreLabel = $derived(track.genre_family ?? track.genre ?? null);
	const scoreDisplay = $derived(Math.round(item.score * 100));
	const bpmDelta = $derived.by(() => {
		if (!track.bpm || !parentBpm) return null;
		const diff = Math.round(track.bpm) - Math.round(parentBpm);
		return diff;
	});

	// Harmonic move from the current track — same vocabulary as the Harmonic
	// mixing card (energy up/down, mood switch, same key, distant keys).
	const harmony = $derived.by(() => {
		if (!track.key || !parentKey) return null;
		return keyMoveLabel(parentKey, track.key);
	});

	// Compact icon per harmonic move — the standardized HarmonyIcon glyph
	// (replaces the long label on the card). null when the move can't be classified.
	const harmonyRelation = $derived(harmony ? toHarmonyRelation(harmony.label) : null);

	// Phase pill colors: fill + text per zone
	const PHASE_PILL_COLORS: Record<string, { bg: string; text: string }> = {
		intro:   { bg: '#E6F1FB', text: '#185FA5' },
		warmup:  { bg: '#E1F5EE', text: '#0F6E56' },
		build:   { bg: '#FAEEDA', text: '#854F0B' },
		drive:   { bg: '#FAEEDA', text: '#854F0B' },
		peak:    { bg: '#FAECE7', text: '#993C1D' },
		close:   { bg: '#E1F5EE', text: '#085041' },
		cooldown:{ bg: '#E1F5EE', text: '#085041' },
	};

	function handleCardClick() {
		ui.selectedTrack = track;
		ui.activeTab = 'track';
	}

	function handleMenuClick(e: MouseEvent) {
		e.stopPropagation();
		e.preventDefault();
		menuX = e.clientX;
		menuY = e.clientY;
		menuOpen = true;
	}

	function handleContextMenu(e: MouseEvent) {
		e.preventDefault();
		e.stopPropagation();
		menuX = e.clientX;
		menuY = e.clientY;
		menuOpen = true;
	}

	function handleDragStart(e: DragEvent) {
		e.dataTransfer?.setData(
			'application/x-kiku-track',
			JSON.stringify({ id: track.id, title: track.title })
		);
		if (e.dataTransfer) e.dataTransfer.effectAllowed = 'copy';
	}

	async function handleAffinity(value: 'good' | 'bad') {
		menuOpen = false;
		try {
			await setTrackAffinity(parentTrackId, track.id, value);
			onaffinitychange?.(track.id, value);
		} catch {
			// Silently fail — affinity API may not exist yet
		}
	}

	async function handleRemoveAffinity() {
		menuOpen = false;
		try {
			await removeTrackAffinity(parentTrackId, track.id);
			onaffinitychange?.(track.id, null);
		} catch {
			// Silently fail
		}
	}

	function handlePlay() {
		menuOpen = false;
		player.play(track);
	}

	function handleOpenTrack() {
		menuOpen = false;
		ui.selectedTrack = track;
		ui.activeTab = 'track';
	}

	function handleAddToSet(e: MouseEvent) {
		e.stopPropagation();
		showAddPicker = !showAddPicker;
	}
</script>

<div
	class="similar-card"
	class:selected={isSelected}
	role="button"
	tabindex="0"
	draggable="true"
	onclick={handleCardClick}
	oncontextmenu={handleContextMenu}
	ondragstart={handleDragStart}
	onkeydown={(e) => { if (e.key === 'Enter') handleCardClick(); }}
>
	<!-- Zone 1: Header Row — artwork + title/artist + menu -->
	<div class="zone-header">
		<div class="artwork-wrap">
			{#if artworkFailed}
				<div class="artwork-fallback">
					<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
						<path d="M9 18V5l12-2v13" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
						<circle cx="6" cy="18" r="3" stroke="currentColor" stroke-width="1.5"/>
						<circle cx="18" cy="16" r="3" stroke="currentColor" stroke-width="1.5"/>
					</svg>
				</div>
			{:else}
				<img
					src={getTrackArtworkUrl(track.id)}
					alt=""
					class="artwork-img"
					onerror={() => { artworkFailed = true; }}
				/>
			{/if}
		</div>

		<div class="text-col">
			<span class="track-title">{track.title ?? 'Unknown'}</span>
			<span class="track-artist">{track.artist ?? 'Unknown'}</span>
		</div>

		<div class="menu-area">
			{#if affinity}
				<span
					class="affinity-dot"
					style="background: {affinity === 'good' ? 'var(--accent)' : 'var(--energy-high)'}"
					title="{affinity === 'good' ? 'Marked: great together' : 'Marked: not for me'}"
				></span>
			{/if}
			<button
				class="menu-btn"
				onclick={handleAddToSet}
				aria-label="Add to set"
				title="Add to set"
			>+</button>
			<button
				class="menu-btn"
				onclick={handleMenuClick}
				aria-label="Track options"
			>&#8942;</button>
			{#if showAddPicker}
				<div class="add-picker-popover">
					<AddToSetPicker
						trackId={track.id}
						trackTitle={track.title ?? 'track'}
						onclose={() => showAddPicker = false}
					/>
				</div>
			{/if}
		</div>
	</div>

	<!-- Divider -->
	<div class="zone-divider"></div>

	<!-- Zone 2: Track Metadata Row — BPM + delta | genre + phase pills -->
	<div class="zone-metadata">
		<div class="meta-left">
			{#if track.bpm}
				<span class="bpm-value">{Math.round(track.bpm)}</span>
				<span class="bpm-unit">BPM</span>
				{#if bpmDelta !== null && bpmDelta !== 0}
					<span
						class="bpm-delta-badge"
						class:delta-up={bpmDelta > 0}
						class:delta-down={bpmDelta < 0}
						title="{Math.abs(bpmDelta)} BPM {bpmDelta > 0 ? 'faster' : 'slower'} than current track"
					>{bpmDelta > 0 ? '+' : '\u2212'}{Math.abs(bpmDelta)}</span>
				{/if}
			{/if}
			{#if track.key}
				<span class="key-chip" style="color: {getCamelotColor(track.key)}" title="Key {formatKey(track.key)}">{formatKey(track.key)}</span>
				{#if harmony}
					<span
						class="harmony-badge"
						style="color: {harmonyColor(harmony.score)}; border-color: {harmonyColor(harmony.score)}"
					>
						{#if harmonyRelation}
							<HarmonyIcon
								relation={harmonyRelation}
								size="sm"
								label={HARMONY_RELATION_LABEL[harmonyRelation]}
								title="{formatKey(track.key)} — {harmony.label} from this track"
							/>
						{:else}
							<span class="harmony-fallback" title="{formatKey(track.key)} — {harmony.label} from this track">{harmony.label}</span>
						{/if}
					</span>
				{/if}
			{/if}
		</div>
		<div class="meta-right">
			{#if genreLabel}
				<span class="pill pill-genre" title={genreLabel}>{genreLabel}</span>
			{/if}
			{#if energyZone}
				{@const colors = PHASE_PILL_COLORS[energyZone]}
				<span
					class="pill pill-phase"
					style="background: {colors?.bg ?? 'var(--surface-3)'}; color: {colors?.text ?? 'var(--text-2)'}"
				>{energyZone}</span>
			{/if}
		</div>
	</div>

	<!-- Divider -->
	<div class="zone-divider"></div>

	<!-- Zone 3: Score + Actions Row -->
	<div class="zone-score">
		<div class="score-display">
			<span class="score-number">{scoreDisplay}</span>
			<span class="score-suffix">/ 100</span>
		</div>
		{#if track.rating && track.rating > 0}
			<StarRating rating={track.rating} readonly size="sm" />
		{/if}
	</div>
</div>

<!-- Context menu -->
<ContextMenu bind:open={menuOpen} x={menuX} y={menuY}>
	<button class="ctx-item" onclick={() => handleAffinity('good')}>
		<span class="ctx-icon" style="color: var(--accent)">&#9679;</span>
		Great together
	</button>
	<button class="ctx-item" onclick={() => handleAffinity('bad')}>
		<span class="ctx-icon" style="color: var(--energy-high)">&#9679;</span>
		Not for me
	</button>
	{#if affinity}
		<button class="ctx-item" onclick={handleRemoveAffinity}>
			<span class="ctx-icon">&#10005;</span>
			Remove opinion
		</button>
	{/if}
	<div class="ctx-divider"></div>
	<button class="ctx-item" onclick={handlePlay}>
		<span class="ctx-icon">&#9654;</span>
		Play
	</button>
	<button class="ctx-item" onclick={handleOpenTrack}>
		<span class="ctx-icon">&#8599;</span>
		Open track
	</button>
</ContextMenu>

<style>
	/* ── Card Container ── */
	.similar-card {
		background: var(--surface-2);
		border: var(--space-px) solid var(--border-subtle);
		border-radius: var(--radius-xl);
		cursor: pointer;
		transition: border-color var(--dur-fast) var(--ease-standard);
		display: flex;
		flex-direction: column;
		flex: 1; /* fill the equal-height grid cell */
		min-width: 0;
		overflow: hidden;
	}

	/* Push the score/action row to the bottom so it lines up across all cards. */
	.zone-metadata + .zone-divider {
		margin-top: auto;
	}

	.similar-card:hover {
		border-color: var(--border-strong);
	}

	.similar-card.selected {
		border: var(--space-2xs) solid var(--accent);
	}

	/* ── Zone Divider ── */
	.zone-divider {
		height: var(--space-px);
		background: currentColor;
		opacity: 0.08;
	}

	/* ── Zone 1: Header ── */
	.zone-header {
		display: flex;
		gap: var(--space-md);
		align-items: flex-start;
		padding: var(--space-md) var(--space-md) var(--space-sm);
	}

	.artwork-wrap {
		width: 38px;
		height: 38px;
		flex-shrink: 0;
		border-radius: var(--radius-md);
		overflow: hidden;
		background: var(--surface-1);
	}

	.artwork-img {
		width: 100%;
		height: 100%;
		object-fit: cover;
		display: block;
	}

	.artwork-fallback {
		width: 100%;
		height: 100%;
		display: flex;
		align-items: center;
		justify-content: center;
		color: var(--text-4);
	}

	.artwork-fallback svg {
		width: var(--space-3xl);
		height: var(--space-3xl);
	}

	.text-col {
		flex: 1;
		min-width: 0;
		display: flex;
		flex-direction: column;
		gap: var(--space-2xs);
	}

	.track-title {
		font-size: var(--text-sm);
		font-weight: var(--font-weight-medium);
		line-height: var(--lh-sm);
		color: var(--text-1);
		display: -webkit-box;
		-webkit-line-clamp: 2;
		-webkit-box-orient: vertical;
		overflow: hidden;
	}

	.track-artist {
		font-size: var(--text-xs);
		color: var(--text-2);
		margin-top: var(--space-px);
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.menu-area {
		flex-shrink: 0;
		display: flex;
		align-items: center;
		gap: var(--space-xs);
		position: relative;
	}

	.affinity-dot {
		width: var(--space-sm);
		height: var(--space-sm);
		border-radius: var(--radius-full);
		flex-shrink: 0;
	}

	.menu-btn {
		background: none;
		border: none;
		color: var(--text-4);
		cursor: pointer;
		font-size: var(--text-lg);
		padding: var(--space-2xs) var(--space-xs);
		border-radius: var(--radius-sm);
		line-height: 1;
		transition: background var(--dur-fast) var(--ease-standard), color var(--dur-fast) var(--ease-standard);
	}

	.menu-btn:hover {
		background: var(--surface-3);
		color: var(--text-1);
	}

	/* ── Zone 2: Metadata ── */
	.zone-metadata {
		display: flex;
		flex-direction: column;
		align-items: stretch;
		padding: var(--space-sm) var(--space-md);
		gap: var(--space-xs);
	}

	.meta-left {
		display: flex;
		align-items: baseline;
		flex-wrap: wrap;
		gap: var(--space-xs) 0;
		flex-shrink: 0;
	}

	.key-chip {
		font-size: var(--text-sm);
		font-weight: var(--font-weight-semibold);
		margin-left: var(--space-md);
	}

	.harmony-badge {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		width: 17px;
		height: 17px;
		font-size: var(--text-2xs);
		font-weight: var(--font-weight-semibold);
		line-height: 1;
		border: var(--space-px) solid;
		border-radius: var(--radius-full);
		margin-left: var(--space-sm);
		flex-shrink: 0;
	}
	/* the standardized SVG glyph sits inside the colored circle; shrink it a step
	 * so it reads as a glyph within the ring (icon inherits the badge color). */
	.harmony-badge :global(.harmony-icon--sm) {
		width: 12px;
		height: 12px;
	}
	.harmony-fallback {
		font-size: var(--text-2xs);
	}

	.bpm-value {
		font-size: var(--text-base);
		font-weight: var(--font-weight-medium);
		font-variant-numeric: tabular-nums;
		color: var(--text-1);
	}

	.bpm-unit {
		font-size: var(--text-xs);
		color: var(--text-3);
		margin-left: var(--space-2xs);
	}

	.bpm-delta-badge {
		font-size: var(--text-xs);
		font-weight: var(--font-weight-medium);
		padding: var(--space-px) var(--space-sm);
		border-radius: var(--radius-full);
		margin-left: var(--space-sm);
		font-variant-numeric: tabular-nums;
	}

	.bpm-delta-badge.delta-up {
		background: #FAEEDA;
		color: #854F0B;
	}

	.bpm-delta-badge.delta-down {
		background: #E6F1FB;
		color: #185FA5;
	}

	.meta-right {
		display: flex;
		flex-wrap: wrap;
		gap: var(--space-xs);
		min-width: 0;
	}

	.pill {
		font-size: var(--text-xs);
		font-weight: var(--font-weight-medium);
		padding: var(--space-2xs) var(--space-md);
		border-radius: var(--radius-full);
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.pill-genre {
		background: var(--surface-3);
		color: var(--text-2);
		max-width: 100%;
	}

	/* pill-phase colors set inline via style attribute */

	/* ── Zone 3: Score + Stars ── */
	.zone-score {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: var(--space-sm) var(--space-md) var(--space-md);
	}

	.score-display {
		display: flex;
		align-items: baseline;
	}

	.score-number {
		font-size: var(--text-lg);
		font-weight: var(--font-weight-medium);
		color: var(--text-1);
		font-variant-numeric: tabular-nums;
		line-height: 1;
	}

	.score-suffix {
		font-size: var(--text-xs);
		color: var(--text-3);
		margin-left: var(--space-2xs);
	}

	/* ── Context menu items ── */
	.ctx-item {
		display: flex;
		align-items: center;
		gap: var(--space-md);
		width: 100%;
		padding: var(--space-sm) var(--space-md);
		background: none;
		border: none;
		border-radius: var(--radius-sm);
		color: var(--text-1);
		font-size: var(--text-base);
		cursor: pointer;
		text-align: left;
	}

	.ctx-item:hover {
		background: var(--surface-2);
	}

	.ctx-icon {
		width: var(--space-xl);
		text-align: center;
		font-size: var(--text-sm);
		flex-shrink: 0;
	}

	.ctx-divider {
		height: var(--space-px);
		background: var(--border-subtle);
		margin: var(--space-2xs) 0;
	}

	/* ── Add to Set Popover ── */
	.add-picker-popover {
		position: absolute;
		top: 100%;
		right: 0;
		margin-top: var(--space-xs);
		background: var(--surface-1);
		border: var(--space-px) solid var(--border-subtle);
		border-radius: var(--radius-lg);
		box-shadow: var(--elev-3);
		z-index: 10;
		min-width: 220px;
	}
</style>
