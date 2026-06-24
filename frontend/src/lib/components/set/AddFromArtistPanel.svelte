<script lang="ts">
	import type { ArtistPick } from '$lib/types';
	import { getArtistPicks, addTrackToSet } from '$lib/api/sets';
	import { autocompleteArtists } from '$lib/api/tracks';
	import Typeahead from '$lib/components/library/Typeahead.svelte';
	import Chip from '$lib/components/primitives/Chip.svelte';

	let {
		setId,
		onInserted,
		onclose,
	}: {
		setId: number;
		onInserted: () => void;
		onclose: () => void;
	} = $props();

	let selectedArtists = $state<string[]>([]);
	let artist = $derived(selectedArtists[0] ?? '');
	let picks = $state<ArtistPick[]>([]);
	let loading = $state(false);
	let searched = $state(false);
	let error = $state<string | null>(null);
	let insertingId = $state<number | null>(null);

	async function loadPicks() {
		if (!artist) return;
		loading = true;
		searched = true;
		error = null;
		try {
			const res = await getArtistPicks(setId, artist, 5);
			picks = res.picks;
		} catch (e) {
			error = e instanceof Error ? e.message : 'Something went wrong reading your library.';
			picks = [];
		} finally {
			loading = false;
		}
	}

	// Re-run when the chosen artist changes.
	$effect(() => {
		if (artist) loadPicks();
	});

	async function insertPick(pick: ArtistPick) {
		insertingId = pick.track.id;
		try {
			await addTrackToSet(setId, pick.track.id, pick.position);
			onInserted();
			onclose();
		} catch (e) {
			error = e instanceof Error ? e.message : "Couldn't add that track.";
			insertingId = null;
		}
	}

	function scoreColor(score: number): string {
		if (score >= 0.7) return 'var(--energy-low, #2ecc71)';
		if (score >= 0.5) return 'var(--energy-mid, #f39c12)';
		return 'var(--energy-high, #e94560)';
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Escape') onclose();
	}

	function handleBackdropClick(e: MouseEvent) {
		if ((e.target as HTMLElement).classList.contains('modal-backdrop')) onclose();
	}
</script>

<svelte:window onkeydown={handleKeydown} />

