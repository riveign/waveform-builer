<script lang="ts">
	import type { Track, SuggestNextItem } from '$lib/types';
	import { getTrackArtworkUrl, setTrackAffinity, removeTrackAffinity } from '$lib/api/tracks';
	import { ZONE_COLORS } from './EnergyZonePicker.svelte';
	import StarRating from './StarRating.svelte';
	import ContextMenu from '../ContextMenu.svelte';
	import AddToSetPicker from '../set/AddToSetPicker.svelte';
	import { getPlayerStore } from '$lib/stores/player.svelte';
	import { getUiStore } from '$lib/stores/ui.svelte';

	let {
		item,
		parentTrackId,
		parentBpm = null,
		affinity = null,
		onaffinitychange,
	}: {
		item: SuggestNextItem;
		parentTrackId: number;
		parentBpm?: number | null;
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
					style="background: {affinity === 'good' ? 'var(--accent, #4ecdc4)' : 'var(--energy-high, #e74c3c)'}"
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
		</div>
		<div class="meta-right">
			{#if genreLabel}
				<span class="pill pill-genre">{genreLabel}</span>
			{/if}
			{#if energyZone}
				{@const colors = PHASE_PILL_COLORS[energyZone]}
				<span
					class="pill pill-phase"
					style="background: {colors?.bg ?? 'var(--bg-tertiary)'}; color: {colors?.text ?? 'var(--text-secondary)'}"
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
		<span class="ctx-icon" style="color: var(--accent, #4ecdc4)">&#9679;</span>
		Great together
	</button>
	<button class="ctx-item" onclick={() => handleAffinity('bad')}>
		<span class="ctx-icon" style="color: var(--energy-high, #e74c3c)">&#9679;</span>
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
		background: var(--bg-secondary);
		border: 0.5px solid var(--border);
		border-radius: 12px;
		cursor: pointer;
		transition: border-color 0.15s;
		display: flex;
		flex-direction: column;
		min-width: 0;
		overflow: hidden;
	}

	.similar-card:hover {
		border-color: var(--border-focus);
	}

	.similar-card.selected {
		border: 2px solid var(--accent);
	}

	/* ── Zone Divider ── */
	.zone-divider {
		height: 1px;
		background: currentColor;
		opacity: 0.08;
	}

	/* ── Zone 1: Header ── */
	.zone-header {
		display: flex;
		gap: 10px;
		align-items: flex-start;
		padding: 14px 14px 10px;
	}

	.artwork-wrap {
		width: 48px;
		height: 48px;
		flex-shrink: 0;
		border-radius: 6px;
		overflow: hidden;
		background: #1a1a1a;
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
		color: var(--text-dim);
	}

	.artwork-fallback svg {
		width: 24px;
		height: 24px;
	}

	.text-col {
		flex: 1;
		min-width: 0;
		display: flex;
		flex-direction: column;
		gap: 2px;
	}

	.track-title {
		font-size: 13px;
		font-weight: 500;
		line-height: 1.35;
		color: var(--text-primary);
		display: -webkit-box;
		-webkit-line-clamp: 2;
		-webkit-box-orient: vertical;
		overflow: hidden;
	}

	.track-artist {
		font-size: 12px;
		color: var(--text-secondary);
		margin-top: 2px;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.menu-area {
		flex-shrink: 0;
		display: flex;
		align-items: center;
		gap: 4px;
		position: relative;
	}

	.affinity-dot {
		width: 6px;
		height: 6px;
		border-radius: 50%;
		flex-shrink: 0;
	}

	.menu-btn {
		background: none;
		border: none;
		color: var(--text-dim);
		cursor: pointer;
		font-size: 16px;
		padding: 2px 4px;
		border-radius: 4px;
		line-height: 1;
		transition: background 0.1s, color 0.1s;
	}

	.menu-btn:hover {
		background: var(--bg-tertiary);
		color: var(--text-primary);
	}

	/* ── Zone 2: Metadata ── */
	.zone-metadata {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 8px 14px;
		gap: 8px;
	}

	.meta-left {
		display: flex;
		align-items: baseline;
		flex-shrink: 0;
	}

	.bpm-value {
		font-size: 13px;
		font-weight: 500;
		font-variant-numeric: tabular-nums;
		color: var(--text-primary);
	}

	.bpm-unit {
		font-size: 11px;
		color: var(--text-tertiary);
		margin-left: 3px;
	}

	.bpm-delta-badge {
		font-size: 11px;
		font-weight: 500;
		padding: 1px 6px;
		border-radius: 99px;
		margin-left: 6px;
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
		gap: 5px;
		min-width: 0;
	}

	.pill {
		font-size: 11px;
		font-weight: 500;
		padding: 2px 8px;
		border-radius: 99px;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.pill-genre {
		background: var(--bg-tertiary);
		color: var(--text-secondary);
	}

	/* pill-phase colors set inline via style attribute */

	/* ── Zone 3: Score + Stars ── */
	.zone-score {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 8px 14px 14px;
	}

	.score-display {
		display: flex;
		align-items: baseline;
	}

	.score-number {
		font-size: 22px;
		font-weight: 500;
		color: var(--text-primary);
		font-variant-numeric: tabular-nums;
		line-height: 1;
	}

	.score-suffix {
		font-size: 11px;
		color: var(--text-tertiary);
		margin-left: 3px;
	}

	/* ── Context menu items ── */
	.ctx-item {
		display: flex;
		align-items: center;
		gap: 8px;
		width: 100%;
		padding: 6px 10px;
		background: none;
		border: none;
		border-radius: 4px;
		color: var(--text-primary);
		font-size: 13px;
		cursor: pointer;
		text-align: left;
	}

	.ctx-item:hover {
		background: var(--bg-secondary);
	}

	.ctx-icon {
		width: 16px;
		text-align: center;
		font-size: 12px;
		flex-shrink: 0;
	}

	.ctx-divider {
		height: 1px;
		background: var(--border);
		margin: 2px 0;
	}

	/* ── Add to Set Popover ── */
	.add-picker-popover {
		position: absolute;
		top: 100%;
		right: 0;
		margin-top: 4px;
		background: var(--bg-primary);
		border: 1px solid var(--border);
		border-radius: 8px;
		box-shadow: 0 4px 16px rgba(0, 0, 0, 0.4);
		z-index: 10;
		min-width: 220px;
	}
</style>
