<script lang="ts">
	import type { Track } from '$lib/types';
	import AlbumGrid from './AlbumGrid.svelte';
	import AlbumDetail from './AlbumDetail.svelte';
	import { getUiStore } from '$lib/stores/ui.svelte';

	const ui = getUiStore();
	let openAlbumKey = $state<string | null>(null);

	function handleTrackSelect(track: Track) {
		ui.selectedTrack = track;
		ui.activeTab = 'track';
	}
</script>

<div class="albums-view">
	{#if openAlbumKey}
		<AlbumDetail
			albumKey={openAlbumKey}
			onback={() => (openAlbumKey = null)}
			onselect={handleTrackSelect}
		/>
	{:else}
		<AlbumGrid onselect={(album) => (openAlbumKey = album.album_key)} />
	{/if}
</div>

<style>
	.albums-view {
		display: flex;
		flex-direction: column;
		flex: 1;
		min-height: 0;
		overflow: hidden;
	}
</style>
