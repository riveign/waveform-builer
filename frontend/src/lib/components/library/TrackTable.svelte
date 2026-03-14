<script lang="ts">
	import type { Track } from '$lib/types';
	import { getCamelotColor } from '$lib/utils/camelot';
	import { formatTime } from '$lib/utils/waveform';

	let {
		tracks,
		selectedId = null,
		onselect,
	}: {
		tracks: Track[];
		selectedId?: number | null;
		onselect: (track: Track) => void;
	} = $props();
</script>

<div class="track-table-wrapper">
	<table class="track-table">
		<thead>
			<tr>
				<th class="col-title">Title</th>
				<th class="col-artist">Artist</th>
				<th class="col-key">Key</th>
				<th class="col-bpm">BPM</th>
				<th class="col-energy">Energy</th>
				<th class="col-rating">Rating</th>
			</tr>
		</thead>
		<tbody>
			{#each tracks as track (track.id)}
				<tr
					class="track-row"
					class:selected={track.id === selectedId}
					class:has-waveform={track.has_waveform}
					onclick={() => onselect(track)}
				>
					<td class="col-title" title={track.title ?? ''}>
						{track.title ?? '?'}
					</td>
					<td class="col-artist" title={track.artist ?? ''}>
						{track.artist ?? '?'}
					</td>
					<td class="col-key">
						<span class="key-badge" style="color: {getCamelotColor(track.key)}">
							{track.key ?? '?'}
						</span>
					</td>
					<td class="col-bpm">
						{track.bpm ? Math.round(track.bpm) : '?'}
					</td>
					<td class="col-energy">
						<span class="energy-tag">{track.energy ?? '?'}</span>
					</td>
					<td class="col-rating">
						{#if track.rating}
							{'★'.repeat(track.rating)}
						{:else}
							<span class="dim">—</span>
						{/if}
					</td>
				</tr>
			{/each}
		</tbody>
	</table>
</div>

<style>
	.track-table-wrapper {
		overflow-y: auto;
		flex: 1;
	}

	.track-table {
		width: 100%;
		border-collapse: collapse;
		font-size: 12px;
	}

	thead {
		position: sticky;
		top: 0;
		z-index: 1;
	}

	th {
		background: var(--bg-tertiary);
		padding: 6px 8px;
		text-align: left;
		font-weight: 600;
		color: var(--text-secondary);
		font-size: 11px;
		text-transform: uppercase;
		letter-spacing: 0.5px;
		border-bottom: 1px solid var(--border);
	}

	td {
		padding: 5px 8px;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
		border-bottom: 1px solid var(--bg-tertiary);
	}

	.track-row {
		cursor: pointer;
		transition: background 0.1s;
	}

	.track-row:hover {
		background: var(--bg-hover);
	}

	.track-row.selected {
		background: var(--bg-active);
		border-left: 2px solid var(--accent);
	}

	.track-row.has-waveform .col-title {
		color: var(--accent);
	}

	.col-title { max-width: 140px; }
	.col-artist { max-width: 100px; color: var(--text-secondary); }
	.col-key { width: 40px; text-align: center; }
	.col-bpm { width: 40px; text-align: right; }
	.col-energy { width: 60px; }
	.col-rating { width: 50px; color: #ffc107; font-size: 11px; }

	.key-badge {
		font-weight: 600;
		font-size: 11px;
	}

	.energy-tag {
		font-size: 11px;
		color: var(--text-secondary);
	}

	.dim {
		color: var(--text-dim);
	}
</style>
