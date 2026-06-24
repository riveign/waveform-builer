<script lang="ts" module>
	export type ChipVariant =
		| 'neutral'
		| 'genre'
		| 'key'
		| 'bpm'
		| 'energy'
		| 'harmony'
		| 'vibe'
		| 'level';
	export type ChipSize = 'sm' | 'md';
	export type ChipTone = 'default' | 'success' | 'warn' | 'danger' | 'accent';
</script>

<script lang="ts">
	import type { Snippet } from 'svelte';

	let {
		variant = 'neutral',
		value,
		size = 'md',
		tone = 'default',
		color,
		icon,
		removable = false,
		onremove,
		removeLabel = 'Remove',
		title,
		children,
	}: {
		/** Primary axis — selects the token mapping and the kind of value shown. */
		variant?: ChipVariant;
		/** The single canonical formatted value (BPM integer, "8A", "Peak"). */
		value?: string | number;
		size?: ChipSize;
		/** Secondary status axis for neutral/level chips (filter type, ownership). */
		tone?: ChipTone;
		/** Dynamic color (Camelot key, zone, vibe HSL). Flows in from the caller so
		 *  the chip stays presentational and never hardcodes hex. */
		color?: string;
		/** Leading glyph/snippet — harmony move, vibe dot, etc. (a non-color cue). */
		icon?: Snippet;
		removable?: boolean;
		onremove?: () => void;
		/** Accessible name for the remove control. */
		removeLabel?: string;
		/** Full value for truncated labels (content-conventions §2). */
		title?: string;
		/** Structured content fallback when `value` isn't a single string (e.g. A → B). */
		children?: Snippet;
	} = $props();

	// Missing data renders the canonical muted em dash, never blank/null/0.
	const display = $derived(
		value === undefined || value === null || value === '' ? '—' : String(value),
	);
	const isEmpty = $derived(value === undefined || value === null || value === '');
</script>

<span
	class="chip chip--{variant} chip--{size} chip--tone-{tone}"
	class:chip--colored={Boolean(color)}
	class:chip--empty={isEmpty && !children}
	style:--chip-color={color ?? null}
	{title}
>
	{#if icon}
		<span class="chip__icon" aria-hidden="true">{@render icon()}</span>
	{/if}
	<span class="chip__label">
		{#if children}{@render children()}{:else}{display}{/if}
	</span>
	{#if removable}
		<button
			type="button"
			class="chip__remove"
			aria-label={removeLabel}
			title={removeLabel}
			onclick={onremove}
		>
			×
		</button>
	{/if}
</span>

<style>
	.chip {
		display: inline-flex;
		align-items: center;
		gap: var(--chip-gap);
		box-sizing: border-box;
		max-width: 100%;
		border: 1px solid transparent;
		border-radius: var(--chip-radius);
		background: var(--chip-bg);
		color: var(--chip-fg);
		font-family: inherit;
		font-weight: var(--font-weight-medium);
		line-height: 1;
		white-space: nowrap;
		/* Sentence case everywhere — no text-transform (content-conventions §1). */
		transition:
			background var(--dur-fast) var(--ease-standard),
			border-color var(--dur-fast) var(--ease-standard),
			color var(--dur-fast) var(--ease-standard);
	}

	/* sizes — fixed height owns the box; size differs by padding + font only. */
	.chip--sm {
		height: var(--chip-height-sm);
		padding: 0 var(--chip-pad-x-sm);
		font-size: var(--chip-font-sm);
	}
	.chip--md {
		height: var(--chip-height-md);
		padding: 0 var(--chip-pad-x-md);
		font-size: var(--chip-font-md);
	}

	/* The label is the truncatable part; short numerics (bpm/key) never wrap and
	 * sit alone, so they always fit. */
	.chip__label {
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
		min-width: 0;
	}
	.chip--empty .chip__label {
		color: var(--text-4);
	}

	/* leading glyph — single size step, shares the chip color when colored. */
	.chip__icon {
		display: inline-flex;
		align-items: center;
		flex-shrink: 0;
		font-size: 1em;
		line-height: 1;
	}

	/* --- Dynamic color (key / energy / harmony / vibe) ---
	 * The caller passes a meaning-derived color; the chip tints text by it and
	 * pairs it with the always-present label/glyph (color is never the only cue). */
	.chip--colored.chip--key .chip__label,
	.chip--colored.chip--energy .chip__label,
	.chip--colored.chip--harmony .chip__label,
	.chip--colored.chip--level .chip__label {
		color: var(--chip-color);
	}
	.chip--colored.chip--harmony {
		border-color: var(--chip-color);
	}
	/* vibe — the dot carries the dynamic color, the descriptor word stays readable. */
	.chip--vibe {
		border-color: var(--border-subtle);
		color: var(--text-1);
	}

	/* --- bpm delta — signed value, colored by the ±6% tension rule.
	 * Callers pass tone="warn" beyond ±6%, default within. --- */
	.chip--bpm.chip--tone-default {
		color: var(--bpm-delta-neutral);
	}
	.chip--bpm.chip--tone-warn {
		color: var(--bpm-delta-warn);
	}

	/* --- tone (status / filter type axis, mainly for neutral + level) --- */
	.chip--tone-success.chip--neutral,
	.chip--tone-success.chip--level {
		color: var(--score-excellent);
	}
	.chip--tone-warn.chip--neutral,
	.chip--tone-warn.chip--level {
		color: var(--score-good);
	}
	.chip--tone-danger.chip--neutral,
	.chip--tone-danger.chip--level {
		color: var(--destructive);
	}
	.chip--tone-accent.chip--neutral {
		color: var(--accent-text);
	}

	/* --- interactive (removable) states ---
	 * Hover shifts the surface; the remove control is a real, focusable button. */
	.chip:hover {
		background: var(--surface-hover);
	}
	.chip__remove {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		flex-shrink: 0;
		/* ≥ the chip height so the keyboard/touch target meets ~min size (§5). */
		width: var(--chip-height-sm);
		height: var(--chip-height-sm);
		margin-right: calc(-1 * var(--space-xs));
		padding: 0;
		border: none;
		border-radius: var(--radius-xs);
		background: transparent;
		color: var(--text-3);
		font-size: var(--text-md);
		line-height: 1;
		cursor: pointer;
		transition: color var(--dur-fast) var(--ease-standard),
			background var(--dur-fast) var(--ease-standard);
	}
	.chip__remove:hover {
		color: var(--text-1);
		background: var(--surface-active);
	}
	/* The global :where(...):focus-visible rule (tokens.semantic.css) supplies the
	 * ring on the remove button. It is keyboard-reachable, not hover-only. */
</style>
