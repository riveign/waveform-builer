<script lang="ts">
	import type { SuggestNextItem } from '$lib/types';
	import { suggestNext } from '$lib/api/tracks';
	import { addTrackToSet } from '$lib/api/sets';
	import { getCamelotColor } from '$lib/utils/camelot';

	let {
		trackId,
		setId,
		onAdd,
	}: {
		trackId: number;
		setId: number;
		onAdd?: () => void;
	} = $props();

	let suggestions = $state<SuggestNextItem[]>([]);
	let loading = $state(true);
	let error = $state<string | null>(null);
	let addingId = $state<number | null>(null);

	async function load() {
		loading = true;
		error = null;
		try {
			const res = await suggestNext(trackId, 10);
			suggestions = res.suggestions;
		} catch (e) {
			error = e instanceof Error ? e.message : 'Could not load suggestions';
		} finally {
			loading = false;
		}
	}

	async function handleAdd(item: SuggestNextItem) {
		addingId = item.track.id;
		try {
			await addTrackToSet(setId, item.track.id);
			suggestions = suggestions.filter((s) => s.track.id !== item.track.id);
			onAdd?.();
		} catch (e) {
			error = e instanceof Error ? e.message : 'Could not add track';
		} finally {
			addingId = null;
		}
	}

	function scoreColor(score: number): string {
		if (score >= 0.8) return 'var(--energy-low, #4ecdc4)';
		if (score >= 0.6) return 'var(--accent, #00CED1)';
		if (score >= 0.4) return 'var(--text-secondary, #999)';
		return 'var(--energy-high, #ff6b6b)';
	}

	// Load on mount
	load();
</script>

<div class="suggest-panel">
	<div class="suggest-header">
		<h4>What could come next</h4>
	</div>

	{#if loading}
		<div class="suggest-status">Exploring your library...</div>
	{:else if error}
		<div class="suggest-status error">{error}</div>
	{:else if suggestions.length === 0}
		<div class="suggest-status">No strong suggestions found for this track</div>
	{:else}
		<div class="suggest-list">
			{#each suggestions as item, i (item.track.id)}
				<div class="suggest-row">
					<span class="rank">#{i + 1}</span>
					<span class="score-badge" style="color: {scoreColor(item.score)}">
						{(item.score * 100).toFixed(0)}
					</span>
					<div class="suggest-info">
						<span class="suggest-title">{item.track.title ?? '?'}</span>
						<span class="suggest-artist">{item.track.artist ?? '?'}</span>
					</div>
					{#if item.track.key}
						<span class="key-badge" style="color: {getCamelotColor(item.track.key)}">{item.track.key}</span>
					{/if}
					{#if item.track.bpm}
						<span class="bpm-badge">{Math.round(item.track.bpm)}</span>
					{/if}
					<button
						class="add-btn"
						onclick={() => handleAdd(item)}
						disabled={addingId === item.track.id}
					>
						{addingId === item.track.id ? '...' : 'Add'}
					</button>
				</div>
			{/each}
		</div>
	{/if}
</div>

<style>
	.suggest-panel {
		border-top: 1px solid var(--border);
		padding: 12px 16px;
	}

	.suggest-header h4 {
		font-size: 13px;
		font-weight: 600;
		color: var(--text-primary);
		margin: 0 0 8px;
	}

	.suggest-status {
		font-size: 12px;
		color: var(--text-secondary);
		padding: 8px 0;
	}

	.suggest-status.error {
		color: var(--energy-high, #ff6b6b);
	}

	.suggest-list {
		display: flex;
		flex-direction: column;
		gap: 2px;
	}

	.suggest-row {
		display: flex;
		align-items: center;
		gap: 8px;
		padding: 6px 8px;
		border-radius: 4px;
		transition: background 0.1s;
	}

	.suggest-row:hover {
		background: var(--bg-secondary);
	}

	.rank {
		font-size: 11px;
		color: var(--text-dim);
		width: 20px;
		text-align: right;
		font-variant-numeric: tabular-nums;
	}

	.score-badge {
		font-size: 12px;
		font-weight: 700;
		font-variant-numeric: tabular-nums;
		min-width: 28px;
		text-align: center;
	}

	.suggest-info {
		flex: 1;
		min-width: 0;
		display: flex;
		flex-direction: column;
		gap: 1px;
	}

	.suggest-title {
		font-size: 12px;
		font-weight: 600;
		color: var(--text-primary);
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.suggest-artist {
		font-size: 11px;
		color: var(--text-secondary);
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.key-badge {
		font-size: 11px;
		font-weight: 600;
		padding: 1px 5px;
		background: var(--bg-tertiary);
		border-radius: 3px;
	}

	.bpm-badge {
		font-size: 11px;
		color: var(--text-secondary);
		font-variant-numeric: tabular-nums;
	}

	.add-btn {
		padding: 3px 10px;
		font-size: 11px;
		font-weight: 600;
		border-radius: 3px;
		background: var(--bg-tertiary);
		color: var(--text-primary);
		border: 1px solid var(--border);
		transition: all 0.15s;
	}

	.add-btn:hover:not(:disabled) {
		background: var(--accent);
		color: #000;
		border-color: var(--accent);
	}

	.add-btn:disabled {
		opacity: 0.4;
	}
</style>
