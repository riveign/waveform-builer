<script lang="ts">
	import { onMount } from 'svelte';
	import type { Track } from '$lib/types';
	import type { SearchParams } from '$lib/api/tracks';
	import { getTrackStore } from '$lib/stores/tracks.svelte';
	import { getUiStore } from '$lib/stores/ui.svelte';
	import SearchFilters from './SearchFilters.svelte';
	import AddRecordModal from './AddRecordModal.svelte';
	import TrackTable from './TrackTable.svelte';
	import Pagination from './Pagination.svelte';
	import Spinner from '../Spinner.svelte';

	let { onselect }: { onselect: (track: Track) => void } = $props();

	const store = getTrackStore();
	const ui = getUiStore();
	let selectedId = $state<number | null>(null);

	// Records live in the same library as files — so they're added from here,
	// not from a section of their own. A shelf grows a record at a time.
	let addingRecord = $state(false);
	let shelfNote = $state('');
	let lastParams = $state<SearchParams>({});

	function handleImported(summary: string) {
		shelfNote = summary;
		store.search(lastParams);
	}

	function handleSearch(params: SearchParams) {
		lastParams = params;
		// Sort only reorders; anything else hides tracks — worth a dot on the rail.
		ui.libraryFiltered = Object.keys(params).some((k) => k !== 'sort');
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

	<div class="shelf-bar">
		<button type="button" class="add-record" onclick={() => (addingRecord = true)}>
			<svg width="13" height="13" viewBox="0 0 16 16" fill="none" aria-hidden="true">
				<circle cx="8" cy="8" r="6.5" stroke="currentColor" stroke-width="1.3" />
				<circle cx="8" cy="8" r="1.2" fill="currentColor" />
			</svg>
			Add a record
		</button>
		{#if shelfNote}
			<span class="shelf-note" role="status">{shelfNote}</span>
			<button type="button" class="dismiss" onclick={() => (shelfNote = '')} aria-label="Dismiss">×</button>
		{/if}
	</div>

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
		<TrackTable tracks={store.tracks} {selectedId} onselect={handleSelect} />
		<Pagination
			page={store.page}
			pageCount={store.pageCount}
			total={store.total}
			pageSize={store.pageSize}
			offset={store.offset}
			onpage={store.goToPage}
			onpagesize={store.setPageSize}
		/>
	{/if}
</div>

<AddRecordModal
	open={addingRecord}
	onclose={() => (addingRecord = false)}
	onimported={handleImported}
/>

<style>
	.shelf-bar {
		display: flex;
		align-items: center;
		gap: var(--space-md);
		padding: var(--space-sm) var(--space-lg);
		border-bottom: 1px solid var(--border-subtle);
		min-height: 34px;
	}

	.add-record {
		display: inline-flex;
		align-items: center;
		gap: var(--space-sm);
		background: transparent;
		border: 1px solid var(--border-default);
		border-radius: var(--radius-sm);
		color: var(--text-2);
		font: inherit;
		font-size: var(--text-xs);
		padding: var(--space-xs) var(--space-md);
		cursor: pointer;
		flex: none;
	}
	.add-record:hover { background: var(--surface-hover); color: var(--text-1); }
	.add-record:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }

	.shelf-note {
		font-size: var(--text-xs);
		color: var(--accent-text);
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	.dismiss {
		background: transparent; border: 0; color: var(--text-4);
		font-size: var(--text-md); line-height: 1; cursor: pointer; padding: 0 var(--space-xs);
		margin-left: auto; flex: none;
	}
	.dismiss:hover { color: var(--text-1); }

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

	.fuzzy-note {
		padding: var(--space-sm) var(--space-lg);
		font-size: var(--text-xs);
		color: var(--accent);
		background: var(--bg-tertiary);
	}
</style>
