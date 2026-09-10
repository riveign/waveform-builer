<script lang="ts">
	let {
		position = null,
	}: {
		/** The side printed on the label — "A1", "B2". */
		position?: string | null;
	} = $props();

	const tip = $derived(position ? `On vinyl — side ${position}` : 'On vinyl');
</script>

<span class="vinyl-pip" title={tip} role="img" aria-label={tip}>
	<svg viewBox="0 0 16 16" width="13" height="13" aria-hidden="true">
		<circle cx="8" cy="8" r="7" fill="none" stroke="currentColor" stroke-width="1.4" />
		<circle cx="8" cy="8" r="3.2" fill="none" stroke="currentColor" stroke-width="1" opacity="0.6" />
		<circle cx="8" cy="8" r="1.1" fill="currentColor" />
	</svg>
	{#if position}<span class="vinyl-pip__side">{position}</span>{/if}
</span>

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
	.vinyl-pip__side {
		font-size: var(--font-size-xs);
		font-variant-numeric: tabular-nums;
		letter-spacing: 0.02em;
	}
</style>
