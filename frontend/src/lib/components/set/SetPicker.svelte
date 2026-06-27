<script lang="ts">
	import type { DJSet, ImportResult } from '$lib/types';
	import { listSets, createSet } from '$lib/api/sets';
	import { onMount } from 'svelte';
	import ImportPlaylistDialog from './ImportPlaylistDialog.svelte';
	import Button from '$lib/components/primitives/Button.svelte';
	import { getUiStore } from '$lib/stores/ui.svelte';

	const ui = getUiStore();

	let { onselect, refreshSignal = 0 }: { onselect: (set: DJSet) => void; refreshSignal?: number } = $props();

	let sets = $state<DJSet[]>([]);
	let loading = $state(true);
	let importOpen = $state(false);
	let creatingNew = $state(false);
	let newName = $state('');
	let newInputEl = $state<HTMLInputElement | null>(null);

	async function refresh() {
		try {
			sets = await listSets();
		} catch {
			sets = [];
		} finally {
			loading = false;
		}
	}

	onMount(refresh);

	$effect(() => {
		if (refreshSignal > 0) refresh();
	});

	async function handleImport(result: ImportResult) {
		// Reload sets and select the newly imported one
		sets = await listSets();
		const imported = sets.find(s => s.id === result.set_id);
		if (imported) onselect(imported);
	}

	async function handleCreateNew() {
		if (!newName.trim()) return;
		try {
			const newSet = await createSet({ name: newName.trim(), source: 'manual' });
			sets = await listSets();
			onselect(newSet);
		} catch {
			// Silently fail — the DJ can try again
		} finally {
			creatingNew = false;
			newName = '';
		}
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
			{#if creatingNew}
				<input
					bind:this={newInputEl}
					bind:value={newName}
					placeholder="Set name..."
					class="new-set-input"
					onkeydown={(e) => { if (e.key === 'Enter') handleCreateNew(); if (e.key === 'Escape') { creatingNew = false; newName = ''; } }}
				/>
			{:else}
				<Button variant="primary" size="sm" onclick={() => { creatingNew = true; setTimeout(() => newInputEl?.focus(), 0); }} title="Create new set">
					+ New
				</Button>
			{/if}
			<Button variant="primary" size="sm" onclick={() => ui.requestBuild()} title="Build a set with energy, genre and vibe">
				Build
			</Button>
			<Button variant="secondary" size="sm" onclick={() => importOpen = true} title="Import playlist">
				Import
			</Button>
		</div>
	{/if}
</div>

<ImportPlaylistDialog bind:open={importOpen} onimport={handleImport} />

<style>
	/* Toolbar band — matches the sidebar's search box: same --band-toolbar-h (48px)
	   and the same zero top offset, so the "Choose a set…" selector's bottom edge /
	   divider lands at the SAME y as the search box (spec 023 band rhythm). */
	.set-picker {
		display: flex;
		align-items: center;
		padding: 0 var(--space-xl);
		height: var(--band-toolbar-h);
		border-bottom: 1px solid var(--border);
	}

	.picker-row {
		display: flex;
		gap: var(--space-md);
		align-items: center;
		width: 100%;
	}

	select {
		flex: 1;
		padding: var(--space-md) var(--space-lg);
		font-size: var(--text-base);
	}

	.new-set-input {
		padding: var(--space-md) var(--space-lg);
		font-size: var(--text-base);
		border: 1px solid var(--border);
		border-radius: 6px;
		background: var(--bg-secondary);
		color: var(--text-primary);
	}

	.dim {
		color: var(--text-dim);
		font-size: var(--text-base);
	}
</style>
