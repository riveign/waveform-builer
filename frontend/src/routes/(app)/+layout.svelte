<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import type { Track, SetBuildParams, SetBuildComplete, SetAnalysis } from '$lib/types';
	import LibraryBrowser from '$lib/components/library/LibraryBrowser.svelte';
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
		const target = e.target as HTMLElement;
		if (target.tagName === 'INPUT' || target.tagName === 'SELECT' || target.tagName === 'TEXTAREA') return;

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

<div class="app-shell">
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
			<aside class="panel-left">
				<LibraryBrowser onselect={handleTrackSelect} />
			</aside>
			<main class="panel-right">
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
		position: sticky;
		top: 0;
		z-index: 50;
	}

	.app-logo {
		display: flex;
		align-items: center;
		gap: var(--space-sm);
		padding-left: var(--space-lg);
		color: var(--accent);
		border-right: 1px solid var(--border);
		min-width: 0;
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
		grid-template-columns: var(--panel-width) 1fr;
		height: 100%;
		overflow: hidden;
	}

	.panel-left {
		border-right: 1px solid var(--border);
		overflow: hidden;
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
