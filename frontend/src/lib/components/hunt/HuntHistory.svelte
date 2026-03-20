<script lang="ts">
	import type { HuntSessionSummary } from '$lib/types';

	interface Props {
		items: HuntSessionSummary[];
		onselect: (id: number) => void;
	}

	let { items, onselect }: Props = $props();
</script>

<div class="hunt-history">
	<h3>Past Hunts</h3>
	{#if items.length === 0}
		<p class="empty">No hunts yet. Paste a URL to start your first hunt.</p>
	{:else}
		<div class="history-list">
			{#each items as item}
				<button class="history-item" onclick={() => onselect(item.id)}>
					<div class="item-title">{item.title || item.url}</div>
					<div class="item-meta">
						<span class="platform">{item.platform}</span>
						<span>{item.track_count} tracks</span>
						<span class="owned-count">{item.owned_count} owned</span>
					</div>
				</button>
			{/each}
		</div>
	{/if}
</div>

<style>
	.hunt-history h3 {
		margin: 0 0 8px;
		font-size: 14px;
	}

	.empty {
		color: var(--text-dim);
		font-size: 13px;
	}

	.history-list {
		display: flex;
		flex-direction: column;
		gap: 4px;
	}

	.history-item {
		display: block;
		width: 100%;
		text-align: left;
		padding: 8px 12px;
		background: var(--bg-secondary);
		border: 1px solid var(--border);
		border-radius: 6px;
		cursor: pointer;
		color: var(--text-primary);
	}

	.history-item:hover {
		background: var(--bg-hover);
	}

	.item-title {
		font-size: 13px;
		font-weight: 500;
		margin-bottom: 2px;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.item-meta {
		font-size: 11px;
		color: var(--text-dim);
		display: flex;
		gap: 8px;
	}

	.platform {
		text-transform: capitalize;
	}

	.owned-count {
		color: #50c878;
	}
</style>
