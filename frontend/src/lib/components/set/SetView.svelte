<script lang="ts">
	import type { DJSet, SetDetail as SetDetailType, SetWaveformTrack, TransitionDetail as TransitionData } from '$lib/types';
	import { getSet, getSetWaveforms, getTransition, exportRekordbox, exportM3U8 } from '$lib/api/sets';
	import { getUiStore } from '$lib/stores/ui.svelte';
	import SetPicker from './SetPicker.svelte';
	import SetTimeline from './SetTimeline.svelte';
	import TransitionDetail from './TransitionDetail.svelte';
	import EnergyFlowChart from './EnergyFlowChart.svelte';
	import SetEnergyReview from './SetEnergyReview.svelte';
	import { getPlaybackStore } from '$lib/stores/playback.svelte';
	import { getPlayerStore } from '$lib/stores/player.svelte';
	import type { Track } from '$lib/types';

	const ui = getUiStore();
	const pb = getPlaybackStore();
	const player = getPlayerStore();

	/** Convert a SetWaveformTrack to the Track shape the player store expects */
	function toTrack(swt: SetWaveformTrack): Track {
		return {
			id: swt.track_id,
			title: swt.title,
			artist: swt.artist,
			album: null,
			bpm: swt.bpm,
			key: swt.key,
			rating: null,
			genre: swt.genre,
			energy: swt.energy,
			duration_sec: swt.duration_sec,
			play_count: null,
			kiku_play_count: null,
			has_waveform: swt.waveform_overview !== null,
			has_features: false,
			resolved_energy: swt.energy,
			energy_source: swt.energy_source,
			energy_confidence: null,
			energy_conflict: swt.energy_conflict,
		};
	}

	function handleTrackPlay(trackId: number) {
		// Toggle off if same track
		if (player.isPlaying && player.currentTrack?.id === trackId) {
			player.pause();
			return;
		}
		const swt = waveformTracks.find((t) => t.track_id === trackId);
		if (swt) {
			player.play(toTrack(swt));
		}
	}

	let selectedSet = $state<DJSet | null>(null);
	let setDetail = $state<SetDetailType | null>(null);
	let waveformTracks = $state<SetWaveformTrack[]>([]);
	let transition = $state<TransitionData | null>(null);
	let activeTransitionIndex = $state(-1);
	let loading = $state(false);
	let loadingTransition = $state(false);
	let exporting = $state(false);
	let exportMsg = $state<string | null>(null);
	let exportFormat = $state<'m3u8' | 'rekordbox'>('m3u8');
	let showEnergyReview = $state(false);
	let error = $state<string | null>(null);
	let timelineContainerEl = $state<HTMLDivElement>(null!);

	/** Tracks that need energy review (not yet approved) */
	let tracksNeedingReview = $derived(
		waveformTracks.filter((t) => t.energy_source !== 'approved' && t.energy_source !== 'tag')
	);

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
			const ext = exportFormat === 'm3u8' ? '.m3u8' : '.xml';
			const blob = exportFormat === 'm3u8'
				? await exportM3U8(setId)
				: await exportRekordbox(setId);
			const url = URL.createObjectURL(blob);
			const a = document.createElement('a');
			a.href = url;
			a.download = `${setName.replace(/[^a-zA-Z0-9_-]/g, '_')}${ext}`;
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
		activeTransitionIndex = -1;
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
		// Toggle off if clicking the same transition
		if (activeTransitionIndex === index) {
			activeTransitionIndex = -1;
			transition = null;
			return;
		}
		activeTransitionIndex = index;
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
			{#if tracksNeedingReview.length > 0}
				<button class="review-energy-btn" onclick={() => { showEnergyReview = true; }}>
					Review energy ({tracksNeedingReview.length})
				</button>
			{/if}
			{#if waveformTracks.length >= 2}
				<button
					class="play-set-btn"
					onclick={() => pb.startExpress(selectedSet!.id, waveformTracks)}
					disabled={pb.isActive}
				>
					Express
				</button>
				<button
					class="play-set-btn builder"
					onclick={() => pb.startBuilder(selectedSet!.id, waveformTracks)}
					disabled={pb.isActive}
				>
					Live Builder
				</button>
			{/if}
			<select bind:value={exportFormat} class="export-select">
				<option value="m3u8">M3U8</option>
				<option value="rekordbox">XML</option>
			</select>
			<button class="export-btn" onclick={handleExport} disabled={exporting}>
				{exporting ? 'Exporting...' : 'Export'}
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
				</div>
				<div class="timeline-scroll">
					<SetTimeline
						tracks={waveformTracks}
						setId={selectedSet.id}
						energyProfile={setDetail?.energy_profile}
						{activeTransitionIndex}
						onTransitionClick={handleTransitionClick}
						onTracksChanged={handleTracksChanged}
						onTrackPlay={handleTrackPlay}
					/>
				</div>
			</div>

			{#if loadingTransition}
				<div class="status">Analyzing the transition...</div>
			{:else if transition}
				<TransitionDetail
					{transition}
					setId={selectedSet.id}
					hasPrev={activeTransitionIndex > 0}
					hasNext={activeTransitionIndex < waveformTracks.length - 2}
					onPrev={() => handleTransitionClick(activeTransitionIndex - 1)}
					onNext={() => handleTransitionClick(activeTransitionIndex + 1)}
				/>
			{/if}

		{:else}
			<div class="status">An empty set — your story starts here</div>
		{/if}
	{:else}
		<div class="empty-state">
			Choose a set to see your journey
		</div>
	{/if}

	{#if showEnergyReview}
		<SetEnergyReview
			trackIds={tracksNeedingReview.map((t) => t.track_id)}
			onclose={(reviewed) => {
				showEnergyReview = false;
				if (reviewed && selectedSet) loadSetData(selectedSet.id);
			}}
		/>
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

	.review-energy-btn {
		padding: 4px 12px;
		font-size: 12px;
		color: #000;
		background: var(--accent);
		border: 1px solid var(--accent);
		border-radius: 4px;
		font-weight: 600;
		transition: all 0.15s;
	}

	.review-energy-btn:hover {
		opacity: 0.85;
	}

	.play-set-btn {
		padding: 4px 12px;
		font-size: 12px;
		font-weight: 600;
		color: #000;
		background: var(--accent);
		border: 1px solid var(--accent);
		border-radius: 4px;
		transition: all 0.15s;
	}

	.play-set-btn:hover:not(:disabled) {
		opacity: 0.85;
	}

	.play-set-btn:disabled {
		opacity: 0.4;
		cursor: default;
	}

	.play-set-btn.builder {
		background: var(--bg-tertiary);
		color: var(--text-primary);
		border-color: var(--border);
	}

	.play-set-btn.builder:hover:not(:disabled) {
		background: var(--accent);
		color: #000;
		border-color: var(--accent);
	}

	.export-select {
		padding: 4px 8px;
		font-size: 12px;
		color: var(--text-primary);
		background: var(--bg-tertiary);
		border: 1px solid var(--border);
		border-radius: 4px 0 0 4px;
		border-right: none;
		cursor: pointer;
	}

	.export-btn {
		padding: 4px 12px;
		font-size: 12px;
		color: var(--text-primary);
		background: var(--bg-tertiary);
		border: 1px solid var(--border);
		border-radius: 0 4px 4px 0;
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
