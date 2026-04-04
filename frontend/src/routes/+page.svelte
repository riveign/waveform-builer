<script lang="ts">
	import type { Track, SetBuildParams, SetBuildComplete, SetAnalysis } from '$lib/types';
	import LibraryBrowser from '$lib/components/library/LibraryBrowser.svelte';
	import Workspace from '$lib/components/Workspace.svelte';
	import BuildSetDialog from '$lib/components/set/BuildSetDialog.svelte';
	import BuildProgress from '$lib/components/set/BuildProgress.svelte';
	import { buildSet } from '$lib/api/sets';
	import { getUiStore } from '$lib/stores/ui.svelte';

	const ui = getUiStore();

	type BuildEvent = {
		type: 'started' | 'track_added' | 'complete' | 'analyzed' | 'error';
		data: any;
	};

	type BuildState = 'idle' | 'building' | 'complete' | 'error';

	// ── Build dialog + progress state ──
	let showBuildDialog = $state(false);
	let buildState = $state<BuildState>('idle');
	let buildEvents = $state<BuildEvent[]>([]);
	let buildError = $state('');
	let lastBuildResult = $state<SetBuildComplete | null>(null);
	let lastBuildAnalysis = $state<SetAnalysis | null>(null);

	function handleTrackSelect(track: Track) {
		ui.selectedTrack = track;
	}

	function handleOpenBuildDialog() {
		showBuildDialog = true;
	}

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
				const event: BuildEvent = {
					type: eventType as BuildEvent['type'],
					data,
				};

				if (eventType === 'started') {
					// Already in building state
				} else if (eventType === 'track_added') {
					buildEvents = [...buildEvents, event];
				} else if (eventType === 'complete') {
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
			if (!errorDuringStream) {
				buildState = 'complete';
			}
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
			// Pass pre-computed analysis to SetView via ui store
			ui.pendingAnalysis = lastBuildAnalysis;
			lastBuildAnalysis = null;
			// Switch to set tab and select the newly built set
			ui.selectedSetId = completedSetId;
			ui.activeTab = 'set';
		}
	}

	let showBuildButton = $derived(ui.activeTab === 'set' && buildState === 'idle');
</script>

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
		<Workspace />
		{#if showBuildButton}
			<button class="build-set-btn" onclick={handleOpenBuildDialog} aria-label="Open build set dialog">
				Build Set
			</button>
		{/if}
	</main>
</div>

<BuildSetDialog bind:open={showBuildDialog} onbuild={handleBuild} />

<style>
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
		padding: 24px;
	}

	/* ── Build Set floating action button ── */
	.build-set-btn {
		position: absolute;
		bottom: 20px;
		right: 20px;
		z-index: 5;
		padding: 10px 22px;
		font-size: 13px;
		font-weight: 600;
		color: #000;
		background: var(--accent);
		border: none;
		border-radius: 8px;
		cursor: pointer;
		box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
		transition: background 0.15s, transform 0.1s, box-shadow 0.15s;
	}

	.build-set-btn:hover {
		background: var(--accent-dim);
		transform: translateY(-1px);
		box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
	}

	.build-set-btn:active {
		transform: translateY(0);
		box-shadow: 0 2px 6px rgba(0, 0, 0, 0.3);
	}
</style>
