<script lang="ts">
	import type { SCTrack } from '$lib/types';
	import Button from '$lib/components/primitives/Button.svelte';
	import Chip from '$lib/components/primitives/Chip.svelte';

	interface Props {
		tracks: SCTrack[];
		hasMore: boolean;
		loading: boolean;
		onloadmore: () => void;
		onchase: (trackIds: number[]) => void;
	}

	let { tracks, hasMore, loading, onloadmore, onchase }: Props = $props();

	let selected = $state<Set<number>>(new Set());

	function toggleTrack(id: number) {
		const next = new Set(selected);
		if (next.has(id)) {
			next.delete(id);
		} else {
			next.add(id);
		}
		selected = next;
	}

	function toggleAll() {
		if (selected.size === tracks.length) {
			selected = new Set();
		} else {
			selected = new Set(tracks.map((t) => t.id));
		}
	}

	function formatDuration(ms: number): string {
		const sec = Math.floor(ms / 1000);
		const m = Math.floor(sec / 60);
		const s = sec % 60;
		return `${m}:${String(s).padStart(2, '0')}`;
	}
</script>

<div class="sc-track-list">
	<div class="list-actions">
		<label class="select-all">
			<input type="checkbox" checked={selected.size === tracks.length && tracks.length > 0} onchange={toggleAll} />
			Select all ({tracks.length})
		</label>
		{#if selected.size > 0}
			<Button size="sm" loading={loading} onclick={() => onchase([...selected])}>
				{loading ? 'Chasing...' : `Chase ${selected.size} selected`}
			</Button>
		{/if}
	</div>

	<div class="track-rows">
		{#each tracks as track}
			<div class="track-row" class:selected={selected.has(track.id)}>
				<input
					type="checkbox"
					checked={selected.has(track.id)}
					onchange={() => toggleTrack(track.id)}
				/>
				{#if track.artwork_url}
					<img src={track.artwork_url} alt="" class="mini-art" />
				{:else}
					<div class="mini-art placeholder"></div>
				{/if}
				<div class="track-info">
					<span class="track-title">{track.title}</span>
					{#if track.artist}
						<span class="track-artist">{track.artist}</span>
					{/if}
				</div>
				<span class="track-duration">{formatDuration(track.duration_ms)}</span>
				{#if track.genre}
					<Chip variant="genre" size="sm" value={track.genre} title={track.genre} />
				{/if}
			</div>
		{/each}
	</div>

	{#if hasMore}
		<div class="load-more">
			<Button variant="secondary" loading={loading} onclick={onloadmore}>
				{loading ? 'Reading...' : 'Load more'}
			</Button>
		</div>
	{/if}
</div>

<style>
	.sc-track-list {
		font-size: 13px;
	}

	.list-actions {
		display: flex;
		align-items: center;
		gap: 12px;
		margin-bottom: 10px;
	}

	.select-all {
		display: flex;
		align-items: center;
		gap: 6px;
		font-size: 12px;
		color: var(--text-secondary);
		cursor: pointer;
	}

	.track-rows {
		display: flex;
		flex-direction: column;
	}

	.track-row {
		display: flex;
		align-items: center;
		gap: 8px;
		padding: 6px 8px;
		border-bottom: 1px solid var(--border-dim, rgba(255, 255, 255, 0.05));
	}

	.track-row.selected {
		background: var(--surface-hover);
	}

	.mini-art, .mini-art.placeholder {
		width: 32px;
		height: 32px;
		border-radius: 4px;
		flex-shrink: 0;
	}

	.mini-art.placeholder {
		background: var(--bg-hover);
	}

	.track-info {
		flex: 1;
		min-width: 0;
		display: flex;
		flex-direction: column;
	}

	.track-title {
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.track-artist {
		font-size: 11px;
		color: var(--text-dim);
	}

	.track-duration {
		font-size: 11px;
		color: var(--text-dim);
		font-variant-numeric: tabular-nums;
		flex-shrink: 0;
	}

	.load-more {
		margin-top: 8px;
		display: flex;
	}

	.load-more :global(.btn) {
		flex: 1;
	}
</style>
