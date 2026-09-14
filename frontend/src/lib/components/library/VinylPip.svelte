<script lang="ts">
	let {
		position = null,
		record = null,
		href = null,
	}: {
		/** The side printed on the label — "A1", "B2". */
		position?: string | null;
		/** For a file you also own on vinyl: the record it's on. */
		record?: string | null;
		/** Set on a file's pip — opens that record on the Shelf. */
		href?: string | null;
	} = $props();

	const tip = $derived(
		record
			? `Also on vinyl — ${record}${position ? `, side ${position}` : ''}`
			: position
				? `On vinyl — side ${position}`
				: 'On vinyl',
	);
</script>

{#snippet disc()}
	<svg viewBox="0 0 16 16" width="13" height="13" aria-hidden="true">
		<circle cx="8" cy="8" r="7" fill="none" stroke="currentColor" stroke-width="1.4" />
		<circle cx="8" cy="8" r="3.2" fill="none" stroke="currentColor" stroke-width="1" opacity="0.6" />
		<circle cx="8" cy="8" r="1.1" fill="currentColor" />
	</svg>
	{#if position}<span class="vinyl-pip__side">{position}</span>{/if}
{/snippet}

{#if href}
	<a
		class="vinyl-pip vinyl-pip--twin"
		{href}
		title={tip}
		aria-label={tip}
		onclick={(e) => e.stopPropagation()}
		ondblclick={(e) => e.stopPropagation()}
	>
		{@render disc()}
	</a>
{:else}
	<span class="vinyl-pip" title={tip} role="img" aria-label={tip}>
		{@render disc()}
	</span>
{/if}
<style>
	.vinyl-pip {
		display: inline-flex;
		align-items: center;
		gap: var(--space-2xs);
		flex-shrink: 0;
		margin-right: var(--space-xs);
		color: var(--text-dim);
		vertical-align: -2px;
	}
	/* A file you also own on vinyl: the lilac says "the other format", and it's a
	   way to the record rather than a label. */
	.vinyl-pip--twin {
		color: var(--zone-build);
		text-decoration: none;
		border-radius: var(--radius-xs);
	}
	.vinyl-pip--twin:hover { color: var(--text-1); }
	.vinyl-pip--twin:focus-visible { outline: 2px solid var(--accent); outline-offset: 1px; }
	.vinyl-pip__side {
		font-size: var(--font-size-xs);
		font-variant-numeric: tabular-nums;
		letter-spacing: 0.02em;
	}
</style>
