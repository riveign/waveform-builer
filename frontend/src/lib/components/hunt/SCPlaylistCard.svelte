<script lang="ts">
	import type { SCPlaylist } from '$lib/types';
	import Button from '$lib/components/primitives/Button.svelte';

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
	<div class="chase">
		<Button size="sm" loading={chasing} onclick={() => onchase(playlist.id)}>
			{chasing ? 'Chasing...' : 'Chase'}
		</Button>
	</div>
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

	.chase {
		flex-shrink: 0;
	}
</style>
