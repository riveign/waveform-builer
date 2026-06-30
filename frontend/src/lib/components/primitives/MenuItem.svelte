<script lang="ts">
	import type { Snippet } from 'svelte';
	import { tick } from 'svelte';

	let {
		onselect,
		icon,
		disabled = false,
		danger = false,
		selected = false,
		children,
		submenu,
		submenuLabel,
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
		/** When provided, this item OWNS a submenu: renders aria-haspopup="menu",
		 *  a trailing arrow, and a nested role="menu" panel containing this snippet. */
		submenu?: Snippet;
		/** Accessible name for the submenu panel. */
		submenuLabel?: string;
	} = $props();

	const hasSubmenu = $derived(Boolean(submenu));

	let submenuOpen = $state(false);
	let itemEl = $state<HTMLButtonElement | null>(null);
	let subPanelEl = $state<HTMLDivElement | null>(null);
	let closeTimer: ReturnType<typeof setTimeout> | null = null;

	/** Focusable rows inside the submenu panel, in DOM order. */
	function subItemEls(): HTMLElement[] {
		if (!subPanelEl) return [];
		return Array.from(
			subPanelEl.querySelectorAll<HTMLElement>(
				'[role="menuitem"]:not([disabled]):not([aria-disabled="true"]),' +
					'[role="menuitemradio"]:not([disabled]):not([aria-disabled="true"]),' +
					'[role="menuitemcheckbox"]:not([disabled]):not([aria-disabled="true"])',
			),
		);
	}

	function clearCloseTimer() {
		if (closeTimer) {
			clearTimeout(closeTimer);
			closeTimer = null;
		}
	}

	function openSubmenu() {
		if (!hasSubmenu || disabled) return;
		clearCloseTimer();
		submenuOpen = true;
		// Move focus into the first row so keyboard users land inside.
		tick().then(() => {
			if (!submenuOpen) return;
			const first = subItemEls()[0];
			// Complex panels (search input first) own their own focus — only grab
			// it when the panel exposes plain menu rows.
			if (first) first.focus();
		});
	}

	function closeSubmenu(returnFocus = true) {
		if (!submenuOpen) return;
		submenuOpen = false;
		if (returnFocus) itemEl?.focus();
	}

	function toggleSubmenu() {
		if (submenuOpen) closeSubmenu();
		else openSubmenu();
	}

	function handleClick() {
		if (disabled) return;
		if (hasSubmenu) toggleSubmenu();
		else onselect?.();
	}

	function handleKeydown(e: KeyboardEvent) {
		if (disabled || !hasSubmenu) return;
		switch (e.key) {
			case 'ArrowRight':
			case 'Enter':
			case ' ':
				e.preventDefault();
				e.stopPropagation();
				openSubmenu();
				break;
		}
	}

	/** Keys handled while focus is inside the open submenu panel. */
	function handleSubmenuKeydown(e: KeyboardEvent) {
		if (e.key === 'ArrowLeft' || e.key === 'Escape') {
			e.preventDefault();
			e.stopPropagation();
			closeSubmenu();
		}
	}

	function handleMouseEnter() {
		if (hasSubmenu) {
			clearCloseTimer();
			submenuOpen = true;
		}
	}

	function handleMouseLeave() {
		if (!hasSubmenu) return;
		clearCloseTimer();
		// Debounce so a brief gap between item and panel doesn't snap it shut.
		closeTimer = setTimeout(() => {
			submenuOpen = false;
		}, 120);
	}
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<div
	class="menu-item-wrap"
	class:menu-item-wrap--has-submenu={hasSubmenu}
	onmouseenter={handleMouseEnter}
	onmouseleave={handleMouseLeave}
>
	<button
		bind:this={itemEl}
		type="button"
		class="menu-item"
		class:menu-item--danger={danger}
		class:menu-item--selected={selected}
		role={selected ? 'menuitemradio' : 'menuitem'}
		{disabled}
		aria-disabled={disabled || undefined}
		aria-checked={selected || undefined}
		aria-haspopup={hasSubmenu ? 'menu' : undefined}
		aria-expanded={hasSubmenu ? submenuOpen : undefined}
		tabindex="-1"
		onclick={handleClick}
		onkeydown={handleKeydown}
	>
		{#if icon}
			<span class="menu-item__icon" aria-hidden="true">{@render icon()}</span>
		{/if}
		<span class="menu-item__label">{@render children?.()}</span>
		{#if selected}
			<span class="menu-item__check" aria-hidden="true">✓</span>
		{/if}
		{#if hasSubmenu}
			<span class="menu-item__submenu-arrow" aria-hidden="true">›</span>
		{/if}
	</button>

	{#if hasSubmenu && submenuOpen}
		<!-- svelte-ignore a11y_no_static_element_interactions -->
		<div
			bind:this={subPanelEl}
			class="menu-item__submenu"
			role="menu"
			aria-label={submenuLabel}
			tabindex="-1"
			onkeydown={handleSubmenuKeydown}
		>
			{@render submenu?.()}
		</div>
	{/if}
</div>

<style>
	.menu-item-wrap {
		position: relative;
		display: flex;
		flex-direction: column;
	}
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
	.menu-item__submenu-arrow {
		margin-left: auto;
		flex-shrink: 0;
		color: var(--text-3);
		font-size: var(--text-base);
		line-height: 1;
	}
	.menu-item__check + .menu-item__submenu-arrow {
		margin-left: var(--space-xs);
	}
	/* Nested submenu panel: sits to the right of its parent row, flips inline
	 * (below the row) on narrow viewports via the container query fallback. */
	.menu-item__submenu {
		position: absolute;
		top: 0;
		left: 100%;
		z-index: var(--menu-z, 500);
		display: flex;
		flex-direction: column;
		gap: var(--menu-item-gap);
		min-width: var(--menu-min-width, 180px);
		margin-left: var(--space-2xs);
		padding: var(--menu-pad);
		background: var(--menu-bg);
		border: 1px solid var(--menu-border);
		border-radius: var(--menu-radius);
		box-shadow: var(--menu-shadow);
		animation: submenu-appear var(--dur-fast) var(--ease-decelerate);
	}
	@keyframes submenu-appear {
		from { opacity: 0; transform: scale(0.98) translateX(-2px); }
		to   { opacity: 1; transform: scale(1)    translateX(0); }
	}
	@media (prefers-reduced-motion: reduce) {
		.menu-item__submenu { animation: none; }
	}
	/* The global :where(...):focus-visible rule supplies the keyboard ring. */
</style>
