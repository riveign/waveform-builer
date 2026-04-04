<script lang="ts">
	import type { DJSet, SetDetail as SetDetailType, SetWaveformTrack, TransitionDetail as TransitionData, SetAnalysis } from '$lib/types';
	import { getSet, getSetWaveforms, getTransition, exportRekordbox, exportM3U8, deleteSet, analyzeSet, getSetAnalysis } from '$lib/api/sets';
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
			energy_confidence: swt.energy_confidence,
			energy_value: swt.energy_value,
			energy_label: swt.energy_label,
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
	let confirmDelete = $state(false);
	let deleting = $state(false);
	let pickerRefresh = $state(0);
	let error = $state<string | null>(null);
	let timelineContainerEl = $state<HTMLDivElement>(null!);
	let analysis = $state<SetAnalysis | null>(null);
	let analyzingSet = $state(false);

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

	async function handleDelete() {
		if (!selectedSet) return;
		if (!confirmDelete) {
			confirmDelete = true;
			setTimeout(() => { confirmDelete = false; }, 3000);
			return;
		}
		deleting = true;
		try {
			await deleteSet(selectedSet.id);
			selectedSet = null;
			setDetail = null;
			waveformTracks = [];
			transition = null;
			confirmDelete = false;
			pickerRefresh++;
		} catch (e) {
			error = e instanceof Error ? e.message : 'Delete failed';
		} finally {
			deleting = false;
		}
	}

	async function handleAnalyze() {
		if (!selectedSet) return;
		analyzingSet = true;
		try {
			analysis = await analyzeSet(selectedSet.id);
		} catch (e) {
			console.error('Analysis failed:', e);
		} finally {
			analyzingSet = false;
		}
	}

	async function loadSetData(setId: number) {
		loading = true;
		error = null;
		transition = null;
		activeTransitionIndex = -1;
		analysis = null;
		try {
			const [detail, waveforms] = await Promise.all([
				getSet(setId),
				getSetWaveforms(setId),
			]);
			setDetail = detail;
			waveformTracks = waveforms;

			// Use pre-computed analysis from build if available
			if (ui.pendingAnalysis && ui.pendingAnalysis.set_id === setId) {
				analysis = ui.pendingAnalysis;
				ui.pendingAnalysis = null;
			} else {
				// Try loading cached analysis
				try {
					analysis = await getSetAnalysis(setId);
				} catch {
					analysis = null;
				}
			}

			// Auto-analyze if no analysis exists and set has enough tracks
			if (!analysis && waveforms.length >= 2) {
				handleAnalyze();
			}
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
	<SetPicker onselect={handleSetSelect} refreshSignal={pickerRefresh} />

	{#if selectedSet}
		<div class="timeline-controls">
			<span class="set-name">{selectedSet.name}</span>
			<span class="set-meta">{selectedSet.track_count} tracks, {selectedSet.duration_min}min</span>
			{#if tracksNeedingReview.length > 0}
				<button class="review-energy-btn" onclick={() => { showEnergyReview = true; }}>
					Review energy ({tracksNeedingReview.length})
				</button>
			{/if}
			{#if waveformTracks.length >= 2 && analysis}
				<button
					class="analyze-btn"
					onclick={handleAnalyze}
					disabled={analyzingSet}
				>
					{analyzingSet ? 'Analyzing...' : 'Re-analyze'}
				</button>
			{:else if waveformTracks.length >= 2 && analyzingSet}
				<span class="analyzing-status">Analyzing...</span>
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
			<button
				class="delete-btn"
				class:confirm={confirmDelete}
				onclick={handleDelete}
				disabled={deleting}
			>
				{deleting ? 'Deleting...' : confirmDelete ? 'Confirm delete?' : 'Delete'}
			</button>
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

				{#if analysis}
					<div class="analysis-bar">
						<span class="analysis-score" style="color: {analysis.overall_score >= 0.7 ? 'var(--color-success, #66BB6A)' : analysis.overall_score >= 0.5 ? 'var(--color-warning, #FFA726)' : 'var(--color-error, #EF5350)'}">
							{analysis.overall_score.toFixed(3)}
						</span>
						<span class="analysis-arc">
							{analysis.arc.energy_shape}
						</span>
						<span class="analysis-arc">
							{analysis.arc.key_style}
						</span>
						<span class="analysis-arc">
							{analysis.arc.bpm_style}
							{#if analysis.arc.bpm_range[0] > 0}
								({analysis.arc.bpm_range[0].toFixed(0)}–{analysis.arc.bpm_range[1].toFixed(0)})
							{/if}
						</span>
						{#each analysis.set_patterns as pattern}
							<span class="analysis-pattern">{pattern}</span>
						{/each}
					</div>
				{/if}

				<div class="timeline-scroll">
					{#if loadingTransition}
						<div class="status">Analyzing the transition...</div>
					{:else if transition}
						<TransitionDetail
							{transition}
							setId={selectedSet.id}
							analysisTransition={analysis?.transitions.find(t => t.position === activeTransitionIndex) ?? null}
							hasPrev={activeTransitionIndex > 0}
							hasNext={activeTransitionIndex < waveformTracks.length - 2}
							onPrev={() => handleTransitionClick(activeTransitionIndex - 1)}
							onNext={() => handleTransitionClick(activeTransitionIndex + 1)}
							onBack={() => { activeTransitionIndex = -1; transition = null; }}
						/>
					{:else}
						<SetTimeline
							tracks={waveformTracks}
							setId={selectedSet.id}
							energyProfile={setDetail?.energy_profile}
							{activeTransitionIndex}
							{analysis}
							onTransitionClick={handleTransitionClick}
							onTracksChanged={handleTracksChanged}
							onTrackPlay={handleTrackPlay}
						/>
					{/if}
				</div>
			</div>

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

	.delete-btn {
		padding: 4px 12px;
		font-size: 12px;
		color: var(--text-dim);
		background: var(--bg-tertiary);
		border: 1px solid var(--border);
		border-radius: 4px;
		transition: all 0.15s;
		margin-left: 4px;
	}

	.delete-btn:hover:not(:disabled) {
		color: #e74c3c;
		border-color: #e74c3c;
	}

	.delete-btn.confirm {
		color: #fff;
		background: #e74c3c;
		border-color: #e74c3c;
	}

	.delete-btn:disabled {
		opacity: 0.5;
		cursor: default;
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

	.analyzing-status {
		font-size: 12px;
		color: var(--text-dim);
	}

	.analyze-btn {
		padding: 4px 12px;
		font-size: 12px;
		font-weight: 600;
		color: var(--text-primary);
		background: var(--bg-tertiary);
		border: 1px solid var(--border);
		border-radius: 4px;
		transition: all 0.15s;
	}

	.analyze-btn:hover:not(:disabled) {
		background: var(--accent);
		color: #000;
		border-color: var(--accent);
	}

	.analyze-btn:disabled {
		opacity: 0.5;
		cursor: default;
	}

	.analysis-bar {
		display: flex;
		align-items: center;
		gap: 12px;
		padding: 6px 16px;
		background: var(--bg-secondary);
		border-bottom: 1px solid var(--border);
		flex-shrink: 0;
		flex-wrap: wrap;
	}

	.analysis-score {
		font-size: 16px;
		font-weight: 700;
		font-variant-numeric: tabular-nums;
	}

	.analysis-arc {
		font-size: 11px;
		color: var(--text-secondary);
		padding: 2px 8px;
		background: var(--bg-tertiary);
		border-radius: 10px;
	}

	.analysis-pattern {
		font-size: 11px;
		color: var(--text-dim);
		font-style: italic;
	}
</style>
