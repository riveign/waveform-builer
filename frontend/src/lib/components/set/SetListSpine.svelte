<script lang="ts">
	/**
	 * Option 2 — the Spine. A continuous rail runs down the list, coloured by the
	 * quality of each move, with every track hanging off it as a node. The move
	 * rides ON the spine as a second line inside the same row, so the harmonic
	 * journey is the first thing you read and a transition still costs no band.
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
		runStarts: Set<number>;
		onselect?: (trackId: number) => void;
		ontransition?: (index: number) => void;
	} = $props();

	/** Plain words for the move, so the badge is never the only explanation. */
	function movePhrase(row: SetRow): string {
		const m = row.moveOut;
		if (!m) return '';
		const bpm = m.bpmDelta == null ? '' : ` · ${formatBpmDelta(m.bpmDelta)} BPM`;
		if (m.kind === 'hold') return `same key${bpm}`;
		if (m.kind === 'switch') return `relative major/minor${bpm}`;
		if (m.kind === 'clash') return `distant keys${bpm}`;
		return `one step ${m.label === 'SETTLE' ? 'down' : 'up'}${bpm}`;
	}
</script>

<div class="spine-list">
	{#each rows as row, i (row.track.position ?? i)}
		{#if runStarts.has(i)}
			<div class="run">The story here is energy, not key</div>
		{/if}
		<div class="row" class:sel={focusedTrackId === row.track.track_id}>
			<span
				class="rail"
				style="--seg:{row.moveOut ? scoreColor(row.moveOut.score) : 'var(--border-default)'}"
				class:first={i === 0}
				class:last={i === rows.length - 1}
			>
				<span class="node" style="background:{row.keyColor}"></span>
			</span>

			<div class="body">
				<div
					class="top"
					role="button"
					tabindex="0"
					onclick={() => onselect?.(row.track.track_id)}
					onkeydown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onselect?.(row.track.track_id); } }}
				>
					<SetCover trackId={row.track.track_id} camelot={row.camelot} keyColor={row.keyColor} size={30} />
					<span class="who">
						<span class="ttl">{row.track.title ?? 'Unknown track'}</span>
						<span class="art">{row.track.artist ?? '—'}{row.track.genre ? ` · ${row.track.genre}` : ''}</span>
					</span>
					<span class="keyblock">
						<span class="key" style="color:{row.keyColor}">
							{row.keyName}{row.camelot ? ` · ${row.camelot}` : ''}
						</span>
						<NextKeys keys={row.nextKeys} />
					</span>
					<span class="tempo">
						<span class="bpm">{row.track.bpm ? Math.round(row.track.bpm) : '—'}</span>
						{#if row.energy != null}
							<span class="zone" style="color:{energyColor(row.energy)}">{row.track.resolved_energy ?? ''}</span>
						{/if}
					</span>
				</div>

				{#if row.moveOut}
					<button
						class="move"
						onclick={() => ontransition?.(i)}
						title="Open this transition"
					>
						<span class="mv {row.moveOut.kind}">{row.moveOut.label}</span>
						<span class="phrase">{movePhrase(row)}</span>
						{#if row.moveOut.teaching}
							<span class="teach">— {row.moveOut.teaching}</span>
						{/if}
					</button>
				{/if}
			</div>
		</div>
	{/each}
</div>

<style>
	.spine-list { display: flex; flex-direction: column; }

	.row { display: grid; grid-template-columns: 34px 1fr; min-height: 54px; }
	.row.sel { background: var(--surface-3); }

	/* The rail IS the option: a continuous line whose colour is the move quality. */
	.rail { position: relative; display: flex; justify-content: center; }
	.rail::before {
		content: '';
		position: absolute;
		top: 0; bottom: 0;
		width: 2px;
		background: var(--seg);
	}
	.rail.first::before { top: 26px; }
	.rail.last::before { display: none; }

	.node {
		position: relative;
		z-index: 1;
		width: 11px; height: 11px;
		margin-top: 20px;
		border-radius: 50%;
		border: 2.5px solid var(--surface-1);
		flex-shrink: 0;
	}

	.body {
		padding: var(--space-md) var(--space-lg) var(--space-md) var(--space-xs);
		border-bottom: 1px solid var(--surface-3);
		min-width: 0;
	}

	.top {
		display: grid;
		grid-template-columns: 30px minmax(120px, 1fr) auto auto;
		gap: var(--space-lg);
		align-items: center;
		cursor: pointer;
		text-align: left;
	}
	.top:focus-visible { outline: var(--focus-ring-width) solid var(--focus-ring); outline-offset: 2px; }

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

	.keyblock { display: flex; flex-direction: column; gap: 2px; align-items: flex-end; }
	.key {
		font-family: var(--font-mono, ui-monospace, monospace);
		font-size: var(--text-xs);
		font-weight: var(--font-weight-semibold);
		font-variant-numeric: tabular-nums;
	}

	.tempo { display: flex; flex-direction: column; align-items: flex-end; gap: 1px; }
	.bpm {
		font-family: var(--font-mono, ui-monospace, monospace);
		font-size: var(--text-xs);
		color: var(--text-2);
		font-variant-numeric: tabular-nums;
	}
	.zone { font-size: var(--text-2xs); }

	.move {
		display: flex;
		align-items: center;
		gap: var(--space-md);
		margin-top: var(--space-sm);
		padding: 2px 0 2px 40px;
		background: none;
		border: none;
		cursor: pointer;
		text-align: left;
		width: 100%;
		min-width: 0;
	}
	.move:focus-visible { outline: var(--focus-ring-width) solid var(--focus-ring); outline-offset: 2px; }

	.mv {
		font-family: var(--font-mono, ui-monospace, monospace);
		font-size: var(--text-2xs);
		font-weight: var(--font-weight-semibold);
		letter-spacing: 0.04em;
		padding: 2px 6px;
		border-radius: 2px;
		flex-shrink: 0;
	}
	.mv.hold { background: color-mix(in srgb, var(--score-excellent) 16%, transparent); color: var(--score-excellent); }
	.mv.lift { background: color-mix(in srgb, var(--energy-high) 16%, transparent); color: var(--energy-high); }
	.mv.switch { background: color-mix(in srgb, var(--role) 16%, transparent); color: var(--role); }
	.mv.clash { background: color-mix(in srgb, var(--score-poor) 16%, transparent); color: var(--score-poor); }

	.phrase { font-size: var(--text-xs); color: var(--text-3); white-space: nowrap; }
	.teach {
		font-size: var(--text-xs);
		color: var(--text-4);
		font-style: italic;
		min-width: 0;
		white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
	}

	.run {
		font-size: var(--text-2xs);
		color: var(--role);
		background: color-mix(in srgb, var(--role) 8%, transparent);
		border-left: 2px solid var(--role);
		padding: var(--space-xs) var(--space-lg);
	}
</style>
