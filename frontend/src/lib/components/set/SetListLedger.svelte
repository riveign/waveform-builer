<script lang="ts">
	/**
	 * Option 1 — the Ledger. One 42px row per track. The move OUT of a track lives
	 * at the right edge of the row it leaves, so a transition costs no band of its
	 * own, and the keys that mix cleanly out of it sit in a permanent column.
	 */
	import type { SetRow } from './rowModel';
	import { formatBpmDelta, scoreColor } from './rowModel';
	import SetCover from './SetCover.svelte';
	import NextKeys from './NextKeys.svelte';
	import { energyColor } from '$lib/utils/energy';

	let {
		rows,
		focusedTrackId = null,
		runStarts,
		onselect,
		ontransition,
	}: {
		rows: SetRow[];
		focusedTrackId?: number | null;
		/** Row indices that begin a run of 3+ tracks in one key. */
		runStarts: Set<number>;
		onselect?: (trackId: number) => void;
		ontransition?: (index: number) => void;
	} = $props();
</script>

<div class="ledger">
	<div class="head" aria-hidden="true">
		<span></span><span>#</span><span>Track</span><span>Genre</span>
		<span>Next keys</span><span>Key</span><span>BPM</span><span>Energy</span><span>Move out</span>
	</div>

	{#each rows as row, i (row.track.position ?? i)}
		{#if runStarts.has(i)}
			<div class="run">The story here is energy, not key</div>
		{/if}
		<div
			class="row"
			class:sel={focusedTrackId === row.track.track_id}
			role="button"
			tabindex="0"
			onclick={() => onselect?.(row.track.track_id)}
			onkeydown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onselect?.(row.track.track_id); } }}
		>
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
			<span class="ebar">
				{#if row.energy != null}
					<i style="width:{Math.round(row.energy * 100)}%;background:{energyColor(row.energy)}"></i>
				{/if}
			</span>
			<span class="move">
				{#if row.moveOut}
					<span class="dot" style="background:{scoreColor(row.moveOut.score)}"></span>
					<button
						class="mv {row.moveOut.kind}"
						title={row.moveOut.teaching ?? 'Open this transition'}
						onclick={(e) => { e.stopPropagation(); ontransition?.(i); }}
					>{row.moveOut.label} {formatBpmDelta(row.moveOut.bpmDelta)}</button>
				{/if}
			</span>
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
	.row:hover { background: var(--surface-hover); }
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

	.ebar { height: 3px; border-radius: 2px; background: var(--surface-3); position: relative; overflow: hidden; }
	.ebar i { position: absolute; inset: 0 auto 0 0; display: block; border-radius: 2px; }

	.move { display: flex; align-items: center; gap: var(--space-sm); justify-content: flex-end; }
	.dot { width: 6px; height: 6px; border-radius: 50%; flex-shrink: 0; }

	.mv {
		font-family: var(--font-mono, ui-monospace, monospace);
		font-size: var(--text-2xs);
		font-weight: var(--font-weight-semibold);
		letter-spacing: 0.04em;
		padding: 2px 6px;
		border-radius: 2px;
		border: none;
		cursor: pointer;
		white-space: nowrap;
	}
	.mv.hold { background: color-mix(in srgb, var(--score-excellent) 16%, transparent); color: var(--score-excellent); }
	.mv.lift { background: color-mix(in srgb, var(--energy-high) 16%, transparent); color: var(--energy-high); }
	.mv.switch { background: color-mix(in srgb, var(--role) 16%, transparent); color: var(--role); }
	.mv.clash { background: color-mix(in srgb, var(--score-poor) 16%, transparent); color: var(--score-poor); }

	.run {
		font-size: var(--text-2xs);
		color: var(--role);
		background: color-mix(in srgb, var(--role) 8%, transparent);
		border-left: 2px solid var(--role);
		padding: var(--space-xs) var(--space-lg);
	}
</style>
