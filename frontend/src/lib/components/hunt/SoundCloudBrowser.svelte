<script lang="ts">
	import type { HuntSession } from '$lib/types';
	import { getSoundCloudStore } from '$lib/stores/soundcloud.svelte';
	import SCPlaylistCard from './SCPlaylistCard.svelte';
	import SCTrackList from './SCTrackList.svelte';
	import SegmentedControl from '$lib/components/primitives/SegmentedControl.svelte';

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
		<SegmentedControl
			options={[
				{ value: 'playlists', label: 'Playlists' },
				{ value: 'likes', label: 'Likes' },
			]}
			value={tab}
			onchange={(v) => (tab = v)}
			ariaLabel="SoundCloud browse mode"
		/>
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
			<div class="playlist-grid grid-12 grid-12--content">
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
		container-type: inline-size; /* query container for the playlist card grid reflow */
	}

	.tab-bar {
		margin-bottom: 12px;
		border-bottom: 1px solid var(--border);
	}

	.sc-error {
		padding: 8px 12px;
		background: color-mix(in srgb, var(--destructive) 12%, transparent);
		border: 1px solid color-mix(in srgb, var(--destructive) 32%, transparent);
		border-radius: 6px;
		color: var(--destructive);
		font-size: 13px;
		margin-bottom: 12px;
	}

	.loading, .empty {
		text-align: center;
		color: var(--text-dim);
		padding: 40px 20px;
		font-size: 14px;
	}

	/* 12-col content grid: playlist row-cards span 6 (2-up) at full width,
	   reflowing to 1-up via container query so the horizontal card never cramps. */
	.playlist-grid > :global(.playlist-card) {
		grid-column: span 6; /* 2-up */
	}

	@container (max-width: 640px) {
		.playlist-grid > :global(.playlist-card) {
			grid-column: span 12; /* 1-up */
		}
	}
</style>
