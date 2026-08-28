<script lang="ts">
	import type { DJSet, SetDetail as SetDetailType, SetWaveformTrack, TransitionDetail as TransitionData, SetAnalysis, SetComparison as SetComparisonType } from '$lib/types';
	import { getSet, getSetWaveforms, getTransition, exportRekordbox, exportM3U8, deleteSet, analyzeSet, getSetAnalysis, updateSet, compareSet, getSetComparison, linkSet, unlinkSet, listSets } from '$lib/api/sets';
	import { getUiStore } from '$lib/stores/ui.svelte';
	import SetPicker from './SetPicker.svelte';
	import SetGrid from './SetGrid.svelte';
	import SetTimeline from './SetTimeline.svelte';
	import SetRail from './SetRail.svelte';
	import SetListLedger from './SetListLedger.svelte';
	import SetListSpine from './SetListSpine.svelte';
	import SetListInspector from './SetListInspector.svelte';
	import { buildRows } from './rowModel';
	import TransitionDetail from './TransitionDetail.svelte';
	import EnergyFlowChart from './EnergyFlowChart.svelte';
	import SetEnergyReview from './SetEnergyReview.svelte';
	import SetComparison from './SetComparison.svelte';
	import FillReorderDialog from './FillReorderDialog.svelte';
	import AddFromArtistPanel from './AddFromArtistPanel.svelte';
	import AddSlotPicksPanel from './AddSlotPicksPanel.svelte';
	import Button from '$lib/components/primitives/Button.svelte';
	import Menu from '$lib/components/primitives/Menu.svelte';
	import MenuItem from '$lib/components/primitives/MenuItem.svelte';
	import MenuSeparator from '$lib/components/primitives/MenuSeparator.svelte';
	import SegmentedControl, { type SegmentOption } from '$lib/components/primitives/SegmentedControl.svelte';
	import { goto } from '$app/navigation';
	import { createResource } from '$lib/data/resource.svelte';
	import { untrack } from 'svelte';
	import { page } from '$app/state';
	import { setHref, setQueryParam } from '$lib/nav';

	/** `ledger` / `spine` / `inspector` are the three redesign candidates — each
	 *  pairs a one-row-per-track list with the shared right rail. They sit beside
	 *  the shipped modes rather than replacing them, so both can be compared. */
	export type SetViewMode = 'list' | 'compact' | 'grid' | 'ledger' | 'spine' | 'inspector';

	/** The candidates share a layout: list left, graph and KPIs right. */
	export const SPLIT_MODES: SetViewMode[] = ['ledger', 'spine', 'inspector'];
	import { getSetTracksStore } from '$lib/stores/setTracks.svelte';
	import { getPlaybackStore } from '$lib/stores/playback.svelte';
	import { getPlayerStore } from '$lib/stores/player.svelte';
	import type { Track } from '$lib/types';

	const ui = getUiStore();

	/** Which set, which track inside it, and which layout — all read from the URL
	 *  by the route and handed down, so this view has no hidden selection state. */
	let {
		setId = null,
		focusedTrackId = null,
		viewMode = 'list',
	}: {
		setId?: number | null;
		focusedTrackId?: number | null;
		viewMode?: SetViewMode;
	} = $props();

	/** Put the focused track in the URL. Replaces rather than pushes: Back should
	 *  leave the set, not walk every row you clicked inside it. */
	function focusTrack(trackId: number | null) {
		setQueryParam(page.url, 't', trackId);
	}

	/** Arc folded away? A layout preference, not selection state — it sticks
	 *  across sets and reloads rather than riding in the URL. */
	const ARC_KEY = 'kiku:set:arc-collapsed';
	let arcCollapsed = $state(
		typeof localStorage !== 'undefined' && localStorage.getItem(ARC_KEY) === '1',
	);

	function setArcCollapsed(v: boolean) {
		arcCollapsed = v;
		if (typeof localStorage !== 'undefined') localStorage.setItem(ARC_KEY, v ? '1' : '0');
	}

	const viewOptions: SegmentOption<SetViewMode>[] = [
		{ value: 'list', label: 'List' },
		{ value: 'compact', label: 'Compact' },
		{ value: 'grid', label: 'Grid' },
		{ value: 'ledger', label: 'Ledger' },
		{ value: 'spine', label: 'Spine' },
		{ value: 'inspector', label: 'Inspect' },
	];

	let isSplit = $derived(SPLIT_MODES.includes(viewMode));

	/** SetTimeline only knows the shipped modes, and the split branch never reaches
	 *  it — narrow here so the candidate names stay out of its prop type. */
	let timelineMode = $derived<'list' | 'compact' | 'grid'>(
		viewMode === 'compact' || viewMode === 'grid' ? viewMode : 'list',
	);

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
			set_roles: [],
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
	/** The running order lives in the store; edits land there and stay there.
	 *  This view reads it rather than keeping a second copy to reconcile. */
	const setTracks = getSetTracksStore();
	const waveformTracks = $derived(setTracks.tracks);
	let transition = $state<TransitionData | null>(null);
	let activeTransitionIndex = $state(-1);
	const res = createResource(
		() => setId,
		async (id, signal) => {
			const [detail, waveforms] = await Promise.all([getSet(id, signal), getSetWaveforms(id, signal)]);
			return { detail, waveforms };
		},
		{ key: (id) => `set:${id}:detail` },
	);
	const loading = $derived(res.loading);
	/** Writes in this view — rename, link, delete, analyze — fail differently from
	 *  the load, so they get their own channel and the view shows either. */
	let actionError = $state<string | null>(null);
	let loadingTransition = $state(false);
	let exporting = $state(false);
	let exportMsg = $state<string | null>(null);
	let exportFormat = $state<'m3u8' | 'rekordbox'>('m3u8');
	let showEnergyReview = $state(false);
	let showAssist = $state(false);
	let showArtistPicks = $state(false);
	let showSlotPicks = $state(false);
	let confirmDelete = $state(false);
	let deleting = $state(false);
	let pickerRefresh = $state(0);
	let renaming = $state(false);
	let renameValue = $state('');
	let savingName = $state(false);
	let renameInputEl = $state<HTMLInputElement | null>(null);
	const error = $derived(res.error ?? actionError);
	let timelineContainerEl = $state<HTMLDivElement>(null!);
	let analysis = $state<SetAnalysis | null>(null);

	/** Rows for the candidate layouts — one derivation, three presentations. */
	let rows = $derived(buildRows(waveformTracks, analysis));

	/** Start indices of runs of 3+ consecutive tracks in one key. Same rule as
	 *  SetTimeline's banner, kept here so the candidates can show it too. */
	let runStarts = $derived.by(() => {
		const starts = new Set<number>();
		let start = 0;
		for (let i = 1; i <= rows.length; i++) {
			const a = rows[i - 1]?.camelot;
			const b = i < rows.length ? rows[i].camelot : null;
			if (!(a && b && a === b)) {
				if (i - start >= 3) starts.add(start);
				start = i;
			}
		}
		return starts;
	});

	/** Which transition the Inspector rail is explaining. */
	let inspectIndex = $state(-1);

	/** Ledger and Spine open the full Transition Detail; Inspector fills the rail. */
	function handleCandidateTransition(index: number) {
		if (viewMode === 'inspector') inspectIndex = index;
		else handleTransitionClick(index);
	}
	let analyzingSet = $state(false);
	let comparison = $state<SetComparisonType | null>(null);
	let comparing = $state(false);
	let showComparison = $state(false);
	let showLinkPicker = $state(false);
	let plannedSets = $state<DJSet[]>([]);
	let linkTargetId = $state<number | null>(null);
	let linking = $state(false);
	let exportMenuOpen = $state(false);
	let moreMenuOpen = $state(false);

	const EXPORT_FORMATS = [
		{ value: 'm3u8', label: 'M3U8' },
		{ value: 'rekordbox', label: 'Rekordbox XML' },
	] as const;
	let exportFormatLabel = $derived(
		EXPORT_FORMATS.find((f) => f.value === exportFormat)?.label ?? 'M3U8'
	);

	/** Tracks that need energy review (not yet approved) */
	let tracksNeedingReview = $derived(
		waveformTracks.filter((t) => t.energy_source !== 'approved' && t.energy_source !== 'tag')
	);

	/** Derive chart selectedIndex from the focused track id in the URL */
	let selectedChartIndex = $derived.by(() => {
		if (focusedTrackId === null) return undefined;
		const idx = waveformTracks.findIndex((t) => t.track_id === focusedTrackId);
		return idx >= 0 ? idx : undefined;
	});

	/** Chart click handler: convert index to track ID, update store */
	function handleChartTrackClick(index: number) {
		if (index >= 0 && index < waveformTracks.length) {
			focusTrack(waveformTracks[index].track_id);
		}
	}

	/** Scroll timeline to selected track when selection changes */
	$effect(() => {
		const trackId = focusedTrackId;
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
			setTracks.load(null, []);
			transition = null;
			confirmDelete = false;
			pickerRefresh++;
		} catch (e) {
			actionError = e instanceof Error ? e.message : 'Delete failed';
		} finally {
			deleting = false;
		}
	}

	/** A failed write leaves the store unsure of the truth; this is how it asks. */
	$effect(() => {
		setTracks.setResync(() => res.refresh());
		return () => setTracks.setResync(null);
	});

	/** The arc is downstream of the running order, so it re-reads itself after an
	 *  edit — quietly, in the background. The list never waits on it and never
	 *  re-mounts for it. */
	let orderKey = $derived(waveformTracks.map((t) => t.track_id).join(','));
	let lastAnalyzedKey: string | null = null;

	$effect(() => {
		const key = orderKey;
		const sid = selectedSet?.id ?? null;
		if (sid === null || waveformTracks.length < 2) return;
		if (untrack(() => lastAnalyzedKey) === key) return;
		const t = setTimeout(() => {
			lastAnalyzedKey = key;
			void handleAnalyze();
		}, 600);
		return () => clearTimeout(t);
	});

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
			actionError = e instanceof Error ? e.message : String(e);
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
			actionError = e instanceof Error ? e.message : String(e);
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
			actionError = e instanceof Error ? e.message : String(e);
		} finally {
			linking = false;
		}
	}

	// The resource owns the request. This seeds the view from it and then chases the
	// two dependent reads — cached analysis, and a comparison when the set is linked.
	$effect(() => {
		const data = res.data;
		transition = null;
		activeTransitionIndex = -1;
		analysis = null;
		comparison = null;
		showComparison = false;
		showLinkPicker = false;
		actionError = null;
		if (!data) {
			// A refresh of the SAME set (after a reorder, a removal, an add) blanks
			// `res.data` for a moment. Tearing the timeline down for that moment
			// unmounts it mid-write: handlers that awaited come back to a null
			// `setId` and throw, so the change silently never happens. Hold the
			// view while the set we're already showing reloads; only a genuine
			// change of subject clears it.
			const showing = untrack(() => selectedSet);
			if (res.loading && showing && showing.id === setId) return;
			selectedSet = null;
			setDetail = null;
			setTracks.load(null, []);
			return;
		}

		const { detail, waveforms } = data;
		setDetail = detail;
		setTracks.load(detail.id, waveforms);
		// This read IS the analysis's subject, so nothing is stale yet.
		lastAnalyzedKey = waveforms.map((t) => t.track_id).join(',');
		selectedSet = {
			id: detail.id,
			name: detail.name,
			created_at: detail.created_at,
			duration_min: detail.duration_min,
			track_count: detail.tracks.length,
			source: detail.source,
		};

		void (async () => {
			// A build hands its analysis over rather than making us recompute it.
			if (ui.pendingAnalysis && ui.pendingAnalysis.set_id === detail.id) {
				analysis = ui.pendingAnalysis;
				ui.pendingAnalysis = null;
			} else {
				try {
					analysis = await getSetAnalysis(detail.id);
				} catch {
					analysis = null;
				}
			}

			if (!analysis && waveforms.length >= 2) handleAnalyze();

			if (detail.planned_set_id) {
				try {
					comparison = await getSetComparison(detail.id);
				} catch {
					comparison = null;
				}
			}
		})();
	});

	function handleSetSelect(set: DJSet) {
		// Selecting a set is a navigation: it changes what the URL identifies.
		goto(setHref(set.id));
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
			actionError = e instanceof Error ? e.message : "Couldn't rename the set";
		} finally {
			savingName = false;
		}
	}

	async function handleTracksChanged() {
		if (!selectedSet) return;
		res.refresh();
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
			actionError = e instanceof Error ? e.message : String(e);
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

			<!-- Toolbar: intent groups separated by dividers. One accent (Play); the
			     rest secondary; Delete (danger) isolated far right. Uniform size="sm". -->
			<div class="toolbar" role="toolbar" aria-label="Set actions">
				<!-- 1 · Playback — the single accent button -->
				{#if waveformTracks.length >= 1}
					<div class="tool-group">
						<Button variant="primary" size="sm" onclick={handlePlaySet} title="Play the whole set in order">
							▶ Play
						</Button>
					</div>
				{/if}

				<!-- 2 · Build / arrange -->
				{#if waveformTracks.length >= 2}
					<div class="tool-divider" role="separator" aria-orientation="vertical"></div>
					<div class="tool-group">
						<Button variant="secondary" size="sm" onclick={() => pb.startBuilder(selectedSet!.id, waveformTracks)} disabled={pb.isActive}>
							Live Builder
						</Button>
						<Button variant="secondary" size="sm" onclick={() => pb.startExpress(selectedSet!.id, waveformTracks)} disabled={pb.isActive}>
							Express
						</Button>
					</div>
				{/if}

				<!-- View: list vs grid — scan the whole set's key/energy field at a glance -->
				{#if waveformTracks.length >= 1}
					<div class="tool-divider" role="separator" aria-orientation="vertical"></div>
					<div class="tool-group">
						<SegmentedControl
							options={viewOptions}
							value={viewMode}
							onchange={(v) => setQueryParam(page.url, 'view', v)}
							ariaLabel="Set view"
							dense
						/>
					</div>
				{/if}

				<!-- 3 · Analyze — keep the energy-review count CTA prominent -->
				{#if tracksNeedingReview.length > 0 || (waveformTracks.length >= 2 && (analysis || analyzingSet))}
					<div class="tool-divider" role="separator" aria-orientation="vertical"></div>
					<div class="tool-group">
						{#if tracksNeedingReview.length > 0}
							<Button variant="secondary" size="sm" onclick={() => { showEnergyReview = true; }}>
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
					</div>
				{/if}

				<!-- Planned-vs-played comparison — contextual, only when linked -->
				{#if setDetail?.planned_set_id}
					<div class="tool-divider" role="separator" aria-orientation="vertical"></div>
					<div class="tool-group">
						<Button variant="secondary" size="sm" onclick={handleCompare} disabled={comparing}>
							{comparing ? 'Comparing...' : 'Planned vs played'}
						</Button>
					</div>
				{/if}

				<!-- 4 · Export — format picker + Export as one unit -->
				<div class="tool-divider" role="separator" aria-orientation="vertical"></div>
				<div class="tool-group export-unit">
					<Menu bind:open={exportMenuOpen} label="Export format" minWidth={160}>
						{#snippet trigger({ open, props })}
							<span {...props}>
								<Button variant="secondary" size="sm" onclick={open} title="Choose the export format">
									{exportFormatLabel} ▾
								</Button>
							</span>
						{/snippet}
						{#each EXPORT_FORMATS as fmt (fmt.value)}
							<MenuItem selected={exportFormat === fmt.value} onselect={() => { exportFormat = fmt.value; }}>
								{fmt.label}
							</MenuItem>
						{/each}
					</Menu>
					<Button variant="secondary" size="sm" onclick={handleExport} disabled={exporting}>
						{exporting ? 'Exporting...' : 'Export'}
					</Button>
				</div>
				{#if exportMsg}
					<span class="export-msg">{exportMsg}</span>
				{/if}

				<!-- More — least-common actions tucked into an overflow menu -->
				<div class="tool-divider" role="separator" aria-orientation="vertical"></div>
				<div class="tool-group">
					<Menu bind:open={moreMenuOpen} label="More set actions" minWidth={200}>
						{#snippet trigger({ open, props })}
							<span {...props}>
								<Button variant="ghost" size="sm" iconOnly ariaLabel="More set actions" onclick={open}>
									{#snippet icon()}⋮{/snippet}
								</Button>
							</span>
						{/snippet}
						{#if waveformTracks.length >= 3}
							<MenuItem onselect={() => { showAssist = true; }}>Assist</MenuItem>
						{/if}
						<MenuItem onselect={() => { showArtistPicks = !showArtistPicks; }}>Add from an artist</MenuItem>
						<MenuItem onselect={() => { showSlotPicks = !showSlotPicks; }}>Directional slot pick</MenuItem>
						{#if setDetail?.planned_set_id}
							<MenuSeparator />
							<MenuItem onselect={handleUnlink}>Unlink from plan</MenuItem>
						{:else if setDetail && setDetail.source !== 'kiku'}
							<MenuSeparator />
							<MenuItem onselect={openLinkPicker}>Link to a plan</MenuItem>
						{/if}
					</Menu>
				</div>

				<!-- 5 · Destructive — isolated on the far right -->
				<div class="tool-divider tool-divider--strong" role="separator" aria-orientation="vertical"></div>
				<div class="tool-group">
					<Button variant={confirmDelete ? 'danger' : 'ghost'} size="sm" onclick={handleDelete} disabled={deleting}>
						{deleting ? 'Deleting...' : confirmDelete ? 'Confirm delete?' : 'Delete'}
					</Button>
				</div>
			</div>
		</div>

		{#if showLinkPicker}
			<!-- Link picker — opened from the More menu; appears as its own band so the
			     select + actions get room without crowding the toolbar. -->
			<div class="link-picker-band">
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
			</div>
		{/if}

		{#if loading}
			<div class="status">Building your timeline...</div>
		{:else if error}
			<div class="status error" role="alert">Couldn't build the timeline. Something tripped while reading the set — try again, or pick another set.</div>
		{:else if waveformTracks.length > 0 && isSplit}
			<!-- Candidate layouts: list left, reference material right. -->
			<div class="split" bind:this={timelineContainerEl}>
				<div class="split-list">
					{#if showComparison && comparison}
						<SetComparison {comparison} onback={() => { showComparison = false; }} />
					{:else if loadingTransition}
						<div class="status">Reading the transition...</div>
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
					{:else if viewMode === 'ledger'}
						<SetListLedger {rows} {runStarts} {focusedTrackId} onselect={focusTrack} ontransition={handleCandidateTransition} />
					{:else if viewMode === 'spine'}
						<SetListSpine {rows} {runStarts} {focusedTrackId} onselect={focusTrack} ontransition={handleCandidateTransition} />
					{:else}
						<SetListInspector {rows} {runStarts} {focusedTrackId} onselect={focusTrack} ontransition={handleCandidateTransition} />
					{/if}
				</div>

				<SetRail
					tracks={waveformTracks}
					{rows}
					{analysis}
					energyProfile={setDetail?.energy_profile}
					plannedCurve={showComparison && comparison ? comparison.arc.planned_curve : null}
					selectedIndex={selectedChartIndex}
					onTrackClick={handleChartTrackClick}
					{inspectIndex}
					showInspector={viewMode === 'inspector'}
				/>
			</div>

		{:else if waveformTracks.length > 0}
			<div class="timeline-container" bind:this={timelineContainerEl}>
				<div class="top-panel">
					<div class="energy-chart-wrapper">
						<EnergyFlowChart
							dense={viewMode === 'compact'}
							collapsed={arcCollapsed}
							oncollapse={setArcCollapsed}
							tracks={waveformTracks}
							energyProfile={setDetail?.energy_profile}
							plannedCurve={showComparison && comparison ? comparison.arc.planned_curve : null}
							selectedIndex={selectedChartIndex}
							onTrackClick={handleChartTrackClick}
						/>
					</div>
				</div>

				{#if analysis}
					<div class="analysis-bar" class:dense={viewMode === 'compact'}>
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
						<div class="status">Reading the transition...</div>
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
							{focusedTrackId}
							viewMode={timelineMode}
							onFocusTrack={focusTrack}
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
				if (reviewed && selectedSet) res.refresh();
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

	{#if showSlotPicks && selectedSet}
		<AddSlotPicksPanel
			setId={selectedSet.id}
			trackCount={selectedSet.track_count}
			onApplied={handleTracksChanged}
			onclose={() => { showSlotPicks = false; }}
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

	/* Name and count hold their ground; the toolbar is what scrolls. */
	.set-name,
	.set-meta {
		flex-shrink: 0;
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

	/* Action toolbar — one horizontal row of intent groups. Even, token-based gaps;
	   subtle vertical dividers carry the grouping alongside order + spacing (color is
	   never the only signal). Wraps gracefully on narrow widths. */
	/* The band is a fixed 44px so its divider lands on the shared baseline, so the
	   toolbar must NOT wrap — a second line overflows the band and lands on top of
	   the rows below. It scrolls instead, the same move the navbar tabs make. */
	.toolbar {
		display: flex;
		align-items: center;
		gap: var(--space-md);
		flex-wrap: nowrap;
		flex: 1;
		min-width: 0;
		overflow-x: auto;
		overflow-y: hidden;
		scrollbar-width: none;
	}

	.toolbar::-webkit-scrollbar {
		display: none;
	}

	.toolbar > :global(*) {
		flex-shrink: 0;
	}

	.tool-group {
		display: inline-flex;
		align-items: center;
		gap: var(--space-sm);
	}

	/* Attached export pair (format picker + Export) reads as one unit. */
	.export-unit {
		gap: var(--space-xs);
	}

	.tool-divider {
		width: 1px;
		align-self: stretch;
		min-height: 20px;
		background: var(--border);
	}

	/* Stronger rule isolates the destructive zone on the far right. */
	.tool-divider--strong {
		background: var(--border-default);
	}

	.export-msg {
		font-size: 11px;
		color: var(--accent);
	}

	/* Link-to-a-plan picker — its own band beneath the toolbar (opened from More). */
	.link-picker-band {
		display: flex;
		align-items: center;
		gap: var(--space-md);
		padding: var(--space-md) var(--space-xl);
		border-bottom: 1px solid var(--border);
		background: var(--bg-secondary);
	}

	.timeline-container {
		flex: 1;
		min-height: 0;
		display: flex;
		flex-direction: column;
		border-bottom: 1px solid var(--border);
	}

	/* Candidate layouts. The rail is a fixed column so the list keeps the room it
	   gains from losing the full-width chart; below 1200px it folds underneath so
	   the list never starves. */
	.split {
		flex: 1;
		min-height: 0;
		display: grid;
		grid-template-columns: minmax(0, 1fr) 320px;
		border-bottom: 1px solid var(--border);
	}

	.split-list {
		min-width: 0;
		min-height: 0;
		overflow-y: auto;
	}

	@media (max-width: 1200px) {
		.split {
			grid-template-columns: minmax(0, 1fr);
			grid-template-rows: minmax(0, 1fr) auto;
		}
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

	/* Compact: the read on the set stays, on one scrollable line. */
	.analysis-bar.dense {
		flex-wrap: nowrap;
		overflow-x: auto;
		padding: 3px 16px;
		scrollbar-width: none;
	}

	.analysis-bar.dense > :global(*) {
		white-space: nowrap;
		flex-shrink: 0;
	}

	.analysis-bar.dense .analysis-score {
		font-size: 14px;
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
