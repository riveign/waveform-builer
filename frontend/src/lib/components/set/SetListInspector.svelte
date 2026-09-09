<script lang="ts">
	/**
	 * Option 3 — the quiet list. 34px rows carrying only what you scan by. Every
	 * explanation moves to the rail's inspector, so the row pays nothing for it.
	 */
	import type { SetRow } from './rowModel';
	import SetCover from './SetCover.svelte';
	import EnergyBar from './EnergyBar.svelte';
	import MoveBadge from './MoveBadge.svelte';

	let {
		rows,
		focusedTrackId = null,
		runStarts,
		onselect,
		ontransition,
	}: {
		rows: SetRow[];
		focusedTrackId?: number | null;
		runStarts: Set<number>;
		onselect?: (trackId: number) => void;
		ontransition?: (index: number) => void;
	} = $props();
</script>

<div class="quiet">
	<div class="head" aria-hidden="true">
		<span></span><span>#</span><span>Track</span>
		<span>Key</span><span>BPM</span><span>Energy</span><span>Move</span>
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
			onclick={() => { onselect?.(row.track.track_id); ontransition?.(i); }}
			onkeydown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onselect?.(row.track.track_id); ontransition?.(i); } }}
		>
			<SetCover trackId={row.track.track_id} camelot={row.camelot} keyColor={row.keyColor} size={22} />
			<span class="pos">{row.position}</span>
			<span class="ttl">
				{row.track.title ?? 'Unknown track'}<span class="art"> — {row.track.artist ?? '—'}</span>
			</span>
			<span class="key" style="color:{row.keyColor}">{row.keyName}</span>
			<span class="bpm">{row.track.bpm ? Math.round(row.track.bpm) : '—'}</span>
			<EnergyBar energy={row.energy} zone={row.track.resolved_energy} />
			<span class="movecell">
				{#if row.moveOut}
					<MoveBadge move={row.moveOut} onclick={() => ontransition?.(i)} />
				{/if}
			</span>
		</div>
	{/each}
</div>

<style>
	.quiet { display: flex; flex-direction: column; }

	.head,
	.row {
		display: grid;
		grid-template-columns: 22px 22px minmax(150px, 1fr) 44px 42px 44px 74px;
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
		height: 34px;
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

	.ttl {
		font-size: var(--text-sm);
		min-width: 0;
		white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
	}
	.art { color: var(--text-3); }

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

	.movecell { display: flex; justify-content: flex-end; }
	.run {
		font-size: var(--text-2xs);
		color: var(--role);
		background: color-mix(in srgb, var(--role) 8%, transparent);
		border-left: 2px solid var(--role);
		padding: var(--space-xs) var(--space-lg);
	}
</style>
