<script lang="ts">
	import type { HuntSession } from '$lib/types';
	import { getHuntingStore } from '$lib/stores/hunting.svelte';
	import { getSoundCloudStore } from '$lib/stores/soundcloud.svelte';
	import HuntResults from './HuntResults.svelte';
	import HuntHistory from './HuntHistory.svelte';
	import SoundCloudConnect from './SoundCloudConnect.svelte';
	import SoundCloudBrowser from './SoundCloudBrowser.svelte';
	import Button from '$lib/components/primitives/Button.svelte';
	import Spinner from '$lib/components/Spinner.svelte';

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
	<!-- Toolbar band — title + SoundCloud connect. Sticky top:0, matches the Set
	     tab's SetPicker band so its divider lands at the sidebar search-box Y. -->
	<div class="hunt-toolbar">
		<h2>Track Hunter</h2>
		<SoundCloudConnect />
	</div>

	<!-- Secondary band — mode tabs. Sticky beneath the toolbar band, matches the
	     Set tab's --band-secondary-h rhythm.
	     Bespoke (not SegmentedControl): the SoundCloud option is conditionally
	     disabled until connected, and SegmentedControl has no per-option disabled. -->
	<div class="hunt-modes">
		<button class="mode-tab" class:active={mode === 'url'} onclick={() => mode = 'url'}>
			URL Hunt
		</button>
		<button class="mode-tab" class:active={mode === 'soundcloud'} onclick={() => mode = 'soundcloud'} disabled={!sc.connected}>
			SoundCloud
		</button>
	</div>

	<!-- Non-sticky search strip: subtitle + form + error scroll away under the bands. -->
	{#if mode === 'url'}
		<div class="hunt-search">
			<p class="subtitle">Paste a set URL or browse your SoundCloud — we'll find every track and show you where to get them</p>

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
				<!-- What happened + why + what to try — never a raw dump, never blame the DJ. -->
				<div class="error" role="alert">
					Couldn't chase that link. It may not be a set we can read yet — check the URL and try again.
				</div>
			{/if}
		</div>
	{/if}

	<!-- Sole scroller: results / history / browser scroll beneath the pinned bands -->
	<div class="hunt-scroll">
		{#if mode === 'url'}
			{#if showHistory}
				<HuntHistory items={store.history} onselect={handleHistorySelect} />
			{:else if store.loading}
				<div class="loading-state">
					<Spinner label="Chasing down the tracks..." />
				</div>
			{:else if store.currentHunt}
				<HuntResults hunt={store.currentHunt} onmarkwanted={store.markWanted} />
			{:else}
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
</div>

<style>
	.hunt-view {
		display: flex;
		flex-direction: column;
		flex: 1;
		min-height: 0;
		overflow: hidden;
	}

	/* Toolbar band — title + SoundCloud connect. Matches the Set tab's SetPicker:
	   same --band-toolbar-h (48px) + zero top offset, so this divider lands at the
	   same y as the sidebar search box (spec 023 band rhythm). Opaque background so
	   scrolling content doesn't bleed through. */
	.hunt-toolbar {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: var(--space-lg);
		padding: 0 var(--space-xl);
		height: var(--band-toolbar-h);
		border-bottom: 1px solid var(--border);
		position: sticky;
		top: 0;
		z-index: 5;
		background: var(--bg-primary);
	}

	.hunt-toolbar h2 {
		margin: 0;
		font-size: 18px;
	}

	/* Secondary band — mode tabs. Sticks directly beneath the toolbar band (offset
	   by --band-toolbar-h), same --band-secondary-h (44px) + border as the Set tab. */
	.hunt-modes {
		display: flex;
		align-items: center;
		gap: 2px;
		padding: 0 var(--space-xl);
		height: var(--band-secondary-h);
		border-bottom: 1px solid var(--border);
		position: sticky;
		top: var(--band-toolbar-h);
		z-index: 4;
		background: var(--bg-primary);
	}

	/* Non-sticky search strip beneath the bands. */
	.hunt-search {
		flex-shrink: 0;
		padding: var(--space-lg) var(--space-xl) 0;
		max-width: 900px;
	}

	/* Sole scroller: results scroll beneath the pinned bands */
	.hunt-scroll {
		flex: 1;
		min-height: 0;
		overflow-y: auto;
		padding: 16px 20px 20px;
		max-width: 900px;
	}

	.subtitle {
		color: var(--text-secondary);
		font-size: 13px;
		margin: 0 0 12px;
	}

	.mode-tab {
		display: inline-flex;
		align-items: center;
		height: 100%;
		padding: 0 16px;
		font-size: 13px;
		font-weight: 500;
		background: transparent;
		color: var(--text-secondary);
		border: none;
		border-bottom: 2px solid transparent;
		margin-bottom: -1px;
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
		margin-bottom: 12px;
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

	.loading-state {
		display: flex;
		justify-content: center;
		padding: 60px 20px;
	}
</style>
