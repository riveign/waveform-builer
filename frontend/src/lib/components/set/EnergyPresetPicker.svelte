<script lang="ts">
	interface EnergyPreset {
		name: string;
		label: string;
		description: string;
		points: number[];
	}

	const ENERGY_PRESETS: EnergyPreset[] = [
		{
			name: 'warmup',
			label: 'Warm Up',
			description: 'Ease into the night',
			points: [0, 0.3, 0.25, 0.35, 0.5, 0.45, 0.75, 0.55, 1, 0.6],
		},
		{
			name: 'peak-time',
			label: 'Peak Time',
			description: 'Straight to the top',
			points: [0, 0.85, 0.25, 0.9, 0.5, 0.95, 0.75, 0.9, 1, 0.85],
		},
		{
			name: 'journey',
			label: 'Journey',
			description: 'The full arc',
			points: [0, 0.3, 0.25, 0.6, 0.5, 0.9, 0.75, 0.7, 1, 0.4],
		},
		{
			name: 'afterhours',
			label: 'After Hours',
			description: 'Late night vibes',
			points: [0, 0.5, 0.25, 0.5, 0.5, 0.45, 0.75, 0.4, 1, 0.3],
		},
	];

	let {
		value = $bindable('journey'),
		onchange,
	}: {
		value: string;
		onchange?: (preset: string) => void;
	} = $props();

	/** Build SVG polyline points string from the normalized x,y pairs */
	function buildPolyline(pts: number[], width: number, height: number, padding: number): string {
		const coords: string[] = [];
		for (let i = 0; i < pts.length; i += 2) {
			const x = padding + pts[i] * (width - padding * 2);
			const y = padding + (1 - pts[i + 1]) * (height - padding * 2);
			coords.push(`${x.toFixed(1)},${y.toFixed(1)}`);
		}
		return coords.join(' ');
	}

	/** Build SVG polygon points for the filled area under the line */
	function buildFillPolygon(pts: number[], width: number, height: number, padding: number): string {
		const linePoints = buildPolyline(pts, width, height, padding);
		const bottomRight = `${(width - padding).toFixed(1)},${(height - padding).toFixed(1)}`;
		const bottomLeft = `${padding.toFixed(1)},${(height - padding).toFixed(1)}`;
		return `${linePoints} ${bottomRight} ${bottomLeft}`;
	}

	function select(name: string) {
		value = name;
		onchange?.(name);
	}
</script>

<div class="preset-grid" role="group" aria-label="Energy arc presets">
	{#each ENERGY_PRESETS as preset}
		{@const selected = value === preset.name}
		<button
			class="preset-card"
			class:selected
			onclick={() => select(preset.name)}
			type="button"
			aria-pressed={selected}
		>
			<svg
				class="sparkline"
				viewBox="0 0 80 30"
				width="80"
				height="30"
				xmlns="http://www.w3.org/2000/svg"
			>
				<defs>
					<linearGradient id="fill-{preset.name}" x1="0" y1="0" x2="0" y2="1">
						<stop offset="0%" stop-color={selected ? 'var(--accent)' : 'var(--text-secondary)'} stop-opacity="0.2" />
						<stop offset="100%" stop-color={selected ? 'var(--accent)' : 'var(--text-secondary)'} stop-opacity="0.02" />
					</linearGradient>
				</defs>
				<polygon
					points={buildFillPolygon(preset.points, 80, 30, 2)}
					fill="url(#fill-{preset.name})"
				/>
				<polyline
					points={buildPolyline(preset.points, 80, 30, 2)}
					fill="none"
					stroke={selected ? 'var(--accent)' : 'var(--text-secondary)'}
					stroke-width="1.5"
					stroke-linecap="round"
					stroke-linejoin="round"
				/>
			</svg>
			<span class="preset-label">{preset.label}</span>
			<span class="preset-desc">{preset.description}</span>
		</button>
	{/each}
</div>

<style>
	.preset-grid {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 8px;
	}

	.preset-card {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 4px;
		padding: 10px 8px;
		background: var(--bg-secondary);
		border: 1px solid var(--border);
		border-radius: 6px;
		cursor: pointer;
		transition: border-color 0.15s, background 0.1s, box-shadow 0.15s;
		text-align: center;
	}

	.preset-card:hover {
		background: var(--bg-hover);
	}

	.preset-card.selected {
		border-color: var(--accent);
		background: var(--bg-active);
		box-shadow: 0 0 8px rgba(0, 206, 209, 0.15);
	}

	.sparkline {
		flex-shrink: 0;
	}

	.preset-label {
		font-size: 12px;
		font-weight: 600;
		color: var(--text-primary);
		line-height: 1;
	}

	.preset-desc {
		font-size: 10px;
		color: var(--text-secondary);
		line-height: 1;
	}
</style>
