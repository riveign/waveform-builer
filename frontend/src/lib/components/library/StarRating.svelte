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
		gap: 2px;
	}
	.star {
		background: none;
		border: none;
		cursor: pointer;
		color: var(--text-dim);
		font-size: 16px;
		padding: 0 1px;
		line-height: 1;
		transition: color 0.1s;
	}
	.star:disabled {
		cursor: default;
	}
	.star.filled {
		color: #ffc107;
	}
	.star-rating-sm .star { font-size: 11px; }
	.star-rating-lg .star { font-size: 20px; }
	.score-hint {
		font-size: 11px;
		color: var(--text-muted, var(--text-secondary));
		margin-left: 6px;
	}
</style>
