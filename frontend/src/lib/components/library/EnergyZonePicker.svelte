<script lang="ts" module>
	export const ZONE_COLORS: Record<string, string> = {
		intro: 'var(--zone-intro)',
		warmup: 'var(--zone-warmup)',
		build: 'var(--zone-build)',
		drive: 'var(--zone-drive)',
		peak: 'var(--zone-peak)',
		close: 'var(--zone-close)',
	};

	export const ZONES = ['intro', 'warmup', 'build', 'drive', 'peak', 'close'] as const;
	export type EnergyZone = (typeof ZONES)[number];

	export const ZONE_TIPS: Record<string, string> = {
		intro: 'Set opener — the first track that sets the mood and invites people in',
		warmup: 'Low energy — opening the night, easing in',
		build: 'Rising energy — crowd warming up, building anticipation',
		drive: 'Mid-high energy — locked in, dancing hard',
		peak: 'Maximum energy — the moment the room ignites',
		close: 'Closing energy — winding down, emotional resolution',
	};
</script>

<script lang="ts">
	import MenuItem from '$lib/components/primitives/MenuItem.svelte';

	let {
		current = null,
		onselect,
		inline = false,
	}: {
		current: string | null;
		onselect: (zone: string) => void;
		inline?: boolean;
	} = $props();
</script>

<div class="zone-picker" class:zone-picker-inline={inline} role="menu">
	{#each ZONES as zone}
		<MenuItem
			selected={current === zone}
			onselect={() => onselect(zone)}
		>
			{#snippet icon()}
				<span class="zone-dot" style="--zone-color: {ZONE_COLORS[zone]}"></span>
			{/snippet}
			{zone}
		</MenuItem>
	{/each}
</div>

<style>
	.zone-picker {
		display: flex;
		flex-direction: column;
		gap: var(--space-2xs);
	}
	.zone-picker-inline {
		padding: var(--space-xs) 0 var(--space-xs) var(--space-lg);
		border-left: 2px solid var(--border-default);
		margin-left: var(--space-md);
	}
	.zone-dot {
		width: 10px;
		height: 10px;
		border-radius: var(--radius-full);
		background: var(--zone-color);
		flex-shrink: 0;
	}
</style>
