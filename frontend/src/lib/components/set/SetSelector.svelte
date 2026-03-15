<script lang="ts">
	import type { DJSet } from '$lib/types';
	import { listSets, createSet, deleteSet } from '$lib/api/sets';
	import { getUiStore } from '$lib/stores/ui.svelte';
	import { onMount } from 'svelte';

	let {
		onselect,
		refreshTrigger = 0,
		selectSetId = null,
	}: {
		onselect: (set: DJSet) => void;
		refreshTrigger?: number;
		selectSetId?: number | null;
	} = $props();

	const ui = getUiStore();

	let sets = $state<DJSet[]>([]);
	let loading = $state(true);
	let error = $state<string | null>(null);

	// Create form state
	let showCreateForm = $state(false);
	let newSetName = $state('');
	let creating = $state(false);

	// Delete confirmation state
	let confirmDeleteId = $state<number | null>(null);
	let deleting = $state(false);

	let selectedSet = $derived(sets.find((s) => s.id === ui.selectedSetId) ?? null);

	onMount(async () => {
		await fetchSets();
	});

	// Re-fetch sets when refreshTrigger changes (parent increments after build completes)
	let lastTrigger = 0;
	$effect(() => {
		const trigger = refreshTrigger;
		if (trigger > lastTrigger) {
			lastTrigger = trigger;
			fetchSets().then(() => {
				// After refresh, auto-select the set if selectSetId is provided
				if (selectSetId !== null) {
					const target = sets.find((s) => s.id === selectSetId);
					if (target) {
						selectSet(target);
					}
				}
			});
		}
	});

	// Auto-detect when ui.selectedSetId points to a set not in the list (e.g. just built)
	$effect(() => {
		const currentId = ui.selectedSetId;
		if (currentId !== null && !loading && sets.length > 0 && !sets.find((s) => s.id === currentId)) {
			fetchSets().then(() => {
				const target = sets.find((s) => s.id === currentId);
				if (target) {
					onselect(target);
				}
			});
		}
	});

	async function fetchSets() {
		loading = true;
		error = null;
		try {
			sets = await listSets();
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load sets';
			sets = [];
		} finally {
			loading = false;
		}
	}

	function selectSet(set: DJSet) {
		ui.selectedSetId = set.id;
		confirmDeleteId = null;
		onselect(set);
	}

	async function handleCreate() {
		const name = newSetName.trim();
		if (!name || creating) return;
		creating = true;
		error = null;
		try {
			const newSet = await createSet({ name });
			sets = [...sets, newSet];
			newSetName = '';
			showCreateForm = false;
			selectSet(newSet);
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to create set';
		} finally {
			creating = false;
		}
	}

	function handleCreateKeydown(e: KeyboardEvent) {
		if (e.key === 'Enter') {
			handleCreate();
		} else if (e.key === 'Escape') {
			showCreateForm = false;
			newSetName = '';
		}
	}

	async function handleDelete(id: number) {
		if (deleting) return;
		deleting = true;
		error = null;
		try {
			await deleteSet(id);
			sets = sets.filter((s) => s.id !== id);
			confirmDeleteId = null;
			if (ui.selectedSetId === id) {
				const next = sets[0] ?? null;
				ui.selectedSetId = next?.id ?? null;
				if (next) onselect(next);
			}
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to delete set';
		} finally {
			deleting = false;
		}
	}
</script>