<!-- svelte-ignore a11y_click_events_have_key_events -->
<div class="modal-backdrop" role="presentation" onclick={handleBackdropClick}>
	<div class="modal" role="dialog" aria-label="Add from an artist">
		<header class="modal-header">
			<div class="head-text">
				<h3>Add from an artist</h3>
				<p class="hint">Pull a track you already own — ranked by where it fits this set.</p>
			</div>
			<button class="close-btn" onclick={onclose} aria-label="Close">
				<svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="1.5">
					<line x1="3" y1="3" x2="11" y2="11" /><line x1="11" y1="3" x2="3" y2="11" />
				</svg>
			</button>
		</header>

		<div class="search-row">
			<Typeahead
				placeholder="Name an artist…"
				bind:selected={selectedArtists}
				fetchSuggestions={(q) => autocompleteArtists(q, 10)}
			/>
		</div>

		<div class="body">
			{#if loading}
				<div class="status">Reading your library…</div>
			{:else if error}
				<div class="status error">{error}</div>
			{:else if searched && artist && picks.length === 0}
				<div class="status">
					Nothing new from {artist} here — you may already have their tracks in this set.
				</div>
			{:else if !searched}
				<div class="status empty-hint">
					Type an artist above. Kiku finds the tracks you own by them — collaborations included — and shows where each one would land in this set.
				</div>
			{:else}
				<ul class="picks">
					{#each picks as pick, i (pick.track.id)}
						<li class="pick-card">
							<div class="rank">{i + 1}</div>
							<div class="pick-main">
								<div class="pick-titlerow">
									<span class="pick-title">{pick.track.title ?? 'Untitled'}</span>
									<span class="slot">→ slot {pick.position + 1}</span>
								</div>
								<div class="pick-artist">{pick.track.artist ?? ''}</div>
								<div class="pick-reason">{pick.reason}</div>
								{#if pick.breakdown}
									<div class="pick-breakdown">
										<Chip variant="neutral" size="sm" value="key {Math.round(pick.breakdown.harmonic * 100)}" />
										<Chip variant="neutral" size="sm" value="energy {Math.round(pick.breakdown.energy_fit * 100)}" />
										<Chip variant="neutral" size="sm" value="bpm {Math.round(pick.breakdown.bpm_compat * 100)}" />
										<Chip variant="neutral" size="sm" value="genre {Math.round(pick.breakdown.genre_coherence * 100)}" />
									</div>
								{/if}
							</div>
							<div class="pick-side">
								<div class="pick-score" style="color: {scoreColor(pick.score)}">{Math.round(pick.score * 100)}</div>
								<button
									class="insert-btn"
									onclick={() => insertPick(pick)}
									disabled={insertingId === pick.track.id}
								>
									{insertingId === pick.track.id ? 'Adding…' : 'Add'}
								</button>
							</div>
						</li>
					{/each}
				</ul>
			{/if}
		</div>
	</div>
</div>

<style>
	.modal-backdrop {
		position: fixed;
		inset: 0;
		background: rgba(0, 0, 0, 0.6);
		display: flex;
		align-items: center;
		justify-content: center;
		z-index: 100;
	}

	.modal {
		background: var(--bg-primary);
		border: 1px solid var(--border);
		border-radius: 10px;
		width: 560px;
		max-width: 95vw;
		max-height: 82vh;
		display: flex;
		flex-direction: column;
		overflow: hidden;
	}

	.modal-header {
		display: flex;
		align-items: flex-start;
		justify-content: space-between;
		gap: 12px;
		padding: 14px 16px;
		border-bottom: 1px solid var(--border);
	}

	.head-text h3 {
		margin: 0;
		font-size: 15px;
		font-weight: 600;
		color: var(--text-primary);
	}

	.hint {
		margin: 3px 0 0;
		font-size: 12px;
		color: var(--text-dim);
	}

	.close-btn {
		flex-shrink: 0;
		background: none;
		border: none;
		color: var(--text-dim);
		cursor: pointer;
		padding: 2px;
		line-height: 0;
	}

	.close-btn:hover {
		color: var(--text-primary);
	}

	.search-row {
		padding: 14px 16px 6px;
	}

	.body {
		padding: 6px 16px 16px;
		overflow-y: auto;
	}

	.status {
		margin-top: 10px;
		font-size: 13px;
		color: var(--text-dim);
		line-height: 1.5;
	}

	.status.empty-hint {
		padding: 14px;
		border: 1px dashed var(--border);
		border-radius: 8px;
	}

	.status.error {
		color: var(--energy-high, #e94560);
	}

	.picks {
		list-style: none;
		margin: 10px 0 0;
		padding: 0;
		display: flex;
		flex-direction: column;
		gap: 10px;
	}

	.pick-card {
		display: flex;
		align-items: flex-start;
		gap: 12px;
		padding: 12px;
		border: 1px solid var(--border);
		border-radius: 8px;
		background: var(--bg-secondary);
	}

	.rank {
		flex-shrink: 0;
		width: 22px;
		height: 22px;
		display: flex;
		align-items: center;
		justify-content: center;
		border-radius: 50%;
		background: var(--bg-tertiary);
		color: var(--text-dim);
		font-size: 12px;
		font-weight: 700;
	}

	.pick-main {
		flex: 1;
		min-width: 0;
	}

	.pick-titlerow {
		display: flex;
		align-items: baseline;
		gap: 8px;
	}

	.pick-title {
		font-weight: 600;
		font-size: 13px;
		color: var(--text-primary);
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.slot {
		flex-shrink: 0;
		font-size: 11px;
		font-weight: 600;
		color: var(--accent);
	}

	.pick-artist {
		font-size: 12px;
		color: var(--text-dim);
		margin-top: 1px;
	}

	.pick-reason {
		margin-top: 6px;
		font-size: 12px;
		color: var(--text-secondary, #9a9b9f);
		line-height: 1.4;
	}

	.pick-breakdown {
		margin-top: 8px;
		display: flex;
		flex-wrap: wrap;
		gap: 5px;
	}

	.pick-side {
		flex-shrink: 0;
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 8px;
	}

	.pick-score {
		font-size: 20px;
		font-weight: 700;
		line-height: 1;
	}

	.insert-btn {
		font-size: 12px;
		font-weight: 600;
		padding: 5px 16px;
		border: 1px solid var(--accent);
		border-radius: 6px;
		background: var(--accent);
		color: #000;
		cursor: pointer;
	}

	.insert-btn:hover:not(:disabled) {
		opacity: 0.85;
	}

	.insert-btn:disabled {
		opacity: 0.5;
		cursor: default;
	}
</style>
