/**
 * Reordering a set, without a mouse — shared by every layout that can edit.
 *
 * Drag-and-drop is fine for a neighbouring swap; for anything further down a
 * long set it fights the scroller. So a track can also be nudged one slot with
 * ↑/↓, or lifted with Space and walked to its new home with the arrow keys.
 *
 * This lived inside `SetTimeline` until the Ledger needed it too. The keyboard
 * contract is the fiddly part — lift, walk, drop, cancel, and keeping focus on
 * the control the DJ is holding as it moves out from under them — and two
 * copies of it would drift. One copy, two callers.
 *
 * The moves land in the store, which is what every layout renders from, so a
 * move shows up immediately and the write follows behind it.
 */

import { tick } from 'svelte';

/** The slice of the set-tracks store this needs. */
export interface ReorderTarget {
	move(from: number, to: number): boolean;
	flush(): Promise<void>;
}

export interface ReorderOptions {
	store: ReorderTarget;
	/** The element the controls live in — focus is re-found by query inside it. */
	getListEl: () => HTMLElement | undefined;
	/** True while another write (a removal) is in flight and must not be raced. */
	isBusy?: () => boolean;
}

export function createReorder({ store, getListEl, isBusy }: ReorderOptions) {
	/** Index of the track currently lifted for a keyboard move, or null. */
	let liftedIndex = $state<number | null>(null);
	/** Where it was picked up from, so Escape can walk it back. */
	let liftOrigin: number | null = null;
	/** Set while we move focus ourselves, so `blur` doesn't read it as a drop. */
	let refocusing = false;

	/** Keep the keyboard on the control the DJ just used, now at its new index. */
	async function refocus(selector: string, fallback?: string) {
		refocusing = true;
		await tick();
		const pick = (sel: string) => {
			const el = getListEl()?.querySelector<HTMLButtonElement>(sel);
			return el && !el.disabled ? el : null;
		};
		(pick(selector) ?? (fallback ? pick(fallback) : null))?.focus();
		refocusing = false;
	}

	async function nudge(index: number, dir: -1 | 1) {
		if (liftedIndex !== null || isBusy?.()) return;
		if (!store.move(index, index + dir)) return;
		const to = index + dir;
		const kind = dir === -1 ? 'up' : 'down';
		// The button may be disabled at the end of its travel; fall back to its twin.
		await refocus(
			`[data-move="${kind}"][data-idx="${to}"]`,
			`[data-move="${dir === -1 ? 'down' : 'up'}"][data-idx="${to}"]`,
		);
	}

	function dropLifted() {
		liftedIndex = null;
		liftOrigin = null;
		void store.flush();
	}

	function keydown(e: KeyboardEvent, index: number) {
		// Stop these from bubbling into svelte-dnd-action's own keyboard drag.
		if (e.key === ' ' || e.key === 'Enter') {
			e.preventDefault();
			e.stopPropagation();
			if (liftedIndex === null) {
				liftedIndex = index;
				liftOrigin = index;
			} else {
				dropLifted();
			}
		} else if (liftedIndex !== null && (e.key === 'ArrowUp' || e.key === 'ArrowDown')) {
			e.preventDefault();
			e.stopPropagation();
			const from = liftedIndex;
			const to = from + (e.key === 'ArrowUp' ? -1 : 1);
			if (store.move(from, to)) {
				liftedIndex = to;
				refocus(`[data-handle][data-idx="${to}"]`);
			}
		} else if (e.key === 'Escape' && liftedIndex !== null) {
			e.preventDefault();
			e.stopPropagation();
			// Walk it back where it was picked up from.
			if (liftOrigin !== null) store.move(liftedIndex, liftOrigin);
			liftedIndex = null;
			liftOrigin = null;
			void store.flush();
		}
	}

	/** Leaving the handle drops whatever it was carrying. */
	function blur() {
		if (refocusing || liftedIndex === null) return;
		dropLifted();
	}

	return {
		get liftedIndex() {
			return liftedIndex;
		},
		nudge,
		keydown,
		blur,
	};
}
