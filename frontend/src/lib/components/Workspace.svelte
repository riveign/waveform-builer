<script lang="ts">
	import type { Track } from '$lib/types';
	import TrackView from './waveform/TrackView.svelte';
	import SetView from './set/SetView.svelte';
	import DnaView from './dna/DnaView.svelte';

	let { track }: { track: Track | null } = $props();

	let tab = $state('track');

	function handleKeydown(e: KeyboardEvent) {
		const target = e.target as HTMLElement;
		if (target.tagName === 'INPUT' || target.tagName === 'SELECT' || target.tagName === 'TEXTAREA') return;
		if (e.key === '1') { tab = 'track'; e.preventDefault(); }
		else if (e.key === '2') { tab = 'set'; e.preventDefault(); }
		else if (e.key === '3') { tab = 'dna'; e.preventDefault(); }
	}
</script>

<svelte:window onkeydown={handleKeydown} />

<div class="workspace">
	<div class="tab-bar">
		<button class="tab" class:active={tab === 'track'} onclick={() => tab = 'track'}>
			Track View <span class="shortcut">1</span>
		</button>
		<button class="tab" class:active={tab === 'set'} onclick={() => tab = 'set'}>
			Set Timeline <span class="shortcut">2</span>
		</button>
		<button class="tab" class:active={tab === 'dna'} onclick={() => tab = 'dna'}>
			Taste DNA <span class="shortcut">3</span>
		</button>
	</div>
	<div class="tab-content">
		{#if tab === 'track'}
			{#if track}
				<TrackView {track} />
			{:else}
				<div class="empty-state">
					<p>Select a track from the library to view its waveform and features</p>
				</div>
			{/if}
		{:else if tab === 'set'}
			<SetView />
		{:else if tab === 'dna'}
			<DnaView />
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
