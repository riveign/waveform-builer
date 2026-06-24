<script lang="ts">
	import type { Snippet } from 'svelte';

	let {
		gap,
		condensed = false,
		children,
	}: {
		/** Override grid gutter, e.g. "var(--space-xl)". */
		gap?: string;
		/** Use the 16px condensed gutter. */
		condensed?: boolean;
		children?: Snippet;
	} = $props();
</script>

<div
	class="grid-12"
	class:grid-12--condensed={condensed}
	style={gap ? `--grid-gutter: ${gap}` : undefined}
>
	{@render children?.()}
</div>

<!-- presentational only; children supply .col-span-N. .grid-12 lives in utilities.css -->
