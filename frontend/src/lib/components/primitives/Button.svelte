<script lang="ts" module>
	export type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger';
	export type ButtonSize = 'sm' | 'md' | 'lg';
</script>

<script lang="ts">
	import type { Snippet } from 'svelte';

	let {
		variant = 'primary',
		size = 'md',
		type = 'button',
		disabled = false,
		loading = false,
		iconOnly = false,
		shape = 'default',
		pressed = undefined,
		ariaLabel = undefined,
		title = undefined,
		onclick,
		icon,
		children,
	}: {
		variant?: ButtonVariant;
		size?: ButtonSize;
		type?: 'button' | 'submit' | 'reset';
		disabled?: boolean;
		loading?: boolean;
		/** Square icon-only button. Renders the `icon` snippet; an accessible name
		 *  (`ariaLabel`) is REQUIRED — a dev-time assertion fires if it's missing. */
		iconOnly?: boolean;
		/** `round` pill-circles an icon-only button (transport controls). Ignored
		 *  for text buttons, which keep the standard `--btn-radius`. */
		shape?: 'default' | 'round';
		/** Toggle capability. When set (true/false), the button advertises
		 *  `aria-pressed` and renders a visible selected state (weight + fill +
		 *  underline — never color alone, so it reads without color too). */
		pressed?: boolean;
		/** Accessible name. Mandatory for icon-only buttons (no visible text). */
		ariaLabel?: string;
		/** Native hover tooltip — preserves the transport/keyboard-hint affordance. */
		title?: string;
		onclick?: (e: MouseEvent) => void;
		/** Icon-only glyph/SVG content. */
		icon?: Snippet;
		children?: Snippet;
	} = $props();

	// Icon-only buttons MUST carry an accessible name (content-conventions §6).
	if (import.meta.env.DEV) {
		$effect(() => {
			if (iconOnly && !ariaLabel) {
				console.error(
					'[Button] iconOnly requires an `ariaLabel` — an icon-only button has no visible text and is unreachable for screen readers.',
				);
			}
		});
	}

	const isToggle = $derived(pressed !== undefined);
</script>

<button
	{type}
	class="btn btn--{variant} btn--{size}"
	class:btn--loading={loading}
	class:btn--icon={iconOnly}
	class:btn--round={iconOnly && shape === 'round'}
	class:btn--pressed={isToggle && pressed}
	disabled={disabled || loading}
	aria-busy={loading}
	aria-label={ariaLabel}
	aria-pressed={isToggle ? pressed : undefined}
	{title}
	{onclick}
>
	{#if loading}
		<span class="btn__spinner" aria-hidden="true"></span>
	{/if}
	{#if iconOnly}
		<span class="btn__icon" aria-hidden="true">{@render icon?.()}</span>
	{:else}
		<span class="btn__label">{@render children?.()}</span>
	{/if}
</button>

<style>
	.btn {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		gap: var(--space-sm);
		/* Single fixed control height for all sizes; centered content + border-box
		   means font-size/horizontal padding can't change the box height. */
		height: var(--btn-height);
		box-sizing: border-box;
		line-height: 1;
		font-family: inherit;
		font-weight: var(--font-weight-medium);
		border: 1px solid transparent;
		border-radius: var(--btn-radius);
		cursor: pointer;
		transition: background var(--dur-fast) var(--ease-standard),
		            border-color var(--dur-fast) var(--ease-standard),
		            color var(--dur-fast) var(--ease-standard);
	}
	/* sizes — vertical padding is 0; the fixed height + centering owns the box.
	   Sizes differ only by horizontal padding and font-size. */
	.btn--sm { padding: 0 var(--space-md);  font-size: var(--text-xs);  }
	.btn--md { padding: 0 var(--space-lg);  font-size: var(--text-sm);  }
	.btn--lg { padding: 0 var(--space-xl);  font-size: var(--text-base);}

	/* icon-only — square per size tier (width = the fixed control height family).
	   All tiers clear the ≈32–36px target (content-conventions §5): sm 32, md/lg 36. */
	.btn--icon { padding: 0; aspect-ratio: 1; }
	.btn--icon.btn--sm { width: 32px; height: 32px; }
	.btn--icon.btn--md { width: 36px; height: 36px; }
	.btn--icon.btn--lg { width: 40px; height: 40px; }
	.btn--round { border-radius: var(--radius-full); }
	.btn__icon {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		font-size: var(--text-md);
		line-height: 1;
	}
	.btn--icon.btn--lg .btn__icon { font-size: var(--text-lg); }

	/* variants */
	.btn--primary {
		background: var(--accent);
		color: var(--on-accent);
	}
	.btn--primary:hover:not(:disabled) { background: var(--accent-hover); }
	.btn--primary:active:not(:disabled) { background: var(--accent-pressed); }

	.btn--secondary {
		background: var(--surface-3);
		color: var(--text-1);
		border-color: var(--border-default);
	}
	.btn--secondary:hover:not(:disabled) { background: var(--surface-hover); }
	.btn--secondary:active:not(:disabled) { background: var(--surface-active); }

	.btn--ghost {
		background: transparent;
		color: var(--text-2);
	}
	.btn--ghost:hover:not(:disabled) { background: var(--surface-hover); color: var(--text-1); }

	.btn--danger {
		background: var(--destructive);
		color: #FFFFFF;
	}
	.btn--danger:hover:not(:disabled) { filter: brightness(1.1); }

	.btn:disabled { opacity: 0.5; cursor: not-allowed; }

	/* ── Toggle / pressed ──────────────────────────────────────────────────────
	   Selected state reads WITHOUT color (content-conventions §4): a font-weight
	   bump + an underline carry the meaning; the surface/border shift is the
	   colored reinforcement, never the only signal. */
	.btn--pressed { font-weight: var(--font-weight-semibold); }
	.btn--pressed .btn__label {
		text-decoration: underline;
		text-decoration-thickness: 2px;
		text-underline-offset: 3px;
	}
	/* ghost is the canonical toggle surface (segmented options) — pressed fills it
	   with the raised surface + a strong border so it reads as the chosen one. */
	.btn--ghost.btn--pressed {
		background: var(--surface-active);
		color: var(--text-1);
		border-color: var(--border-strong);
	}
	.btn--secondary.btn--pressed {
		background: var(--surface-active);
		border-color: var(--border-strong);
	}
	/* icon-only toggles can't underline a label — the pressed surface + a filled
	   accent foreground carry it (still paired with the surface shift, not color
	   alone, since the glyph also gains weight via the accent ramp). */
	.btn--icon.btn--pressed {
		background: var(--surface-active);
		color: var(--accent-text);
		border: 1px solid var(--border-strong);
	}

	/* loading spinner */
	.btn__spinner {
		width: 0.85em; height: 0.85em;
		border: 2px solid currentColor;
		border-top-color: transparent;
		border-radius: var(--radius-full);
		animation: btn-spin 0.7s linear infinite;
	}
	@keyframes btn-spin { to { transform: rotate(360deg); } }
	@media (prefers-reduced-motion: reduce) {
		.btn__spinner { animation: none; }
	}
	/* The global :where(...):focus-visible rule (tokens.semantic.css) supplies the ring. */
</style>
