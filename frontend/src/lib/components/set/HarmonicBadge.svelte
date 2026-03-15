<script lang="ts">
	import { getCamelotColor, harmonicRelationship } from '$lib/utils/camelot';

	let { keyA, keyB }: { keyA: string | null; keyB: string | null } = $props();

	let rel = $derived(harmonicRelationship(keyA, keyB));

	let borderColor = $derived.by(() => {
		switch (rel.type) {
			case 'same':
			case 'adjacent':
				return '#66BB6A';
			case 'modeSwitch':
			case 'adjacentMode':
			case 'twoAway':
				return '#FFB74D';
			case 'clash':
				return '#EF5350';
			default:
				return '#666';
		}
	});
</script>

<div class="harmonic-badge" style="border-color: {borderColor}">
	<span class="key" style="color: {getCamelotColor(keyA)}">{keyA ?? '?'}</span>
	<span class="arrow">→</span>
	<span class="key" style="color: {getCamelotColor(keyB)}">{keyB ?? '?'}</span>
	<span class="rel-label" style="color: {borderColor}">{rel.label}</span>
</div>

<style>
	.harmonic-badge {
		display: inline-flex;
		align-items: center;
		gap: 6px;
		padding: 6px 10px;
		background: var(--bg-secondary);
		border: 1px solid;
		border-radius: 6px;
		font-size: 13px;
	}

	.key {
		font-weight: 700;
		font-variant-numeric: tabular-nums;
	}

	.arrow {
		color: var(--text-dim);
		font-size: 12px;
	}

	.rel-label {
		font-size: 11px;
		font-weight: 500;
		margin-left: 2px;
	}
</style>
