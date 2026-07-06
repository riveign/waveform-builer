<script lang="ts">
	import type { Track } from '$lib/types';
	import { submitDecision } from '$lib/api/tinder';
	import { updateTrackRating, updateTrackSetRoles } from '$lib/api/tracks';
	import { getPlayerStore } from '$lib/stores/player.svelte';
	import EnergyZonePicker from './EnergyZonePicker.svelte';
	import { ZONE_COLORS } from './EnergyZonePicker.svelte';
	import SetRolePicker from './SetRolePicker.svelte';
	import { ROLE_LABEL } from './SetRoleIcon.svelte';
	import StarRating from '../primitives/StarRating.svelte';
	import MenuItem from '../primitives/MenuItem.svelte';
	import MenuSeparator from '../primitives/MenuSeparator.svelte';
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

	const zoneColor = $derived(ZONE_COLORS[track.resolved_energy ?? ''] ?? 'var(--text-3)');

	async function handleZoneSelect(zone: string) {
		const previousZone = track.resolved_energy;
		const previousSource = track.energy_source;
		const previousConfidence = track.energy_confidence;
		ontrackupdated?.({ resolved_energy: zone, energy_source: 'approved', energy_confidence: 1.0 });
		onclose();

		try {
			await submitDecision(track.id, 'override', zone);
		} catch {
			ontrackupdated?.({ resolved_energy: previousZone, energy_source: previousSource, energy_confidence: previousConfidence });
		}
	}

	async function handleRoleToggle(role: string) {
		const previous = track.set_roles ?? [];
		const next = previous.includes(role)
			? previous.filter((r) => r !== role)
			: [...previous, role];
		// Keep the menu open — the DJ may mark several roles at once.
		ontrackupdated?.({ set_roles: next });

		try {
			await updateTrackSetRoles(track.id, next);
		} catch {
			ontrackupdated?.({ set_roles: previous });
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

<span class="menu-label" id="ctx-energy-label">Energy</span>
<MenuItem submenu={energySub} submenuLabel="Energy zone">
	{#snippet icon()}
		<span class="zone-dot" style="background: {zoneColor}"></span>
	{/snippet}
	{track.resolved_energy ?? 'not set'}
</MenuItem>
{#snippet energySub()}
	<EnergyZonePicker current={track.resolved_energy} onselect={handleZoneSelect} />
{/snippet}

<MenuSeparator />

<span class="menu-label" id="ctx-role-label">Set role</span>
<MenuItem submenu={roleSub} submenuLabel="Set role">
	{track.set_roles?.length ? track.set_roles.map((r) => ROLE_LABEL[r] ?? r).join(' · ') : 'not set'}
</MenuItem>
{#snippet roleSub()}
	<SetRolePicker current={track.set_roles ?? []} ontoggle={handleRoleToggle} />
{/snippet}

<MenuSeparator />

<span class="menu-label" id="ctx-rating-label">Rating</span>
<div class="menu-item-static" role="group" aria-labelledby="ctx-rating-label">
	<StarRating
		rating={track.rating ?? 0}
		onchange={handleRatingChange}
		showScore={false}
	/>
</div>

<MenuSeparator />

<MenuItem submenu={addSub} submenuLabel="Add to set">
	Add to set
</MenuItem>
{#snippet addSub()}
	<AddToSetPicker
		trackId={track.id}
		trackTitle={track.title ?? 'track'}
		onclose={onclose}
	/>
{/snippet}

<MenuSeparator />

<MenuItem onselect={() => { player.play(track); onclose(); }}>
	{#snippet icon()}
		<span class="play-glyph" aria-hidden="true">▶</span>
	{/snippet}
	Play
</MenuItem>

<style>
	.menu-label {
		padding: var(--space-2xs) var(--menu-item-pad-x);
		font-size: var(--text-xs);
		color: var(--text-2);
		text-transform: uppercase;
		letter-spacing: 0.05em;
	}
	.menu-item-static {
		padding: var(--space-sm) var(--menu-item-pad-x);
	}
	.zone-dot {
		width: 10px;
		height: 10px;
		border-radius: var(--radius-full);
		flex-shrink: 0;
	}
	.play-glyph {
		display: inline-flex;
		font-size: var(--text-xs);
	}
</style>
