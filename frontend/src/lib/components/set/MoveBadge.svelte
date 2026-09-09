<script lang="ts">
	/**
	 * The move out of a track: what it does to the set, and how well it scores.
	 *
	 * Two facts, two channels, held apart on purpose — the **kind** of move
	 * (hold / lift / switch / jump) tints the badge, and the **score** colours the
	 * dot beside it. A good clash and a bad hold both exist, so folding them into
	 * one colour would lie about one of them.
	 *
	 * All three layouts drew this differently before — tinted-with-dot, tinted
	 * without, and grey-with-a-score-border — which made the same transition read
	 * as three different verdicts. One component, one reading.
	 */
	import type { MoveOut } from './rowModel';
	import { formatBpmDelta, scoreColor } from './rowModel';

	let {
		move,
		showDelta = true,
		showDot = true,
		onclick,
	}: {
		move: MoveOut;
		/** Off where the layout already spells the tempo change out in words. */
		showDelta?: boolean;
		/** Off in the Spine, whose rail already carries the score as its colour. */
		showDot?: boolean;
		onclick?: (e: MouseEvent) => void;
	} = $props();
</script>

<span class="wrap">
	{#if showDot}
		<span
			class="dot"
			style="background:{scoreColor(move.score)}"
			title={move.score == null ? 'Not scored yet' : `Transition scores ${move.score.toFixed(2)}`}
		></span>
	{/if}
	<button
		class="mv {move.kind}"
		title={move.teaching ?? 'Open this transition'}
		onclick={(e) => { e.stopPropagation(); onclick?.(e); }}
	>
		{move.label}{showDelta && move.bpmDelta != null ? ` ${formatBpmDelta(move.bpmDelta)}` : ''}
	</button>
</span>

<style>
	.wrap {
		display: inline-flex;
		align-items: center;
		gap: var(--space-sm);
		min-width: 0;
	}

	.dot {
		width: 6px;
		height: 6px;
		border-radius: 50%;
		flex-shrink: 0;
	}

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
		flex-shrink: 0;
	}
	.mv:focus-visible {
		outline: var(--focus-ring-width) solid var(--focus-ring);
		outline-offset: 1px;
	}

	.mv.hold { background: color-mix(in srgb, var(--score-excellent) 16%, transparent); color: var(--score-excellent); }
	.mv.lift { background: color-mix(in srgb, var(--energy-high) 16%, transparent); color: var(--energy-high); }
	.mv.switch { background: color-mix(in srgb, var(--role) 16%, transparent); color: var(--role); }
	.mv.clash { background: color-mix(in srgb, var(--score-poor) 16%, transparent); color: var(--score-poor); }
</style>
