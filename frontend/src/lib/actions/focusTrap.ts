import type { Action } from 'svelte/action';

/**
 * Selector for the elements a keyboard user can land on inside a dialog.
 * Mirrors the focusable set the `Menu` primitive traps within, broadened from
 * menu rows to the full set of dialog controls (buttons, links, fields, and any
 * explicitly `tabindex`-ed node), while skipping disabled / hidden / -1 nodes.
 */
const FOCUSABLE_SELECTOR = [
	'a[href]',
	'button:not([disabled])',
	'input:not([disabled])',
	'select:not([disabled])',
	'textarea:not([disabled])',
	'[tabindex]:not([tabindex="-1"])',
].join(',');

function isVisible(el: HTMLElement): boolean {
	// offsetParent is null for display:none (and fixed elements need a size check).
	return el.offsetWidth > 0 || el.offsetHeight > 0 || el.getClientRects().length > 0;
}

/**
 * Focus-trap action for bespoke (non-native-`<dialog>`) modals.
 *
 * On mount it remembers the element that had focus (the opener), then moves
 * focus into the dialog. While mounted it traps Tab / Shift-Tab so focus cannot
 * escape behind the backdrop. On destroy (the modal closing / unmounting) it
 * returns focus to the opener — the same in/trap/return model the `Menu`
 * primitive already implements.
 *
 * Usage: `<div role="dialog" use:focusTrap> … </div>`
 */
export const focusTrap: Action<HTMLElement> = (node) => {
	// Remember who opened us so focus can return there on close (a11y: focus
	// must not be lost). Guard the type — activeElement can be null or non-HTML.
	const active = document.activeElement;
	const opener = active instanceof HTMLElement ? active : null;

	/** Focusable controls inside the dialog, in DOM order, visible + enabled. */
	function focusables(): HTMLElement[] {
		return Array.from(node.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR)).filter(isVisible);
	}

	// Move focus into the dialog: first control if any, else the container.
	// The container must be focusable for the fallback, so ensure a tabindex.
	function focusInside() {
		const els = focusables();
		if (els.length > 0) {
			els[0].focus();
			return;
		}
		if (!node.hasAttribute('tabindex')) {
			node.setAttribute('tabindex', '-1');
		}
		node.focus();
	}

	function onKeydown(e: KeyboardEvent) {
		if (e.key !== 'Tab') return;
		const els = focusables();
		if (els.length === 0) {
			// Nothing to cycle to — keep focus on the container.
			e.preventDefault();
			node.focus();
			return;
		}

		const current = document.activeElement;
		const idx = current instanceof HTMLElement ? els.indexOf(current) : -1;

		// Wrap at both ends, matching Menu's focusItem() modular wrap.
		let next: number;
		if (e.shiftKey) {
			next = idx <= 0 ? els.length - 1 : idx - 1;
		} else {
			next = idx === els.length - 1 ? 0 : idx + 1;
		}
		e.preventDefault();
		els[next].focus();
	}

	// Defer initial focus a tick so the dialog content is laid out first
	// (mirrors Menu's tick()-then-focus on open).
	const raf = requestAnimationFrame(focusInside);
	node.addEventListener('keydown', onKeydown);

	return {
		destroy() {
			cancelAnimationFrame(raf);
			node.removeEventListener('keydown', onKeydown);
			// Return focus to the opener if it's still in the document.
			if (opener && document.contains(opener)) {
				opener.focus();
			}
		},
	};
};
