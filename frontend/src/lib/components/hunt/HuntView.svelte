<script lang="ts">
	import type { HuntSession } from '$lib/types';
	import { getHuntingStore } from '$lib/stores/hunting.svelte';
	import { getSoundCloudStore } from '$lib/stores/soundcloud.svelte';
	import HuntResults from './HuntResults.svelte';
	import HuntHistory from './HuntHistory.svelte';
	import SoundCloudConnect from './SoundCloudConnect.svelte';
	import SoundCloudBrowser from './SoundCloudBrowser.svelte';

	const store = getHuntingStore();
	const sc = getSoundCloudStore();

	let urlInput = $state('');
	let showHistory = $state(false);
	let mode = $state<'url' | 'soundcloud'>('url');

	// Check SC status on mount
	$effect(() => {
		sc.checkStatus();
	});

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

	function handleSCHuntResult(hunt: HuntSession) {
		// Pipe SC chase result into the hunting store's currentHunt
		store.loadHunt(hunt.id);
		mode = 'url'; // Switch back to show results
	}

	$effect(() => {
		if (showHistory) store.loadHistory();
	});
</script>

<div class="hunt-view">
	<div class="hunt-header">
		<div class="header-top">
			<h2>Track Hunter</h2>
			<SoundCloudConnect />
		</div>
		<p class="subtitle">Paste a set URL or browse your SoundCloud — we'll find every track and show you where to get them</p>
	</div>

	<div class="mode-tabs">
		<button class="mode-tab" class:active={mode === 'url'} onclick={() => mode = 'url'}>
			URL Hunt
		</button>
		<button class="mode-tab" class:active={mode === 'soundcloud'} onclick={() => mode = 'soundcloud'} disabled={!sc.connected}>
			SoundCloud
		</button>
	</div>

	{#if mode === 'url'}
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
	{:else}
		{#if !sc.connected}
			<div class="empty-state">
				<p>Connect your SoundCloud account to browse playlists and chase tracks.</p>
			</div>
		{:else}
			<SoundCloudBrowser onhuntresult={handleSCHuntResult} />
		{/if}
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

	.header-top {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 4px;
	}

	.subtitle {
		color: var(--text-secondary);
		font-size: 13px;
		margin: 0 0 12px;
	}

	.mode-tabs {
		display: flex;
		gap: 2px;
		margin-bottom: 12px;
		border-bottom: 1px solid var(--border);
	}

	.mode-tab {
		padding: 8px 16px;
		font-size: 13px;
		font-weight: 500;
		background: transparent;
		color: var(--text-secondary);
		border: none;
		border-bottom: 2px solid transparent;
		cursor: pointer;
	}

	.mode-tab.active {
		color: var(--text-primary);
		border-bottom-color: var(--accent);
	}

	.mode-tab:disabled {
		opacity: 0.4;
		cursor: default;
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
