<script lang="ts">
	import { onMount } from 'svelte';
	import type { Track } from '$lib/types';
	import type { SearchParams } from '$lib/api/tracks';
	import { getTrackStore } from '$lib/stores/tracks.svelte';
	import SearchFilters from './SearchFilters.svelte';
	import TrackTable from './TrackTable.svelte';
	import AlbumGrid from './AlbumGrid.svelte';
	import AlbumDetail from './AlbumDetail.svelte';

	let { onselect }: { onselect: (track: Track) => void } = $props();

	const store = getTrackStore();
	let selectedId = $state<number | null>(null);
	type ViewMode = 'tracks' | 'albums';
	let mode = $state<ViewMode>('tracks');
	let openAlbumKey = $state<string | null>(null);

	function handleSearch(params: SearchParams) {
		store.search(params);
	}

	function handleSelect(track: Track) {
		selectedId = track.id;
		onselect(track);
	}

	function setMode(next: ViewMode) {
		mode = next;
		try {
			localStorage.setItem('kiku:libraryViewMode', next);
		} catch {}
		if (next === 'tracks') openAlbumKey = null;
	}

	onMount(() => {
		try {
			const saved = localStorage.getItem('kiku:libraryViewMode');
			if (saved === 'albums' || saved === 'tracks') mode = saved;
		} catch {}
		if (mode === 'tracks') store.search({});
	});
</script>

<div class="library-browser">
	<div class="mode-toggle">
		<button class:active={mode === 'tracks'} onclick={() => setMode('tracks')}>Tracks</button>
		<button class:active={mode === 'albums'} onclick={() => setMode('albums')}>Albums</button>
	</div>

	{#if mode === 'tracks'}
		<SearchFilters onsearch={handleSearch} />

		{#if store.loading}
			<div class="status">Reading your library...</div>
		{:else if store.error}
			<div class="status error">{store.error}</div>
		{:else if store.tracks.length === 0}
			<div class="status">Nothing matched those filters. Try loosening the search?</div>
		{:else}
			<div class="track-count">{store.tracks.length} of {store.total} tracks</div>
			<TrackTable tracks={store.tracks} {selectedId} onselect={handleSelect} />
		{/if}
	{:else if openAlbumKey}
		<AlbumDetail
			albumKey={openAlbumKey}
			onback={() => (openAlbumKey = null)}
			onselect={handleSelect}
		/>
	{:else}
		<AlbumGrid onselect={(album) => (openAlbumKey = album.album_key)} />
	{/if}
</div>

<style>
	.library-browser {
		display: flex;
		flex-direction: column;
		height: 100%;
		overflow: hidden;
	}

	.mode-toggle {
		display: flex;
		gap: 4px;
		padding: 8px 10px;
		border-bottom: 1px solid var(--border);
		background: var(--bg-secondary, transparent);
	}
	.mode-toggle button {
		appearance: none;
		background: transparent;
		color: var(--text-secondary);
		border: 1px solid var(--border);
		border-radius: 6px;
		padding: 4px 12px;
		font-size: 12px;
		font-weight: 500;
		cursor: pointer;
		transition: background 0.15s, color 0.15s, border-color 0.15s;
	}
	.mode-toggle button:hover {
		color: var(--text-primary);
		border-color: var(--accent);
	}
	.mode-toggle button.active {
		background: var(--accent);
		color: var(--bg-primary, #000);
		border-color: var(--accent);
	}

	.status {
		padding: 20px;
		text-align: center;
		color: var(--text-secondary);
		font-size: 13px;
	}

	.status.error {
		color: var(--energy-high);
	}

	.track-count {
		padding: 4px 10px;
		font-size: 11px;
		color: var(--text-dim);
		border-bottom: 1px solid var(--border);
	}
</style>
