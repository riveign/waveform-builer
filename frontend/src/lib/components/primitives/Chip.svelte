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
	/** Presentational mode — orthogonal to `variant`/`color`.
	 *  - `box`           : default border + surface fill (current behavior).
	 *  - `plain`         : bare (colored) text, no box / bg / border.
	 *  - `tone`          : filled soft-tint badge derived from the meaning color.
	 *  - `clickToRemove` : the whole chip is a remove <button> (distinct from the
	 *                      `removable` prop, which adds a secondary inline × button). */
	export type ChipMode = 'box' | 'plain' | 'tone' | 'clickToRemove';
</script>

<script lang="ts">
	import type { Snippet } from 'svelte';
	import MetronomeIcon from './MetronomeIcon.svelte';

	let {
		variant = 'neutral',
		value,
		size = 'md',
		mode = 'box',
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
		/** Presentational mode — box (default), plain, tone, or clickToRemove. */
		mode?: ChipMode;
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

	// The bpm variant always leads with the metronome glyph instead of a literal
	// "BPM" text label (saves space; the glyph + a11y label carry the meaning).
	// A caller-supplied `icon` snippet wins; otherwise the bpm chip auto-renders
	// the metronome. The chip's title still carries the tempo meaning for AT.
	const showMetronome = $derived(variant === 'bpm' && !icon);
	const bpmTitle = $derived(variant === 'bpm' ? (title ?? 'Beats per minute') : title);

	// clickToRemove turns the WHOLE chip into a remove button. It is mutually
	// exclusive with the `removable` inline × button — the whole-chip click
	// already removes, so a second control would be redundant/confusing.
	const isClickToRemove = $derived(mode === 'clickToRemove');
	const showInlineRemove = $derived(removable && !isClickToRemove);
</script>

{#snippet body()}
	{#if icon}
		<span class="chip__icon" aria-hidden="true">{@render icon()}</span>
	{:else if showMetronome}
		<span class="chip__icon"><MetronomeIcon size="sm" /></span>
	{/if}
	<span class="chip__label">
		{#if children}{@render children()}{:else}{display}{/if}
	</span>
	{#if showInlineRemove}
		<button
			type="button"
			class="chip__remove"
			aria-label={removeLabel}
			title={removeLabel}
			onclick={onremove}
		>
			×
		</button>
	{:else if isClickToRemove}
		<span class="chip__x" aria-hidden="true">×</span>
	{/if}
{/snippet}

{#if isClickToRemove}
	<button
		type="button"
		class="chip chip--{variant} chip--{size} chip--tone-{tone} chip--mode-{mode}"
		class:chip--colored={Boolean(color)}
		class:chip--empty={isEmpty && !children}
		style:--chip-color={color ?? null}
		title={bpmTitle}
		aria-label={removeLabel}
		onclick={onremove}
	>
		{@render body()}
	</button>
{:else}
	<span
		class="chip chip--{variant} chip--{size} chip--tone-{tone} chip--mode-{mode}"
		class:chip--colored={Boolean(color)}
		class:chip--empty={isEmpty && !children}
		style:--chip-color={color ?? null}
		title={bpmTitle}
	>
		{@render body()}
	</span>
{/if}

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

	/* genre — descriptive identity metadata. Gets its own visible tinted treatment
	 * so it reads as clearly as the colored key/energy chips instead of fading into
	 * the surface. Fully tokenized (cerceta re-points --accent-text). */
	.chip--genre {
		background: var(--chip-genre-bg);
		color: var(--chip-genre-fg);
		border-color: var(--chip-genre-border);
	}
	.chip--genre:hover {
		background: var(--chip-genre-bg);
	}

	/* --- mode=plain — bare (colored) text, no box / bg / border / padding.
	 * Formalizes the genre-colored-text + colored list-cell pattern. The label
	 * still carries the meaning; color is paired with the always-present text. */
	.chip--mode-plain {
		background: transparent;
		border-color: transparent;
		padding: var(--chip-plain-pad);
		height: auto;
	}
	.chip--mode-plain:hover {
		background: transparent;
	}
	/* colored plain chips flow the meaning color to the label (all colorable
	 * variants, not just the box-colored set above). */
	.chip--mode-plain.chip--colored .chip__label {
		color: var(--chip-color);
	}
	/* status-driven plain text reuses the tone color path on neutral/level. */
	.chip--mode-plain.chip--tone-success .chip__label {
		color: var(--score-excellent);
	}
	.chip--mode-plain.chip--tone-warn .chip__label {
		color: var(--score-good);
	}
	.chip--mode-plain.chip--tone-danger .chip__label {
		color: var(--destructive);
	}
	.chip--mode-plain.chip--tone-accent .chip__label {
		color: var(--accent-text);
	}

	/* --- mode=tone — a FILLED soft-tint badge (not an outline). Generalizes the
	 * genre recipe: tint the flowing meaning color (--chip-color, → accent) into
	 * the surface, use it as fg, and a matching soft border. Status tones reuse
	 * the same recipe by feeding their token into --chip-color at the call site,
	 * or fall back to the accent tint here. */
	.chip--mode-tone {
		background: var(--chip-tone-bg);
		color: var(--chip-tone-fg);
		border-color: var(--chip-tone-border);
	}
	.chip--mode-tone:hover {
		background: var(--chip-tone-bg);
	}
	/* tone keeps the label readable in the meaning color even on colorable
	 * variants whose box rules would otherwise re-tint only the label. */
	.chip--mode-tone.chip--colored .chip__label {
		color: var(--chip-tone-fg);
	}

	/* --- mode=clickToRemove — the WHOLE chip is the remove button. Reset the
	 * UA button chrome so it matches the span chip, then add affordances. The
	 * trailing × is decorative (the accessible name comes from aria-label). */
	.chip--mode-clickToRemove {
		position: relative; /* anchors the invisible ≥44px hit-area overlay (F2) */
		font-family: inherit;
		font-weight: var(--font-weight-medium);
		text-align: inherit;
		cursor: pointer;
		appearance: none;
		-webkit-appearance: none;
	}
	/* Touch-target guard (F2): a clickToRemove chip's visible box is only
	 * 24–32px tall, below the 44px minimum tap target. Expand the *interactive*
	 * area to ≥44×44 with a transparent centered overlay WITHOUT growing the
	 * visual chip — the box still renders at its chip height; only the hittable
	 * region grows. The overlay is the button's own ::before so it inherits the
	 * click, stays keyboard-irrelevant (decorative), and never reflows layout. */
	.chip--mode-clickToRemove::before {
		content: '';
		position: absolute;
		top: 50%;
		left: 50%;
		transform: translate(-50%, -50%);
		min-width: 44px;
		min-height: 44px;
		width: 100%;
		height: 100%;
		/* invisible — purely a hit-slop, no paint */
	}
	.chip--mode-clickToRemove:hover {
		background: var(--surface-hover);
	}
	/* keep the filled/plain hover intent when combined with another mode class. */
	.chip--mode-clickToRemove.chip--mode-tone:hover {
		background: var(--chip-tone-bg);
	}
	.chip__x {
		display: inline-flex;
		align-items: center;
		flex-shrink: 0;
		margin-right: calc(-1 * var(--space-2xs));
		color: var(--text-3);
		font-size: var(--text-md);
		line-height: 1;
	}
	.chip--mode-clickToRemove:hover .chip__x {
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
