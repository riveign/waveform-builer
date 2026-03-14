<script lang="ts">
	import type { DJSet, SetWaveformTrack, TransitionDetail as TransitionData } from '$lib/types';
	import { getSetWaveforms, getTransition, exportRekordbox } from '$lib/api/sets';
	import SetPicker from './SetPicker.svelte';
	import SetTimeline from './SetTimeline.svelte';
	import TransitionDetail from './TransitionDetail.svelte';

	let selectedSet = $state<DJSet | null>(null);
	let waveformTracks = $state<SetWaveformTrack[]>([]);
	let transition = $state<TransitionData | null>(null);
	let timelineMode = $state<'linear' | 'staircase'>('linear');
	let loading = $state(false);
	let loadingTransition = $state(false);
	let exporting = $state(false);
	let exportMsg = $state<string | null>(null);
	let error = $state<string | null>(null);

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

	async function handleSetSelect(set: DJSet) {
		selectedSet = set;
		transition = null;
		loading = true;
		error = null;
		try {
			waveformTracks = await getSetWaveforms(set.id);
		} catch (e) {
			error = e instanceof Error ? e.message : String(e);
			waveformTracks = [];
		} finally {
			loading = false;
		}
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
			<div class="mode-toggle">
				<button
					class="mode-btn"
					class:active={timelineMode === 'linear'}
					onclick={() => timelineMode = 'linear'}
				>Linear</button>
				<button
					class="mode-btn"
					class:active={timelineMode === 'staircase'}
					onclick={() => timelineMode = 'staircase'}
				>Staircase</button>
			</div>
			<button class="export-btn" onclick={handleExport} disabled={exporting}>
				{exporting ? 'Exporting...' : 'Export XML'}
			</button>
			{#if exportMsg}
				<span class="export-msg">{exportMsg}</span>
			{/if}
		</div>

		{#if loading}
			<div class="status">Loading timeline...</div>
		{:else if error}
			<div class="status error">{error}</div>
		{:else if waveformTracks.length > 0}
			<div class="timeline-container" style="height: {timelineMode === 'staircase' ? Math.max(300, waveformTracks.length * 80 + 20) : 280}px">
				<SetTimeline
					tracks={waveformTracks}
					mode={timelineMode}
					onTransitionClick={handleTransitionClick}
				/>
			</div>

			<div class="hint">Click a transition boundary to see score breakdown</div>

			{#if loadingTransition}
				<div class="status">Loading transition...</div>
			{:else if transition}
				<TransitionDetail {transition} />
			{/if}
		{:else}
			<div class="status">No tracks in this set</div>
		{/if}
	{:else}
		<div class="empty-state">
			Select a set to view its timeline
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
	}

	.mode-toggle {
		margin-left: auto;
		display: flex;
		background: var(--bg-tertiary);
		border-radius: 4px;
		overflow: hidden;
	}

	.mode-btn {
		padding: 4px 12px;
		font-size: 12px;
		color: var(--text-secondary);
		transition: all 0.15s;
	}

	.mode-btn.active {
		background: var(--accent);
		color: #000;
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
		flex-shrink: 0;
		border-bottom: 1px solid var(--border);
	}

	.hint {
		padding: 4px 16px;
		font-size: 11px;
		color: var(--text-dim);
		border-bottom: 1px solid var(--border);
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
