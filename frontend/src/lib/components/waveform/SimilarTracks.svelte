<script lang="ts">
	import type { SuggestNextItem } from '$lib/types';
	import { suggestNext, getTrackAffinities, type TrackAffinity } from '$lib/api/tracks';
	import SimilarTrackCard from '../library/SimilarTrackCard.svelte';
	import Spinner from '../Spinner.svelte';
	import AddToSetPicker from '../set/AddToSetPicker.svelte';

	let { trackId, trackKey = null, parentBpm = null }: { trackId: number; trackKey?: string | null; parentBpm?: number | null } = $props();

	let pool = $state<SuggestNextItem[]>([]);
	let rejectedIds = $state<Set<number>>(new Set());
	let loading = $state(false);
	let showAll = $state(false);
	let affinityMap = $state<Record<number, string>>({});
	let dismissing = $state<Set<number>>(new Set());
	let addToSetTrackId = $state<number | null>(null);

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
			suggestNext(id, FETCH_COUNT),
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
	<h3 class="section-title">Sounds like</h3>

	{#if loading}
		<Spinner label="Listening to your library..." />
	{:else if available.length === 0}
		<p class="muted">No similar tracks found</p>
	{:else}
		<div class="cards-grid">
			{#each visibleSuggestions as item (item.track.id)}
				<div class="card-slot" class:dismissing={dismissing.has(item.track.id)}>
					<SimilarTrackCard
						{item}
						parentTrackId={trackId}
						{parentBpm}
						affinity={affinityMap[item.track.id] ?? null}
						onaffinitychange={handleAffinityChange}
					/>
					<button
						class="add-to-set-icon"
						onclick={(e) => { e.stopPropagation(); addToSetTrackId = addToSetTrackId === item.track.id ? null : item.track.id; }}
						title="Add to set"
					>+</button>
					{#if addToSetTrackId === item.track.id}
						<div class="add-picker-popover">
							<AddToSetPicker
								trackId={item.track.id}
								trackTitle={item.track.title ?? 'track'}
								onclose={() => addToSetTrackId = null}
							/>
						</div>
					{/if}
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

	.add-to-set-icon {
		position: absolute;
		top: 4px;
		right: 4px;
		width: 22px;
		height: 22px;
		border-radius: 50%;
		border: 1px solid var(--border);
		background: var(--bg-primary);
		color: var(--accent);
		font-size: 14px;
		font-weight: 700;
		cursor: pointer;
		display: flex;
		align-items: center;
		justify-content: center;
		opacity: 0;
		transition: opacity 0.15s;
		z-index: 2;
	}

	.card-slot:hover .add-to-set-icon {
		opacity: 1;
	}

	.add-picker-popover {
		position: absolute;
		top: 28px;
		right: 0;
		background: var(--bg-primary);
		border: 1px solid var(--border);
		border-radius: 8px;
		box-shadow: 0 4px 16px rgba(0, 0, 0, 0.4);
		z-index: 10;
		min-width: 220px;
	}
</style>
