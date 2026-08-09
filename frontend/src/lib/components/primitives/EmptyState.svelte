<script lang="ts">
	import type { Snippet } from 'svelte';

	/**
	 * The "nothing here yet" state.
	 *
	 * Fourteen surfaces had written their own, which is why the tone drifted. An
	 * empty state is a teaching opportunity: say what would fill this space and how
	 * to get there, never just "no results".
	 */

	let {
		title,
		hint = undefined,
		compact = false,
		icon,
		action,
	}: {
		/** What is missing, in the DJ's terms. */
		title: string;
		/** How to fill it. One sentence. */
		hint?: string;
		/** Inline sizing for panels rather than a whole surface. */
		compact?: boolean;
		icon?: Snippet;
		action?: Snippet;
	} = $props();
</script>

<div class="empty" class:compact>
	{#if icon}
		<div class="empty-icon">{@render icon()}</div>
	{/if}
	<p class="empty-title">{title}</p>
	{#if hint}
		<p class="empty-hint">{hint}</p>
	{/if}
	{#if action}
		<div class="empty-action">{@render action()}</div>
	{/if}
</div>

<style>
	.empty {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		gap: var(--space-sm);
		padding: var(--space-3xl) var(--space-lg);
		text-align: center;
		height: 100%;
	}

	.empty.compact {
		padding: var(--space-lg);
		height: auto;
	}

	.empty-icon {
		font-size: var(--text-xl);
		color: var(--text-4);
		line-height: 1;
	}

	.empty-title {
		font-size: var(--text-md);
		color: var(--text-2);
	}

	.empty-hint {
		font-size: var(--text-sm);
		color: var(--text-4);
		max-width: 44ch;
	}

	.empty-action {
		margin-top: var(--space-xs);
	}
</style>
