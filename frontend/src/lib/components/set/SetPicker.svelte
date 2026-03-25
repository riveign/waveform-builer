<script lang="ts">
	import type { DJSet, ImportResult } from '$lib/types';
	import { listSets } from '$lib/api/sets';
	import { onMount } from 'svelte';
	import ImportPlaylistDialog from './ImportPlaylistDialog.svelte';

	let { onselect }: { onselect: (set: DJSet) => void } = $props();

	let sets = $state<DJSet[]>([]);
	let loading = $state(true);
	let importOpen = $state(false);

	onMount(async () => {
		try {
			sets = await listSets();
		} catch {
			sets = [];
		} finally {
			loading = false;
		}
	});

	async function handleImport(result: ImportResult) {
		// Reload sets and select the newly imported one
		sets = await listSets();
		const imported = sets.find(s => s.id === result.set_id);
		if (imported) onselect(imported);
	}
</script>

<div class="set-picker">
	{#if loading}
		<span class="dim">Finding your sets...</span>
	{:else}
		<div class="picker-row">
			{#if sets.length === 0}
				<span class="dim">No sets yet — build or import one</span>
			{:else}
				<select onchange={(e) => {
					const id = Number((e.target as HTMLSelectElement).value);
					const s = sets.find(s => s.id === id);
					if (s) onselect(s);
				}}>
					<option value="">Choose a set...</option>
					{#each sets as s (s.id)}
						<option value={s.id}>
							{s.name} ({s.track_count} tracks{s.source === 'm3u8' ? ', imported' : ''})
						</option>
					{/each}
				</select>
			{/if}
			<button class="import-btn" onclick={() => importOpen = true} title="Import playlist">
				Import
			</button>
		</div>
	{/if}
</div>

<ImportPlaylistDialog bind:open={importOpen} onimport={handleImport} />

<style>
	.set-picker {
		padding: 10px 16px;
		border-bottom: 1px solid var(--border);
	}

	.picker-row {
		display: flex;
		gap: 8px;
		align-items: center;
	}

	select {
		flex: 1;
		padding: 8px 10px;
		font-size: 13px;
	}

	.import-btn {
		padding: 8px 12px;
		font-size: 12px;
		border: 1px solid var(--border);
		border-radius: 6px;
		background: var(--bg-secondary);
		color: var(--text-primary);
		cursor: pointer;
		white-space: nowrap;
	}

	.import-btn:hover {
		background: var(--bg-tertiary);
	}

	.dim {
		color: var(--text-dim);
		font-size: 13px;
	}
</style>
