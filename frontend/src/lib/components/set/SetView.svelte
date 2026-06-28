<script lang="ts">
	import type { DJSet, SetDetail as SetDetailType, SetWaveformTrack, TransitionDetail as TransitionData, SetAnalysis, SetComparison as SetComparisonType } from '$lib/types';
	import { getSet, getSetWaveforms, getTransition, exportRekordbox, exportM3U8, deleteSet, analyzeSet, getSetAnalysis, updateSet, compareSet, getSetComparison, linkSet, unlinkSet, listSets } from '$lib/api/sets';
	import { getUiStore } from '$lib/stores/ui.svelte';
	import SetPicker from './SetPicker.svelte';
	import SetGrid from './SetGrid.svelte';
	import SetTimeline from './SetTimeline.svelte';
	import TransitionDetail from './TransitionDetail.svelte';
	import EnergyFlowChart from './EnergyFlowChart.svelte';
	import SetEnergyReview from './SetEnergyReview.svelte';
	import SetComparison from './SetComparison.svelte';
	import FillReorderDialog from './FillReorderDialog.svelte';
	import AddFromArtistPanel from './AddFromArtistPanel.svelte';
	import Button from '$lib/components/primitives/Button.svelte';
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
			label: null,
			date_added: null,
			release_year: null,
			track_number: null,
			disc_number: null,
			comment: null,
			playlist_tags: [],
			genre_family: null,
		};
	}

	function handlePlaySet() {
		if (!selectedSet || waveformTracks.length === 0) return;
		// Play the whole set through the global queue (NowPlayingBar), like albums
		player.playSet(selectedSet.id, waveformTracks.map(toTrack), 0);
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
	let showAssist = $state(false);
	let showArtistPicks = $state(false);
	let confirmDelete = $state(false);
	let deleting = $state(false);
	let pickerRefresh = $state(0);
	let renaming = $state(false);
	let renameValue = $state('');
	let savingName = $state(false);
	let renameInputEl = $state<HTMLInputElement | null>(null);
	let error = $state<string | null>(null);
	let timelineContainerEl = $state<HTMLDivElement>(null!);
	let analysis = $state<SetAnalysis | null>(null);
	let analyzingSet = $state(false);
	let comparison = $state<SetComparisonType | null>(null);
	let comparing = $state(false);
	let showComparison = $state(false);
	let showLinkPicker = $state(false);
	let plannedSets = $state<DJSet[]>([]);
	let linkTargetId = $state<number | null>(null);
	let linking = $state(false);

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

	async function handleCompare() {
		if (!selectedSet || comparing) return;
		comparing = true;
		try {
			comparison = await compareSet(selectedSet.id);
			showComparison = true;
		} catch (e) {
			error = e instanceof Error ? e.message : String(e);
		} finally {
			comparing = false;
		}
	}

	async function handleUnlink() {
		if (!selectedSet) return;
		try {
			await unlinkSet(selectedSet.id);
			comparison = null;
			showComparison = false;
			if (setDetail) setDetail = { ...setDetail, planned_set_id: null };
		} catch (e) {
			error = e instanceof Error ? e.message : String(e);
		}
	}

	async function openLinkPicker() {
		if (!selectedSet) return;
		try {
			const all = await listSets();
			// Offer the DJ's planned (Kiku-built) sets, never this set itself
			plannedSets = all.filter((s) => s.source === 'kiku' && s.id !== selectedSet!.id);
		} catch {
			plannedSets = [];
		}
		linkTargetId = null;
		showLinkPicker = true;
	}

	async function confirmLink() {
		if (!selectedSet || linkTargetId === null || linking) return;
		linking = true;
		try {
			await linkSet(selectedSet.id, linkTargetId);
			if (setDetail) setDetail = { ...setDetail, planned_set_id: linkTargetId };
			showLinkPicker = false;
			// Show how the night deviated right away
			await handleCompare();
		} catch (e) {
			error = e instanceof Error ? e.message : String(e);
		} finally {
			linking = false;
		}
	}

	async function loadSetData(setId: number) {
		loading = true;
		error = null;
		transition = null;
		activeTransitionIndex = -1;
		analysis = null;
		comparison = null;
		showComparison = false;
		showLinkPicker = false;
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

			// Load the cached comparison when this set is linked to a plan
			if (detail.planned_set_id) {
				try {
					comparison = await getSetComparison(setId);
				} catch {
					comparison = null;
				}
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
		renaming = false;
		await loadSetData(set.id);
	}

	function startRename() {
		if (!selectedSet) return;
		renameValue = selectedSet.name ?? '';
		renaming = true;
		setTimeout(() => renameInputEl?.select(), 0);
	}

	async function saveRename() {
		if (!selectedSet || savingName) return;
		const name = renameValue.trim();
		// Nothing to save — just close
		if (!name || name === selectedSet.name) {
			renaming = false;
			return;
		}
		savingName = true;
		try {
			await updateSet(selectedSet.id, { name });
			selectedSet = { ...selectedSet, name };
			if (setDetail) setDetail = { ...setDetail, name };
			renaming = false;
			pickerRefresh++;
		} catch (e) {
			error = e instanceof Error ? e.message : "Couldn't rename the set";
		} finally {
			savingName = false;
		}
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
			{#if renaming}
				<input
					bind:this={renameInputEl}
					class="set-name-input"
					bind:value={renameValue}
					disabled={savingName}
					onkeydown={(e) => { if (e.key === 'Enter') saveRename(); if (e.key === 'Escape') renaming = false; }}
					onblur={saveRename}
				/>
			{:else}
				<button class="set-name" onclick={startRename} title="Rename this set">
					{selectedSet.name ?? 'Untitled set'}
					<span class="rename-hint">✎</span>
				</button>
			{/if}
			<span class="set-meta">{selectedSet.track_count} tracks, {selectedSet.duration_min}min</span>
			{#if tracksNeedingReview.length > 0}
				<Button variant="primary" size="sm" onclick={() => { showEnergyReview = true; }}>
					Review energy ({tracksNeedingReview.length})
				</Button>
			{/if}
			{#if waveformTracks.length >= 2 && analysis}
				<Button variant="secondary" size="sm" onclick={handleAnalyze} disabled={analyzingSet}>
					{analyzingSet ? 'Analyzing...' : 'Re-analyze'}
				</Button>
			{:else if waveformTracks.length >= 2 && analyzingSet}
				<span class="analyzing-status">Analyzing...</span>
			{/if}
			{#if waveformTracks.length >= 1}
				<Button variant="primary" size="sm" onclick={handlePlaySet} title="Play the whole set in order">
					▶ Play
				</Button>
			{/if}
			{#if setDetail?.planned_set_id}
				<Button variant="secondary" size="sm" onclick={handleCompare} disabled={comparing}>
					{comparing ? 'Comparing...' : 'Planned vs played'}
				</Button>
				<Button variant="ghost" size="sm" onclick={handleUnlink} title="Remove the link to the planned set">
					Unlink
				</Button>
			{:else if setDetail && setDetail.source !== 'kiku'}
				{#if showLinkPicker}
					{#if plannedSets.length === 0}
						<span class="link-empty">No planned sets to link yet — build one first.</span>
						<Button variant="ghost" size="sm" onclick={() => (showLinkPicker = false)}>Cancel</Button>
					{:else}
						<select class="link-select" bind:value={linkTargetId} aria-label="Choose the planned set">
							<option value={null}>Which set did you plan from?</option>
							{#each plannedSets as p (p.id)}
								<option value={p.id}>{p.name} ({p.track_count} tracks)</option>
							{/each}
						</select>
						<Button variant="secondary" size="sm" onclick={confirmLink} disabled={linkTargetId === null || linking}>
							{linking ? 'Linking...' : 'Link'}
						</Button>
						<Button variant="ghost" size="sm" onclick={() => (showLinkPicker = false)}>Cancel</Button>
					{/if}
				{:else}
					<Button variant="ghost" size="sm" onclick={openLinkPicker} title="Link this set to the plan you built it from">
						Link to a plan
					</Button>
				{/if}
			{/if}
			{#if waveformTracks.length >= 2}
				<Button variant="primary" size="sm" onclick={() => pb.startExpress(selectedSet!.id, waveformTracks)} disabled={pb.isActive}>
					Express
				</Button>
				<Button variant="secondary" size="sm" onclick={() => pb.startBuilder(selectedSet!.id, waveformTracks)} disabled={pb.isActive}>
					Live Builder
				</Button>
			{/if}
			{#if waveformTracks.length >= 3}
				<Button variant="secondary" size="sm" onclick={() => { showAssist = true; }}>
					Assist
				</Button>
			{/if}
			<Button variant="secondary" size="sm" onclick={() => { showArtistPicks = !showArtistPicks; }}>
				Add from an artist
			</Button>
			<select bind:value={exportFormat} class="export-select">
				<option value="m3u8">M3U8</option>
				<option value="rekordbox">XML</option>
			</select>
			<Button variant="secondary" size="sm" onclick={handleExport} disabled={exporting}>
				{exporting ? 'Exporting...' : 'Export'}
			</Button>
			{#if exportMsg}
				<span class="export-msg">{exportMsg}</span>
			{/if}
			<span class="delete-slot">
				<Button variant={confirmDelete ? 'danger' : 'ghost'} size="sm" onclick={handleDelete} disabled={deleting}>
					{deleting ? 'Deleting...' : confirmDelete ? 'Confirm delete?' : 'Delete'}
				</Button>
			</span>
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
							plannedCurve={showComparison && comparison ? comparison.arc.planned_curve : null}
							selectedIndex={selectedChartIndex}
							onTrackClick={handleChartTrackClick}
						/>
					</div>
				</div>

				{#if analysis}
					<div class="analysis-bar">
						<span class="analysis-score" style="color: {analysis.overall_score >= 0.7 ? 'var(--score-excellent)' : analysis.overall_score >= 0.5 ? 'var(--score-fair)' : 'var(--score-poor)'}">
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
					{#if showComparison && comparison}
						<SetComparison {comparison} onback={() => { showComparison = false; }} />
					{:else if loadingTransition}
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
		<SetGrid onselect={handleSetSelect} refreshSignal={pickerRefresh} onchange={() => pickerRefresh++} />
	{/if}

	{#if showAssist && selectedSet}
		<FillReorderDialog
			setId={selectedSet.id}
			setName={selectedSet.name ?? 'set'}
			trackCount={selectedSet.track_count}
			durationMin={selectedSet.duration_min ?? 0}
			energyProfile={setDetail?.energy_profile}
			onclose={() => { showAssist = false; }}
			onapplied={handleTracksChanged}
		/>
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

	{#if showArtistPicks && selectedSet}
		<AddFromArtistPanel
			setId={selectedSet.id}
			onInserted={handleTracksChanged}
			onclose={() => { showArtistPicks = false; }}
		/>
	{/if}
</div>

<style>
	/* Fixed-frame, internal-scroll surface — mirrors the sidebar `.library-browser`:
	   the set's top region (SetPicker toolbar, set-name/actions row, energy chart,
	   analysis bar) stays pinned while ONLY the timeline rows / set grid scroll
	   beneath them. `flex:1; min-height:0` fills the `.content-grid` frame; the frame
	   itself never scrolls (`overflow:hidden`) so nothing slides under the navbar.
	   NOTE: this only bounds correctly because `.tab-content` (Workspace) is a flex
	   column — that gives `.content-grid` a definite height for this `flex:1` to
	   resolve against. Without it the whole `.set-view` grew to content height and
	   `.tab-content` scrolled the chart + analysis bar away. */
	.set-view {
		flex: 1;
		min-height: 0;
		display: flex;
		flex-direction: column;
		overflow: hidden;
	}

	/* Secondary band — set name + actions. Matches the sidebar's filter row:
	   same --band-secondary-h (44px) + border-bottom, so this divider lands at the
	   SAME y as the Recent/Plays/Unplayed/Played row (spec 023 band rhythm). */
	.timeline-controls {
		display: flex;
		align-items: center;
		gap: var(--space-lg);
		padding: 0 var(--space-xl);
		height: var(--band-secondary-h);
		border-bottom: 1px solid var(--border);
		/* Second content-pane band: sticks directly beneath the SetPicker toolbar band
		   (offset by --band-toolbar-h) so the set name/actions row stays visible and
		   keeps aligning with the sidebar's filter row. Opaque so rows don't bleed. */
		position: sticky;
		top: var(--band-toolbar-h);
		z-index: 4;
		background: var(--bg-primary);
	}

	.set-name {
		font-weight: 600;
		font-size: 14px;
		display: inline-flex;
		align-items: center;
		gap: 6px;
		padding: 2px 6px;
		border: 1px solid transparent;
		border-radius: 4px;
		background: transparent;
		color: var(--text-primary);
		cursor: text;
	}

	.set-name:hover {
		border-color: var(--border);
	}

	.rename-hint {
		font-size: 11px;
		color: var(--text-dim);
		opacity: 0;
		transition: opacity 0.15s;
	}

	.set-name:hover .rename-hint {
		opacity: 1;
	}

	.set-name-input {
		font-weight: 600;
		font-size: 14px;
		padding: 2px 6px;
		border: 1px solid var(--accent);
		border-radius: 4px;
		background: var(--bg-secondary);
		color: var(--text-primary);
		min-width: 180px;
	}

	.set-meta {
		font-size: 12px;
		color: var(--text-dim);
		margin-right: auto;
	}

	/* Native select kept (not a button); aligned to the toolbar Button tier. */
	.export-select {
		padding: 4px 8px;
		font-size: 12px;
		color: var(--text-primary);
		background: var(--bg-tertiary);
		border: 1px solid var(--border);
		border-radius: var(--radius-sm);
		cursor: pointer;
	}

	.export-msg {
		font-size: 11px;
		color: var(--accent);
	}

	.delete-slot {
		display: inline-flex;
		margin-left: 4px;
	}

	.timeline-container {
		flex: 1;
		min-height: 0;
		display: flex;
		flex-direction: column;
		border-bottom: 1px solid var(--border);
	}

	/* Pinned top region — energy chart. A `flex-shrink:0` sibling ABOVE the
	   `.timeline-scroll` scroller (NOT inside it), so it holds fixed while only the
	   rows scroll beneath. Solid background so scrolled rows can't bleed through. */
	.top-panel {
		display: flex;
		flex-shrink: 0;
		border-bottom: 1px solid var(--border);
		min-height: 0;
		background: var(--bg-primary);
	}

	.energy-chart-wrapper {
		flex: 3;
		min-width: 0;
	}

	/* The ONLY scroller in the loaded-set frame. `flex:1; min-height:0` so it takes
	   the leftover height under the pinned energy chart + analysis bar and scrolls
	   its rows (timeline / TransitionDetail / SetComparison) internally. */
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


	.analyzing-status {
		font-size: 12px;
		color: var(--text-dim);
	}

	.link-select {
		padding: 4px 8px;
		font-size: 12px;
		color: var(--text-primary);
		background: var(--bg-tertiary);
		border: 1px solid var(--border);
		border-radius: 4px;
		max-width: 220px;
	}

	.link-empty {
		font-size: 12px;
		color: var(--text-dim);
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
