<script lang="ts">
	import type { EnergyConflict } from '$lib/types';

	let { conflict }: { conflict: EnergyConflict } = $props();

	const zoneColors: Record<string, string> = {
		warmup: '#4ecdc4',
		build: '#ffe66d',
		drive: '#f39c12',
		peak: '#ff6b6b',
		close: '#9b59b6',
	};
</script>

<span class="conflict-badge" title={conflict.message}>
	<span class="zone" style="color: {zoneColors[conflict.dir_energy] ?? 'var(--text-secondary)'}">
		{conflict.dir_energy}
	</span>
	<span class="vs">/</span>
	<span class="zone" style="color: {zoneColors[conflict.predicted] ?? 'var(--text-secondary)'}">
		{conflict.predicted}
	</span>
	<span class="icon">?</span>
</span>

<style>
	.conflict-badge {
		display: inline-flex;
		align-items: center;
		gap: 2px;
		padding: 1px 5px;
		border-radius: 3px;
		background: rgba(255, 190, 11, 0.1);
		border: 1px solid rgba(255, 190, 11, 0.3);
		font-size: 9px;
		text-transform: uppercase;
		letter-spacing: 0.3px;
		cursor: help;
	}

	.zone {
		font-weight: 600;
	}

	.vs {
		color: var(--text-dim);
		font-size: 8px;
	}

	.icon {
		font-size: 8px;
		font-weight: 700;
		color: var(--accent);
		margin-left: 1px;
	}
</style>
