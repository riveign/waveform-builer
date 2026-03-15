<script lang="ts">
	import type { TinderQueueItem, TinderDecision } from '$lib/types';
	import { getTinderQueue, submitDecision } from '$lib/api/tinder';
	import TinderCard from '../tinder/TinderCard.svelte';

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
			<button class="close-btn" onclick={() => onclose(reviewed > 0)}>Esc</button>
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
				<button class="done-btn" onclick={() => onclose(reviewed > 0)}>Close</button>
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
		border-radius: 12px;
		width: 560px;
		max-width: 95vw;
		max-height: 90vh;
		overflow-y: auto;
	}

	.dialog-header {
		display: flex;
		align-items: center;
		gap: 12px;
		padding: 12px 16px;
		border-bottom: 1px solid var(--border);
	}

	.dialog-title {
		font-weight: 600;
		font-size: 14px;
	}

	.progress {
		font-size: 12px;
		color: var(--text-dim);
		margin-right: auto;
	}

	.close-btn {
		padding: 4px 10px;
		font-size: 11px;
		color: var(--text-dim);
		background: var(--bg-tertiary);
		border: 1px solid var(--border);
		border-radius: 4px;
	}

	.close-btn:hover {
		color: var(--text-primary);
	}

	.dialog-status {
		padding: 40px 20px;
		text-align: center;
		font-size: 13px;
		color: var(--text-secondary);
	}

	.dialog-status.error {
		color: var(--energy-high);
	}

	.dialog-done {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 8px;
		padding: 40px 20px;
	}

	.done-count {
		font-size: 18px;
		font-weight: 600;
		color: var(--accent);
	}

	.done-msg {
		font-size: 13px;
		color: var(--text-secondary);
	}

	.done-btn {
		margin-top: 12px;
		padding: 8px 24px;
		font-size: 13px;
		font-weight: 600;
		background: var(--accent);
		color: #000;
		border-radius: 6px;
	}

	.done-btn:hover {
		opacity: 0.9;
	}
</style>
