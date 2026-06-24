<script lang="ts">
	import type { Snippet } from 'svelte';

	let {
		gap,
		children,
	}: {
		/** Any --space-* value, e.g. "var(--space-lg)" or "16px". Defaults to .stack's 8px. */
		gap?: string;
		children?: Snippet;
	} = $props();
</script>

<div class="stack" style={gap ? `--stack-gap: ${gap}` : undefined}>
	{@render children?.()}
</div>

<!-- presentational only: no role, not focusable; .stack class lives in utilities.css -->
