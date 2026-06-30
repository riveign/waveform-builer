<script lang="ts">
	import { onMount } from 'svelte';
	import type { TinderDecision, TinderBatchDecision } from '$lib/types';
	import { getTinderStore } from '$lib/stores/tinder.svelte';
	import TinderCard from './TinderCard.svelte';
	import TinderBatch from './TinderBatch.svelte';
	import TinderSummary from './TinderSummary.svelte';
	import Button from '../primitives/Button.svelte';

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
		<div class="status">Reading your review queue...</div>
	{:else if store.error}
		<div class="status error" role="alert">
			<p>Couldn't read your review queue.</p>
			<p class="hint">The predictions may still be settling — give it a moment and try again.</p>
		</div>
	{:else if store.queue.length === 0}
		<div class="empty">
			<p>Nothing to review right now — your queue is clear.</p>
			<p class="hint">Run the autotagger first, and fresh predictions will land here to confirm.</p>
		</div>
	{:else if store.isComplete}
		<TinderSummary onrestart={loadWithFilters} />
	{:else}
		<!-- Toolbar band: queue progress + mode toggle (sticky, matches Set tab) -->
		<div class="toolbar">
			<div class="progress-bar">
				<span>{store.currentIndex + 1} / {store.queue.length}</span>
				<span class="queue-total">({store.queueTotal} total in queue)</span>
			</div>
			<Button
				variant="secondary"
				size="sm"
				pressed={batchMode}
				onclick={() => batchMode = !batchMode}
			>
				{batchMode ? 'Card mode' : 'Batch mode'}
			</Button>
		</div>

		<!-- Secondary band: genre/BPM filters (sticky beneath the toolbar band) -->
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

		<!-- Sole scroller: the card/batch stage scrolls beneath the pinned band -->
		<div class="tinder-stage">
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
		</div>
	{/if}
</div>

<style>
	.energy-tinder { flex: 1; min-height: 0; display: flex; flex-direction: column; overflow: hidden; }
	.status { padding: 40px; text-align: center; color: var(--text-secondary); }
	.status.error { color: var(--energy-high); }
	.status p { margin: 4px 0; }
	.empty { text-align: center; padding: 40px; color: var(--text-dim); }
	.empty p { margin: 4px 0; }
	.hint { font-size: 12px; color: var(--text-dim); }
	/* Toolbar band: progress + mode toggle, sticky (matches Set tab recipe) */
	.toolbar {
		display: flex; align-items: center; justify-content: space-between;
		padding: 0 var(--space-xl);
		height: var(--band-toolbar-h);
		border-bottom: 1px solid var(--border);
		position: sticky; top: 0; z-index: 5;
		background: var(--bg-primary);
	}
	/* Secondary band: genre/BPM filters, sticky beneath the toolbar band */
	.filters {
		display: flex; align-items: center; gap: var(--space-md); justify-content: center;
		padding: 0 var(--space-xl);
		height: var(--band-secondary-h);
		border-bottom: 1px solid var(--border);
		position: sticky; top: var(--band-toolbar-h); z-index: 4;
		background: var(--bg-primary);
	}
	/* Sole scroller: card/batch stage scrolls beneath the pinned bands */
	.tinder-stage { flex: 1; min-height: 0; overflow-y: auto; padding: var(--space-lg); }
	.progress-bar { font-size: 13px; color: var(--text-secondary); }
	.queue-total { font-size: 11px; color: var(--text-dim); margin-left: 4px; }
	.filters select, .filters input { padding: 4px 8px; font-size: 12px; background: var(--bg-secondary); color: var(--text-primary); border: 1px solid var(--border); border-radius: 4px; }
	.filters input { width: 80px; }
</style>
