<script lang="ts">
	import '../app.css';
	import NowPlayingBar from '$lib/components/player/NowPlayingBar.svelte';
	import SegmentedControl, { type SegmentOption } from '$lib/components/primitives/SegmentedControl.svelte';
	import { getPlayerStore } from '$lib/stores/player.svelte';
	import { getUiStore } from '$lib/stores/ui.svelte';

	let { children } = $props();

	const player = getPlayerStore();
	const ui = getUiStore();

	type TabId = 'track' | 'set' | 'dna' | 'tinder' | 'hunt' | 'albums';

	const tabs: SegmentOption<TabId>[] = [
		{ value: 'track', label: 'Track view', shortcut: '1' },
		{ value: 'set', label: 'Set timeline', shortcut: '2' },
		{ value: 'dna', label: 'Taste DNA', shortcut: '3' },
		{ value: 'tinder', label: 'Energy tinder', shortcut: '4' },
		{ value: 'hunt', label: 'Track hunter', shortcut: '5' },
		{ value: 'albums', label: 'Albums', shortcut: '6' },
	];
</script>

<svelte:window onkeydown={(e) => {
	// Skip if user is typing in an input/textarea/select
	const tag = (e.target as HTMLElement)?.tagName;
	if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return;

	if (e.key === ' ' && player.hasTrack) {
		e.preventDefault();
		player.togglePlay();
	} else if (e.key === 'ArrowLeft' && player.hasTrack) {
		e.preventDefault();
		player.seek(Math.max(0, player.currentTime - 5));
	} else if (e.key === 'ArrowRight' && player.hasTrack) {
		e.preventDefault();
		player.seek(Math.min(player.duration, player.currentTime + 5));
	}
}} />

<div class="app-shell">
	<header class="app-header">
		<div class="app-logo">
			<span class="app-kanji">聴</span>
			<h1 class="app-title">Kiku</h1>
		</div>
		<nav class="app-tabs">
			<SegmentedControl
				options={tabs}
				value={ui.activeTab as TabId}
				onchange={(v) => (ui.activeTab = v)}
				ariaLabel="Workspace views"
			/>
		</nav>
	</header>
	<div class="app-body" class:has-player={player.hasTrack}>
		{@render children()}
	</div>
</div>

<NowPlayingBar />

<style>
	.app-shell {
		display: flex;
		flex-direction: column;
		height: 100vh;
		overflow: hidden;
	}

	.app-header {
		height: var(--band-h);
		display: flex;
		align-items: stretch;
		padding: 0 var(--space-xl);
		background: var(--bg-secondary);
		border-bottom: 1px solid var(--border);
		flex-shrink: 0;
		gap: var(--space-2xl);
	}

	.app-logo {
		display: flex;
		align-items: center;
		gap: var(--space-sm);
		color: var(--accent);
		flex-shrink: 0;
	}

	/* Tabs live in the navbar (right of the logo). Segments stretch to the full
	   band height so their active underline lands on the navbar's bottom border —
	   the single shared baseline the body content starts at. */
	.app-tabs {
		display: flex;
		align-items: stretch;
		min-width: 0;
		overflow-x: auto;
		scrollbar-width: none;
	}

	.app-tabs::-webkit-scrollbar {
		display: none;
	}

	.app-kanji {
		font-size: var(--text-xl);
		font-weight: var(--font-weight-semibold);
		line-height: 1;
		color: var(--text-primary);
	}

	.app-title {
		font-size: 15px;
		font-weight: var(--font-weight-semibold);
		letter-spacing: 0.5px;
		color: var(--accent);
	}

	.app-body {
		flex: 1;
		overflow: hidden;
	}

	.app-body.has-player {
		padding-bottom: 72px;
	}
</style>
