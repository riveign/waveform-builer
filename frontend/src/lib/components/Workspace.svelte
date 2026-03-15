<script lang="ts">
	import TrackView from './waveform/TrackView.svelte';
	import SetView from './set/SetView.svelte';
	import DnaView from './dna/DnaView.svelte';
	import EnergyTinder from './tinder/EnergyTinder.svelte';
	import { getUiStore } from '$lib/stores/ui.svelte';

	const ui = getUiStore();

	function handleKeydown(e: KeyboardEvent) {
		const target = e.target as HTMLElement;
		if (target.tagName === 'INPUT' || target.tagName === 'SELECT' || target.tagName === 'TEXTAREA') return;
		if (e.key === '1') { ui.activeTab = 'track'; e.preventDefault(); }
		else if (e.key === '2') { ui.activeTab = 'set'; e.preventDefault(); }
		else if (e.key === '3') { ui.activeTab = 'dna'; e.preventDefault(); }
		else if (e.key === '4') { ui.activeTab = 'tinder'; e.preventDefault(); }
	}
</script>

<svelte:window onkeydown={handleKeydown} />

<div class="workspace">
	<div class="tab-bar">
		<button class="tab" class:active={ui.activeTab === 'track'} onclick={() => ui.activeTab = 'track'}>
			Track View <span class="shortcut">1</span>
		</button>
		<button class="tab" class:active={ui.activeTab === 'set'} onclick={() => ui.activeTab = 'set'}>
			Set Timeline <span class="shortcut">2</span>
		</button>
		<button class="tab" class:active={ui.activeTab === 'dna'} onclick={() => ui.activeTab = 'dna'}>
			Taste DNA <span class="shortcut">3</span>
		</button>
		<button class="tab" class:active={ui.activeTab === 'tinder'} onclick={() => ui.activeTab = 'tinder'}>
			Energy Tinder <span class="shortcut">4</span>
		</button>
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
		{/if}
	</div>
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

	.tab {
		padding: 8px 20px;
		font-size: 13px;
		color: var(--text-secondary);
		border-bottom: 2px solid transparent;
		transition: all 0.15s;
	}

	.tab:hover {
		color: var(--text-primary);
		background: var(--bg-hover);
	}

	.tab.active {
		color: var(--accent);
		border-bottom-color: var(--accent);
	}

	.shortcut {
		font-size: 10px;
		color: var(--text-dim);
		margin-left: 4px;
		opacity: 0.6;
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
		font-size: 14px;
	}
</style>
