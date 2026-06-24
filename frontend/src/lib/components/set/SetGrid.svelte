<script lang="ts">
	import type { DJSet } from '$lib/types';
	import { listSets, deleteSet, getDeletedSets, restoreSet } from '$lib/api/sets';
	import { onMount } from 'svelte';

	let {
		onselect,
		refreshSignal = 0,
		onchange,
	}: { onselect: (set: DJSet) => void; refreshSignal?: number; onchange?: () => void } = $props();

	const TRASH_DAYS = 3;

	let sets = $state<DJSet[]>([]);
	let loading = $state(true);
	let search = $state('');
	let viewMode = $state<'active' | 'trash'>('active');
	let confirmDeleteId = $state<number | null>(null);
	let deletingId = $state<number | null>(null);
	let restoringId = $state<number | null>(null);

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
			onchange?.();
		} catch {
			// Leave the set in place if the delete didn't go through.
		} finally {
			deletingId = null;
			confirmDeleteId = null;
		}
	}

	async function handleRestore(e: MouseEvent, s: DJSet) {
		e.stopPropagation();
		restoringId = s.id;
		try {
			await restoreSet(s.id);
			sets = sets.filter((x) => x.id !== s.id);
			onchange?.();
		} catch {
			// Leave it in the trash if restore failed.
		} finally {
			restoringId = null;
		}
	}

	/** Whole days left before a trashed set is purged for good. */
	function daysLeft(deletedAt: string | null | undefined): number {
		if (!deletedAt) return 0;
		const d = new Date(deletedAt);
		if (Number.isNaN(d.getTime())) return 0;
		const elapsedDays = (Date.now() - d.getTime()) / 86_400_000;
		return Math.max(0, Math.ceil(TRASH_DAYS - elapsedDays));
	}

	async function refresh() {
		loading = true;
		try {
			sets = viewMode === 'trash'
				? await getDeletedSets()
				: await listSets(search.trim() || undefined, 200);
		} catch {
			sets = [];
		} finally {
			loading = false;
		}
	}

	function switchMode(mode: 'active' | 'trash') {
		viewMode = mode;
		search = '';
		confirmDeleteId = null;
		refresh();
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
		<h2>{viewMode === 'trash' ? 'Recently deleted' : 'Your sets'}</h2>
		<div class="head-actions">
			{#if viewMode === 'active'}
				<input
					class="grid-search"
					placeholder="Find a set..."
					bind:value={search}
					oninput={refresh}
				/>
				<button class="mode-btn" onclick={() => switchMode('trash')} title="Recently deleted sets">
					Recently deleted
				</button>
			{:else}
				<button class="mode-btn" onclick={() => switchMode('active')}>← Back to sets</button>
			{/if}
		</div>
	</div>

	{#if loading}
		<p class="dim">{viewMode === 'trash' ? 'Opening the trash...' : 'Reading your sets...'}</p>
	{:else if filtered.length === 0}
		<p class="dim">
			{#if viewMode === 'trash'}
				Nothing in the trash. Deleted sets stay here for {TRASH_DAYS} days, then they're gone for good.
			{:else if search.trim()}
				No sets match that — try a different name.
			{:else}
				No sets yet — build or import one to start.
			{/if}
		</p>
	{:else}
		<div class="grid">
			{#each filtered as s (s.id)}
				{#if viewMode === 'active'}
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
				{:else}
					<div class="set-card trashed">
						<button
							class="card-recover"
							disabled={restoringId === s.id}
							onclick={(e) => handleRestore(e, s)}
							title="Recover this set"
						>{restoringId === s.id ? 'Recovering…' : '↺ Recover'}</button>
						<span class="card-name">{s.name ?? 'Untitled set'}</span>
						<span class="card-meta">
							{s.track_count} tracks{#if s.duration_min}, {s.duration_min}min{/if}
						</span>
						<span class="card-foot">
							<span class="tag trash-tag">{daysLeft(s.deleted_at)}d left</span>
							{#if shortDate(s.created_at)}<span class="date">{shortDate(s.created_at)}</span>{/if}
						</span>
					</div>
				{/if}
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

	.head-actions {
		display: flex;
		align-items: center;
		gap: 8px;
	}

	.mode-btn {
		padding: 7px 12px;
		font-size: 12px;
		border: 1px solid var(--border);
		border-radius: 6px;
		background: var(--bg-secondary);
		color: var(--text-secondary);
		cursor: pointer;
		white-space: nowrap;
	}

	.mode-btn:hover {
		background: var(--bg-tertiary);
		color: var(--text-primary);
	}

	.set-card.trashed {
		cursor: default;
		opacity: 0.85;
	}

	.set-card.trashed:hover {
		border-color: var(--border);
		background: var(--bg-secondary);
	}

	.card-recover {
		position: absolute;
		top: 6px;
		right: 6px;
		padding: 2px 8px;
		font-size: 11px;
		font-weight: 600;
		border: 1px solid var(--accent);
		border-radius: 5px;
		background: transparent;
		color: var(--accent);
		cursor: pointer;
	}

	.card-recover:hover:not(:disabled) {
		background: var(--accent);
		color: #000;
	}

	.card-recover:disabled {
		opacity: 0.6;
		cursor: default;
	}

	.trash-tag {
		background: rgba(239, 83, 80, 0.15);
		color: var(--energy-high, #EF5350);
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
