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

	/* Navbar shares the body's split: first column is exactly --panel-width (over
	   the sidebar), second is 1fr (over the content pane). Grid origin is x=0 with
	   no header padding, identical to .two-panel, so the logo|tabs boundary lands on
	   the SAME x as the sidebar|content boundary — one continuous vertical line. */
	.app-header {
		height: var(--band-h);
		display: grid;
		grid-template-columns: var(--panel-width) 1fr;
		align-items: stretch;
		background: var(--bg-secondary);
		border-bottom: 1px solid var(--border);
		flex-shrink: 0;
		/* Pin the chrome to the top of the shell. In the fixed-frame model the body
		   scrolls internally, so sticky keeps the navbar above any in-pane sticky
		   bands (z 5) and content rows. */
		position: sticky;
		top: 0;
		z-index: 50;
	}

	.app-logo {
		display: flex;
		align-items: center;
		gap: var(--space-sm);
		/* Left-pad to --space-lg so "聴 Kiku" aligns with the sidebar search box
		   (SearchFilters toolbar pads 0 var(--space-lg)). Right border continues the
		   sidebar|content divider up through the navbar. */
		padding-left: var(--space-lg);
		color: var(--accent);
		border-right: 1px solid var(--border);
		min-width: 0;
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
		/* Clear the fixed NowPlayingBar so the sidebar's internal list + the content
		   pane don't hide their last rows behind it. Token, not a magic number. */
		padding-bottom: var(--playback-bar-h);
	}
</style>
