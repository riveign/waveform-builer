<script lang="ts">
	import type { Snippet } from 'svelte';

	let {
		onselect,
		icon,
		disabled = false,
		danger = false,
		selected = false,
		children,
	}: {
		onselect?: () => void;
		/** Leading glyph/snippet — a non-color cue (icon, dot). */
		icon?: Snippet;
		disabled?: boolean;
		/** Destructive tone (delete, remove). */
		danger?: boolean;
		/** Picker-style selected/check state — shows a trailing check. */
		selected?: boolean;
		children?: Snippet;
	} = $props();
</script>

<button
	type="button"
	class="menu-item"
	class:menu-item--danger={danger}
	class:menu-item--selected={selected}
	role={selected ? 'menuitemradio' : 'menuitem'}
	{disabled}
	aria-disabled={disabled || undefined}
	aria-checked={selected || undefined}
	tabindex="-1"
	onclick={() => { if (!disabled) onselect?.(); }}
>
	{#if icon}
		<span class="menu-item__icon" aria-hidden="true">{@render icon()}</span>
	{/if}
	<span class="menu-item__label">{@render children?.()}</span>
	{#if selected}
		<span class="menu-item__check" aria-hidden="true">✓</span>
	{/if}
</button>

<style>
	.menu-item {
		display: flex;
		align-items: center;
		gap: var(--space-md);
		width: 100%;
		min-height: var(--menu-item-height);
		padding: 0 var(--menu-item-pad-x);
		border: none;
		border-radius: var(--menu-item-radius);
		background: none;
		color: var(--text-1);
		font-family: inherit;
		font-size: var(--text-base);
		line-height: 1;
		text-align: left;
		cursor: pointer;
		transition:
			background var(--dur-fast) var(--ease-standard),
			color var(--dur-fast) var(--ease-standard);
	}
	.menu-item:hover:not(:disabled),
	.menu-item:focus-visible:not(:disabled) {
		background: var(--menu-item-hover);
	}
	.menu-item:active:not(:disabled) {
		background: var(--menu-item-active);
	}
	.menu-item:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}
	.menu-item--danger {
		color: var(--destructive);
	}
	.menu-item__icon {
		display: inline-flex;
		align-items: center;
		flex-shrink: 0;
	}
	.menu-item__label {
		flex: 1;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
		min-width: 0;
	}
	.menu-item__check {
		margin-left: auto;
		flex-shrink: 0;
		color: var(--accent-text);
		font-size: var(--text-sm);
	}
	/* The global :where(...):focus-visible rule supplies the keyboard ring. */
</style>
