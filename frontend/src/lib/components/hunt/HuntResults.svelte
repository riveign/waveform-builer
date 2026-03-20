<script lang="ts">
	import type { HuntSession } from '$lib/types';

	interface Props {
		hunt: HuntSession;
		onmarkwanted: (trackId: number) => void;
	}

	let { hunt, onmarkwanted }: Props = $props();

	const owned = $derived(hunt.tracks.filter((t) => t.acquisition_status === 'owned').length);
	const total = $derived(hunt.tracks.length);
</script>

<div class="hunt-results">
	<div class="results-header">
		<div>
			<h3>{hunt.title || 'Untitled Set'}</h3>
			{#if hunt.uploader}
				<span class="uploader">by {hunt.uploader}</span>
			{/if}
		</div>
		<div class="gap-badge">
			{#if owned === total}
				<span class="badge owned">You own all {total} tracks</span>
			{:else}
				<span class="badge gap">Missing {total - owned} of {total}</span>
			{/if}
		</div>
	</div>

	<table class="track-table">
		<thead>
			<tr>
				<th class="col-pos">#</th>
				<th class="col-artist">Artist</th>
				<th class="col-title">Title</th>
				<th class="col-source">Source</th>
				<th class="col-status">Status</th>
				<th class="col-links">Links</th>
			</tr>
		</thead>
		<tbody>
			{#each hunt.tracks as track}
				<tr class:owned={track.acquisition_status === 'owned'}>
					<td class="col-pos">{track.position}</td>
					<td class="col-artist">{track.artist ?? '?'}</td>
					<td class="col-title">
						{track.title ?? '?'}
						{#if track.remix_info}
							<span class="remix">({track.remix_info})</span>
						{/if}
					</td>
					<td class="col-source">{track.source ?? ''}</td>
					<td class="col-status">
						{#if track.acquisition_status === 'owned'}
							<span class="status-owned">in library</span>
						{:else if track.acquisition_status === 'wanted'}
							<span class="status-wanted">wanted</span>
						{:else}
							<button class="want-btn" onclick={() => onmarkwanted(track.id)}>
								want
							</button>
						{/if}
					</td>
					<td class="col-links">
						{#if track.acquisition_status !== 'owned'}
							{#each Object.entries(track.purchase_links) as [store, url]}
								<a href={url} target="_blank" rel="noopener" class="store-link">
									{store}
								</a>
							{/each}
						{/if}
					</td>
				</tr>
			{/each}
		</tbody>
	</table>
</div>

<style>
	.hunt-results {
		font-size: 13px;
	}

	.results-header {
		display: flex;
		justify-content: space-between;
		align-items: start;
		margin-bottom: 12px;
	}

	.results-header h3 {
		margin: 0;
		font-size: 16px;
	}

	.uploader {
		color: var(--text-secondary);
		font-size: 12px;
	}

	.badge {
		padding: 4px 10px;
		border-radius: 12px;
		font-size: 12px;
		font-weight: 600;
	}

	.badge.owned {
		background: rgba(80, 200, 120, 0.15);
		color: #50c878;
	}

	.badge.gap {
		background: rgba(255, 200, 50, 0.15);
		color: #ffc832;
	}

	.track-table {
		width: 100%;
		border-collapse: collapse;
	}

	.track-table th {
		text-align: left;
		padding: 6px 8px;
		border-bottom: 1px solid var(--border);
		color: var(--text-secondary);
		font-size: 11px;
		text-transform: uppercase;
	}

	.track-table td {
		padding: 6px 8px;
		border-bottom: 1px solid var(--border-dim, rgba(255, 255, 255, 0.05));
	}

	tr.owned {
		opacity: 0.6;
	}

	.col-pos { width: 30px; text-align: right; color: var(--text-dim); }
	.col-source { color: var(--text-dim); font-size: 11px; }

	.remix {
		color: var(--text-dim);
		font-size: 12px;
	}

	.status-owned {
		color: #50c878;
		font-size: 11px;
	}

	.status-wanted {
		color: #ffc832;
		font-size: 11px;
	}

	.want-btn {
		padding: 2px 8px;
		font-size: 11px;
		background: transparent;
		border: 1px solid var(--border);
		border-radius: 4px;
		color: var(--text-secondary);
		cursor: pointer;
	}

	.want-btn:hover {
		border-color: #ffc832;
		color: #ffc832;
	}

	.store-link {
		display: inline-block;
		margin-right: 6px;
		padding: 1px 6px;
		font-size: 11px;
		color: var(--accent);
		text-decoration: none;
		border: 1px solid var(--border);
		border-radius: 3px;
	}

	.store-link:hover {
		background: var(--bg-hover);
	}
</style>
