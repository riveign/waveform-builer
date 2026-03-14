<script lang="ts">
	import type { DJSet } from '$lib/types';
	import { listSets } from '$lib/api/sets';
	import { onMount } from 'svelte';

	let { onselect }: { onselect: (set: DJSet) => void } = $props();

	let sets = $state<DJSet[]>([]);
	let loading = $state(true);

	onMount(async () => {
		try {
			sets = await listSets();
		} catch {
			sets = [];
		} finally {
			loading = false;
		}
	});
</script>

<div class="set-picker">
	{#if loading}
		<span class="dim">Loading sets...</span>
	{:else if sets.length === 0}
		<span class="dim">No sets found. Run <code>djset build</code> first.</span>
	{:else}
		<select onchange={(e) => {
			const id = Number((e.target as HTMLSelectElement).value);
			const s = sets.find(s => s.id === id);
			if (s) onselect(s);
		}}>
			<option value="">Select a set...</option>
			{#each sets as s (s.id)}
				<option value={s.id}>
					{s.name} ({s.track_count} tracks, {s.duration_min}min)
				</option>
			{/each}
		</select>
	{/if}
</div>

<style>
	.set-picker {
		padding: 10px 16px;
		border-bottom: 1px solid var(--border);
	}

	select {
		width: 100%;
		padding: 8px 10px;
		font-size: 13px;
	}

	.dim {
		color: var(--text-dim);
		font-size: 13px;
	}

	code {
		background: var(--bg-tertiary);
		padding: 2px 6px;
		border-radius: 3px;
		font-size: 12px;
	}
</style>
