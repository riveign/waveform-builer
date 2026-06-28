<script lang="ts">
	import type { EnergyConflict } from '$lib/types';
	import Chip from '$lib/components/primitives/Chip.svelte';

	let { conflict }: { conflict: EnergyConflict } = $props();

	// Zone colors now live as semantic tokens (--zone-*), single source of truth.
	function zoneColor(zone: string): string {
		const known = ['intro', 'warmup', 'build', 'drive', 'peak', 'close'];
		return known.includes(zone) ? `var(--zone-${zone})` : 'var(--text-2)';
	}
</script>

<Chip variant="energy" title={conflict.message}>
	<span class="zone" style:color={zoneColor(conflict.dir_energy)}>{conflict.dir_energy}</span>
	<span class="vs">/</span>
	<span class="zone" style:color={zoneColor(conflict.predicted)}>{conflict.predicted}</span>
	<span class="icon" aria-hidden="true">?</span>
</Chip>

<style>
	.zone {
		font-weight: var(--font-weight-semibold);
	}
	.vs {
		color: var(--text-4);
	}
	.icon {
		font-size: var(--text-2xs);
		font-weight: var(--font-weight-semibold);
		color: var(--accent-text);
		margin-left: var(--space-px);
	}
</style>
