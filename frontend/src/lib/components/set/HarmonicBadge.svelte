<script lang="ts">
	import { formatKey, getCamelotColor, harmonicRelationship } from '$lib/utils/camelot';
	import Chip from '$lib/components/primitives/Chip.svelte';
	import HarmonyIcon, { toHarmonyRelation } from '$lib/components/primitives/HarmonyIcon.svelte';

	let { keyA, keyB }: { keyA: string | null; keyB: string | null } = $props();

	let rel = $derived(harmonicRelationship(keyA, keyB));
	let relation = $derived(toHarmonyRelation(rel.label));

	let relColor = $derived.by(() => {
		switch (rel.type) {
			case 'same':
			case 'adjacent':
				return 'var(--score-excellent)';
			case 'modeSwitch':
			case 'adjacentMode':
			case 'twoAway':
				return 'var(--score-good)';
			case 'clash':
				return 'var(--score-poor)';
			default:
				return 'var(--text-3)';
		}
	});
</script>

<Chip variant="harmony" color={relColor}>
	<span class="key" style:color={getCamelotColor(keyA)}>{formatKey(keyA) || '—'}</span>
	<span class="arrow">→</span>
	<span class="key" style:color={getCamelotColor(keyB)}>{formatKey(keyB) || '—'}</span>
	{#if relation}
		<span class="rel-icon" style:color={relColor}>
			<HarmonyIcon {relation} size="sm" label={rel.label} title={rel.description} />
		</span>
	{/if}
	<span class="rel-label" style:color={relColor}>{rel.label}</span>
</Chip>

<style>
	.key {
		font-weight: var(--font-weight-semibold);
		font-variant-numeric: tabular-nums;
	}
	.arrow {
		color: var(--text-4);
		font-size: var(--text-sm);
	}
	.rel-icon {
		display: inline-flex;
		align-items: center;
		margin-left: var(--space-2xs);
	}
	.rel-icon :global(.harmony-icon--sm) {
		width: var(--text-base);
		height: var(--text-base);
	}
	.rel-label {
		font-size: var(--text-xs);
		font-weight: var(--font-weight-medium);
		margin-left: var(--space-2xs);
	}
</style>
