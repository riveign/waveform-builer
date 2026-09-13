<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import type { Track, SetBuildParams, SetBuildComplete, SetAnalysis } from '$lib/types';
	import LibraryBrowser from '$lib/components/library/LibraryBrowser.svelte';
	import SidebarRail from '$lib/components/library/SidebarRail.svelte';
	import { focusAfterFold, LIBRARY_TOGGLE, RAIL_SEARCH, RAIL_TOGGLE } from '$lib/components/library/sidebarFocus';
	import BuildSetDialog from '$lib/components/set/BuildSetDialog.svelte';
	import BuildProgress from '$lib/components/set/BuildProgress.svelte';
	import SetPlaybackBar from '$lib/components/set/SetPlaybackBar.svelte';
	import PlaybackDeck from '$lib/components/set/PlaybackDeck.svelte';
	import SegmentedControl, { type SegmentOption } from '$lib/components/primitives/SegmentedControl.svelte';
	import { buildSet } from '$lib/api/sets';
	import { getUiStore } from '$lib/stores/ui.svelte';
	import { getPlaybackStore } from '$lib/stores/playback.svelte';
	import { getPlayerStore } from '$lib/stores/player.svelte';
	import { TABS, type Tab, tabFromPath, trackHref, setHref } from '$lib/nav';

	let { children } = $props<{ children: import('svelte').Snippet }>();

	const ui = getUiStore();
	const pb = getPlaybackStore();
	const player = getPlayerStore();

	/* Measured fit-width threshold (a layout breakpoint, not a color/spacing token):
	   below 900px the full labels + shortcut hints no longer fit the navbar's tab
	   column, so we condense. We bind the navbar's own width rather than the viewport
	   so the trigger tracks the actual space the tabs have (the logo column is fixed). */
	let headerWidth = $state(0);
	const condenseTabs = $derived(headerWidth > 0 && headerWidth < 900);

	const tabOptions: SegmentOption<Tab>[] = TABS.map((t) => ({
		value: t.value,
		label: t.label,
		shortcut: t.shortcut,
	}));
	const activeTab = $derived(tabFromPath(page.url.pathname) ?? 'track');

	// ── Build dialog + progress state ──
	type BuildEvent = { type: 'started' | 'track_added' | 'complete' | 'analyzed' | 'error'; data: any };
	type BuildState = 'idle' | 'building' | 'complete' | 'error';

	let showBuildDialog = $state(false);
	let buildState = $state<BuildState>('idle');
	let buildEvents = $state<BuildEvent[]>([]);
	let buildError = $state('');
	let lastBuildResult = $state<SetBuildComplete | null>(null);
	let lastBuildAnalysis = $state<SetAnalysis | null>(null);

	function handleTrackSelect(track: Track) {
		// Clicking a track anywhere lands on its own URL, so it can be shared.
		goto(trackHref(track.id));
		// A peek is a quick visit: picking the track is the end of it.
		if (ui.sidebarPeeking) closePeek();
	}

	// ── Library sidebar ──
	let libraryFrame = $state<HTMLElement>(null!);

	/** Fold or unfold from the keyboard, handing focus across so it's never left
	 *  inside the half that just went inert. */
	function toggleSidebarFromKeys() {
		const active = document.activeElement;
		const inLibrary = !!active && libraryFrame.contains(active);
		const inRail = !!active && !inLibrary && !!active.closest('[data-rail]');
		ui.toggleSidebar();
		if (inLibrary) focusAfterFold(RAIL_TOGGLE);
		else if (inRail) focusAfterFold(LIBRARY_TOGGLE);
	}

	function closePeek() {
		const inLibrary = libraryFrame.contains(document.activeElement);
		ui.closePeek();
		if (inLibrary) focusAfterFold(RAIL_SEARCH);
	}

	// Open the build dialog when something (e.g. the Build button in the set toolbar)
	// requests it via the ui store. Decouples the trigger from this dialog owner.
	$effect(() => {
		if (ui.buildRequested > 0) showBuildDialog = true;
	});

	async function handleBuild(params: SetBuildParams) {
		showBuildDialog = false;
		buildState = 'building';
		buildEvents = [];
		buildError = '';
		lastBuildResult = null;
		lastBuildAnalysis = null;

		let errorDuringStream = false;

		try {
			const result = await buildSet(params, (eventType, data) => {
				const event: BuildEvent = { type: eventType as BuildEvent['type'], data };

				if (eventType === 'track_added' || eventType === 'complete') {
					buildEvents = [...buildEvents, event];
				} else if (eventType === 'analyzed') {
					lastBuildAnalysis = data as SetAnalysis;
				} else if (eventType === 'error') {
					errorDuringStream = true;
					buildState = 'error';
					buildError = (data as { detail?: string })?.detail ?? 'Build failed';
				}
			});

			lastBuildResult = result;
			if (!errorDuringStream) buildState = 'complete';
		} catch (e) {
			if (!errorDuringStream) {
				buildState = 'error';
				buildError = e instanceof Error ? e.message : 'Something went wrong during the build';
			}
		}
	}

	function handleBuildRetry() {
		buildState = 'idle';
		buildEvents = [];
		buildError = '';
		showBuildDialog = true;
	}

	function handleBuildClose() {
		const completedSetId = lastBuildResult?.set_id ?? null;
		buildState = 'idle';
		buildEvents = [];
		buildError = '';
		lastBuildResult = null;

		if (completedSetId !== null) {
			// Hand the freshly computed analysis to the set view so it need not re-run.
			ui.pendingAnalysis = lastBuildAnalysis;
			lastBuildAnalysis = null;
			goto(setHref(completedSetId));
		}
	}

	function handleKeydown(e: KeyboardEvent) {
		// Esc closes a peek even from inside the search box.
		if (e.key === 'Escape' && ui.sidebarPeeking) {
			closePeek();
			e.preventDefault();
			return;
		}

		const target = e.target as HTMLElement;
		if (target.tagName === 'INPUT' || target.tagName === 'SELECT' || target.tagName === 'TEXTAREA') return;

		if (!e.metaKey && !e.ctrlKey && !e.altKey) {
			if (e.key === '[') { toggleSidebarFromKeys(); e.preventDefault(); return; }
			if (e.key === '/') { ui.focusSearch(); e.preventDefault(); return; }
		}

		// Playback shortcuts take precedence while a set is playing.
		if (pb.isActive) {
			if (e.key === ' ') { pb.togglePlayPause(); e.preventDefault(); return; }
			if (e.key === 'ArrowRight') { pb.next(); e.preventDefault(); return; }
			if (e.key === 'ArrowLeft') { pb.previous(); e.preventDefault(); return; }
			if (e.key === 'Escape') { pb.stop(); e.preventDefault(); return; }
			if (pb.mode === 'builder' && (e.key === 'k' || e.key === 'K')) { pb.keep(); e.preventDefault(); return; }
		}

		const tab = TABS.find((t) => t.shortcut === e.key);
		if (tab) {
			goto(tab.path);
			e.preventDefault();
		}
	}
