<script lang="ts">
	import TrackView from './waveform/TrackView.svelte';
	import SetView from './set/SetView.svelte';
	import DnaView from './dna/DnaView.svelte';
	import EnergyTinder from './tinder/EnergyTinder.svelte';
	import HuntView from './hunt/HuntView.svelte';
	import AlbumsView from './library/AlbumsView.svelte';
	import SetPlaybackBar from './set/SetPlaybackBar.svelte';
	import PlaybackDeck from './set/PlaybackDeck.svelte';
	import { getUiStore } from '$lib/stores/ui.svelte';
	import { getPlaybackStore } from '$lib/stores/playback.svelte';

	const ui = getUiStore();
	const pb = getPlaybackStore();

	// Tab strip now lives in the navbar (+layout.svelte). This component owns the
	// tab CONTENT switch + the 1–6 number-key shortcuts below.
	function handleKeydown(e: KeyboardEvent) {
		const target = e.target as HTMLElement;
		if (target.tagName === 'INPUT' || target.tagName === 'SELECT' || target.tagName === 'TEXTAREA') return;

		// Playback shortcuts (active when playback is running)
		if (pb.isActive) {
			if (e.key === ' ') { pb.togglePlayPause(); e.preventDefault(); return; }
			if (e.key === 'ArrowRight') { pb.next(); e.preventDefault(); return; }
			if (e.key === 'ArrowLeft') { pb.previous(); e.preventDefault(); return; }
			if (e.key === 'Escape') { pb.stop(); e.preventDefault(); return; }
			if (pb.mode === 'builder') {
				if (e.key === 'k' || e.key === 'K') { pb.keep(); e.preventDefault(); return; }
			}
		}

		if (e.key === '1') { ui.activeTab = 'track'; e.preventDefault(); }
		else if (e.key === '2') { ui.activeTab = 'set'; e.preventDefault(); }
		else if (e.key === '3') { ui.activeTab = 'dna'; e.preventDefault(); }
		else if (e.key === '4') { ui.activeTab = 'tinder'; e.preventDefault(); }
		else if (e.key === '5') { ui.activeTab = 'hunt'; e.preventDefault(); }
		else if (e.key === '6') { ui.activeTab = 'albums'; e.preventDefault(); }
	}
</script>

<svelte:window onkeydown={handleKeydown} />

<div class="workspace">
	<div class="tab-content">
		<!-- Content-pane grid foundation. Surfaces render full-width for now; the
		     .grid-12--content host is ready for per-surface card grids (deferred). -->
		<div class="content-grid">
			{#if ui.activeTab === 'track'}
				{#if ui.selectedTrack}
					<TrackView track={ui.selectedTrack} />
				{:else}
					<div class="empty-state">
						<p>Choose a track to explore its sound</p>
					</div>
				{/if}
			{:else if ui.activeTab === 'set'}
				<SetView />
			{:else if ui.activeTab === 'dna'}
				<DnaView />
			{:else if ui.activeTab === 'tinder'}
				<EnergyTinder />
			{:else if ui.activeTab === 'hunt'}
				<HuntView />
			{:else if ui.activeTab === 'albums'}
				<AlbumsView />
			{/if}
		</div>
	</div>

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
</div>

<style>
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
	   everything (e.g. the set's energy chart + analysis bar slid away). Shorter,
	   non-frame surfaces (track view, empty states) still grow and scroll here. */
	.tab-content {
		flex: 1;
		min-height: 0;
		display: flex;
		flex-direction: column;
		overflow-y: auto;
	}

	/* Content-pane grid foundation (spec 023 shell). Carries the dense 16px gutter
	   token and the page padding. Renders as a block for now so existing surfaces
	   stay full-width — per-surface opt-in to a 12-col card grid is a later wave.
	   Flex column + min-height:100% gives full-height surfaces (e.g. .set-view) a
	   definite frame to fill (so they can host their OWN internal scroller, like the
	   sidebar), while shorter surfaces still grow and let .tab-content scroll. */
	.content-grid {
		--grid-gutter: var(--space-xl);
		display: flex;
		flex-direction: column;
		min-height: 100%;
	}

	.empty-state {
		display: flex;
		align-items: center;
		justify-content: center;
		height: 100%;
		color: var(--text-dim);
		font-size: var(--text-md);
	}
</style>
