<script lang="ts">
	import type { SuggestNextItem } from '$lib/types';
	import { suggestNext, getTrackAffinities, type TrackAffinity } from '$lib/api/tracks';
	import SimilarTrackCard from '../library/SimilarTrackCard.svelte';
	import Spinner from '../Spinner.svelte';

	let { trackId, trackKey = null, parentBpm = null }: { trackId: number; trackKey?: string | null; parentBpm?: number | null } = $props();

	// These are mix suggestions, so weight what actually makes a mix work — key and
	// tempo lead, energy/genre/quality support. (Overrides the default balance that
	// let clashing-key tracks rank high.)
	const MIX_WEIGHTS = {
		harmonic: 0.4,
		bpm_compat: 0.25,
		energy_fit: 0.15,
		genre_coherence: 0.1,
		track_quality: 0.1,
	};

	let pool = $state<SuggestNextItem[]>([]);
	let rejectedIds = $state<Set<number>>(new Set());
	let loading = $state(false);
	let showAll = $state(false);
	let affinityMap = $state<Record<number, string>>({});
	let dismissing = $state<Set<number>>(new Set());
	const VISIBLE_COUNT = 12;
	const FETCH_COUNT = 30;

	// Filter out rejected tracks from the pool
	let available = $derived(
		pool.filter((item) => !rejectedIds.has(item.track.id))
	);

	let visibleSuggestions = $derived(
		showAll ? available : available.slice(0, VISIBLE_COUNT)
	);
	let hasMore = $derived(available.length > VISIBLE_COUNT);

	// Auto-load when track changes
	$effect(() => {
		const id = trackId;
		loading = true;
		pool = [];
		rejectedIds = new Set();
		showAll = false;
		affinityMap = {};
		dismissing = new Set();

		Promise.all([
			suggestNext(id, FETCH_COUNT, undefined, MIX_WEIGHTS),
			getTrackAffinities(id).catch(() => [] as TrackAffinity[]),
		])
			.then(([res, affinities]) => {
				pool = res.suggestions;
				const map: Record<number, string> = {};
				const rejected = new Set<number>();
				for (const a of affinities) {
					map[a.track_id] = a.affinity;
					if (a.affinity === 'bad') rejected.add(a.track_id);
				}
				affinityMap = map;
				rejectedIds = rejected;
			})
			.catch(() => {
				pool = [];
			})
			.finally(() => {
				loading = false;
			});
	});

	function handleAffinityChange(trackIdChanged: number, newAffinity: string | null) {
		if (newAffinity === 'bad') {
			// Animate out, then remove from visible pool
			dismissing = new Set([...dismissing, trackIdChanged]);
			setTimeout(() => {
				rejectedIds = new Set([...rejectedIds, trackIdChanged]);
				dismissing = new Set([...dismissing].filter((id) => id !== trackIdChanged));
			}, 300);
			affinityMap = { ...affinityMap, [trackIdChanged]: newAffinity };
		} else if (newAffinity) {
			affinityMap = { ...affinityMap, [trackIdChanged]: newAffinity };
		} else {
			// Remove opinion — if it was rejected, bring it back
			const next = { ...affinityMap };
			delete next[trackIdChanged];
			affinityMap = next;
			if (rejectedIds.has(trackIdChanged)) {
				const updated = new Set(rejectedIds);
				updated.delete(trackIdChanged);
				rejectedIds = updated;
			}
		}
	}
</script>

<div class="similar-section">
	<h3 class="section-title">Mix next</h3>

	{#if loading}
		<Spinner label="Finding what mixes..." />
	{:else if available.length === 0}
		<p class="muted">Nothing in your library mixes cleanly from here yet</p>
	{:else}
		<div class="cards-grid">
			{#each visibleSuggestions as item (item.track.id)}
				<div class="card-slot" class:dismissing={dismissing.has(item.track.id)}>
					<SimilarTrackCard
						{item}
						parentTrackId={trackId}
						{parentBpm}
						parentKey={trackKey}
						affinity={affinityMap[item.track.id] ?? null}
						onaffinitychange={handleAffinityChange}
					/>
				</div>
			{/each}
		</div>
		{#if hasMore && !showAll}
			<button class="show-more" onclick={() => { showAll = true; }}>
				Show {available.length - VISIBLE_COUNT} more
			</button>
		{/if}
	{/if}
</div>

<style>
	.similar-section {
		display: flex;
		flex-direction: column;
		gap: 12px;
		min-width: 0;
		overflow: hidden;
	}

	.section-title {
		font-size: 12px;
		text-transform: uppercase;
		letter-spacing: 0.5px;
		color: var(--text-secondary);
		margin: 0;
	}

	.muted {
		font-size: 12px;
		color: var(--text-dim);
		margin: 0;
	}

	.cards-grid {
		display: grid;
		grid-template-columns: repeat(6, minmax(0, 1fr));
		grid-auto-rows: 1fr; /* every row the same height → all cards equal */
		gap: 12px;
	}

	@media (max-width: 1200px) {
		.cards-grid {
			grid-template-columns: repeat(4, minmax(0, 1fr));
		}
	}

	@media (max-width: 900px) {
		.cards-grid {
			grid-template-columns: repeat(3, minmax(0, 1fr));
		}
	}

	@media (max-width: 600px) {
		.cards-grid {
			grid-template-columns: repeat(2, minmax(0, 1fr));
		}
	}

	.card-slot {
		position: relative;
		display: flex; /* let the card stretch to fill the equal-height cell */
		transition: opacity 0.3s, transform 0.3s;
	}

	.card-slot.dismissing {
		opacity: 0;
		transform: scale(0.9);
		pointer-events: none;
	}

	.show-more {
		display: block;
		width: 100%;
		padding: 8px;
		background: none;
		border: 1px solid var(--border);
		border-radius: 6px;
		color: var(--text-secondary);
		font-size: 12px;
		cursor: pointer;
		transition: background 0.1s, color 0.1s;
	}

	.show-more:hover {
		background: var(--bg-tertiary);
		color: var(--text-primary);
	}


</style>
