<script lang="ts">
	import type { DJSet, SetDetail as SetDetailType, SetWaveformTrack, TransitionDetail as TransitionData } from '$lib/types';
	import { getSet, getSetWaveforms, getTransition, exportRekordbox } from '$lib/api/sets';
	import { getUiStore } from '$lib/stores/ui.svelte';
	import SetPicker from './SetPicker.svelte';
	import SetTimeline from './SetTimeline.svelte';
	import TransitionDetail from './TransitionDetail.svelte';
	import EnergyFlowChart from './EnergyFlowChart.svelte';
	import WavesurferPlayer from '../waveform/WavesurferPlayer.svelte';

	const ui = getUiStore();

	/** The track currently loaded in the player (derived from playingTrackId) */
	let playerTrack = $derived.by(() => {
		if (ui.playingTrackId === null) return null;
		return waveformTracks.find((t) => t.track_id === ui.playingTrackId) ?? null;
	});

	function handleTrackPlay(trackId: number) {
		if (ui.playingTrackId === trackId) {
			ui.playingTrackId = null;
			return;
		}
		ui.playingTrackId = trackId;
	}

	let selectedSet = $state<DJSet | null>(null);
	let setDetail = $state<SetDetailType | null>(null);
	let waveformTracks = $state<SetWaveformTrack[]>([]);
	let transition = $state<TransitionData | null>(null);
	let loading = $state(false);
	let loadingTransition = $state(false);
	let exporting = $state(false);
	let exportMsg = $state<string | null>(null);
	let error = $state<string | null>(null);
	let timelineContainerEl = $state<HTMLDivElement>(null!);

	/** Derive chart selectedIndex from ui.selectedTrackInSet (track ID) */
	let selectedChartIndex = $derived.by(() => {
		if (ui.selectedTrackInSet === null) return undefined;
		const idx = waveformTracks.findIndex((t) => t.track_id === ui.selectedTrackInSet);
		return idx >= 0 ? idx : undefined;
	});

	/** Chart click handler: convert index to track ID, update store */
	function handleChartTrackClick(index: number) {
		if (index >= 0 && index < waveformTracks.length) {
			ui.selectedTrackInSet = waveformTracks[index].track_id;
		}
	}

	/** Scroll timeline to selected track when selection changes */
	$effect(() => {
		const trackId = ui.selectedTrackInSet;
		if (trackId !== null && timelineContainerEl) {
			const trackEl = timelineContainerEl.querySelector(
				`[data-track-id="${trackId}"]`
			);
			trackEl?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
		}
	});

	async function handleExport() {
		if (!selectedSet || exporting) return;
		const setId = selectedSet.id;
		const setName = selectedSet.name ?? 'set';
		exporting = true;
		exportMsg = null;
		try {
			const blob = await exportRekordbox(setId);
			const url = URL.createObjectURL(blob);
			const a = document.createElement('a');
			a.href = url;
			a.download = `${setName.replace(/[^a-zA-Z0-9_-]/g, '_')}.xml`;
			document.body.appendChild(a);
			a.click();
			document.body.removeChild(a);
			URL.revokeObjectURL(url);
			exportMsg = 'Exported!';
			setTimeout(() => { exportMsg = null; }, 3000);
		} catch (e) {
			exportMsg = e instanceof Error ? e.message : 'Export failed';
			setTimeout(() => { exportMsg = null; }, 5000);
		} finally {
			exporting = false;
		}
	}

	async function loadSetData(setId: number) {
		loading = true;
		error = null;
		transition = null;
		try {
			const [detail, waveforms] = await Promise.all([
				getSet(setId),
				getSetWaveforms(setId),
			]);
			setDetail = detail;
			waveformTracks = waveforms;
		} catch (e) {
			error = e instanceof Error ? e.message : String(e);
			waveformTracks = [];
			setDetail = null;
		} finally {
			loading = false;
		}
	}

	async function handleSetSelect(set: DJSet) {
		selectedSet = set;
		await loadSetData(set.id);
	}

	async function handleTracksChanged() {
		if (!selectedSet) return;
		await loadSetData(selectedSet.id);
	}

	async function handleTransitionClick(index: number) {
		if (!selectedSet) return;
		loadingTransition = true;
		transition = null;
		try {
			transition = await getTransition(selectedSet.id, index);
		} catch (e) {
			error = e instanceof Error ? e.message : String(e);
		} finally {
			loadingTransition = false;
		}
	}
</script>

