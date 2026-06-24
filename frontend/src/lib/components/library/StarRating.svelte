<script lang="ts">
	let {
		rating = 0,
		readonly = false,
		onchange,
		showScore = false,
		size = 'md',
	}: {
		rating: number;
		readonly?: boolean;
		onchange?: (rating: number) => void;
		showScore?: boolean;
		size?: 'sm' | 'md' | 'lg';
	} = $props();

	let hovered = $state<number | null>(null);
	let displayRating = $derived(hovered ?? rating);

	function scoreHint(r: number): string {
		if (r === 0) return 'unrated — neutral weight in transitions';
		const pct = Math.round((r / 5) * 40);
		return `${r}★ — ${pct}% of curation score`;
	}
</script>

<div
	class="star-rating"
	class:star-rating-sm={size === 'sm'}
	class:star-rating-lg={size === 'lg'}
	role="group"
	aria-label="Track rating"
>
	{#each [1, 2, 3, 4, 5] as n}
		<button
			class="star"
			class:filled={displayRating >= n}
			role="radio"
			aria-checked={rating === n}
			aria-label="{n} star{n !== 1 ? 's' : ''}"
			disabled={readonly}
			onmouseenter={() => { if (!readonly) hovered = n; }}
			onmouseleave={() => { if (!readonly) hovered = null; }}
			onclick={(e) => {
				e.stopPropagation();
				if (readonly) return;
				const newRating = rating === n ? 0 : n;
				onchange?.(newRating);
			}}
		>★</button>
	{/each}

	{#if showScore && !readonly}
		<span class="score-hint" aria-live="polite">
			{scoreHint(hovered ?? rating)}
		</span>
	{/if}
</div>

<style>
	.star-rating {
		display: flex;
		align-items: center;
		gap: var(--space-2xs);
	}
	.star {
		background: none;
		border: none;
		cursor: pointer;
		color: var(--text-4);
		font-size: var(--text-lg);
		/* Vertical padding keeps the interactive hit area ≥32px tall on the
		 * default size, even though the glyph itself is smaller. */
		padding: var(--space-md) var(--space-2xs);
		line-height: 1;
		border-radius: var(--radius-xs);
		transition: color var(--dur-fast) var(--ease-standard);
	}
	.star:disabled {
		cursor: default;
	}
	.star.filled {
		color: var(--star-fill);
	}
	.star:not(:disabled):hover {
		color: var(--star-fill);
	}
	.star:focus-visible {
		outline: var(--focus-ring-width) solid var(--focus-ring);
		outline-offset: var(--focus-ring-offset);
	}
	.star-rating-sm .star { font-size: var(--text-xs); padding: var(--space-sm) var(--space-2xs); }
	.star-rating-lg .star { font-size: var(--text-xl); }
	.score-hint {
		font-size: var(--text-xs);
		color: var(--text-3);
		margin-left: var(--space-sm);
	}
</style>
