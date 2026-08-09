<script lang="ts" module>
	export type SkeletonShape = 'text' | 'block' | 'circle';
</script>

<script lang="ts">
	/**
	 * A placeholder holding the shape of content that is still loading.
	 *
	 * Preferred over a spinner wherever the eventual layout is known, because it
	 * doesn't move the page when the data lands.
	 */

	let {
		shape = 'text',
		lines = 1,
		width = undefined,
		height = undefined,
		label = 'Loading',
	}: {
		shape?: SkeletonShape;
		/** For `text`: how many lines to stack. The last is shortened. */
		lines?: number;
		width?: string;
		height?: string;
		/** Announced to screen readers in place of the visual placeholder. */
		label?: string;
	} = $props();
</script>

<div class="skeleton-group" role="status" aria-label={label} aria-busy="true">
	{#if shape === 'text'}
		{#each Array(lines) as _, i (i)}
			<span
				class="skeleton skeleton--text"
				class:last={i === lines - 1 && lines > 1}
				style:width={i === lines - 1 && lines > 1 ? '60%' : width}
			></span>
		{/each}
	{:else}
		<span
			class="skeleton skeleton--{shape}"
			style:width
			style:height
		></span>
	{/if}
</div>

<style>
	.skeleton-group {
		display: flex;
		flex-direction: column;
		gap: var(--space-xs);
		width: 100%;
	}

	.skeleton {
		display: block;
		background: var(--surface-3);
		border-radius: var(--radius-sm, 4px);
		position: relative;
		overflow: hidden;
	}

	.skeleton--text { height: 0.9em; width: 100%; }
	.skeleton--block { height: 100px; width: 100%; }
	.skeleton--circle { width: 40px; height: 40px; border-radius: 50%; }

	/* A slow sheen reads as "working" without the twitchiness of a spinner. */
	.skeleton::after {
		content: '';
		position: absolute;
		inset: 0;
		transform: translateX(-100%);
		background: linear-gradient(
			90deg,
			transparent,
			var(--surface-hover),
			transparent
		);
		animation: sheen 1.6s ease-in-out infinite;
	}

	@keyframes sheen {
		100% { transform: translateX(100%); }
	}

	@media (prefers-reduced-motion: reduce) {
		.skeleton::after { animation: none; }
	}
</style>