<div class="set-view">
	<SetPicker onselect={handleSetSelect} />

	{#if selectedSet}
		<div class="timeline-controls">
			<span class="set-name">{selectedSet.name}</span>
			<span class="set-meta">{selectedSet.track_count} tracks, {selectedSet.duration_min}min</span>
			<button class="export-btn" onclick={handleExport} disabled={exporting}>
				{exporting ? 'Exporting...' : 'Export XML'}
			</button>
			{#if exportMsg}
				<span class="export-msg">{exportMsg}</span>
			{/if}
		</div>

		{#if loading}
			<div class="status">Building your timeline...</div>
		{:else if error}
			<div class="status error">{error}</div>
		{:else if waveformTracks.length > 0}
			<div class="timeline-container" bind:this={timelineContainerEl}>
				<div class="top-panel">
					<div class="energy-chart-wrapper">
						<EnergyFlowChart
							tracks={waveformTracks}
							energyProfile={setDetail?.energy_profile}
							selectedIndex={selectedChartIndex}
							onTrackClick={handleChartTrackClick}
						/>
					</div>
					<div class="player-panel">
						{#if playerTrack && playerTrack.waveform_overview && playerTrack.duration_sec}
							<div class="player-track-info">
								<span class="player-title" title={playerTrack.title ?? ''}>{playerTrack.title ?? 'Untitled'}</span>
								<span class="player-artist" title={playerTrack.artist ?? ''}>{playerTrack.artist ?? 'Unknown'}</span>
							</div>
							{#key playerTrack.track_id}
								<WavesurferPlayer
									trackId={playerTrack.track_id}
									peaks={playerTrack.waveform_overview}
									duration={playerTrack.duration_sec}
									height={80}
									autoplay
									onfinish={() => { ui.playingTrackId = null; }}
								/>
							{/key}
						{:else if playerTrack}
							<div class="player-empty">No waveform available</div>
						{:else}
							<div class="player-empty">Tap play on a track to preview</div>
						{/if}
					</div>
				</div>
				<div class="timeline-scroll">
					<SetTimeline
						tracks={waveformTracks}
						setId={selectedSet.id}
						energyProfile={setDetail?.energy_profile}
						onTransitionClick={handleTransitionClick}
						onTracksChanged={handleTracksChanged}
						onTrackPlay={handleTrackPlay}
					/>
				</div>
			</div>

			{#if loadingTransition}
				<div class="status">Analyzing the transition...</div>
			{:else if transition}
				<TransitionDetail {transition} />
			{/if}
		{:else}
			<div class="status">An empty set — your story starts here</div>
		{/if}
	{:else}
		<div class="empty-state">
			Choose a set to see your journey
		</div>
	{/if}
</div>

<style>
	.set-view {
		display: flex;
		flex-direction: column;
		height: 100%;
		overflow-y: auto;
	}

	.timeline-controls {
		display: flex;
		align-items: center;
		gap: 12px;
		padding: 8px 16px;
		border-bottom: 1px solid var(--border);
	}

	.set-name {
		font-weight: 600;
		font-size: 14px;
	}

	.set-meta {
		font-size: 12px;
		color: var(--text-dim);
		margin-right: auto;
	}

	.export-btn {
		padding: 4px 12px;
		font-size: 12px;
		color: var(--text-primary);
		background: var(--bg-tertiary);
		border: 1px solid var(--border);
		border-radius: 4px;
		transition: all 0.15s;
	}

	.export-btn:hover:not(:disabled) {
		background: var(--accent);
		color: #000;
		border-color: var(--accent);
	}

	.export-btn:disabled {
		opacity: 0.5;
		cursor: default;
	}

	.export-msg {
		font-size: 11px;
		color: var(--accent);
	}

	.timeline-container {
		flex: 1;
		min-height: 0;
		display: flex;
		flex-direction: column;
		border-bottom: 1px solid var(--border);
	}

	.top-panel {
		display: flex;
		flex-shrink: 0;
		border-bottom: 1px solid var(--border);
		min-height: 0;
	}

	.energy-chart-wrapper {
		flex: 3;
		min-width: 0;
	}

	.player-panel {
		flex: 1;
		min-width: 200px;
		border-left: 1px solid var(--border);
		display: flex;
		flex-direction: column;
		justify-content: center;
		padding: 8px;
		gap: 6px;
		background: var(--bg-secondary);
	}

	.player-track-info {
		display: flex;
		flex-direction: column;
		gap: 1px;
		padding: 0 4px;
		min-width: 0;
	}

	.player-title {
		font-size: 12px;
		font-weight: 600;
		color: var(--text-primary);
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.player-artist {
		font-size: 11px;
		color: var(--text-secondary);
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.player-empty {
		display: flex;
		align-items: center;
		justify-content: center;
		height: 100%;
		font-size: 12px;
		color: var(--text-dim);
		text-align: center;
		padding: 12px;
	}

	.timeline-scroll {
		flex: 1;
		min-height: 0;
		overflow-y: auto;
	}

	.status {
		padding: 20px;
		text-align: center;
		font-size: 13px;
		color: var(--text-secondary);
	}

	.status.error {
		color: var(--energy-high);
	}

	.empty-state {
		display: flex;
		align-items: center;
		justify-content: center;
		flex: 1;
		color: var(--text-dim);
		font-size: 14px;
	}
</style>
