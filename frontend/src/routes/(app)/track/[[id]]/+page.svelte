<script lang="ts">
	import TrackView from '$lib/components/waveform/TrackView.svelte';
	import { getUiStore } from '$lib/stores/ui.svelte';

	let { data } = $props();

	const ui = getUiStore();

	// The build dialog offers the track you were last looking at as a seed or tail.
	// This route is the only writer of that memory.
	$effect(() => {
		if (data.track) ui.selectedTrack = data.track;
	});
</script>

{#if data.track}
	{#key data.track.id}
		<TrackView track={data.track} />
	{/key}
{:else}
	<div class="empty-state">
		<p>Choose a track to explore its sound</p>
	</div>
{/if}

<style>
	.empty-state {
		display: flex;
		align-items: center;
		justify-content: center;
		height: 100%;
		color: var(--text-dim);
		font-size: var(--text-md);
	}
</style>
