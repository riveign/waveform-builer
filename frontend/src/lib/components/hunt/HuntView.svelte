<script lang="ts">
	import type { HuntSession } from '$lib/types';
	import { getHuntingStore } from '$lib/stores/hunting.svelte';
	import { getSoundCloudStore } from '$lib/stores/soundcloud.svelte';
	import HuntResults from './HuntResults.svelte';
	import HuntHistory from './HuntHistory.svelte';
	import SoundCloudConnect from './SoundCloudConnect.svelte';
	import SoundCloudBrowser from './SoundCloudBrowser.svelte';
	import Button from '$lib/components/primitives/Button.svelte';

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

	<!-- Bespoke (not SegmentedControl): the SoundCloud option is conditionally
	     disabled until connected, and SegmentedControl has no per-option disabled. -->
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
			<Button type="submit" loading={store.loading} disabled={!urlInput.trim()}>
				{store.loading ? 'Hunting...' : 'Hunt'}
			</Button>
			<Button type="button" variant="secondary" pressed={showHistory} onclick={() => showHistory = !showHistory}>
				History
			</Button>
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

	.error {
		padding: 8px 12px;
		background: color-mix(in srgb, var(--destructive) 12%, transparent);
		border: 1px solid color-mix(in srgb, var(--destructive) 32%, transparent);
		border-radius: 6px;
		color: var(--destructive);
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
