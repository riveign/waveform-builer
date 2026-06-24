<script lang="ts">
	import Chip from '$lib/components/primitives/Chip.svelte';

	let { bpmA, bpmB }: { bpmA: number | null; bpmB: number | null } = $props();

	let analysis = $derived.by(() => {
		if (bpmA == null || bpmB == null) {
			return { pct: null, label: 'Unknown', color: 'var(--text-3)', note: null };
		}

		// Detect double/half time
		const ratio = bpmA > bpmB ? bpmA / bpmB : bpmB / bpmA;
		if (ratio >= 1.9 && ratio <= 2.1) {
			const slower = Math.min(bpmA, bpmB);
			const faster = Math.max(bpmA, bpmB);
			return {
				pct: 0,
				label: 'Double time',
				color: 'var(--score-excellent)',
				note: `${Math.round(slower)} → ${Math.round(faster)}`,
			};
		}

		const pct = (Math.abs(bpmA - bpmB) / Math.max(bpmA, bpmB)) * 100;

		if (pct <= 3) return { pct, label: 'Seamless', color: 'var(--score-excellent)', note: null };
		if (pct <= 6) return { pct, label: 'Smooth', color: 'var(--score-excellent)', note: null };
		if (pct <= 12) return { pct, label: 'Noticeable', color: 'var(--score-good)', note: null };
		return { pct, label: 'Large gap', color: 'var(--score-poor)', note: null };
	});
</script>

<Chip variant="bpm" color={analysis.color}>
	<span class="bpm-val">{bpmA ? Math.round(bpmA) : '—'}</span>
	<span class="arrow">→</span>
	<span class="bpm-val">{bpmB ? Math.round(bpmB) : '—'}</span>
	<span class="unit">BPM</span>
	{#if analysis.pct != null}
		<span class="pct" style:color={analysis.color}>
			{analysis.note ?? `${analysis.pct.toFixed(1)}%`}
		</span>
	{/if}
	<span class="bpm-label" style:color={analysis.color}>{analysis.label}</span>
</Chip>

<style>
	.bpm-val {
		font-weight: var(--font-weight-semibold);
		font-variant-numeric: tabular-nums;
		color: var(--text-1);
	}
	.arrow {
		color: var(--text-4);
		font-size: var(--text-sm);
	}
	/* Sentence case — no uppercase (content-conventions §1). */
	.unit {
		font-size: var(--text-2xs);
		color: var(--text-4);
	}
	.pct {
		font-size: var(--text-xs);
		font-weight: var(--font-weight-medium);
	}
	.bpm-label {
		font-size: var(--text-xs);
		font-weight: var(--font-weight-medium);
	}
</style>
