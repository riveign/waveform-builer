<script lang="ts">
	import { getHuntingStore } from '$lib/stores/hunting.svelte';
	import HuntResults from './HuntResults.svelte';
	import HuntHistory from './HuntHistory.svelte';

	const store = getHuntingStore();

	let urlInput = $state('');
	let showHistory = $state(false);

	async function handleSubmit() {
		const url = urlInput.trim();
		if (!url) return;
		await store.hunt(url);
		urlInput = '';
	}

	function handleHistorySelect(huntId: number) {
		showHistory = false;
		store.loadHunt(huntId);
	}

	$effect(() => {
		if (showHistory) store.loadHistory();
	});
</script>

<div class="hunt-view">
	<div class="hunt-header">
		<h2>Track Hunter</h2>
		<p class="subtitle">Paste a set URL — we'll find every track and show you where to get them</p>
	</div>

	<form class="hunt-form" onsubmit={(e) => { e.preventDefault(); handleSubmit(); }}>
		<input
			type="url"
			bind:value={urlInput}
			placeholder="YouTube, SoundCloud, or Mixcloud URL..."
			disabled={store.loading}
		/>
		<button type="submit" disabled={store.loading || !urlInput.trim()}>
			{store.loading ? 'Hunting...' : 'Hunt'}
		</button>
		<button type="button" class="history-btn" onclick={() => showHistory = !showHistory}>
			History
		</button>
	</form>

	{#if store.error}
		<div class="error">{store.error}</div>
	{/if}

	{#if showHistory}
		<HuntHistory items={store.history} onselect={handleHistorySelect} />
	{:else if store.currentHunt}
		<HuntResults hunt={store.currentHunt} onmarkwanted={store.markWanted} />
	{:else if !store.loading}
		<div class="empty-state">
			<p>Hear a set you love? Paste the link above to hunt down every track.</p>
		</div>
	{/if}
</div>

<style>
	.hunt-view {
		padding: 20px;
		max-width: 900px;
	}

	.hunt-header h2 {
		margin: 0 0 4px;
		font-size: 18px;
	}

	.subtitle {
		color: var(--text-secondary);
		font-size: 13px;
		margin: 0 0 16px;
	}

	.hunt-form {
		display: flex;
		gap: 8px;
		margin-bottom: 16px;
	}

	.hunt-form input {
		flex: 1;
		padding: 8px 12px;
		font-size: 13px;
		background: var(--bg-secondary);
		border: 1px solid var(--border);
		border-radius: 6px;
		color: var(--text-primary);
	}

	.hunt-form button {
		padding: 8px 16px;
		font-size: 13px;
		font-weight: 600;
		border-radius: 6px;
		cursor: pointer;
	}

	.hunt-form button[type='submit'] {
		background: var(--accent);
		color: #000;
		border: none;
	}

	.hunt-form button[type='submit']:disabled {
		opacity: 0.5;
		cursor: default;
	}

	.history-btn {
		background: transparent;
		color: var(--text-secondary);
		border: 1px solid var(--border);
	}

	.error {
		padding: 8px 12px;
		background: rgba(255, 80, 80, 0.1);
		border: 1px solid rgba(255, 80, 80, 0.3);
		border-radius: 6px;
		color: #ff5050;
		font-size: 13px;
		margin-bottom: 12px;
	}

	.empty-state {
		text-align: center;
		color: var(--text-dim);
		padding: 60px 20px;
		font-size: 14px;
	}
</style>
