<script lang="ts">
	import type { Track } from '$lib/types';
	import { submitDecision } from '$lib/api/tinder';
	import { updateTrackRating } from '$lib/api/tracks';
	import { getPlayerStore } from '$lib/stores/player.svelte';
	import EnergyZonePicker from './EnergyZonePicker.svelte';
	import { ZONE_COLORS } from './EnergyZonePicker.svelte';
	import StarRating from './StarRating.svelte';
	import AddToSetPicker from '../set/AddToSetPicker.svelte';

	const player = getPlayerStore();

	let {
		track,
		onclose,
		ontrackupdated,
	}: {
		track: Track;
		onclose: () => void;
		ontrackupdated?: (updated: Partial<Track>) => void;
	} = $props();

	let showEnergySubmenu = $state(false);
	let showAddToSet = $state(false);

	async function handleZoneSelect(zone: string) {
		const previousZone = track.resolved_energy;
		const previousSource = track.energy_source;
		const previousConfidence = track.energy_confidence;
		ontrackupdated?.({ resolved_energy: zone, energy_source: 'approved', energy_confidence: 1.0 });
		showEnergySubmenu = false;
		onclose();

		try {
			await submitDecision(track.id, 'override', zone);
		} catch {
			ontrackupdated?.({ resolved_energy: previousZone, energy_source: previousSource, energy_confidence: previousConfidence });
		}
	}

	async function handleRatingChange(rating: number) {
		const previousRating = track.rating;
		ontrackupdated?.({ rating });
		onclose();

		try {
			await updateTrackRating(track.id, rating);
		} catch {
			ontrackupdated?.({ rating: previousRating });
		}
	}
</script>

<div class="menu-section">
	<span class="menu-label">Energy</span>
	<button
		class="menu-item has-submenu"
		onclick={() => showEnergySubmenu = !showEnergySubmenu}
		role="menuitem"
		aria-haspopup="true"
		aria-expanded={showEnergySubmenu}
	>
		<span class="zone-dot" style="background: {ZONE_COLORS[track.resolved_energy ?? ''] ?? 'var(--text-dim)'}"></span>
		{track.resolved_energy ?? 'not set'}
		<span class="submenu-arrow">›</span>
	</button>

	{#if showEnergySubmenu}
		<EnergyZonePicker
			current={track.resolved_energy}
			onselect={handleZoneSelect}
			inline={true}
		/>
	{/if}
</div>

<div class="menu-divider"></div>

<div class="menu-section">
	<span class="menu-label">Rating</span>
	<div class="menu-item-static">
		<StarRating
			rating={track.rating ?? 0}
			onchange={handleRatingChange}
			showScore={false}
		/>
	</div>
</div>

<div class="menu-divider"></div>

<div class="menu-section">
	<button
		class="menu-item has-submenu"
		onclick={() => showAddToSet = !showAddToSet}
		role="menuitem"
		aria-haspopup="true"
		aria-expanded={showAddToSet}
	>
		+ Add to Set
		<span class="submenu-arrow">›</span>
	</button>
	{#if showAddToSet}
		<AddToSetPicker
			trackId={track.id}
			trackTitle={track.title ?? 'track'}
			onclose={onclose}
		/>
	{/if}
</div>

<div class="menu-divider"></div>

<button
	class="menu-item"
	role="menuitem"
	onclick={() => { player.play(track); onclose(); }}
>
	▶ Play
</button>

<style>
	.menu-item {
		display: flex;
		align-items: center;
		gap: 8px;
		padding: 6px 10px;
		border-radius: 4px;
		border: none;
		background: none;
		width: 100%;
		text-align: left;
		color: var(--text-primary);
		font-size: 13px;
		cursor: pointer;
	}
	.menu-item:hover {
		background: var(--bg-secondary);
	}
	.menu-item-static {
		padding: 6px 10px;
	}
	.menu-label {
		padding: 2px 10px;
		font-size: 11px;
		color: var(--text-secondary);
		text-transform: uppercase;
		letter-spacing: 0.05em;
	}
	.menu-divider {
		height: 1px;
		background: var(--border);
		margin: 3px 0;
	}
	.zone-dot {
		width: 10px;
		height: 10px;
		border-radius: 50%;
		flex-shrink: 0;
	}
	.submenu-arrow {
		margin-left: auto;
		color: var(--text-dim);
		font-size: 14px;
	}
</style>
