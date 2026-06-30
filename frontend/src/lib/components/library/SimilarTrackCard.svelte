<script lang="ts" module>
	/* SimilarTrackCard is the RELATED-mode wrapper over the shared `TrackCard`.
	 * Its anatomy, tiers, container-query tiers and tokens all live in TrackCard;
	 * this file just binds the comparative props (parent track / score / affinity)
	 * into the `related` arm of the mode union, so the Related-tracks section and
	 * the design-system showcase keep their existing call shape unchanged.
	 *
	 * The shared helpers `capFirst` and `scoreStrength` are RE-EXPORTED here so the
	 * existing import in `waveform/TrackView.svelte` (`import { capFirst } from
	 * '../library/SimilarTrackCard.svelte'`) keeps resolving without an edit. */
	export { capFirst, scoreStrength } from './TrackCard.svelte';
</script>

<script lang="ts">
	import type { SuggestNextItem } from '$lib/types';
	import TrackCard from './TrackCard.svelte';

	let {
		item,
		parentTrackId,
		parentBpm = null,
		parentKey = null,
		affinity = null,
		onaffinitychange,
	}: {
		item: SuggestNextItem;
		parentTrackId: number;
		parentBpm?: number | null;
		parentKey?: string | null;
		affinity?: string | null;
		onaffinitychange?: (trackId: number, newAffinity: string | null) => void;
	} = $props();
</script>

<TrackCard
	mode={{
		kind: 'related',
		item,
		parentTrackId,
		parentBpm,
		parentKey,
		affinity,
		onaffinitychange,
	}}
/>
