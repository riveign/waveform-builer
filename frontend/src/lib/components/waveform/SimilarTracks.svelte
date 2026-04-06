<script lang="ts">
	import type { SuggestNextItem } from '$lib/types';
	import { suggestNext, getTrackAffinities, type TrackAffinity } from '$lib/api/tracks';
	import SimilarTrackCard from '../library/SimilarTrackCard.svelte';
	import Spinner from '../Spinner.svelte';

	let { trackId, trackKey = null }: { trackId: number; trackKey?: string | null } = $props();

	let suggestions = $state<SuggestNextItem[]>([]);
	let loading = $state(false);
	let showAll = $state(false);
	let affinityMap = $state<Record<number, string>>({});

	const INITIAL_COUNT = 12;

	let visibleSuggestions = $derived(
		showAll ? suggestions : suggestions.slice(0, INITIAL_COUNT)
	);
	let hasMore = $derived(suggestions.length > INITIAL_COUNT);

	// Auto-load when track changes
	$effect(() => {
		const id = trackId;
		loading = true;
		suggestions = [];
		showAll = false;
		affinityMap = {};

		Promise.all([
			suggestNext(id, 18),
			getTrackAffinities(id).catch(() => [] as TrackAffinity[]),
		])
			.then(([res, affinities]) => {
				suggestions = res.suggestions;
				const map: Record<number, string> = {};
				for (const a of affinities) {
					map[a.track_id] = a.affinity;
				}
				affinityMap = map;
			})
			.catch(() => {
				suggestions = [];
			})
			.finally(() => {
				loading = false;
			});
	});

	function handleAffinityChange(trackIdChanged: number, newAffinity: string | null) {
		if (newAffinity) {
			affinityMap = { ...affinityMap, [trackIdChanged]: newAffinity };
		} else {
			const next = { ...affinityMap };
			delete next[trackIdChanged];
			affinityMap = next;
		}
	}
</script>

<div class="similar-section">
	<h3 class="section-title">Sounds like</h3>

	{#if loading}
		<Spinner label="Listening to your library..." />
	{:else if suggestions.length === 0}
		<p class="muted">No similar tracks found</p>
	{:else}
		<div class="cards-grid">
			{#each visibleSuggestions as item (item.track.id)}
				<SimilarTrackCard
					{item}
					parentTrackId={trackId}
					affinity={affinityMap[item.track.id] ?? null}
					onaffinitychange={handleAffinityChange}
				/>
			{/each}
		</div>
		{#if hasMore && !showAll}
			<button class="show-more" onclick={() => { showAll = true; }}>
				Show {suggestions.length - INITIAL_COUNT} more
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
		gap: 12px;
	}

	@media (max-width: 1200px) {
		.cards-grid {
			grid-template-columns: repeat(4, 1fr);
		}
	}

	@media (max-width: 900px) {
		.cards-grid {
			grid-template-columns: repeat(3, 1fr);
		}
	}

	@media (max-width: 600px) {
		.cards-grid {
			grid-template-columns: repeat(2, 1fr);
		}
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
