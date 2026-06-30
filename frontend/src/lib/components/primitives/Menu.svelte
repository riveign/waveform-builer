<script lang="ts" module>
	import type { Snippet } from 'svelte';

	/** A single actionable row in a menu. `separator` draws a divider instead. */
	export type MenuItemModel = {
		/** Sentence-case label (the visible text + accessible name). */
		label: string;
		/** Called when the item is activated (click / Enter / Space). */
		onselect?: () => void;
		/** Leading glyph/snippet — a non-color cue (icon, dot). */
		icon?: Snippet;
		/** Dim + non-interactive. */
		disabled?: boolean;
		/** Destructive tone (delete, remove). */
		danger?: boolean;
		/** Picker-style selected/check state — shows a trailing check. */
		selected?: boolean;
	};
</script>

<script lang="ts">
	import { tick } from 'svelte';
	import MenuItem from './MenuItem.svelte';

	let {
		// --- shared ---
		open = $bindable(false),
		onclose,
		/** Item-model list (picker / simple menus). Omit to use `children` instead. */
		items,
		/** Free-form menu body — render MenuItem / MenuSeparator yourself, or any
		 *  rows that carry role="menuitem". Used by the richer context menus. */
		children,
		/** Accessible name for the menu panel. */
		label = 'Menu',
		minWidth = 180,

		// --- trigger mode (anchored to a button) ---
		trigger,

		// --- context mode (free-positioned, e.g. right-click) ---
		x,
		y,
	}: {
		open?: boolean;
		onclose?: () => void;
		items?: MenuItemModel[];
		children?: Snippet;
		label?: string;
		minWidth?: number;
		trigger?: Snippet<[{ open: () => void; props: Record<string, unknown> }]>;
		x?: number;
		y?: number;
	} = $props();

	let panelEl = $state<HTMLDivElement | null>(null);
	let triggerWrapEl = $state<HTMLSpanElement | null>(null);
	let posX = $state(0);
	let posY = $state(0);

	const isContextMode = $derived(x !== undefined && y !== undefined);

	/** The role="menu" panel that currently owns focus — the root panel, or a
	 *  nested submenu when focus has moved into one. Keeps arrow nav scoped to
	 *  the active level instead of merging parent + submenu rows. */
	function activeMenuPanel(): HTMLElement | null {
		const active = document.activeElement;
		if (active instanceof HTMLElement) {
			const owner = active.closest<HTMLElement>('[role="menu"]');
			if (owner && panelEl?.contains(owner)) return owner;
		}
		return panelEl;
	}

	/** Focusable menu items in the ACTIVE (sub)menu panel, in DOM order. */
	function itemEls(): HTMLElement[] {
		const scope = activeMenuPanel();
		if (!scope) return [];
		return Array.from(
			scope.querySelectorAll<HTMLElement>(
				'[role="menuitem"]:not([disabled]):not([aria-disabled="true"]),' +
					'[role="menuitemradio"]:not([disabled]):not([aria-disabled="true"]),' +
					'[role="menuitemcheckbox"]:not([disabled]):not([aria-disabled="true"])',
			),
		).filter((el) => el.closest('[role="menu"]') === scope); // exclude deeper-nested rows
	}

	/** True when focus is inside a nested submenu rather than the root panel. */
	function inSubmenu(): boolean {
		const scope = activeMenuPanel();
		return scope !== null && scope !== panelEl;
	}

	function focusItem(index: number) {
		const els = itemEls();
		if (els.length === 0) return;
		const i = ((index % els.length) + els.length) % els.length;
		els[i].focus();
	}

	function focusFirst() {
		focusItem(0);
	}

	function close(returnFocus = true) {
		if (!open) return;
		open = false;
		onclose?.();
		if (returnFocus) {
			// Return focus to the trigger in anchored mode (a11y: focus must not be lost).
			const t = triggerWrapEl?.querySelector<HTMLElement>('button, [tabindex]');
			t?.focus();
		}
	}

	function openMenu() {
		open = true;
	}

	// Position + initial focus when opening.
	$effect(() => {
		if (!open || !panelEl) return;
		const { innerWidth, innerHeight } = window;
		const { offsetWidth: w, offsetHeight: h } = panelEl;

		if (isContextMode) {
			// Free-positioned: clamp/flip so the panel stays inside the viewport.
			posX = Math.min(x ?? 0, innerWidth - w - 8);
			posY = Math.min(y ?? 0, innerHeight - h - 8);
		} else if (triggerWrapEl) {
			// Anchored: sit under the trigger, flip up / left when near an edge.
			const r = triggerWrapEl.getBoundingClientRect();
			let top = r.bottom + 4;
			if (top + h > innerHeight - 8) top = Math.max(8, r.top - h - 4);
			let left = r.left;
			if (left + w > innerWidth - 8) left = Math.max(8, innerWidth - w - 8);
			posX = left;
			posY = top;
		}

		// Focus the first item once positioned (keyboard users land inside).
		tick().then(() => {
			if (open) focusFirst();
		});
	});

	// Dismiss on outside click + Escape; trap focus inside while open.
	$effect(() => {
		if (!open) return;

		function onPointerDown(e: MouseEvent) {
			const target = e.target as Node;
			if (panelEl?.contains(target)) return;
			if (triggerWrapEl?.contains(target)) return;
			close(false);
		}

		function onKeydown(e: KeyboardEvent) {
			const els = itemEls();
			const current = document.activeElement as HTMLElement | null;
			const idx = current ? els.indexOf(current) : -1;
			switch (e.key) {
				case 'Escape':
					// A submenu handles its own Escape (close submenu only) and
					// stops propagation; if it reaches here, focus is at the root.
					if (inSubmenu()) return;
					e.preventDefault();
					close();
					break;
				case 'ArrowDown':
					e.preventDefault();
					focusItem(idx + 1);
					break;
				case 'ArrowUp':
					e.preventDefault();
					focusItem(idx <= 0 ? els.length - 1 : idx - 1);
					break;
				case 'Home':
					e.preventDefault();
					focusItem(0);
					break;
				case 'End':
					e.preventDefault();
					focusItem(els.length - 1);
					break;
				case 'Tab':
					// Keep focus trapped within the open menu.
					e.preventDefault();
					focusItem(e.shiftKey ? idx - 1 : idx + 1);
					break;
			}
		}

		// Defer the pointer listener a tick so the opening click doesn't self-close.
		const timer = setTimeout(() => {
			document.addEventListener('mousedown', onPointerDown);
		}, 0);
		document.addEventListener('keydown', onKeydown);
		return () => {
			clearTimeout(timer);
			document.removeEventListener('mousedown', onPointerDown);
			document.removeEventListener('keydown', onKeydown);
		};
	});

	function handleItemSelect(item: MenuItemModel) {
		item.onselect?.();
		close();
	}

	const triggerProps = {
		'aria-haspopup': 'menu',
		'aria-expanded': open,
	};
