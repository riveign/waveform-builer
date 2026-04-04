<script lang="ts">
	import type { SuggestNextItem } from '$lib/types';
	import { suggestNext } from '$lib/api/tracks';
	import { getCamelotColor } from '$lib/utils/camelot';
	import ScoreBreakdown from '../set/ScoreBreakdown.svelte';

	let { trackId, trackKey = null }: { trackId: number; trackKey?: string | null } = $props();

	let expanded = $state(false);
	let suggestions = $state<SuggestNextItem[]>([]);
	let loaded = $state(false);
	let loading = $state(false);
	let expandedIdx = $state<number | null>(null);

	// Reset when track changes
	$effect(() => {
		trackId;
		expanded = false;
		loaded = false;
		suggestions = [];
		expandedIdx = null;
	});

	async function toggle() {
		expanded = !expanded;
		if (expanded && !loaded) {
			loading = true;
			try {
				const res = await suggestNext(trackId, 8);
				suggestions = res.suggestions;
			} catch {
				suggestions = [];
			} finally {
				loading = false;
				loaded = true;
			}
		}
	}

	function toggleBreakdown(idx: number) {
		expandedIdx = expandedIdx === idx ? null : idx;
	}

	function scoreColor(score: number): string {
		if (score >= 0.75) return 'var(--accent)';
		if (score >= 0.5) return 'var(--energy-mid, #f39c12)';
		return 'var(--energy-high, #e74c3c)';
	}
</script>

<div class="card">
	<button class="card-header" onclick={toggle}>
		<div class="card-icon">
			<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
				<circle cx="12" cy="12" r="3" stroke="currentColor" stroke-width="1.5"/>
				<path d="M12 1v4M12 19v4M23 12h-4M5 12H1" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
				<path d="M19.8 4.2l-2.8 2.8M7 17l-2.8 2.8M19.8 19.8l-2.8-2.8M7 7L4.2 4.2" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
			</svg>
		</div>
		<span class="card-title">Sounds like</span>
		{#if loaded}
			<span class="count">{suggestions.length}</span>
		{/if}
		<span class="chevron" class:open={expanded}>&#9662;</span>
	</button>

	{#if expanded}
		<div class="card-body">
			{#if loading}
				<p class="muted">Listening to your library...</p>
			{:else if suggestions.length === 0}
				<p class="muted">No similar tracks found</p>
			{:else}
				{#each suggestions as item, idx}
					<button class="similar-row" onclick={() => toggleBreakdown(idx)}>
						<span class="score" style="color: {scoreColor(item.score)}">
							{(item.score * 100).toFixed(0)}
						</span>
						<div class="track-info">
							<span class="title">{item.track.title ?? 'Unknown'}</span>
							<span class="artist">{item.track.artist ?? 'Unknown'}</span>
						</div>
						<div class="badges">
							<span class="badge" style="color: {getCamelotColor(item.track.key)}">{item.track.key ?? '?'}</span>
							<span class="badge">{item.track.bpm ? Math.round(item.track.bpm) : '?'}</span>
						</div>
					</button>
					{#if expandedIdx === idx}
						<div class="breakdown-wrapper">
							<ScoreBreakdown
								breakdown={item.breakdown}
								keyA={trackKey}
								keyB={item.track.key}
							/>
						</div>
					{/if}
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

	.similar-row {
		display: flex;
		align-items: center;
		gap: 10px;
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

	.similar-row:hover {
		background: var(--bg-tertiary);
	}

	.score {
		font-size: 13px;
		font-weight: 600;
		font-variant-numeric: tabular-nums;
		width: 28px;
		text-align: right;
		flex-shrink: 0;
	}

	.track-info {
		flex: 1;
		min-width: 0;
		display: flex;
		flex-direction: column;
		gap: 1px;
	}

	.title {
		font-size: 12px;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.artist {
		font-size: 11px;
		color: var(--text-secondary);
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.badges {
		display: flex;
		gap: 6px;
		flex-shrink: 0;
	}

	.badge {
		font-size: 11px;
		font-weight: 500;
		font-variant-numeric: tabular-nums;
	}

	.breakdown-wrapper {
		padding: 4px 8px 8px 46px;
		animation: slide-in 0.15s ease-out;
	}

	@keyframes slide-in {
		from { opacity: 0; transform: translateY(-4px); }
		to   { opacity: 1; transform: translateY(0); }
	}
</style>
