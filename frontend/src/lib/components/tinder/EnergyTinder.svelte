<script lang="ts">
	import { onMount } from 'svelte';
	import type { TinderDecision, TinderBatchDecision } from '$lib/types';
	import { getTinderStore } from '$lib/stores/tinder.svelte';
	import TinderCard from './TinderCard.svelte';
	import TinderBatch from './TinderBatch.svelte';
	import TinderSummary from './TinderSummary.svelte';

	const store = getTinderStore();

	let genreFamily = $state('');
	let bpmMin = $state('');
	let bpmMax = $state('');
	let batchMode = $state(false);

	const BATCH_SIZE = 5;

	function loadWithFilters() {
		store.loadQueue({
			genre_family: genreFamily || undefined,
			bpm_min: bpmMin ? Number(bpmMin) : undefined,
			bpm_max: bpmMax ? Number(bpmMax) : undefined,
			limit: 50,
		});
	}

	onMount(() => {
		loadWithFilters();
	});

	function handleDecide(decision: TinderDecision, overrideZone?: string) {
		store.decide(decision, overrideZone);
	}

	function handleBatchSubmit(decisions: TinderBatchDecision[]) {
		store.decideBatch(decisions);
	}

	let batchItems = $derived(
		store.queue.slice(store.currentIndex, store.currentIndex + BATCH_SIZE)
	);
</script>

<div class="energy-tinder">
	{#if store.loading}
		<div class="status">Loading your review queue...</div>
	{:else if store.error}
		<div class="status error">{store.error}</div>
	{:else if store.queue.length === 0}
		<div class="empty">
			<p>No tracks to review right now.</p>
			<p class="hint">Run the autotagger first to generate predictions.</p>
		</div>
	{:else if store.isComplete}
		<TinderSummary onrestart={loadWithFilters} />
	{:else}
		<!-- Queue progress + mode toggle -->
		<div class="toolbar">
			<div class="progress-bar">
				<span>{store.currentIndex + 1} / {store.queue.length}</span>
				<span class="queue-total">({store.queueTotal} total in queue)</span>
			</div>
			<button class="mode-toggle" onclick={() => batchMode = !batchMode}>
				{batchMode ? 'Card mode' : 'Batch mode'}
			</button>
		</div>

		<!-- Filters -->
		<div class="filters">
			<select bind:value={genreFamily} onchange={loadWithFilters}>
				<option value="">All genres</option>
				<option value="techno">Techno</option>
				<option value="house">House</option>
				<option value="groove">Groove</option>
				<option value="trance">Trance</option>
				<option value="breaks">Breaks</option>
				<option value="electronic">Electronic</option>
			</select>
			<input type="number" placeholder="BPM min" bind:value={bpmMin} onchange={loadWithFilters} />
			<input type="number" placeholder="BPM max" bind:value={bpmMax} onchange={loadWithFilters} />
		</div>

		{#if batchMode}
			<!-- Batch mode: show multiple tracks at once -->
			{#if batchItems.length > 0}
				<TinderBatch items={batchItems} onsubmit={handleBatchSubmit} />
			{/if}
		{:else}
			<!-- Card mode: one track at a time -->
			{#if store.currentItem}
				{#key store.currentItem.track.id}
					<TinderCard
						item={store.currentItem}
						ondecide={handleDecide}
						teachingMoment={store.lastTeachingMoment}
					/>
				{/key}
			{/if}
		{/if}
	{/if}
</div>

<style>
	.energy-tinder { height: 100%; display: flex; flex-direction: column; overflow-y: auto; padding: 12px; }
	.status { padding: 40px; text-align: center; color: var(--text-secondary); }
	.status.error { color: var(--energy-high); }
	.empty { text-align: center; padding: 40px; color: var(--text-dim); }
	.empty p { margin: 4px 0; }
	.hint { font-size: 12px; }
	.toolbar { display: flex; align-items: center; justify-content: space-between; padding: 4px 0; }
	.progress-bar { font-size: 13px; color: var(--text-secondary); }
	.queue-total { font-size: 11px; color: var(--text-dim); margin-left: 4px; }
	.mode-toggle { padding: 3px 10px; font-size: 11px; background: var(--bg-secondary); color: var(--text-secondary); border: 1px solid var(--border); border-radius: 4px; cursor: pointer; }
	.mode-toggle:hover { background: var(--bg-hover); }
	.filters { display: flex; gap: 8px; justify-content: center; padding: 8px 0; }
	.filters select, .filters input { padding: 4px 8px; font-size: 12px; background: var(--bg-secondary); color: var(--text-primary); border: 1px solid var(--border); border-radius: 4px; }
	.filters input { width: 80px; }
</style>
