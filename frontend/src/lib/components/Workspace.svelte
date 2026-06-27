<script lang="ts">
	import TrackView from './waveform/TrackView.svelte';
	import SetView from './set/SetView.svelte';
	import DnaView from './dna/DnaView.svelte';
	import EnergyTinder from './tinder/EnergyTinder.svelte';
	import HuntView from './hunt/HuntView.svelte';
	import AlbumsView from './library/AlbumsView.svelte';
	import SetPlaybackBar from './set/SetPlaybackBar.svelte';
	import PlaybackDeck from './set/PlaybackDeck.svelte';
	import SegmentedControl, { type SegmentOption } from './primitives/SegmentedControl.svelte';
	import { getUiStore } from '$lib/stores/ui.svelte';
	import { getPlaybackStore } from '$lib/stores/playback.svelte';

	const ui = getUiStore();
	const pb = getPlaybackStore();

	type TabId = 'track' | 'set' | 'dna' | 'tinder' | 'hunt' | 'albums';

	const tabs: SegmentOption<TabId>[] = [
		{ value: 'track', label: 'Track view', shortcut: '1' },
		{ value: 'set', label: 'Set timeline', shortcut: '2' },
		{ value: 'dna', label: 'Taste DNA', shortcut: '3' },
		{ value: 'tinder', label: 'Energy tinder', shortcut: '4' },
		{ value: 'hunt', label: 'Track hunter', shortcut: '5' },
		{ value: 'albums', label: 'Albums', shortcut: '6' },
	];

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
	<div class="tab-bar">
		<SegmentedControl
			options={tabs}
			value={ui.activeTab as TabId}
			onchange={(v) => (ui.activeTab = v)}
			ariaLabel="Workspace views"
		/>
	</div>
	<div class="tab-content">
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

	.tab-bar {
		display: flex;
		background: var(--bg-secondary);
		border-bottom: 1px solid var(--border);
		flex-shrink: 0;
	}

	.tab-content {
		flex: 1;
		overflow-y: auto;
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
