<script lang="ts">
	import type { Track, SuggestNextItem } from '$lib/types';
	import { getTrackArtworkUrl, setTrackAffinity, removeTrackAffinity } from '$lib/api/tracks';
	import { ZONE_COLORS } from './EnergyZonePicker.svelte';
	import StarRating from './StarRating.svelte';
	import ContextMenu from '../ContextMenu.svelte';
	import { getPlayerStore } from '$lib/stores/player.svelte';
	import { getUiStore } from '$lib/stores/ui.svelte';

	let {
		item,
		parentTrackId,
		affinity = null,
		onaffinitychange,
	}: {
		item: SuggestNextItem;
		parentTrackId: number;
		affinity?: string | null;
		onaffinitychange?: (trackId: number, newAffinity: string | null) => void;
	} = $props();

	const player = getPlayerStore();
	const ui = getUiStore();

	let artworkFailed = $state(false);
	let menuOpen = $state(false);
	let menuX = $state(0);
	let menuY = $state(0);

	// Reset artwork error when item changes
	$effect(() => {
		item.track.id;
		artworkFailed = false;
	});

	const track = $derived(item.track);
	const energyZone = $derived(track.resolved_energy ?? null);
	const energyColor = $derived(energyZone ? (ZONE_COLORS[energyZone] ?? 'var(--text-dim)') : 'var(--text-dim)');
	const genreLabel = $derived(track.genre_family ?? track.genre ?? null);

	function scoreColor(score: number): string {
		if (score >= 0.75) return 'var(--accent)';
		if (score >= 0.5) return 'var(--energy-mid, #f39c12)';
		return 'var(--energy-high, #e74c3c)';
	}

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
</script>

<div
	class="similar-card"
	role="button"
	tabindex="0"
	draggable="true"
	onclick={handleCardClick}
	oncontextmenu={handleContextMenu}
	ondragstart={handleDragStart}
	onkeydown={(e) => { if (e.key === 'Enter') handleCardClick(); }}
>
	<!-- Top row: artwork + title/artist + menu button -->
	<div class="card-top">
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
				onclick={handleMenuClick}
				aria-label="Track options"
			>&#8942;</button>
		</div>
	</div>

	<!-- Chips row -->
	<div class="chips-row">
		{#if genreLabel}
			<span class="chip chip-genre">{genreLabel}</span>
		{/if}
		{#if energyZone}
			<span class="chip chip-energy" style="--zone-color: {energyColor}">
				<span class="energy-dot"></span>
				{energyZone}
			</span>
		{/if}
		{#if track.rating && track.rating > 0}
			<span class="chip chip-rating">
				<StarRating rating={track.rating} readonly size="sm" />
			</span>
		{/if}
	</div>

	<!-- Score -->
	<div class="score-row">
		<span class="score-label">Score</span>
		<span class="score-value" style="color: {scoreColor(item.score)}">
			{(item.score * 100).toFixed(0)}
		</span>
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
	.similar-card {
		background: var(--bg-secondary);
		border: 1px solid var(--border);
		border-radius: 8px;
		padding: 10px 12px;
		cursor: pointer;
		transition: box-shadow 0.15s, border-color 0.15s;
		display: flex;
		flex-direction: column;
		gap: 8px;
		min-width: 0;
		overflow: hidden;
	}

	.similar-card:hover {
		border-color: var(--text-dim);
		box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
	}

	.similar-card:active {
		box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
	}

	/* Top row */
	.card-top {
		display: flex;
		align-items: flex-start;
		gap: 10px;
		min-width: 0;
	}

	.artwork-wrap {
		width: 60px;
		height: 60px;
		flex-shrink: 0;
		border-radius: 4px;
		overflow: hidden;
		background: var(--bg-tertiary);
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
		width: 28px;
		height: 28px;
	}

	.text-col {
		flex: 1;
		min-width: 0;
		display: flex;
		flex-direction: column;
		gap: 2px;
		padding-top: 2px;
	}

	.track-title {
		font-size: 13px;
		font-weight: 600;
		color: var(--text-primary);
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.track-artist {
		font-size: 11px;
		color: var(--text-secondary);
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.menu-area {
		flex-shrink: 0;
		display: flex;
		align-items: center;
		gap: 4px;
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

	/* Chips */
	.chips-row {
		display: flex;
		flex-wrap: wrap;
		gap: 6px;
		align-items: center;
	}

	.chip {
		font-size: 10px;
		padding: 2px 6px;
		border-radius: 4px;
		background: var(--bg-tertiary);
		color: var(--text-secondary);
		white-space: nowrap;
		display: flex;
		align-items: center;
		gap: 4px;
	}

	.chip-energy {
		color: var(--zone-color);
	}

	.energy-dot {
		width: 6px;
		height: 6px;
		border-radius: 50%;
		background: var(--zone-color);
		flex-shrink: 0;
	}

	.chip-rating {
		padding: 1px 4px;
	}

	/* Score */
	.score-row {
		display: flex;
		align-items: center;
		gap: 6px;
	}

	.score-label {
		font-size: 10px;
		color: var(--text-dim);
		text-transform: uppercase;
		letter-spacing: 0.5px;
	}

	.score-value {
		font-size: 12px;
		font-weight: 600;
		font-variant-numeric: tabular-nums;
	}

	/* Context menu items */
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
</style>
