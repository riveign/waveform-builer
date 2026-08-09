<script lang="ts">
	import type { SuggestNextItem } from '$lib/types';
	import { suggestNext, getTrackAffinities, type TrackAffinity } from '$lib/api/tracks';
	import { createResource } from '$lib/data/resource.svelte';
	import RelatedTrackCard from '../library/RelatedTrackCard.svelte';
	import Spinner from '../Spinner.svelte';
	import { rovingFocus } from '$lib/actions/rovingFocus';

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

	const res = createResource(
		() => trackId,
		async (id, signal) => {
			const [suggestions, affinities] = await Promise.all([
				suggestNext(id, FETCH_COUNT, undefined, MIX_WEIGHTS, undefined, signal),
				getTrackAffinities(id, signal).catch(() => [] as TrackAffinity[]),
			]);
			return { suggestions: suggestions.suggestions, affinities };
		},
		{ key: (id) => `track:${id}:similar` },
	);

	const pool = $derived<SuggestNextItem[]>(res.data?.suggestions ?? []);
	const loading = $derived(res.loading);

	// Seeded from the fetch, then owned locally as the DJ marks tracks good or bad.
	let rejectedIds = $state<Set<number>>(new Set());
	let showAll = $state(false);
	let affinityMap = $state<Record<number, string>>({});
	let dismissing = $state<Set<number>>(new Set());

	$effect(() => {
		const data = res.data;
		const map: Record<number, string> = {};
		const rejected = new Set<number>();
		for (const a of data?.affinities ?? []) {
			map[a.track_id] = a.affinity;
			if (a.affinity === 'bad') rejected.add(a.track_id);
		}
		affinityMap = map;
		rejectedIds = rejected;
		showAll = false;
		dismissing = new Set();
	});
	const VISIBLE_COUNT = 8; // 2 rows × 4 columns at full content width
	const FETCH_COUNT = 30;

	// Filter out rejected tracks from the pool
	let available = $derived(
		pool.filter((item) => !rejectedIds.has(item.track.id))
	);

	let visibleSuggestions = $derived(
		showAll ? available : available.slice(0, VISIBLE_COUNT)
	);
	let hasMore = $derived(available.length > VISIBLE_COUNT);


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
	<h3 class="section-title">Related tracks</h3>

	{#if loading}
		<Spinner label="Finding what mixes..." />
	{:else if available.length === 0}
		<p class="muted">Nothing in your library mixes cleanly from here yet</p>
	{:else}
		<div class="cards-grid grid-12 grid-12--content" use:rovingFocus>
			{#each visibleSuggestions as item (item.track.id)}
				<div class="card-slot" class:dismissing={dismissing.has(item.track.id)}>
					<RelatedTrackCard
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
		container-type: inline-size;
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

	/* 12-col content grid: every card is an equal column-multiple. Cards span 3
	   (4-up) at full content width — with VISIBLE_COUNT 8 that reads as a tidy
	   2-rows-×-4-columns block. Each card lands ≈230px wide, where the taller
	   RelatedTrackCard relaxes into its compact-artwork tier. Reflow steps down so
	   the card never crams: 4-up → 3-up → 2-up → 1-up via container queries. */
	.cards-grid {
		grid-auto-rows: 1fr; /* every row the same height → all cards equal */
	}

	.cards-grid > :global(.card-slot) {
		grid-column: span 3; /* 4-up at full content width */
	}

	@container (max-width: 880px) {
		.cards-grid > :global(.card-slot) {
			grid-column: span 4; /* 3-up */
		}
	}

	@container (max-width: 640px) {
		.cards-grid > :global(.card-slot) {
			grid-column: span 6; /* 2-up */
		}
	}

	@container (max-width: 440px) {
		.cards-grid > :global(.card-slot) {
			grid-column: span 12; /* 1-up */
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
