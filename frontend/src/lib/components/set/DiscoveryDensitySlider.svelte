<script lang="ts">
	let {
		value = $bindable(0),
	}: {
		value: number;
	} = $props();

	const LABELS: [number, string, string][] = [
		[-100, 'Fresh picks', 'Surfaces unplayed and rarely-heard tracks from your library'],
		[-50, 'Lean fresh', 'Gently favors tracks you haven\'t played much'],
		[0, 'Balanced', 'No bias — scores tracks on merit alone'],
		[50, 'Lean proven', 'Gently favors tracks with more plays and set appearances'],
		[100, 'Battle-tested', 'Prioritizes your most-played, set-proven tracks'],
	];

	function getLabel(v: number): { name: string; description: string } {
		if (v <= -75) return { name: LABELS[0][1], description: LABELS[0][2] };
		if (v <= -25) return { name: LABELS[1][1], description: LABELS[1][2] };
		if (v <= 25) return { name: LABELS[2][1], description: LABELS[2][2] };
		if (v <= 75) return { name: LABELS[3][1], description: LABELS[3][2] };
		return { name: LABELS[4][1], description: LABELS[4][2] };
	}

	let current = $derived(getLabel(value));
</script>

<div class="discovery-density">
	<div class="dd-header">
		<span class="dd-label">Discovery / Density</span>
		<span class="dd-value">{current.name}</span>
	</div>
	<input
		type="range"
		class="dd-slider"
		min={-100}
		max={100}
		step={1}
		bind:value={value}
	/>
	<div class="dd-range">
		<span>Fresh picks</span>
		<span>Battle-tested</span>
	</div>
	<p class="dd-description">{current.description}</p>
</div>

<style>
	.discovery-density {
		display: flex;
		flex-direction: column;
		gap: 4px;
	}

	.dd-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
	}

	.dd-label {
		font-size: 11px;
		font-weight: 600;
		color: var(--text-secondary);
		text-transform: uppercase;
		letter-spacing: 0.5px;
	}

	.dd-value {
		font-size: 11px;
		color: var(--accent);
		font-weight: 500;
	}

	.dd-slider {
		width: 100%;
		accent-color: var(--accent);
		cursor: pointer;
		height: 6px;
		margin-top: 2px;
	}

	.dd-range {
		display: flex;
		justify-content: space-between;
		font-size: 9px;
		color: var(--text-dim);
		margin-top: -2px;
	}

	.dd-description {
		font-size: 10px;
		color: var(--text-dim);
		margin: 0;
		font-style: italic;
	}
</style>
