<script lang="ts">
	import type { DJSet } from '$lib/types';
	import { listSets, deleteSet } from '$lib/api/sets';
	import { onMount } from 'svelte';

	let {
		onselect,
		refreshSignal = 0,
		ondelete,
	}: { onselect: (set: DJSet) => void; refreshSignal?: number; ondelete?: () => void } = $props();

	let sets = $state<DJSet[]>([]);
	let loading = $state(true);
	let search = $state('');
	let confirmDeleteId = $state<number | null>(null);
	let deletingId = $state<number | null>(null);

	async function handleDelete(e: MouseEvent, s: DJSet) {
		e.stopPropagation();
		// Two-click confirm: first click arms, second within 3s deletes.
		if (confirmDeleteId !== s.id) {
			confirmDeleteId = s.id;
			setTimeout(() => { if (confirmDeleteId === s.id) confirmDeleteId = null; }, 3000);
			return;
		}
		deletingId = s.id;
		try {
			await deleteSet(s.id);
			sets = sets.filter((x) => x.id !== s.id);
			ondelete?.();
		} catch {
			// Leave the set in place if the delete didn't go through.
		} finally {
			deletingId = null;
			confirmDeleteId = null;
		}
	}

	async function refresh() {
		loading = true;
		try {
			sets = await listSets(search.trim() || undefined, 200);
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

	let filtered = $derived(sets);

	function sourceLabel(source: string | null): string {
		switch (source) {
			case 'm3u8':
				return 'imported';
			case 'kiku':
				return 'built';
			case 'manual':
				return 'hand-built';
			case 'rb_playlist':
				return 'Rekordbox';
			default:
				return '';
		}
	}

	function shortDate(iso: string | null): string {
		if (!iso) return '';
		const d = new Date(iso);
		if (Number.isNaN(d.getTime())) return '';
		return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
	}
</script>

<div class="set-grid-wrap">
	<div class="grid-head">
		<h2>Your sets</h2>
		<input
			class="grid-search"
			placeholder="Find a set..."
			bind:value={search}
			oninput={refresh}
		/>
	</div>

	{#if loading}
		<p class="dim">Reading your sets...</p>
	{:else if filtered.length === 0}
		<p class="dim">
			{search.trim() ? 'No sets match that — try a different name.' : 'No sets yet — build or import one to start.'}
		</p>
	{:else}
		<div class="grid">
			{#each filtered as s (s.id)}
				<div
					class="set-card"
					role="button"
					tabindex="0"
					onclick={() => onselect(s)}
					onkeydown={(e) => { if (e.key === 'Enter') onselect(s); }}
				>
					<button
						class="card-delete"
						class:confirm={confirmDeleteId === s.id}
						title={confirmDeleteId === s.id ? 'Click again to delete' : 'Delete set'}
						aria-label="Delete set {s.name ?? ''}"
						disabled={deletingId === s.id}
						onclick={(e) => handleDelete(e, s)}
					>{confirmDeleteId === s.id ? 'Delete?' : '×'}</button>
					<span class="card-name">{s.name ?? 'Untitled set'}</span>
					<span class="card-meta">
						{s.track_count} tracks{#if s.duration_min}, {s.duration_min}min{/if}
					</span>
					<span class="card-foot">
						{#if sourceLabel(s.source)}<span class="tag">{sourceLabel(s.source)}</span>{/if}
						{#if shortDate(s.created_at)}<span class="date">{shortDate(s.created_at)}</span>{/if}
					</span>
				</div>
			{/each}
		</div>
	{/if}
</div>

<style>
	.set-grid-wrap {
		padding: 20px 24px;
		overflow-y: auto;
	}

	.grid-head {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 16px;
		margin-bottom: 16px;
	}

	.grid-head h2 {
		margin: 0;
		font-size: 16px;
		font-weight: 600;
		color: var(--text-primary);
	}

	.grid-search {
		padding: 7px 10px;
		font-size: 13px;
		border: 1px solid var(--border);
		border-radius: 6px;
		background: var(--bg-secondary);
		color: var(--text-primary);
		min-width: 220px;
	}

	.grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
		gap: 12px;
	}

	.set-card {
		position: relative;
		display: flex;
		flex-direction: column;
		gap: 6px;
		padding: 14px;
		text-align: left;
		border: 1px solid var(--border);
		border-radius: 8px;
		background: var(--bg-secondary);
		color: var(--text-primary);
		cursor: pointer;
		transition: border-color 0.15s, background 0.15s;
	}

	.set-card:hover {
		border-color: var(--accent);
		background: var(--bg-tertiary);
	}

	.card-delete {
		position: absolute;
		top: 6px;
		right: 6px;
		min-width: 20px;
		height: 20px;
		padding: 0 6px;
		display: flex;
		align-items: center;
		justify-content: center;
		font-size: 13px;
		line-height: 1;
		border: 1px solid var(--border);
		border-radius: 5px;
		background: var(--bg-primary);
		color: var(--text-dim);
		cursor: pointer;
		opacity: 0;
		transition: opacity 0.15s, color 0.15s, border-color 0.15s;
	}

	.set-card:hover .card-delete,
	.card-delete:focus-visible {
		opacity: 1;
	}

	.card-delete:hover {
		color: var(--energy-high, #EF5350);
		border-color: var(--energy-high, #EF5350);
	}

	.card-delete.confirm {
		opacity: 1;
		font-size: 11px;
		font-weight: 600;
		color: #fff;
		background: var(--energy-high, #EF5350);
		border-color: var(--energy-high, #EF5350);
	}

	.card-name {
		font-size: 14px;
		font-weight: 600;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.card-meta {
		font-size: 12px;
		color: var(--text-dim);
	}

	.card-foot {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 8px;
		margin-top: 2px;
	}

	.tag {
		font-size: 10px;
		text-transform: uppercase;
		letter-spacing: 0.04em;
		padding: 2px 6px;
		border-radius: 4px;
		background: var(--bg-tertiary);
		color: var(--text-dim);
	}

	.date {
		font-size: 11px;
		color: var(--text-dim);
	}

	.dim {
		color: var(--text-dim);
		font-size: 13px;
	}
</style>
