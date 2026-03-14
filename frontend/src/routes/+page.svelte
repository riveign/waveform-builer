<script lang="ts">
	import type { Track } from '$lib/types';
	import LibraryBrowser from '$lib/components/library/LibraryBrowser.svelte';
	import Workspace from '$lib/components/Workspace.svelte';

	let selectedTrack = $state<Track | null>(null);

	function handleTrackSelect(track: Track) {
		selectedTrack = track;
	}
</script>

<div class="two-panel">
	<aside class="panel-left">
		<LibraryBrowser onselect={handleTrackSelect} />
	</aside>
	<main class="panel-right">
		<Workspace track={selectedTrack} />
	</main>
</div>

<style>
	.two-panel {
		display: grid;
		grid-template-columns: var(--panel-width) 1fr;
		height: 100%;
		overflow: hidden;
	}

	.panel-left {
		border-right: 1px solid var(--border);
		overflow: hidden;
	}

	.panel-right {
		overflow: hidden;
	}
</style>