</script>

<svelte:window onkeydown={handleKeydown} />

<div class="app-shell" class:collapsed={ui.sidebarCollapsed} class:peeking={ui.sidebarPeeking}>
	<header class="app-header" bind:clientWidth={headerWidth}>
		<div class="app-logo">
			<span class="app-kanji">聴</span>
			<h1 class="app-title">Kiku</h1>
		</div>
		<div class="app-nav">
			<nav class="app-tabs" class:scrollable={condenseTabs}>
				<SegmentedControl
					options={tabOptions}
					value={activeTab}
					onchange={(v) => goto(TABS.find((t) => t.value === v)!.path)}
					ariaLabel="Workspace views"
					dense={condenseTabs}
				/>
			</nav>
			<div class="app-actions"></div>
		</div>
	</header>

	<div class="app-body" class:has-player={player.hasTrack}>
		<div class="two-panel">
			<aside class="panel-left" id="library-sidebar" aria-label="Library">
				<SidebarRail />
				<div class="library-frame" inert={!ui.libraryOpen} bind:this={libraryFrame}>
					<LibraryBrowser onselect={handleTrackSelect} />
				</div>
			</aside>
			<main class="panel-right">
				<!-- Pointer-only dismiss; Esc is the keyboard path (handleKeydown). -->
				<!-- svelte-ignore a11y_click_events_have_key_events -->
				<div class="scrim" role="presentation" onclick={closePeek}></div>
				{#if buildState !== 'idle'}
					<div class="build-overlay" role="region" aria-label="Build progress">
						<BuildProgress
							{buildState}
							events={buildEvents}
							error={buildError}
							onretry={handleBuildRetry}
							onclose={handleBuildClose}
						/>
					</div>
				{/if}
				<div class="workspace">
					<div class="tab-content">
						<div class="content-grid">
							{@render children()}
						</div>
					</div>
				</div>
			</main>
		</div>
	</div>
</div>

<BuildSetDialog bind:open={showBuildDialog} onbuild={handleBuild} />

{#if pb.isActive}
	<SetPlaybackBar />
	<PlaybackDeck
		deck="A"
		track={pb.deckATrack}
		onready={pb.onDeckReady}
		onfinish={pb.onDeckFinish}
		ontimeupdate={pb.onDeckTimeUpdate}
		onerror={pb.onDeckError}
	/>
	<PlaybackDeck
		deck="B"
		track={pb.deckBTrack}
		onready={pb.onDeckReady}
		onfinish={pb.onDeckFinish}
		ontimeupdate={pb.onDeckTimeUpdate}
		onerror={pb.onDeckError}
	/>
{/if}

<style>
	/* One width drives both the navbar and the body grids, so the logo|tabs line
	   follows the sidebar edge as it folds to the rail and back. */
	.app-shell {
		--sidebar-w: var(--panel-width);
		display: flex;
		flex-direction: column;
		height: 100vh;
		overflow: hidden;
	}

	.app-shell.collapsed {
		--sidebar-w: var(--rail-width);
	}

	/* Navbar shares the body's split: first column is exactly --panel-width (over
	   the sidebar), second is 1fr (over the content pane). Grid origin is x=0 with
	   no header padding, identical to .two-panel, so the logo|tabs boundary lands on
	   the SAME x as the sidebar|content boundary — one continuous vertical line. */
	.app-header {
		height: var(--band-h);
		display: grid;
		grid-template-columns: var(--sidebar-w) 1fr;
		transition: grid-template-columns var(--dur-base) var(--ease-standard);
		align-items: stretch;
		background: var(--bg-secondary);
		border-bottom: 1px solid var(--border);
		flex-shrink: 0;
		position: sticky;
		top: 0;
		z-index: 50;
	}

	.app-logo {
		display: flex;
		align-items: center;
		gap: var(--space-sm);
		/* Centers the 1em-wide kanji inside the rail, and keeps it put when unfolded. */
		padding-left: calc((var(--rail-width) - var(--text-xl)) / 2);
		color: var(--accent);
		border-right: 1px solid var(--border);
		min-width: 0;
		overflow: hidden;
		white-space: nowrap;
	}

	.app-nav {
		display: flex;
		align-items: stretch;
		min-width: 0;
	}

	.app-tabs {
		display: flex;
		align-items: stretch;
		min-width: 0;
		overflow-x: auto;
		scrollbar-width: none;
	}

	/* Only when tabs are condensed do we fade the scrolled-off edges rather than
	   hard-cutting a tab. At wide widths the unconditional mask would dim the
	   outermost tabs, so the fade is gated behind the condense state. */
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
		transition: opacity var(--dur-base) var(--ease-standard);
	}

	.collapsed .app-title {
		opacity: 0;
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

	.two-panel {
		display: grid;
		grid-template-columns: var(--sidebar-w) 1fr;
		transition: grid-template-columns var(--dur-base) var(--ease-standard);
		height: 100%;
		overflow: hidden;
	}

	.panel-left {
		position: relative;
		min-width: 0;
	}

	.peeking .panel-left {
		z-index: 20; /* above the scrim (15) and the build overlay (10) */
	}

	/* The library keeps its full width while the column narrows, and is clipped
	   rather than squeezed — so the track table never re-lays its columns mid-fold.
	   It stays mounted when collapsed: search, filters, page and scroll survive. */
	.library-frame {
		position: absolute;
		inset: 0 auto 0 0;
		width: var(--panel-width);
		background: var(--bg-primary);
		border-right: 1px solid var(--border);
		z-index: 2;
		clip-path: inset(0 0 0 0);
		transition:
			clip-path var(--dur-base) var(--ease-standard),
			visibility 0s linear 0s;
	}

	.collapsed .library-frame {
		visibility: hidden;
		clip-path: inset(0 calc(100% - var(--rail-width)) 0 0);
		transition:
			clip-path var(--dur-base) var(--ease-standard),
			visibility 0s linear var(--dur-base);
	}

	.collapsed.peeking .library-frame {
		visibility: visible;
		clip-path: none;
		transition: none;
		box-shadow: 12px 0 32px rgba(0, 0, 0, 0.55);
		animation: peek-in var(--dur-base) var(--ease-decelerate);
	}

	@keyframes peek-in {
		from {
			transform: translateX(calc(-1 * var(--space-xl)));
			opacity: 0;
		}
	}

	.scrim {
		position: absolute;
		inset: 0;
		z-index: 15;
		background: rgba(0, 0, 0, 0.45);
		opacity: 0;
		pointer-events: none;
		transition: opacity var(--dur-base) var(--ease-standard);
	}

	.peeking .scrim {
		opacity: 1;
		pointer-events: auto;
	}

	.panel-right {
		overflow: hidden;
		position: relative;
	}

	/* ── Build overlay — sits above the workspace when building ── */
	.build-overlay {
		position: absolute;
		inset: 0;
		z-index: 10;
		display: flex;
		align-items: center;
		justify-content: center;
		background: rgba(0, 0, 0, 0.55);
		padding: var(--space-3xl);
	}

	.workspace {
		display: flex;
		flex-direction: column;
		height: 100%;
		overflow: hidden;
	}

	/* Content scroll region. Flex column so its single child (.content-grid) is
	   bounded by this region's DEFINITE height — giving full-height surfaces that
	   opt into `flex:1; min-height:0; overflow:hidden` (set/dna/tinder/hunt/albums)
	   a real frame for their OWN internal scroller. Without this, `.content-grid`'s
	   `min-height:100%` lets the column grow to content and THIS region scrolls
	   everything. Shorter surfaces (track view, empty states) still scroll here. */
	.tab-content {
		flex: 1;
		min-height: 0;
		display: flex;
		flex-direction: column;
		overflow-y: auto;
	}

	/* Content-pane grid foundation (spec 023 shell). Carries the dense gutter token
	   and the page padding. Flex column + min-height:100% gives full-height surfaces
	   a definite frame to fill, while shorter surfaces still let .tab-content scroll. */
	.content-grid {
		--grid-gutter: var(--space-xl);
		display: flex;
		flex-direction: column;
		min-height: 100%;
	}
</style>
