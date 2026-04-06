<script lang="ts">
	import type { Track, SuggestNextItem } from '$lib/types';
	import { suggestNext } from '$lib/api/tracks';
	import { addTrackToSet } from '$lib/api/sets';
	import { getCamelotColor } from '$lib/utils/camelot';

	let {
		setId,
		lastTrackId = null,
		excludeTrackIds = [],
		energyProfile = null,
		positionMin = null,
		ontrackadded,
	}: {
		setId: number;
		lastTrackId?: number | null;
		excludeTrackIds?: number[];
		energyProfile?: string | null;
		positionMin?: number | null;
		ontrackadded?: () => void;
	} = $props();

	let expanded = $state(false);
	let loading = $state(false);
	let results = $state<SuggestNextItem[]>([]);
	let adding = $state<number | null>(null);
	let toast = $state<string | null>(null);

	let filtered = $derived(
		results.filter((r) => !excludeTrackIds.includes(r.track.id))
	);

	async function loadSuggestions() {
		if (!lastTrackId) return;
		loading = true;
		try {
			const res = await suggestNext(lastTrackId, 20, undefined, undefined, setId);
			results = res.suggestions;
		} catch {
			results = [];
		} finally {
			loading = false;
		}
	}

	function handleExpand() {
		expanded = true;
		loadSuggestions();
	}

	async function handleAdd(track: Track) {
		adding = track.id;
		try {
			await addTrackToSet(setId, track.id);
			results = results.filter((r) => r.track.id !== track.id);
			toast = `Added ${track.title ?? 'track'}`;
			setTimeout(() => { toast = null; }, 2500);
			ontrackadded?.();
		} catch {
			toast = 'Could not add track';
			setTimeout(() => { toast = null; }, 3000);
		} finally {
			adding = null;
		}
	}

	function scoreColor(score: number): string {
		if (score >= 0.8) return 'var(--color-success, #66BB6A)';
		if (score >= 0.6) return 'var(--color-warning, #FFA726)';
		return 'var(--color-error, #EF5350)';
	}
</script>

{#if !expanded}
	<button class="search-trigger" onclick={handleExpand}>
		Search library to add tracks...
	</button>
{:else}
	<div class="in-set-search">
		<div class="search-header">
			<span class="search-label">Add tracks</span>
			<button class="close-btn" onclick={() => { expanded = false; results = []; }}>&times;</button>
		</div>

		{#if loading}
			<div class="search-status">Listening to your library...</div>
		{:else if !lastTrackId}
			<div class="search-status">Add a track first, then search for what comes next</div>
		{:else if filtered.length === 0}
			<div class="search-status">No suggestions found</div>
		{:else}
			<div class="results-table">
				<div class="results-header">
					<span class="col-score">Score</span>
					<span class="col-title">Title</span>
					<span class="col-key">Key</span>
					<span class="col-bpm">BPM</span>
					<span class="col-add"></span>
				</div>
				{#each filtered as item (item.track.id)}
					<div class="result-row">
						<span class="col-score" style="color: {scoreColor(item.score)}">
							{item.score.toFixed(2)}
						</span>
						<span class="col-title" title={`${item.track.title} - ${item.track.artist}`}>
							{item.track.title ?? '?'}
							<span class="artist-dim">{item.track.artist ?? ''}</span>
						</span>
						<span class="col-key" style="color: {getCamelotColor(item.track.key)}">{item.track.key ?? '?'}</span>
						<span class="col-bpm">{item.track.bpm ? Math.round(item.track.bpm) : '?'}</span>
						<button
							class="add-btn"
							onclick={() => handleAdd(item.track)}
							disabled={adding === item.track.id}
							title="Add to set"
						>
							{adding === item.track.id ? '...' : '+'}
						</button>
					</div>
				{/each}
			</div>
		{/if}
	</div>
{/if}

{#if toast}
	<div class="toast">{toast}</div>
{/if}

<style>
	.search-trigger {
		display: block;
		width: 100%;
		padding: 10px 16px;
		font-size: 13px;
		color: var(--text-dim);
		background: var(--bg-secondary);
		border: 1px dashed var(--border);
		border-radius: 6px;
		cursor: pointer;
		text-align: left;
		margin-top: 8px;
	}

	.search-trigger:hover {
		color: var(--text-primary);
		border-color: var(--accent);
	}

	.in-set-search {
		border: 1px solid var(--border);
		border-radius: 8px;
		margin-top: 8px;
		overflow: hidden;
	}

	.search-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 8px 12px;
		border-bottom: 1px solid var(--border);
	}

	.search-label {
		font-size: 12px;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.5px;
		color: var(--text-secondary);
	}

	.close-btn {
		background: none;
		border: none;
		color: var(--text-dim);
		font-size: 18px;
		cursor: pointer;
		padding: 0 4px;
	}

	.search-status {
		padding: 16px 12px;
		font-size: 12px;
		color: var(--text-dim);
	}

	.results-table {
		max-height: 300px;
		overflow-y: auto;
	}

	.results-header {
		display: flex;
		gap: 8px;
		padding: 6px 12px;
		font-size: 11px;
		color: var(--text-dim);
		text-transform: uppercase;
		letter-spacing: 0.05em;
		border-bottom: 1px solid var(--border);
	}

	.result-row {
		display: flex;
		align-items: center;
		gap: 8px;
		padding: 6px 12px;
		font-size: 13px;
	}

	.result-row:hover {
		background: var(--bg-secondary);
	}

	.col-score { width: 50px; font-weight: 600; font-size: 12px; }
	.col-title { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
	.col-key { width: 40px; font-size: 12px; }
	.col-bpm { width: 40px; font-size: 12px; }
	.col-add { width: 30px; }

	.artist-dim {
		color: var(--text-dim);
		font-size: 11px;
		margin-left: 4px;
	}

	.add-btn {
		width: 24px;
		height: 24px;
		border-radius: 50%;
		border: 1px solid var(--accent);
		background: transparent;
		color: var(--accent);
		font-size: 14px;
		font-weight: 700;
		cursor: pointer;
		display: flex;
		align-items: center;
		justify-content: center;
	}

	.add-btn:hover:not(:disabled) {
		background: var(--accent);
		color: #000;
	}

	.add-btn:disabled {
		opacity: 0.5;
	}

	.toast {
		position: fixed;
		bottom: 80px;
		left: 50%;
		transform: translateX(-50%);
		background: var(--bg-secondary);
		color: var(--text-primary);
		padding: 8px 16px;
		border-radius: 6px;
		font-size: 13px;
		border: 1px solid var(--border);
		z-index: 1000;
	}
</style>
