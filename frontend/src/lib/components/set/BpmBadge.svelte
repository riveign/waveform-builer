<script lang="ts">
	let { bpmA, bpmB }: { bpmA: number | null; bpmB: number | null } = $props();

	let analysis = $derived.by(() => {
		if (bpmA == null || bpmB == null) {
			return { pct: null, label: 'Unknown', color: '#666', note: null };
		}

		// Detect double/half time
		const ratio = bpmA > bpmB ? bpmA / bpmB : bpmB / bpmA;
		if (ratio >= 1.9 && ratio <= 2.1) {
			const slower = Math.min(bpmA, bpmB);
			const faster = Math.max(bpmA, bpmB);
			return {
				pct: 0,
				label: 'Double time',
				color: '#66BB6A',
				note: `${Math.round(slower)} → ${Math.round(faster)}`
			};
		}

		const pct = (Math.abs(bpmA - bpmB) / Math.max(bpmA, bpmB)) * 100;

		if (pct <= 3) return { pct, label: 'Seamless', color: '#66BB6A', note: null };
		if (pct <= 6) return { pct, label: 'Smooth', color: '#A5D6A7', note: null };
		if (pct <= 12) return { pct, label: 'Noticeable', color: '#FFB74D', note: null };
		return { pct, label: 'Large gap', color: '#EF5350', note: null };
	});
</script>

<div class="bpm-badge" style="border-color: {analysis.color}">
	<span class="bpm-val">{bpmA ? Math.round(bpmA) : '?'}</span>
	<span class="arrow">→</span>
	<span class="bpm-val">{bpmB ? Math.round(bpmB) : '?'}</span>
	<span class="unit">BPM</span>
	{#if analysis.pct != null}
		<span class="pct" style="color: {analysis.color}">
			{analysis.note ?? `${analysis.pct.toFixed(1)}%`}
		</span>
	{/if}
	<span class="bpm-label" style="color: {analysis.color}">{analysis.label}</span>
</div>

<style>
	.bpm-badge {
		display: inline-flex;
		align-items: center;
		gap: 6px;
		padding: 6px 10px;
		background: var(--bg-secondary);
		border: 1px solid;
		border-radius: 6px;
		font-size: 13px;
	}

	.bpm-val {
		font-weight: 700;
		font-variant-numeric: tabular-nums;
		color: var(--text-primary);
	}

	.arrow {
		color: var(--text-dim);
		font-size: 12px;
	}

	.unit {
		font-size: 10px;
		color: var(--text-dim);
		text-transform: uppercase;
	}

	.pct {
		font-size: 11px;
		font-weight: 500;
	}

	.bpm-label {
		font-size: 11px;
		font-weight: 500;
	}
</style>
