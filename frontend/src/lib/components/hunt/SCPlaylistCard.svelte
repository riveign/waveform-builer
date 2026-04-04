<script lang="ts">
	import type { SCPlaylist } from '$lib/types';

	interface Props {
		playlist: SCPlaylist;
		onchase: (id: number) => void;
		chasing: boolean;
	}

	let { playlist, onchase, chasing }: Props = $props();

	function formatDuration(ms: number): string {
		const min = Math.floor(ms / 60000);
		return min > 0 ? `${min} min` : '';
	}
</script>

<div class="playlist-card">
	{#if playlist.artwork_url}
		<img src={playlist.artwork_url} alt="" class="artwork" />
	{:else}
		<div class="artwork-placeholder"></div>
	{/if}
	<div class="info">
		<div class="title">{playlist.title}</div>
		<div class="meta">
			{playlist.track_count} tracks
			{#if playlist.duration_ms > 0}
				<span class="dot">·</span> {formatDuration(playlist.duration_ms)}
			{/if}
		</div>
	</div>
	<button class="chase-btn" onclick={() => onchase(playlist.id)} disabled={chasing}>
		{chasing ? 'Chasing...' : 'Chase'}
	</button>
</div>

<style>
	.playlist-card {
		display: flex;
		align-items: center;
		gap: 12px;
		padding: 10px 12px;
		border: 1px solid var(--border);
		border-radius: 8px;
		background: var(--bg-secondary);
	}

	.artwork, .artwork-placeholder {
		width: 48px;
		height: 48px;
		border-radius: 6px;
		flex-shrink: 0;
	}

	.artwork-placeholder {
		background: var(--bg-hover);
	}

	.info {
		flex: 1;
		min-width: 0;
	}

	.title {
		font-size: 14px;
		font-weight: 500;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.meta {
		font-size: 12px;
		color: var(--text-dim);
		margin-top: 2px;
	}

	.dot {
		margin: 0 4px;
	}

	.chase-btn {
		padding: 6px 14px;
		font-size: 12px;
		font-weight: 600;
		background: var(--accent);
		color: #000;
		border: none;
		border-radius: 6px;
		cursor: pointer;
		flex-shrink: 0;
	}

	.chase-btn:disabled {
		opacity: 0.5;
		cursor: default;
	}
</style>
