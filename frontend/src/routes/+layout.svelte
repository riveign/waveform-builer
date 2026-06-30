<script lang="ts">
	import '../app.css';
	import NowPlayingBar from '$lib/components/player/NowPlayingBar.svelte';
	import SegmentedControl, { type SegmentOption } from '$lib/components/primitives/SegmentedControl.svelte';
	import { getPlayerStore } from '$lib/stores/player.svelte';
	import { getUiStore } from '$lib/stores/ui.svelte';

	let { children, rightActions } = $props<{
		children: import('svelte').Snippet;
		/** Optional right-aligned navbar actions; renders into the reserved slot. */
		rightActions?: import('svelte').Snippet;
	}>();

	const player = getPlayerStore();
	const ui = getUiStore();

	/* Measured fit-width threshold (a layout breakpoint, not a color/spacing token):
	   below 900px the full labels + shortcut hints no longer fit the navbar's tab
	   column, so we condense. We bind the navbar's own width rather than the viewport
	   so the trigger tracks the actual space the tabs have (the logo column is fixed). */
	let headerWidth = $state(0);
	const condenseTabs = $derived(headerWidth > 0 && headerWidth < 900);

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
	<header class="app-header" bind:clientWidth={headerWidth}>
		<div class="app-logo">
			<span class="app-kanji">聴</span>
			<h1 class="app-title">Kiku</h1>
		</div>
		<div class="app-nav">
			<nav class="app-tabs" class:scrollable={condenseTabs}>
				<SegmentedControl
					options={tabs}
					value={ui.activeTab as TabId}
					onchange={(v) => (ui.activeTab = v)}
					ariaLabel="Workspace views"
					dense={condenseTabs}
				/>
			</nav>
			<div class="app-actions">
				{@render rightActions?.()}
			</div>
		</div>
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

	/* Second grid column: tabs on the left, a reserved right-actions slot pushed to
	   the far edge. The tabs don't stretch across the bar — they keep their natural
	   width and the actions slot owns the remainder, so adding actions later doesn't
	   re-lay-out the navbar. */
	.app-nav {
		display: flex;
		align-items: stretch;
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

	/* Safety net under condensing: only when tabs are in the condensed/scrollable
	   state do we fade the scrolled-off edges rather than hard-cutting a tab. At wide
	   widths (no overflow) the unconditional mask would dim the leftmost/rightmost
	   tabs, so the fade is gated behind the condense state. Scrollbar is hidden but
	   the region stays wheel/keyboard scrollable. The fade width is a small fixed
	   edge inset, not a color token. */
	.app-tabs.scrollable {
		-webkit-mask-image: linear-gradient(
			to right,
			transparent 0,
			#000 var(--space-xl),
			#000 calc(100% - var(--space-xl)),
			transparent 100%
		);
		mask-image: linear-gradient(
			to right,
			transparent 0,
			#000 var(--space-xl),
			#000 calc(100% - var(--space-xl)),
			transparent 100%
		);
	}

	.app-tabs::-webkit-scrollbar {
		display: none;
	}

	/* Reserved right-aligned slot for future navbar actions. Empty today; the flex
	   region keeps the space so adding actions doesn't shift the tabs. */
	.app-actions {
		display: flex;
		align-items: center;
		gap: var(--space-sm);
		margin-left: auto;
		padding-right: var(--space-lg);
	}

	.app-actions:empty {
		padding-right: 0;
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
