<script lang="ts" module>
	export type SegmentOption<T extends string = string> = {
		/** The value reported back via `onchange` and compared against `value`. */
		value: T;
		/** Visible label (sentence case — content-conventions §1). */
		label: string;
		/** Optional keyboard-shortcut hint shown muted after the label (e.g. `1`). */
		shortcut?: string;
	};
</script>

<script lang="ts" generics="T extends string">
	let {
		options,
		value,
		onchange,
		ariaLabel,
	}: {
		/** The mutually-exclusive choices, rendered left-to-right as one control. */
		options: SegmentOption<T>[];
		/** The currently-selected value (exactly one). */
		value: T;
		/** Fired when a different segment is chosen (click or keyboard). */
		onchange: (value: T) => void;
		/** Names the group for AT (e.g. "Workspace views"). */
		ariaLabel: string;
	} = $props();

	let buttons = $state<HTMLButtonElement[]>([]);

	const activeIndex = $derived(Math.max(0, options.findIndex((o) => o.value === value)));

	/** Roving-tablist keyboard model: arrows/Home/End move + select, focus follows. */
	function handleKeydown(e: KeyboardEvent) {
		const last = options.length - 1;
		let next = -1;
		if (e.key === 'ArrowRight' || e.key === 'ArrowDown') next = activeIndex === last ? 0 : activeIndex + 1;
		else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') next = activeIndex === 0 ? last : activeIndex - 1;
		else if (e.key === 'Home') next = 0;
		else if (e.key === 'End') next = last;
		else return;

		e.preventDefault();
		const opt = options[next];
		if (opt) {
			onchange(opt.value);
			buttons[next]?.focus();
		}
	}
</script>

<div class="segmented" role="tablist" aria-label={ariaLabel}>
	{#each options as opt, i (opt.value)}
		<button
			bind:this={buttons[i]}
			role="tab"
			type="button"
			class="segment"
			class:active={opt.value === value}
			aria-selected={opt.value === value}
			tabindex={opt.value === value ? 0 : -1}
			onclick={() => onchange(opt.value)}
			onkeydown={handleKeydown}
		>
			{opt.label}
			{#if opt.shortcut}<span class="segment__shortcut">{opt.shortcut}</span>{/if}
		</button>
	{/each}
</div>

<style>
	.segmented {
		display: flex;
		align-items: stretch;
	}

	/* A segment is an underline-active tab: the active one reads via a weight bump
	   + an accent underline (non-color cues) reinforced by the accent text color. */
	.segment {
		padding: var(--space-md) var(--space-2xl);
		font-size: var(--text-base);
		font-family: inherit;
		font-weight: var(--font-weight-regular);
		color: var(--text-2);
		background: transparent;
		border: none;
		border-bottom: 2px solid transparent;
		cursor: pointer;
		white-space: nowrap;
		transition: color var(--dur-fast) var(--ease-standard),
		            background var(--dur-fast) var(--ease-standard),
		            border-color var(--dur-fast) var(--ease-standard);
	}

	.segment:hover {
		color: var(--text-1);
		background: var(--surface-hover);
	}

	.segment.active {
		color: var(--accent-text);
		font-weight: var(--font-weight-semibold);
		border-bottom-color: var(--accent);
	}

	.segment__shortcut {
		font-size: var(--text-2xs);
		color: var(--text-4);
		margin-left: var(--space-xs);
		opacity: 0.6;
	}
	/* The global :where(...):focus-visible rule supplies the keyboard ring. */
</style>
