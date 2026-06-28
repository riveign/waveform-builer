<script lang="ts">
	import type { TinderQueueItem, TinderDecision } from '$lib/types';
	import { getTinderQueue, submitDecision } from '$lib/api/tinder';
	import TinderCard from '../tinder/TinderCard.svelte';
	import Button from '$lib/components/primitives/Button.svelte';

	let {
		trackIds,
		onclose,
	}: {
		trackIds: number[];
		onclose: (reviewed: boolean) => void;
	} = $props();

	let queue = $state<TinderQueueItem[]>([]);
	let currentIndex = $state(0);
	let loading = $state(true);
	let error = $state<string | null>(null);
	let teachingMoment = $state<string | null>(null);
	let reviewed = $state(0);
	let totalToReview = $state(0);

	let currentItem = $derived(currentIndex < queue.length ? queue[currentIndex] : null);
	let done = $derived(!loading && (queue.length === 0 || currentIndex >= queue.length));

	async function loadQueue() {
		loading = true;
		error = null;
		try {
			const res = await getTinderQueue({
				track_ids: trackIds,
				include_conflicts: true,
				limit: 100,
			});
			queue = res.items;
			totalToReview = res.items.length;
			currentIndex = 0;
			reviewed = 0;
		} catch (e) {
			error = e instanceof Error ? e.message : String(e);
		} finally {
			loading = false;
		}
	}

	async function handleDecide(decision: TinderDecision, overrideZone?: string) {
		if (!currentItem) return;
		teachingMoment = null;
		try {
			const result = await submitDecision(currentItem.track.id, decision, overrideZone);
			if (result.teaching_moment) {
				teachingMoment = result.teaching_moment;
			}
			if (decision !== 'skip') {
				reviewed++;
			}
			currentIndex++;
		} catch (e) {
			error = e instanceof Error ? e.message : String(e);
		}
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Escape') {
			e.preventDefault();
			onclose(reviewed > 0);
		}
	}

	// Load queue on mount
	loadQueue();
</script>

<svelte:window onkeydown={handleKeydown} />

<!-- svelte-ignore a11y_no_static_element_interactions -->
<!-- svelte-ignore a11y_click_events_have_key_events -->
<div class="overlay" onclick={() => onclose(reviewed > 0)}>
	<div class="dialog" onclick={(e) => e.stopPropagation()}>
		<div class="dialog-header">
			<span class="dialog-title">Review energy</span>
			{#if !done && totalToReview > 0}
				<span class="progress">{currentIndex + 1} / {totalToReview}</span>
			{/if}
			<Button variant="ghost" size="sm" title="Close (Esc)" onclick={() => onclose(reviewed > 0)}>Esc</Button>
		</div>

		{#if loading}
			<div class="dialog-status">Reading your set...</div>
		{:else if error}
			<div class="dialog-status error">{error}</div>
		{:else if done}
			<div class="dialog-done">
				{#if reviewed > 0}
					<div class="done-count">{reviewed} track{reviewed === 1 ? '' : 's'} reviewed</div>
					<div class="done-msg">Your set's energy data is up to date.</div>
				{:else if totalToReview === 0}
					<div class="done-msg">All tracks in this set already have reviewed energy.</div>
				{:else}
					<div class="done-msg">All done.</div>
				{/if}
				<div class="done-action">
					<Button variant="primary" onclick={() => onclose(reviewed > 0)}>Close</Button>
				</div>
			</div>
		{:else if currentItem}
			{#key currentItem.track.id}
				<TinderCard item={currentItem} ondecide={handleDecide} {teachingMoment} />
			{/key}
		{/if}
	</div>
</div>

<style>
	.overlay {
		position: fixed;
		inset: 0;
		background: rgba(0, 0, 0, 0.7);
		z-index: 100;
		display: flex;
		align-items: center;
		justify-content: center;
	}

	.dialog {
		background: var(--bg-primary);
		border: 1px solid var(--border);
		border-radius: var(--radius-xl);
		width: 560px;
		max-width: 95vw;
		max-height: 90vh;
		overflow-y: auto;
	}

	.dialog-header {
		display: flex;
		align-items: center;
		gap: var(--space-lg);
		padding: var(--space-lg) var(--space-xl);
		border-bottom: 1px solid var(--border);
	}

	.dialog-title {
		font-weight: var(--font-weight-semibold);
		font-size: var(--text-md);
	}

	.progress {
		font-size: var(--text-sm);
		color: var(--text-dim);
		margin-right: auto;
	}

	.dialog-status {
		padding: var(--space-5xl) var(--space-2xl);
		text-align: center;
		font-size: var(--text-base);
		color: var(--text-secondary);
	}

	.dialog-status.error {
		color: var(--energy-high);
	}

	.dialog-done {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: var(--space-md);
		padding: var(--space-5xl) var(--space-2xl);
	}

	.done-count {
		font-size: var(--text-lg);
		font-weight: var(--font-weight-semibold);
		color: var(--accent);
	}

	.done-msg {
		font-size: var(--text-base);
		color: var(--text-secondary);
	}

	.done-action {
		margin-top: var(--space-lg);
	}
</style>
