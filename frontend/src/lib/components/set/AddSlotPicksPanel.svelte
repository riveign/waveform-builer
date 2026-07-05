<script lang="ts">
	import type { SlotSuggestion } from '$lib/types';
	import { getSlotSuggestions, addTrackToSet, replaceTrackInSet } from '$lib/api/sets';

	let {
		setId,
		trackCount,
		onApplied,
		onclose,
	}: {
		setId: number;
		trackCount: number;
		onApplied: () => void;
		onclose: () => void;
	} = $props();

	const MOVES = [
		{ intent: 'push_higher', label: 'Push higher' },
		{ intent: 'brighten', label: 'Brighten' },
		{ intent: 'cool_down', label: 'Cool down' },
		{ intent: 'hold', label: 'Hold' },
	];

	let mode = $state<'insert' | 'replace'>('insert');
	let intent = $state<string | null>(null);
	// 1-based in the UI; the API/back end is 0-based.
	let slotDisplay = $state(1);
	let position = $derived(Math.max(0, Math.min(trackCount - 1, slotDisplay - 1)));
	let suggestions = $state<SlotSuggestion[]>([]);
	let loading = $state(false);
	let searched = $state(false);
	let error = $state<string | null>(null);
	let applyingId = $state<number | null>(null);

	async function loadSuggestions(nextIntent: string) {
		intent = nextIntent;
		loading = true;
		searched = true;
		error = null;
		try {
			const res = await getSlotSuggestions(setId, position, { mode, intent, n: 8 });
			suggestions = res.suggestions;
		} catch (e) {
			error = e instanceof Error ? e.message : 'Something went wrong reading your library.';
			suggestions = [];
		} finally {
			loading = false;
		}
	}

	async function applyPick(pick: SlotSuggestion) {
		applyingId = pick.track.id;
		try {
			if (mode === 'insert') {
				await addTrackToSet(setId, pick.track.id, position);
			} else {
				await replaceTrackInSet(setId, position, pick.track.id);
			}
			onApplied();
			onclose();
		} catch (e) {
			error = e instanceof Error ? e.message : "Couldn't apply that pick.";
		} finally {
			applyingId = null;
		}
	}
</script>

<div class="slot-panel">
	<div class="panel-header">
		<h3>Directional slot pick</h3>
		<button class="close-btn" onclick={onclose} aria-label="Close">×</button>
	</div>
	<p class="hint">
		Name a slot and a direction — Kiku ranks tracks you own that make the move
		while still mixing out of the track before and into the one after.
	</p>

	<div class="controls">
		<div class="mode-toggle" role="group" aria-label="Insert or replace">
			<button class:active={mode === 'insert'} onclick={() => { mode = 'insert'; }}>Insert</button>
			<button class:active={mode === 'replace'} onclick={() => { mode = 'replace'; }}>Replace</button>
		</div>
		<label class="slot-input">
			Slot
			<input type="number" min="1" max={trackCount} bind:value={slotDisplay} />
		</label>
	</div>

	<div class="moves">
		{#each MOVES as m (m.intent)}
			<button
				class="move-btn"
				class:active={intent === m.intent}
				onclick={() => loadSuggestions(m.intent)}
			>
				{m.label}
			</button>
		{/each}
	</div>

	{#if loading}
		<div class="status">Reading your library…</div>
	{:else if error}
		<div class="status error">{error}</div>
	{:else if searched && suggestions.length === 0}
		<div class="status">
			No owned track makes that move here cleanly — try Hold, or another direction.
		</div>
	{:else}
		<ul class="picks">
			{#each suggestions as pick (pick.track.id)}
				<li class="pick-card">
					<div class="pick-main">
						<div class="pick-title">{pick.track.title ?? 'Untitled'}</div>
						<div class="pick-artist">{pick.track.artist ?? ''}</div>
						<div class="pick-move">{pick.move}</div>
						{#if pick.caveat}
							<div class="pick-caveat">{pick.caveat}</div>
						{/if}
					</div>
					<div class="pick-side">
						<div class="pick-score">{Math.round(pick.score * 100)}</div>
						<button
							class="apply-btn"
							onclick={() => applyPick(pick)}
							disabled={applyingId === pick.track.id}
						>
							{applyingId === pick.track.id
								? 'Applying…'
								: mode === 'insert'
									? `Insert at ${slotDisplay}`
									: `Replace ${slotDisplay}`}
						</button>
					</div>
				</li>
			{/each}
		</ul>
	{/if}
</div>

<style>
	.slot-panel {
		position: absolute;
		top: 56px;
		right: 16px;
		z-index: 30;
		width: 400px;
		max-height: 72vh;
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
	.controls {
		display: flex;
		align-items: center;
		gap: 12px;
		margin-bottom: 10px;
	}
	.mode-toggle {
		display: inline-flex;
		border: 1px solid var(--border, #2a2b30);
		border-radius: 6px;
		overflow: hidden;
	}
	.mode-toggle button {
		background: transparent;
		border: none;
		color: var(--text-secondary, #9a9b9f);
		padding: 5px 10px;
		font-size: 12px;
		cursor: pointer;
	}
	.mode-toggle button.active {
		background: var(--accent, #7aa2f7);
		color: #10131a;
	}
	.slot-input {
		font-size: 12px;
		color: var(--text-secondary, #9a9b9f);
		display: inline-flex;
		align-items: center;
		gap: 6px;
	}
	.slot-input input {
		width: 56px;
		padding: 4px 6px;
		background: var(--surface-2, #23242a);
		border: 1px solid var(--border, #2a2b30);
		border-radius: 6px;
		color: inherit;
	}
	.moves {
		display: flex;
		flex-wrap: wrap;
		gap: 6px;
		margin-bottom: 8px;
	}
	.move-btn {
		font-size: 12px;
		padding: 5px 10px;
		border: 1px solid var(--border, #2a2b30);
		border-radius: 6px;
		background: transparent;
		color: var(--text-secondary, #9a9b9f);
		cursor: pointer;
	}
	.move-btn.active {
		border-color: var(--accent, #7aa2f7);
		color: var(--accent, #7aa2f7);
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
	.pick-move {
		margin-top: 4px;
		font-size: 12px;
		color: var(--text-tertiary, #7a7b82);
	}
	.pick-caveat {
		margin-top: 6px;
		font-size: 12px;
		color: var(--warn, #e5c07b);
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
	.apply-btn {
		font-size: 12px;
		padding: 5px 9px;
		border: 1px solid var(--accent, #7aa2f7);
		border-radius: 6px;
		background: transparent;
		color: var(--accent, #7aa2f7);
		cursor: pointer;
		white-space: nowrap;
	}
	.apply-btn:disabled {
		opacity: 0.5;
		cursor: default;
	}
</style>
