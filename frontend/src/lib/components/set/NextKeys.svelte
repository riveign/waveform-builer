<script lang="ts">
	import type { CompatibleKey } from '$lib/utils/camelot';

	let {
		keys,
		verbose = false,
	}: {
		keys: CompatibleKey[];
		/** Spell out what each move does, rather than leaning on the glyph alone. */
		verbose?: boolean;
	} = $props();

	/** Glyph + plain words per relation. The glyph is never the only carrier —
	 *  each chip is titled, and verbose mode says it outright. */
	const MOVES: Record<CompatibleKey['relation'], { glyph: string; word: string; hint: string }> = {
		'energy up': { glyph: '↑', word: 'lifts', hint: 'one step up the wheel — lifts, opens out' },
		'energy down': { glyph: '↓', word: 'settles', hint: 'one step down the wheel — settles, deepens' },
		'mood switch': { glyph: '↺', word: 'switches', hint: 'relative major/minor — same drive, new colour' },
	};

	const TONE: Record<CompatibleKey['relation'], string> = {
		'energy up': 'var(--energy-high)',
		'energy down': 'var(--energy-low)',
		'mood switch': 'var(--role)',
	};
</script>

{#if keys.length}
	<span class="next" class:verbose>
		{#each keys as k (k.camelot)}
			<span class="chip" title="{k.name} ({k.camelot}) — {MOVES[k.relation].hint}">
				<span class="glyph" style="color:{TONE[k.relation]}" aria-hidden="true">{MOVES[k.relation].glyph}</span>
				<span class="name">{k.name}</span>
				{#if verbose}<span class="word">{MOVES[k.relation].word}</span>{/if}
			</span>
		{/each}
	</span>
{/if}

<style>
	.next {
		display: flex;
		gap: 3px;
		align-items: center;
		min-width: 0;
	}

	.chip {
		display: inline-flex;
		align-items: center;
		gap: 3px;
		padding: 2px 5px;
		border-radius: 2px;
		background: var(--surface-3);
		color: var(--text-2);
		font-family: var(--font-mono, ui-monospace, monospace);
		font-size: var(--text-2xs);
		font-weight: var(--font-weight-semibold);
		letter-spacing: -0.01em;
		white-space: nowrap;
	}

	.glyph {
		font-weight: var(--font-weight-semibold);
	}

	.verbose .chip {
		padding: 3px 7px;
		font-size: var(--text-xs);
	}

	.word {
		color: var(--text-4);
		font-weight: var(--font-weight-regular);
	}
</style>
