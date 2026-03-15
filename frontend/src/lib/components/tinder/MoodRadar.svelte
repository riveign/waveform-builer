<script lang="ts">
	let {
		happy = 0,
		sad = 0,
		aggressive = 0,
		relaxed = 0,
		size = 120,
	}: {
		happy?: number;
		sad?: number;
		aggressive?: number;
		relaxed?: number;
		size?: number;
	} = $props();

	const cx = $derived(size / 2);
	const cy = $derived(size / 2);
	const r = $derived(size / 2 - 16);

	// Axes: top=happy, right=aggressive, bottom=sad, left=relaxed
	function point(angle: number, value: number, _cx: number, _cy: number, _r: number): string {
		const rad = (angle - 90) * (Math.PI / 180);
		const x = _cx + _r * value * Math.cos(rad);
		const y = _cy + _r * value * Math.sin(rad);
		return `${x},${y}`;
	}

	const polygon = $derived(
		[point(0, happy, cx, cy, r), point(90, aggressive, cx, cy, r), point(180, sad, cx, cy, r), point(270, relaxed, cx, cy, r)].join(' ')
	);
</script>

<svg width={size} height={size} class="mood-radar">
	<!-- Grid circles -->
	{#each [0.25, 0.5, 0.75, 1.0] as level}
		<circle cx={cx} cy={cy} r={r * level} fill="none" stroke="var(--border)" stroke-width="0.5" opacity="0.4" />
	{/each}
	<!-- Axis lines -->
	<line x1={cx} y1={cy - r} x2={cx} y2={cy + r} stroke="var(--border)" stroke-width="0.5" opacity="0.3" />
	<line x1={cx - r} y1={cy} x2={cx + r} y2={cy} stroke="var(--border)" stroke-width="0.5" opacity="0.3" />
	<!-- Data polygon -->
	<polygon points={polygon} fill="var(--accent)" fill-opacity="0.25" stroke="var(--accent)" stroke-width="1.5" />
	<!-- Labels -->
	<text x={cx} y={8} text-anchor="middle" class="label">Happy</text>
	<text x={size - 2} y={cy + 4} text-anchor="end" class="label">Aggro</text>
	<text x={cx} y={size - 2} text-anchor="middle" class="label">Sad</text>
	<text x={2} y={cy + 4} text-anchor="start" class="label">Chill</text>
</svg>

<style>
	.mood-radar {
		display: block;
	}

	.label {
		font-size: 9px;
		fill: var(--text-dim);
		font-family: inherit;
	}
</style>