<div class="set-selector">
	<div class="header">
		<span class="title">Sets</span>
		<button
			class="create-btn"
			onclick={() => { showCreateForm = !showCreateForm; }}
			title="Create new set"
		>+</button>
	</div>

	{#if showCreateForm}
		<div class="create-form">
			<input
				type="text"
				class="create-input"
				placeholder="Set name..."
				bind:value={newSetName}
				onkeydown={handleCreateKeydown}
				disabled={creating}
			/>
			<button
				class="action-btn confirm"
				onclick={handleCreate}
				disabled={creating || !newSetName.trim()}
			>
				{creating ? '...' : 'Create'}
			</button>
			<button
				class="action-btn cancel"
				onclick={() => { showCreateForm = false; newSetName = ''; }}
			>
				Cancel
			</button>
		</div>
	{/if}

	{#if error}
		<div class="error-bar">{error}</div>
	{/if}

	<div class="set-list">
		{#if loading}
			<div class="status">Loading sets...</div>
		{:else if sets.length === 0}
			<div class="status">No sets yet. Create one to get started.</div>
		{:else}
			{#each sets as s (s.id)}
				<!-- svelte-ignore a11y_no_static_element_interactions -->
				<div
					class="set-item"
					class:active={s.id === ui.selectedSetId}
					onclick={() => selectSet(s)}
					onkeydown={(e: KeyboardEvent) => { if (e.key === 'Enter' || e.key === ' ') selectSet(s); }}
					role="option"
					aria-selected={s.id === ui.selectedSetId}
					tabindex="0"
				>
					<div class="set-info">
						<span class="set-name">{s.name ?? 'Untitled'}</span>
						<span class="set-meta">
							{s.track_count} tracks{#if s.duration_min}, {s.duration_min}min{/if}
						</span>
					</div>
					<div class="set-actions">
						{#if confirmDeleteId === s.id}
							<button
								class="action-btn danger"
								onclick={(e: MouseEvent) => { e.stopPropagation(); handleDelete(s.id); }}
								disabled={deleting}
							>
								{deleting ? '...' : 'Yes'}
							</button>
							<button
								class="action-btn cancel"
								onclick={(e: MouseEvent) => { e.stopPropagation(); confirmDeleteId = null; }}
							>
								No
							</button>
						{:else}
							<button
								class="delete-btn"
								onclick={(e: MouseEvent) => { e.stopPropagation(); confirmDeleteId = s.id; }}
								title="Delete set"
							>
								&times;
							</button>
						{/if}
					</div>
				</div>
			{/each}
		{/if}
	</div>

	{#if selectedSet}
		<div class="selected-detail">
			<span class="detail-label">Selected:</span>
			<span class="detail-value">{selectedSet.name ?? 'Untitled'}</span>
		</div>
	{/if}
</div>

<style>
	.set-selector {
		display: flex;
		flex-direction: column;
		border-bottom: 1px solid var(--border);
	}

	.header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 8px 16px;
		border-bottom: 1px solid var(--border);
	}

	.title {
		font-weight: 600;
		font-size: 13px;
		color: var(--text-primary);
		text-transform: uppercase;
		letter-spacing: 0.5px;
	}

	.create-btn {
		width: 24px;
		height: 24px;
		display: flex;
		align-items: center;
		justify-content: center;
		font-size: 16px;
		font-weight: 600;
		color: var(--text-secondary);
		background: var(--bg-tertiary);
		border: 1px solid var(--border);
		border-radius: 4px;
		cursor: pointer;
		transition: all 0.15s;
	}

	.create-btn:hover {
		background: var(--accent);
		color: #000;
		border-color: var(--accent);
	}

	.create-form {
		display: flex;
		gap: 6px;
		padding: 8px 16px;
		border-bottom: 1px solid var(--border);
	}

	.create-input {
		flex: 1;
		padding: 6px 8px;
		font-size: 13px;
		background: var(--bg-tertiary);
		border: 1px solid var(--border);
		border-radius: 4px;
		color: var(--text-primary);
		outline: none;
	}

	.create-input:focus {
		border-color: var(--accent);
	}

	.create-input:disabled {
		opacity: 0.5;
	}

	.error-bar {
		padding: 6px 16px;
		font-size: 12px;
		color: var(--energy-high, #ff4444);
		background: rgba(255, 68, 68, 0.1);
		border-bottom: 1px solid var(--border);
	}

	.set-list {
		max-height: 200px;
		overflow-y: auto;
	}

	.set-item {
		display: flex;
		align-items: center;
		justify-content: space-between;
		width: 100%;
		padding: 8px 16px;
		background: transparent;
		border: none;
		border-bottom: 1px solid var(--border);
		cursor: pointer;
		text-align: left;
		color: var(--text-primary);
		transition: background 0.1s;
	}

	.set-item:hover {
		background: var(--bg-tertiary);
	}

	.set-item.active {
		background: var(--bg-tertiary);
		border-left: 3px solid var(--accent);
		padding-left: 13px;
	}

	.set-info {
		display: flex;
		flex-direction: column;
		gap: 2px;
		min-width: 0;
	}

	.set-name {
		font-size: 13px;
		font-weight: 500;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.set-meta {
		font-size: 11px;
		color: var(--text-dim);
	}

	.set-actions {
		display: flex;
		gap: 4px;
		align-items: center;
		flex-shrink: 0;
	}

	.delete-btn {
		width: 20px;
		height: 20px;
		display: flex;
		align-items: center;
		justify-content: center;
		font-size: 14px;
		color: var(--text-dim);
		background: transparent;
		border: none;
		border-radius: 3px;
		cursor: pointer;
		opacity: 0;
		transition: all 0.15s;
	}

	.set-item:hover .delete-btn {
		opacity: 1;
	}

	.delete-btn:hover {
		color: var(--energy-high, #ff4444);
		background: rgba(255, 68, 68, 0.1);
	}

	.action-btn {
		padding: 3px 8px;
		font-size: 11px;
		border: 1px solid var(--border);
		border-radius: 3px;
		cursor: pointer;
		transition: all 0.15s;
		background: var(--bg-tertiary);
		color: var(--text-secondary);
	}

	.action-btn.confirm {
		color: var(--accent);
		border-color: var(--accent);
	}

	.action-btn.confirm:hover:not(:disabled) {
		background: var(--accent);
		color: #000;
	}

	.action-btn.confirm:disabled {
		opacity: 0.4;
		cursor: default;
	}

	.action-btn.danger {
		color: var(--energy-high, #ff4444);
		border-color: var(--energy-high, #ff4444);
	}

	.action-btn.danger:hover:not(:disabled) {
		background: var(--energy-high, #ff4444);
		color: #fff;
	}

	.action-btn.cancel:hover {
		background: var(--bg-secondary);
	}

	.status {
		padding: 16px;
		text-align: center;
		font-size: 13px;
		color: var(--text-dim);
	}

	.selected-detail {
		display: flex;
		gap: 6px;
		padding: 6px 16px;
		font-size: 11px;
		color: var(--text-dim);
		border-top: 1px solid var(--border);
	}

	.detail-label {
		color: var(--text-dim);
	}

	.detail-value {
		color: var(--accent);
		font-weight: 500;
	}
</style>
