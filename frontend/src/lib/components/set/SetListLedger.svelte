<script lang="ts">
	/**
	 * Option 1 — the Ledger. One 42px row per track. The move OUT of a track lives
	 * at the right edge of the row it leaves, so a transition costs no band of its
	 * own, and the keys that mix cleanly out of it sit in a permanent column.
	 *
	 * Editable since 2026-09-09: nudge, keyboard move and remove, driven straight
	 * into the set-tracks store — the same store `rows` is derived from, so an edit
	 * is on screen before the write leaves. There is deliberately **no** drag-and-
	 * drop here: `svelte-dnd-action` maps a zone's children 1:1 onto its `items`,
	 * and this list interleaves a sticky header and run banners between the rows.
	 * That mismatch is what silently killed dragging in the timeline once already.
	 */
	import type { SetRow } from './rowModel';
	import SetCover from './SetCover.svelte';
	import NextKeys from './NextKeys.svelte';
	import ReorderControls from './ReorderControls.svelte';
	import EnergyBar from './EnergyBar.svelte';
	import MoveBadge from './MoveBadge.svelte';
	import { createReorder } from './reorder.svelte';
	import { getSetTracksStore } from '$lib/stores/setTracks.svelte';

	let {
		rows,
		focusedTrackId = null,
		runStarts,
		editable = true,
		onselect,
		ontransition,
	}: {
		rows: SetRow[];
		focusedTrackId?: number | null;
		/** Row indices that begin a run of 3+ tracks in one key. */
		runStarts: Set<number>;
		/** Off for a read-only render; the reorder and remove columns disappear. */
		editable?: boolean;
		onselect?: (trackId: number) => void;
		ontransition?: (index: number) => void;
	} = $props();

	const store = getSetTracksStore();

	let listEl = $state<HTMLElement | undefined>();
	let removeInFlight = $state<number | null>(null);

	const reorder = createReorder({
		store,
		getListEl: () => listEl,
		isBusy: () => removeInFlight !== null,
	});

	async function removeTrack(trackId: number) {
		if (removeInFlight !== null) return;
		removeInFlight = trackId;
		try {
			await store.remove(trackId);
		} finally {
			removeInFlight = null;
		}
	}
</script>

