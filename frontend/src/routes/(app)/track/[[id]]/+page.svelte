<script lang="ts">
	import TrackView from '$lib/components/waveform/TrackView.svelte';
	import EmptyState from '$lib/components/primitives/EmptyState.svelte';
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
	<EmptyState
		title="Choose a track to explore its sound"
		hint="Pick one from your library on the left — you'll see its waveform, what Kiku hears in it, and what mixes well next."
	/>
{/if}
