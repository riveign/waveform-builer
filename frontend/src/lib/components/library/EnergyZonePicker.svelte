<script lang="ts" module>
	export const ZONE_COLORS: Record<string, string> = {
		intro: '#6388b4',
		warmup: '#4ecdc4',
		build: '#ffe66d',
		drive: '#f39c12',
		peak: '#ff6b6b',
		close: '#9b59b6',
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

<div class="zone-picker" class:zone-picker-inline={inline}>
	{#each ZONES as zone}
		<button
			class="zone-btn"
			class:active={current === zone}
			style="--zone-color: {ZONE_COLORS[zone]}"
			title={ZONE_TIPS[zone]}
			role="menuitem"
			onclick={() => onselect(zone)}
		>
			<span class="zone-dot"></span>
			<span class="zone-name">{zone}</span>
			{#if current === zone}
				<span class="zone-check" aria-label="current">✓</span>
			{/if}
		</button>
	{/each}
</div>

<style>
	.zone-picker {
		display: flex;
		flex-direction: column;
		gap: 2px;
	}
	.zone-picker-inline {
		padding: 4px 0 4px 12px;
		border-left: 2px solid var(--border);
		margin-left: 10px;
	}
	.zone-btn {
		display: flex;
		align-items: center;
		gap: 8px;
		padding: 5px 10px;
		border: none;
		border-radius: 4px;
		background: none;
		cursor: pointer;
		color: var(--text-primary);
		font-size: 13px;
		width: 100%;
		text-align: left;
	}
	.zone-btn:hover {
		background: var(--bg-secondary);
	}
	.zone-btn.active {
		background: color-mix(in srgb, var(--zone-color) 15%, transparent);
	}
	.zone-dot {
		width: 10px;
		height: 10px;
		border-radius: 50%;
		background: var(--zone-color);
		flex-shrink: 0;
	}
	.zone-check {
		margin-left: auto;
		font-size: 11px;
		color: var(--zone-color);
	}
</style>
