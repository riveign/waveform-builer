<script lang="ts">
	import type { Snippet } from 'svelte';

	let {
		variant = 'primary',
		size = 'md',
		type = 'button',
		disabled = false,
		loading = false,
		onclick,
		children,
	}: {
		variant?: 'primary' | 'secondary' | 'ghost' | 'danger';
		size?: 'sm' | 'md' | 'lg';
		type?: 'button' | 'submit' | 'reset';
		disabled?: boolean;
		loading?: boolean;
		onclick?: (e: MouseEvent) => void;
		children?: Snippet;
	} = $props();
</script>

<button
	{type}
	class="btn btn--{variant} btn--{size}"
	class:btn--loading={loading}
	disabled={disabled || loading}
	aria-busy={loading}
	{onclick}
>
	{#if loading}
		<span class="btn__spinner" aria-hidden="true"></span>
	{/if}
	<span class="btn__label">{@render children?.()}</span>
</button>

<style>
	.btn {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		gap: var(--space-sm);
		font-family: inherit;
		font-weight: var(--font-weight-medium);
		border: 1px solid transparent;
		border-radius: var(--btn-radius);
		cursor: pointer;
		transition: background var(--dur-fast) var(--ease-standard),
		            border-color var(--dur-fast) var(--ease-standard),
		            color var(--dur-fast) var(--ease-standard);
	}
	/* sizes */
	.btn--sm { padding: var(--space-xs) var(--space-md);  font-size: var(--text-xs);  }
	.btn--md { padding: var(--space-sm) var(--space-lg);  font-size: var(--text-sm);  }
	.btn--lg { padding: var(--space-md) var(--space-xl);  font-size: var(--text-base);}
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
