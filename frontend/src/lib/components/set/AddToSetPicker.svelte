<script lang="ts">
	import type { DJSet } from '$lib/types';
	import { listSets, createSet, addTrackToSet } from '$lib/api/sets';
	import { onMount } from 'svelte';
	import Button from '$lib/components/primitives/Button.svelte';
	import MenuItem from '$lib/components/primitives/MenuItem.svelte';

	let {
		trackId,
		trackTitle = 'track',
		onclose,
		onadded,
	}: {
		trackId: number;
		trackTitle?: string;
		onclose: () => void;
		onadded?: (setId: number, setName: string) => void;
	} = $props();

	let sets = $state<DJSet[]>([]);
	let search = $state('');
	let loading = $state(true);
	let adding = $state<number | null>(null);
	let creatingNew = $state(false);
	let newName = $state('');
	let trackSetIds = $state<Set<number>>(new Set());
	let toast = $state<string | null>(null);
	let inputEl = $state<HTMLInputElement | null>(null);
	let searchEl = $state<HTMLInputElement | null>(null);

	let filtered = $derived(
		search
			? sets.filter((s) => (s.name ?? '').toLowerCase().includes(search.toLowerCase()))
			: sets
	);

	onMount(async () => {
		try {
			const allSets = await listSets('', 100);
			sets = allSets;
		} catch {
			sets = [];
		} finally {
			loading = false;
			searchEl?.focus();
		}
	});

	async function handlePickSet(set: DJSet) {
		if (trackSetIds.has(set.id)) return;
		adding = set.id;
		try {
			await addTrackToSet(set.id, trackId);
			trackSetIds = new Set([...trackSetIds, set.id]);
			onadded?.(set.id, set.name ?? 'set');
			showToast(`Added to ${set.name}`);
			onclose();
		} catch {
			showToast('Could not add track');
		} finally {
			adding = null;
		}
	}

	async function handleCreateAndAdd() {
		if (!newName.trim()) return;
		adding = -1;
		try {
			const newSet = await createSet({ name: newName.trim(), source: 'manual' });
			await addTrackToSet(newSet.id, trackId);
			onadded?.(newSet.id, newSet.name ?? newName.trim());
			showToast(`Created "${newName.trim()}" and added track`);
			onclose();
		} catch {
			showToast('Could not create set');
		} finally {
			adding = null;
			creatingNew = false;
			newName = '';
		}
	}

	function showToast(msg: string) {
		toast = msg;
		setTimeout(() => { toast = null; }, 3000);
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Escape') {
			if (creatingNew) {
				creatingNew = false;
				newName = '';
			} else {
				onclose();
			}
		}
	}
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<div class="add-to-set-picker" onkeydown={handleKeydown}>
	<input
		bind:this={searchEl}
		bind:value={search}
		placeholder="Search sets..."
		class="search-input"
	/>

	<div class="set-list">
		{#if creatingNew}
			<div class="new-set-row">
				<input
					bind:this={inputEl}
					bind:value={newName}
					placeholder="Set name..."
					class="new-set-input"
					onkeydown={(e) => { if (e.key === 'Enter') handleCreateAndAdd(); if (e.key === 'Escape') { creatingNew = false; newName = ''; } }}
				/>
				<Button
					variant="primary"
					size="sm"
					loading={adding === -1}
					disabled={!newName.trim() || adding !== null}
					onclick={handleCreateAndAdd}
				>
					Create
				</Button>
			</div>
		{:else}
			<MenuItem onselect={() => { creatingNew = true; setTimeout(() => inputEl?.focus(), 0); }}>
				<span class="new-set-trigger">+ New set</span>
			</MenuItem>
		{/if}

		{#if loading}
			<div class="loading">Finding your sets...</div>
		{:else if filtered.length === 0}
			<div class="empty">No sets found</div>
		{:else}
			{#each filtered as set (set.id)}
				{@const inSet = trackSetIds.has(set.id)}
				<MenuItem
					disabled={inSet || adding !== null}
					onselect={() => handlePickSet(set)}
				>
					<span class="set-row-body">
						<span class="set-name">{set.name}</span>
						<span class="set-meta">
							{#if inSet}
								(already in set)
							{:else if adding === set.id}
								...
							{:else}
								{set.track_count} tracks
							{/if}
						</span>
					</span>
				</MenuItem>
			{/each}
		{/if}
	</div>
</div>

{#if toast}
	<div class="toast">{toast}</div>
{/if}

<style>
	.add-to-set-picker {
		display: flex;
		flex-direction: column;
		min-width: 220px;
		max-height: 320px;
		overflow: hidden;
	}

	.search-input {
		padding: var(--space-md) var(--space-lg);
		font-size: var(--text-base);
		border: none;
		border-bottom: 1px solid var(--border);
		background: transparent;
		color: var(--text-primary);
		outline: none;
	}

	.set-list {
		overflow-y: auto;
		flex: 1;
	}

	.set-row-body {
		display: flex;
		align-items: center;
		gap: var(--space-md);
		width: 100%;
		min-width: 0;
	}

	.new-set-trigger {
		color: var(--accent-text);
		font-weight: var(--font-weight-semibold);
	}

	.set-name {
		flex: 1;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.set-meta {
		font-size: var(--text-xs);
		color: var(--text-dim);
		white-space: nowrap;
	}

	.new-set-row {
		display: flex;
		gap: var(--space-xs);
		padding: var(--space-sm) var(--space-md);
	}

	.new-set-input {
		flex: 1;
		padding: var(--space-sm) var(--space-md);
		font-size: var(--text-base);
		background: var(--bg-secondary);
		border: 1px solid var(--border);
		border-radius: var(--radius-sm);
		color: var(--text-primary);
	}

	.loading, .empty {
		padding: var(--space-lg) var(--space-lg);
		font-size: var(--text-sm);
		color: var(--text-dim);
	}

	.toast {
		position: fixed;
		bottom: 80px;
		left: 50%;
		transform: translateX(-50%);
		background: var(--bg-secondary);
		color: var(--text-primary);
		padding: var(--space-md) var(--space-xl);
		border-radius: var(--radius-md);
		font-size: var(--text-base);
		border: 1px solid var(--border);
		z-index: 1000;
		animation: toast-in 0.2s ease-out;
	}

	@keyframes toast-in {
		from { opacity: 0; transform: translateX(-50%) translateY(8px); }
		to { opacity: 1; transform: translateX(-50%) translateY(0); }
	}
</style>
