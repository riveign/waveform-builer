import type { Action } from 'svelte/action';

/**
 * Default selector for the cards a keyboard user roves between. Matches Kiku's
 * two grids: the TrackCard `role="button"` div (Related / Standalone) AND the
 * native album `<button class="card">`. Disabled buttons are skipped so a dead
 * card never becomes a focus stop.
 */
const DEFAULT_SELECTOR = '[role="button"], a[href], button:not([disabled])';

interface RovingFocusParams {
	/**
	 * CSS selector for the roving children. Defaults to {@link DEFAULT_SELECTOR},
	 * which reaches the cards in both Kiku grids (the TrackCard role="button" div
	 * lives one level under `.card-slot`, so a descendant query is required).
	 */
	selector?: string;
	/**
	 * Optional fixed column count for Up/Down strides. When omitted (the common
	 * case) the column count is measured from the live layout each keypress, so
	 * it stays correct as the grid reflows. Pass this only for a grid with a
	 * known, static column count.
	 */
	columns?: number;
}

function isVisible(el: HTMLElement): boolean {
	// offsetParent is null for display:none; size / client-rect cover the rest.
	return el.offsetWidth > 0 || el.offsetHeight > 0 || el.getClientRects().length > 0;
}

/**
 * Roving-tabindex keyboard navigation for a flat grid of activatable cards.
 *
 * The grid becomes a single tab stop: exactly one card carries `tabindex="0"`,
 * the rest `tabindex="-1"`. Arrow keys rove focus between cards — Left/Right by
 * one card (wrapping at the ends), Up/Down by one visual row (clamped), Home/End
 * to first/last. The cards keep their own `role="button"` semantics; this action
 * never imposes `role="grid"`. Activation (Enter / Space) stays on the card.
 *
 * Column count for Up/Down is read from the live layout rather than the CSS
 * template, because cards span several track-columns and reflow via container
 * queries — so the rendered column count is what we measure, not what we declare.
 *
 * Usage: `<div class="grid" use:rovingFocus> … cards … </div>`
 */
export const rovingFocus: Action<HTMLElement, RovingFocusParams | undefined> = (node, params) => {
	const selector = params?.selector ?? DEFAULT_SELECTOR;

	/**
	 * Roving cards, in DOM order, visible only. Re-read so reflow/list changes
	 * are reflected.
	 *
	 * `querySelectorAll` is descendant-wide, so the selector also matches the
	 * interactive controls NESTED inside each card (the `+` / `⋮` menu buttons and
	 * the StarRating `role="radio"` stars). Roving must land on ONE item per card,
	 * not on its inner controls — otherwise the tab stop scatters onto nested
	 * buttons and the offsetTop column-stride math counts interleaved same-row
	 * buttons. So we keep only the OUTERMOST matches: a match is dropped when it
	 * has an ancestor (still within this grid) that is ALSO a match. This is
	 * wrapper-depth-agnostic — it works whether the card is a direct child or sits
	 * under one or more wrapper elements — and it leaves the inner controls out of
	 * the roving set entirely (they stay normally Tab-focusable within the card).
	 */
	function cards(): HTMLElement[] {
		const matches = Array.from(node.querySelectorAll<HTMLElement>(selector)).filter(isVisible);
		const matchSet = new Set<HTMLElement>(matches);
		return matches.filter((el) => {
			// Walk up to (but not past) the grid container; if any ancestor is also a
			// match, this element is nested inside another card → not a roving item.
			let ancestor = el.parentElement;
			while (ancestor && ancestor !== node) {
				if (matchSet.has(ancestor)) return false;
				ancestor = ancestor.parentElement;
			}
			return true;
		});
	}

	/** Set exactly one card focusable (tabindex 0), the rest -1, and move focus there. */
	function setActive(els: HTMLElement[], idx: number, moveFocus: boolean) {
		els.forEach((el, i) => el.setAttribute('tabindex', i === idx ? '0' : '-1'));
		if (moveFocus) els[idx]?.focus();
	}

	/** Index of the currently-focused card, or -1 if focus is elsewhere. */
	function activeIndex(els: HTMLElement[]): number {
		const current = document.activeElement;
		return current instanceof HTMLElement ? els.indexOf(current) : -1;
	}

	/**
	 * Visual column count: how many leading cards share the first card's
	 * offsetTop (= the first rendered row's length). Reflow- and span-agnostic.
	 */
	function columnCount(els: HTMLElement[]): number {
		if (els.length <= 1) return els.length;
		if (params?.columns && params.columns > 0) return params.columns;
		const firstTop = els[0].offsetTop;
		let cols = 0;
		for (const el of els) {
			if (el.offsetTop === firstTop) cols++;
			else break;
		}
		return Math.max(1, cols);
	}

	/** Ensure exactly one card is a tab stop (after the list grows / shrinks). */
	function normalize() {
		const els = cards();
		if (els.length === 0) return;
		const hasStop = els.some((el) => el.getAttribute('tabindex') === '0');
		if (!hasStop) {
			// The previous tab stop was removed (or none set yet) — fall back to the
			// first card so the grid stays Tab-reachable. No focus move here; we only
			// reassign the single tab stop.
			setActive(els, 0, false);
		}
	}

	function onKeydown(e: KeyboardEvent) {
		const els = cards();
		if (els.length === 0) return;

		const idx = activeIndex(els);
		if (idx === -1) return; // focus isn't on a card — let the event pass through

		let next: number;
		switch (e.key) {
			case 'ArrowRight':
				next = idx === els.length - 1 ? 0 : idx + 1;
				break;
			case 'ArrowLeft':
				next = idx === 0 ? els.length - 1 : idx - 1;
				break;
			case 'ArrowDown': {
				const cols = columnCount(els);
				next = Math.min(idx + cols, els.length - 1);
				break;
			}
			case 'ArrowUp': {
				const cols = columnCount(els);
				next = Math.max(idx - cols, 0);
				break;
			}
			case 'Home':
				next = 0;
				break;
			case 'End':
				next = els.length - 1;
				break;
			default:
				return; // leave every other key (incl. Enter/Space activation) alone
		}

		e.preventDefault();
		setActive(els, next, true);
	}

	// Keep one tab stop in sync as cards are added / removed (Show more, dismiss,
	// sort, paging). Re-normalize rather than chase focus — focus is owned by the
	// keyboard handler above.
	const observer = new MutationObserver(() => normalize());
	observer.observe(node, { childList: true, subtree: true });

	// Set the initial tab stop after layout so offsetTop reads are valid.
	const raf = requestAnimationFrame(() => {
		const els = cards();
		if (els.length === 0) return;
		const focused = activeIndex(els);
		setActive(els, focused === -1 ? 0 : focused, false);
	});

	node.addEventListener('keydown', onKeydown);

	return {
		destroy() {
			cancelAnimationFrame(raf);
			observer.disconnect();
			node.removeEventListener('keydown', onKeydown);
		},
	};
};
