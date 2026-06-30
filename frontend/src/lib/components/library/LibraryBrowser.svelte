<script lang="ts">
	import { onMount } from 'svelte';
	import type { Track } from '$lib/types';
	import type { SearchParams } from '$lib/api/tracks';
	import { getTrackStore } from '$lib/stores/tracks.svelte';
	import SearchFilters from './SearchFilters.svelte';
	import TrackTable from './TrackTable.svelte';
	import Spinner from '../Spinner.svelte';

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

	onMount(() => store.search({}));
</script>

<div class="library-browser">
	<SearchFilters onsearch={handleSearch} />

	{#if store.loading}
		<div class="status"><Spinner label="Reading your library..." /></div>
	{:else if store.error}
		<div class="status error" role="alert">Couldn't read your library. Something hiccuped between here and the database — try the search again.</div>
	{:else if store.tracks.length === 0}
		<div class="status">Nothing matched those filters. Try loosening the search?</div>
	{:else}
		{#if store.fuzzy}
			<div class="fuzzy-note">No exact match — showing similar names</div>
		{/if}
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
		padding: var(--space-2xl);
		text-align: center;
		color: var(--text-secondary);
		font-size: var(--text-base);
	}

	.status.error {
		color: var(--energy-high);
	}

	.track-count {
		padding: var(--space-sm) var(--space-lg);
		font-size: var(--text-xs);
		color: var(--text-dim);
		border-bottom: 1px solid var(--border);
	}

	.fuzzy-note {
		padding: var(--space-sm) var(--space-lg);
		font-size: var(--text-xs);
		color: var(--accent);
		background: var(--bg-tertiary);
	}
</style>
