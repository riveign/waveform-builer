<script lang="ts" module>
	/** The five harmonic-move relations Kiku teaches. One distinct SHAPE each so
	 *  the signal survives colorblindness (content-conventions §4 — color is never
	 *  the only cue). Maps the keyMoveLabel / harmonicRelationship vocabularies. */
	export type HarmonyRelation = 'same' | 'up' | 'down' | 'swap' | 'clash';

	/** Sentence-case accessible label per relation — used as aria-label + tooltip,
	 *  and shown verbatim in the design-system showcase. Same meaning everywhere
	 *  (content-conventions §6). */
	export const HARMONY_RELATION_LABEL: Record<HarmonyRelation, string> = {
		same: 'Same key',
		up: 'Energy up',
		down: 'Energy down',
		swap: 'Mood switch',
		clash: 'Clashing keys',
	};

	/** Normalize the move/relationship label vocabularies onto the five relations.
	 *  Accepts keyMoveLabel() labels ("same key", "energy up/down", "mood switch",
	 *  "distant keys") and harmonicRelationship() labels ("Adjacent", "Mode switch",
	 *  "Two steps", "Distant keys", …). Returns null when it can't be classified. */
	export function toHarmonyRelation(label: string | null | undefined): HarmonyRelation | null {
		if (!label) return null;
		const l = label.toLowerCase();
		if (l.includes('same')) return 'same';
		if (l.includes('energy up')) return 'up';
		if (l.includes('energy down')) return 'down';
		if (l.includes('mood') || l.includes('mode')) return 'swap';
		if (l.includes('distant') || l.includes('clash')) return 'clash';
		// adjacent / two-steps fall back to the nearest single-direction cue.
		if (l.includes('adjacent') || l.includes('step')) return 'up';
		return null;
	}
</script>

<script lang="ts">
	import type { IconSize } from './icon-types';

	let {
		relation,
		size = 'sm',
		label,
		title,
	}: {
		/** Which of the five harmonic moves to draw. */
		relation: HarmonyRelation;
		/** One of the shared --icon-size-* steps (content-conventions §6). */
		size?: IconSize;
		/** Override the accessible name; defaults to the canonical relation label. */
		label?: string;
		/** Tooltip text; defaults to the accessible name. */
		title?: string;
	} = $props();

	const accessibleLabel = $derived(label ?? HARMONY_RELATION_LABEL[relation]);
	const tooltip = $derived(title ?? accessibleLabel);
</script>

<!-- 24×24 viewBox, currentColor fill/stroke so it inherits the chip/theme color.
     Each relation is a distinct shape (the non-color signal). -->
<svg
	class="harmony-icon harmony-icon--{size}"
	viewBox="0 0 24 24"
	role="img"
	aria-label={accessibleLabel}
	stroke="currentColor"
	stroke-linecap="round"
	stroke-linejoin="round"
	fill="none"
>
	<title>{tooltip}</title>
	{#if relation === 'same'}
		<!-- equals — two parallel bars -->
		<line x1="6" y1="9" x2="18" y2="9" />
		<line x1="6" y1="15" x2="18" y2="15" />
	{:else if relation === 'up'}
		<!-- upward triangle (filled) -->
		<path d="M12 5 L19 18 H5 Z" fill="currentColor" stroke="none" />
	{:else if relation === 'down'}
		<!-- downward triangle (filled) -->
		<path d="M12 19 L5 6 H19 Z" fill="currentColor" stroke="none" />
	{:else if relation === 'swap'}
		<!-- two opposing horizontal arrows (mode/mood switch) -->
		<path d="M16 8 H6 m3 -3 l-3 3 l3 3" />
		<path d="M8 16 H18 m-3 -3 l3 3 l-3 3" />
	{:else}
		<!-- clash — an X cross -->
		<line x1="6" y1="6" x2="18" y2="18" />
		<line x1="18" y1="6" x2="6" y2="18" />
	{/if}
</svg>

<style>
	.harmony-icon {
		display: inline-block;
		flex-shrink: 0;
		vertical-align: middle;
		/* color comes from the parent (chip/theme) via currentColor. */
		stroke-width: var(--icon-stroke);
	}
	.harmony-icon--sm {
		width: var(--icon-size-sm);
		height: var(--icon-size-sm);
	}
	.harmony-icon--md {
		width: var(--icon-size-md);
		height: var(--icon-size-md);
	}
	.harmony-icon--lg {
		width: var(--icon-size-lg);
		height: var(--icon-size-lg);
	}
</style>
