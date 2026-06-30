<script lang="ts">
	/* StandaloneTrackCard is the STANDALONE-mode wrapper over the shared
	 * `TrackCard`. It shows a track on its OWN terms — absolute key / BPM / energy
	 * attributes (no delta) and the track's own quality read (rating · plays ·
	 * energy settledness). There is no reference track, so it structurally cannot
	 * render a match score, a harmony move, or an affinity strength: those fields
	 * only exist on the `related` arm of the mode union. Use this anywhere a single
	 * track is presented without a "mix-from" comparison. */
	import type { Track } from '$lib/types';
	import TrackCard from './TrackCard.svelte';

	let { track }: { track: Track } = $props();
</script>

<TrackCard mode={{ kind: 'standalone', track }} />