<div class="ledger" class:editable bind:this={listEl}>
	<div class="head" aria-hidden="true">
		{#if editable}<span></span>{/if}
		<span></span><span>#</span><span>Track</span><span>Genre</span>
		<span>Next keys</span><span>Key</span><span>BPM</span><span>Energy</span><span>Move out</span>
		{#if editable}<span></span>{/if}
	</div>

	{#each rows as row, i (row.track.position ?? i)}
		{#if runStarts.has(i)}
			<div class="run">The story here is energy, not key</div>
		{/if}
		<div
			class="row"
			class:sel={focusedTrackId === row.track.track_id}
			class:lifted={reorder.liftedIndex === i}
			role="button"
			tabindex="0"
			onclick={() => onselect?.(row.track.track_id)}
			onkeydown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onselect?.(row.track.track_id); } }}
		>
			{#if editable}
				<ReorderControls
					index={i}
					count={rows.length}
					dense
					draggable={false}
					lifted={reorder.liftedIndex === i}
					disabled={removeInFlight !== null}
					onnudge={(dir) => reorder.nudge(i, dir)}
					onkeydown={(e) => reorder.keydown(e, i)}
					onblur={() => reorder.blur()}
				/>
			{/if}
			<SetCover trackId={row.track.track_id} camelot={row.camelot} keyColor={row.keyColor} size={26} />
			<span class="pos">{row.position}</span>
			<span class="who">
				<span class="ttl">{row.track.title ?? 'Unknown track'}</span>
				<span class="art">{row.track.artist ?? '—'}</span>
			</span>
			<span class="gen">{row.track.genre ?? ''}</span>
			<NextKeys keys={row.nextKeys} />
			<span class="key" style="color:{row.keyColor}">{row.keyName}</span>
			<span class="bpm">{row.track.bpm ? Math.round(row.track.bpm) : '—'}</span>
			<EnergyBar energy={row.energy} zone={row.track.resolved_energy} />
			<span class="move">
				{#if row.moveOut}
					<MoveBadge move={row.moveOut} onclick={() => ontransition?.(i)} />
				{/if}
			</span>
			{#if editable}
				<button
					class="rm"
					onclick={(e) => { e.stopPropagation(); removeTrack(row.track.track_id); }}
					disabled={removeInFlight !== null}
					title="Take out of the set"
					aria-label="Take {row.track.title ?? 'this track'} out of the set"
				>
					<svg width="10" height="10" viewBox="0 0 10 10" fill="none" stroke="currentColor" stroke-width="1.6">
						<path d="M1.5 1.5l7 7M8.5 1.5l-7 7" />
					</svg>
				</button>
			{/if}
		</div>
	{/each}
</div>

<style>
	.ledger { display: flex; flex-direction: column; }

	.head,
	.row {
		display: grid;
		grid-template-columns: 26px 22px minmax(140px, 1fr) 92px 128px 44px 40px 46px 82px;
		gap: var(--space-lg);
		align-items: center;
		padding: 0 var(--space-lg);
	}

	/* Editing adds the reorder cluster in front and the remove button behind.
	   Both are tight columns with their own small gap, so the ledger proper keeps
	   the spacing it was tuned with. */
	.ledger.editable .head,
	.ledger.editable .row {
		grid-template-columns: 30px 26px 22px minmax(140px, 1fr) 92px 128px 44px 40px 46px 82px 18px;
	}

	.head {
		height: 26px;
		font-family: var(--font-mono, ui-monospace, monospace);
		font-size: var(--text-2xs);
		letter-spacing: 0.1em;
		text-transform: uppercase;
		color: var(--text-4);
		border-bottom: 1px solid var(--border-default);
		position: sticky;
		top: 0;
		background: var(--surface-2);
		z-index: 1;
	}

	.row {
		height: 42px;
		border-bottom: 1px solid var(--surface-3);
		cursor: pointer;
		text-align: left;
	}
	/* The controls stay quiet until the row is under the pointer or holds focus.
	   These two properties are read by ReorderControls; see its docstring. */
	.row:hover,
	.row:focus-within {
		background: var(--surface-hover);
		--reorder-handle-op: 0.8;
		--reorder-nudge-op: 0.8;
	}
	.row.lifted {
		--reorder-handle-op: 1;
		--reorder-nudge-op: 1;
		box-shadow: inset 0 0 0 1px var(--accent);
	}
	.row.sel { background: var(--surface-3); box-shadow: inset 2px 0 0 var(--accent); }
	.row:focus-visible { outline: var(--focus-ring-width) solid var(--focus-ring); outline-offset: calc(-1 * var(--focus-ring-width)); }

	.pos {
		font-family: var(--font-mono, ui-monospace, monospace);
		font-size: var(--text-2xs);
		color: var(--text-4);
		font-variant-numeric: tabular-nums;
		text-align: right;
	}

	.who { min-width: 0; }
	.ttl {
		display: block;
		font-size: var(--text-sm);
		font-weight: var(--font-weight-medium);
		white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
	}
	.art {
		display: block;
		font-size: var(--text-2xs);
		color: var(--text-3);
		white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
	}
	.gen {
		font-size: var(--text-2xs); color: var(--text-3);
		white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
	}

	.key {
		font-family: var(--font-mono, ui-monospace, monospace);
		font-size: var(--text-xs);
		font-weight: var(--font-weight-semibold);
	}
	.bpm {
		font-family: var(--font-mono, ui-monospace, monospace);
		font-size: var(--text-xs);
		color: var(--text-2);
		font-variant-numeric: tabular-nums;
		text-align: right;
	}

	.move { display: flex; align-items: center; justify-content: flex-end; }

	.rm {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 18px;
		height: 18px;
		border: none;
		background: none;
		padding: 0;
		border-radius: 3px;
		color: var(--text-dim);
		cursor: pointer;
		opacity: var(--reorder-nudge-op, 0);
		transition: opacity 0.1s, color 0.1s, background 0.1s;
	}
	.rm:hover:not(:disabled) {
		background: color-mix(in srgb, var(--score-poor) 16%, transparent);
		color: var(--score-poor);
	}
	.rm:disabled { cursor: default; opacity: 0.15; }
	.rm:focus-visible {
		outline: 1px solid var(--accent);
		outline-offset: 1px;
		opacity: 1;
	}

	.run {
		font-size: var(--text-2xs);
		color: var(--role);
		background: color-mix(in srgb, var(--role) 8%, transparent);
		border-left: 2px solid var(--role);
		padding: var(--space-xs) var(--space-lg);
	}
</style>
