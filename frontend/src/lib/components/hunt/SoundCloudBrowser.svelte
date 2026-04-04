<script lang="ts">
	import type { HuntSession } from '$lib/types';
	import { getSoundCloudStore } from '$lib/stores/soundcloud.svelte';
	import SCPlaylistCard from './SCPlaylistCard.svelte';
	import SCTrackList from './SCTrackList.svelte';

	interface Props {
		onhuntresult: (hunt: HuntSession) => void;
	}

	let { onhuntresult }: Props = $props();

	const sc = getSoundCloudStore();

	let tab = $state<'playlists' | 'likes'>('playlists');
	let chasingId = $state<number | null>(null);

	$effect(() => {
		if (tab === 'playlists' && sc.playlists.length === 0 && sc.connected) {
			sc.loadPlaylists();
		}
		if (tab === 'likes' && sc.likes.length === 0 && sc.connected) {
			sc.loadLikes(true);
		}
	});

	async function handleChasePlaylist(playlistId: number) {
		chasingId = playlistId;
		const hunt = await sc.chasePlaylist(playlistId);
		chasingId = null;
		if (hunt) onhuntresult(hunt);
	}

	async function handleChaseLikes(trackIds: number[]) {
		const hunt = await sc.chaseLikes(trackIds);
		if (hunt) onhuntresult(hunt);
	}
</script>

<div class="sc-browser">
	<div class="tab-bar">
		<button class="tab" class:active={tab === 'playlists'} onclick={() => tab = 'playlists'}>
			Playlists
		</button>
		<button class="tab" class:active={tab === 'likes'} onclick={() => tab = 'likes'}>
			Likes
		</button>
	</div>

	{#if sc.error}
		<div class="sc-error">{sc.error}</div>
	{/if}

	{#if tab === 'playlists'}
		{#if sc.loading && sc.playlists.length === 0}
			<div class="loading">Exploring your playlists...</div>
		{:else if sc.playlists.length === 0}
			<div class="empty">No playlists found on your SoundCloud.</div>
		{:else}
			<div class="playlist-grid">
				{#each sc.playlists as playlist}
					<SCPlaylistCard
						{playlist}
						onchase={handleChasePlaylist}
						chasing={chasingId === playlist.id}
					/>
				{/each}
			</div>
		{/if}
	{:else}
		{#if sc.loading && sc.likes.length === 0}
			<div class="loading">Reading your likes...</div>
		{:else if sc.likes.length === 0}
			<div class="empty">No liked tracks found.</div>
		{:else}
			<SCTrackList
				tracks={sc.likes}
				hasMore={sc.likesNextCursor !== null}
				loading={sc.loading}
				onloadmore={() => sc.loadLikes(false)}
				onchase={handleChaseLikes}
			/>
		{/if}
	{/if}
</div>

<style>
	.sc-browser {
		margin-top: 12px;
	}

	.tab-bar {
		display: flex;
		gap: 2px;
		margin-bottom: 12px;
		border-bottom: 1px solid var(--border);
	}

	.tab {
		padding: 8px 16px;
		font-size: 13px;
		font-weight: 500;
		background: transparent;
		color: var(--text-secondary);
		border: none;
		border-bottom: 2px solid transparent;
		cursor: pointer;
	}

	.tab.active {
		color: var(--text-primary);
		border-bottom-color: var(--accent);
	}

	.sc-error {
		padding: 8px 12px;
		background: rgba(255, 80, 80, 0.1);
		border: 1px solid rgba(255, 80, 80, 0.3);
		border-radius: 6px;
		color: #ff5050;
		font-size: 13px;
		margin-bottom: 12px;
	}

	.loading, .empty {
		text-align: center;
		color: var(--text-dim);
		padding: 40px 20px;
		font-size: 14px;
	}

	.playlist-grid {
		display: flex;
		flex-direction: column;
		gap: 8px;
	}
</style>
