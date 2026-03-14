<script lang="ts">
	import { onMount } from 'svelte';
	import type { Track } from '$lib/types';
	import type { SearchParams } from '$lib/api/tracks';
	import { getTrackStore } from '$lib/stores/tracks.svelte';
	import SearchFilters from './SearchFilters.svelte';
	import TrackTable from './TrackTable.svelte';

	let { onselect }: { onselect: (track: Track) => void } = $props();

	const store = getTrackStore();
	let selectedId = $state<number | null>(null);

	function handleSearch(params: SearchParams) {
		store.search(params);
	}

	function handleSelect(track: Track) {
		selectedId = track.id;
		onselect(track);
	}

	// Load initial tracks once on mount (not $effect which re-runs on every render)
	onMount(() => {
		store.search({});
	});
</script>

<div class="library-browser">
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
</div>

<style>
	.library-browser {
		display: flex;
		flex-direction: column;
		height: 100%;
		overflow: hidden;
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
