<script lang="ts">
	import type { TrackSetAppearance } from '$lib/types';
	import { getTrackSets } from '$lib/api/tracks';
	import { getUiStore } from '$lib/stores/ui.svelte';

	let { trackId }: { trackId: number } = $props();

	const ui = getUiStore();

	let expanded = $state(false);
	let appearances = $state<TrackSetAppearance[]>([]);
	let loaded = $state(false);
	let loading = $state(false);

	// Reset when track changes
	$effect(() => {
		trackId;
		expanded = false;
		loaded = false;
		appearances = [];
	});

	async function toggle() {
		expanded = !expanded;
		if (expanded && !loaded) {
			loading = true;
			try {
				appearances = await getTrackSets(trackId);
			} catch {
				appearances = [];
			} finally {
				loading = false;
				loaded = true;
			}
		}
	}

	function navigateToSet(setId: number) {
		ui.selectedSetId = setId;
		ui.activeTab = 'set';
	}
</script>

<div class="card">
	<button class="card-header" onclick={toggle}>
		<div class="card-icon">
			<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
				<rect x="3" y="3" width="7" height="7" rx="1.5" stroke="currentColor" stroke-width="1.5"/>
				<rect x="14" y="3" width="7" height="7" rx="1.5" stroke="currentColor" stroke-width="1.5"/>
				<rect x="3" y="14" width="7" height="7" rx="1.5" stroke="currentColor" stroke-width="1.5"/>
				<rect x="14" y="14" width="7" height="7" rx="1.5" stroke="currentColor" stroke-width="1.5"/>
			</svg>
		</div>
		<span class="card-title">Sets featuring this track</span>
		{#if loaded}
			<span class="count">{appearances.length}</span>
		{/if}
		<span class="chevron" class:open={expanded}>&#9662;</span>
	</button>

	{#if expanded}
		<div class="card-body">
			{#if loading}
				<p class="muted">Checking your sets...</p>
			{:else if appearances.length === 0}
				<p class="muted">Not in any sets yet</p>
			{:else}
				{#each appearances as app}
					<button class="set-row" onclick={() => navigateToSet(app.set_id)}>
						<span class="set-name">{app.set_name ?? 'Untitled'}</span>
						<span class="set-pos">#{app.position + 1}</span>
					</button>
				{/each}
			{/if}
		</div>
	{/if}
</div>

<style>
	.card {
		background: var(--bg-secondary);
		border: 1px solid var(--border);
		border-radius: 10px;
		overflow: hidden;
		transition: border-color 0.15s;
	}

	.card:hover {
		border-color: var(--text-dim);
	}

	.card-header {
		width: 100%;
		display: flex;
		align-items: center;
		gap: 10px;
		padding: 14px 16px;
		background: none;
		border: none;
		color: var(--text-primary);
		font-size: 13px;
		cursor: pointer;
	}

	.card-icon {
		width: 20px;
		height: 20px;
		flex-shrink: 0;
		color: var(--accent);
	}

	.card-icon svg {
		width: 20px;
		height: 20px;
	}

	.card-title {
		flex: 1;
		text-align: left;
		font-weight: 500;
	}

	.count {
		font-size: 11px;
		color: var(--text-dim);
		background: var(--bg-tertiary);
		padding: 1px 6px;
		border-radius: 8px;
		font-variant-numeric: tabular-nums;
	}

	.chevron {
		font-size: 10px;
		color: var(--text-dim);
		transition: transform 0.15s;
	}

	.chevron.open {
		transform: rotate(0deg);
	}

	.chevron:not(.open) {
		transform: rotate(-90deg);
	}

	.card-body {
		padding: 4px 16px 14px;
		border-top: 1px solid var(--border);
	}

	.muted {
		font-size: 12px;
		color: var(--text-dim);
		margin: 8px 0 0;
	}

	.set-row {
		display: flex;
		justify-content: space-between;
		align-items: center;
		width: 100%;
		padding: 6px 8px;
		margin-top: 4px;
		background: none;
		border: none;
		border-radius: 4px;
		color: var(--text-primary);
		font-size: 13px;
		cursor: pointer;
		text-align: left;
		transition: background 0.1s;
	}

	.set-row:hover {
		background: var(--bg-tertiary);
	}

	.set-pos {
		font-size: 11px;
		color: var(--text-dim);
		font-variant-numeric: tabular-nums;
	}
</style>