</script>

{#if trigger}
	<span bind:this={triggerWrapEl} class="menu-trigger">
		{@render trigger({ open: openMenu, props: { ...triggerProps, 'aria-expanded': open } })}
	</span>
{/if}

{#if open}
	<div
		bind:this={panelEl}
		class="menu-panel"
		role="menu"
		aria-label={label}
		tabindex="-1"
		style="left: {posX}px; top: {posY}px; min-width: {minWidth}px;"
		oncontextmenu={(e) => e.preventDefault()}
	>
		{#if items}
			{#each items as item, i (item.label + i)}
				<MenuItem
					icon={item.icon}
					disabled={item.disabled}
					danger={item.danger}
					selected={item.selected}
					onselect={() => handleItemSelect(item)}
				>
					{item.label}
				</MenuItem>
			{/each}
		{:else}
			{@render children?.()}
		{/if}
	</div>
{/if}

<style>
	.menu-trigger {
		display: inline-flex;
	}
	.menu-panel {
		position: fixed;
		z-index: var(--menu-z, 500);
		display: flex;
		flex-direction: column;
		gap: var(--menu-item-gap);
		padding: var(--menu-pad);
		background: var(--menu-bg);
		border: 1px solid var(--menu-border);
		border-radius: var(--menu-radius);
		box-shadow: var(--menu-shadow);
		animation: menu-appear var(--dur-fast) var(--ease-decelerate);
	}
	@keyframes menu-appear {
		from { opacity: 0; transform: scale(0.98) translateY(-2px); }
		to   { opacity: 1; transform: scale(1)    translateY(0); }
	}
	@media (prefers-reduced-motion: reduce) {
		.menu-panel { animation: none; }
	}
</style>
