import { tick } from 'svelte';

/**
 * Keyboard focus across the library fold.
 *
 * Folding the library makes one half `inert`, which silently drops focus to
 * <body>. Whoever triggers the fold hands focus to the matching control on the
 * other side — once the DOM has flipped, so the target is focusable.
 */

export const RAIL_TOGGLE = '[data-rail="toggle"] button';
export const RAIL_SEARCH = '[data-rail="search"] button';
export const LIBRARY_TOGGLE = '[data-sidebar-toggle] button';

export async function focusAfterFold(selector: string): Promise<void> {
	await tick();
	document.querySelector<HTMLElement>(selector)?.focus();
}
