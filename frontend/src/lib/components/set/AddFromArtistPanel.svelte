<script lang="ts">
	import type { ArtistPick } from '$lib/types';
	import { getArtistPicks, addTrackToSet } from '$lib/api/sets';
	import { autocompleteArtists } from '$lib/api/tracks';
	import Typeahead from '$lib/components/library/Typeahead.svelte';

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
		} finally {
			insertingId = null;
		}
	}
</script>

<div class="artist-panel">
	<div class="panel-header">
		<h3>Add from an artist</h3>
		<button class="close-btn" onclick={onclose} aria-label="Close">×</button>
	</div>
	<p class="hint">Pull a track you already own — ranked by where it fits this set.</p>

	<Typeahead
		placeholder="Name an artist…"
		bind:selected={selectedArtists}
		fetchSuggestions={(q) => autocompleteArtists(q, 10)}
	/>

	{#if loading}
		<div class="status">Reading your library…</div>
	{:else if error}
		<div class="status error">{error}</div>
	{:else if searched && artist && picks.length === 0}
		<div class="status">
			Nothing new from {artist} here — you may already have their tracks in this set.
		</div>
	{:else}
		<ul class="picks">
			{#each picks as pick (pick.track.id)}
				<li class="pick-card">
					<div class="pick-main">
						<div class="pick-title">{pick.track.title ?? 'Untitled'}</div>
						<div class="pick-artist">{pick.track.artist ?? ''}</div>
						<div class="pick-reason">{pick.reason}</div>
						{#if pick.breakdown}
							<div class="pick-breakdown">
								<span>key {Math.round(pick.breakdown.harmonic * 100)}</span>
								<span>energy {Math.round(pick.breakdown.energy_fit * 100)}</span>
								<span>bpm {Math.round(pick.breakdown.bpm_compat * 100)}</span>
								<span>genre {Math.round(pick.breakdown.genre_coherence * 100)}</span>
							</div>
						{/if}
					</div>
					<div class="pick-side">
						<div class="pick-score">{Math.round(pick.score * 100)}</div>
						<button
							class="insert-btn"
							onclick={() => insertPick(pick)}
							disabled={insertingId === pick.track.id}
						>
							{insertingId === pick.track.id ? 'Adding…' : `Add at pos ${pick.position + 1}`}
						</button>
					</div>
				</li>
			{/each}
		</ul>
	{/if}
</div>

<style>
	.artist-panel {
		position: absolute;
		top: 56px;
		right: 16px;
		z-index: 30;
		width: 380px;
		max-height: 70vh;
		overflow-y: auto;
		background: var(--surface, #1b1c20);
		border: 1px solid var(--border, #2a2b30);
		border-radius: 10px;
		padding: 14px;
		box-shadow: 0 8px 28px rgba(0, 0, 0, 0.4);
	}
	.panel-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
	}
	.panel-header h3 {
		margin: 0;
		font-size: 15px;
	}
	.close-btn {
		background: none;
		border: none;
		color: var(--text-secondary, #9a9b9f);
		font-size: 20px;
		cursor: pointer;
		line-height: 1;
	}
	.hint {
		margin: 4px 0 10px;
		font-size: 12px;
		color: var(--text-secondary, #9a9b9f);
	}
	.status {
		margin-top: 12px;
		font-size: 13px;
		color: var(--text-secondary, #9a9b9f);
	}
	.status.error {
		color: var(--danger, #e06c75);
	}
	.picks {
		list-style: none;
		margin: 12px 0 0;
		padding: 0;
		display: flex;
		flex-direction: column;
		gap: 8px;
	}
	.pick-card {
		display: flex;
		justify-content: space-between;
		gap: 10px;
		padding: 10px;
		border: 1px solid var(--border, #2a2b30);
		border-radius: 8px;
	}
	.pick-title {
		font-weight: 600;
		font-size: 13px;
	}
	.pick-artist {
		font-size: 12px;
		color: var(--text-secondary, #9a9b9f);
	}
	.pick-reason {
		margin-top: 4px;
		font-size: 12px;
		color: var(--text-tertiary, #7a7b82);
	}
	.pick-breakdown {
		margin-top: 6px;
		display: flex;
		flex-wrap: wrap;
		gap: 6px;
		font-size: 11px;
		color: var(--text-tertiary, #7a7b82);
	}
	.pick-side {
		display: flex;
		flex-direction: column;
		align-items: flex-end;
		gap: 8px;
	}
	.pick-score {
		font-size: 18px;
		font-weight: 700;
		color: var(--accent, #7aa2f7);
	}
	.insert-btn {
		font-size: 12px;
		padding: 5px 9px;
		border: 1px solid var(--accent, #7aa2f7);
		border-radius: 6px;
		background: transparent;
		color: var(--accent, #7aa2f7);
		cursor: pointer;
		white-space: nowrap;
	}
	.insert-btn:disabled {
		opacity: 0.5;
		cursor: default;
	}
</style>
