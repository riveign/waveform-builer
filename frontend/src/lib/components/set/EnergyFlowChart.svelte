<script lang="ts">
	import {
		Chart,
		LineController,
		LineElement,
		PointElement,
		CategoryScale,
		LinearScale,
		Tooltip,
		Legend,
		Filler,
	} from 'chart.js';
	import type { SetWaveformTrack } from '$lib/types';

	Chart.register(LineController, LineElement, PointElement, CategoryScale, LinearScale, Tooltip, Legend, Filler);

	interface Props {
		tracks: SetWaveformTrack[];
		energyProfile?: string | null;
		selectedIndex?: number;
		onTrackClick?: (index: number) => void;
	}

	let { tracks, energyProfile, selectedIndex, onTrackClick }: Props = $props();

	let canvas = $state<HTMLCanvasElement>(null!);
	let chart: Chart | null = null;

	/** Map energy label or numeric string to normalized 0-1. */
	const ENERGY_LABEL_MAP: Record<string, number> = {
		low: 0.15, warmup: 0.3, closing: 0.35, mid: 0.5,
		dance: 0.6, up: 0.7, high: 0.8, fast: 0.85, peak: 0.95,
	};

	function normalizeEnergy(energy: string | null): number | null {
		if (!energy) return null;
		const n = parseInt(energy, 10);
		if (!isNaN(n)) return n / 9.0;
		const mapped = ENERGY_LABEL_MAP[energy.toLowerCase()];
		return mapped ?? null;
	}

	/** Parse energy profile — supports both JSON array and string format.
	 *  JSON: [{"name":"dark","target_energy":0.85,"duration_min":30}, ...]
	 *  String: "warmup(0.3)->build(0.6)->peak(0.9)->cooldown(0.4)" */
	function parseEnergyProfile(profile: string | null | undefined, count: number): (number | null)[] {
		if (!profile || count === 0) return new Array(count).fill(null);

		const segments: { name: string; value: number }[] = [];

		// Try JSON format first
		if (profile.trimStart().startsWith('[')) {
			try {
				const parsed = JSON.parse(profile) as { name: string; target_energy: number; duration_min?: number }[];
				for (const seg of parsed) {
					segments.push({ name: seg.name, value: seg.target_energy });
				}
			} catch { /* fall through to string parsing */ }
		}

		// String format: "warmup(0.3)->build(0.6)"
		if (segments.length === 0) {
			const re = /(\w+)\(([0-9.]+)\)/g;
			let match: RegExpExecArray | null;
			while ((match = re.exec(profile)) !== null) {
				segments.push({ name: match[1], value: parseFloat(match[2]) });
			}
		}

		if (segments.length === 0) return new Array(count).fill(null);
		if (segments.length === 1) return new Array(count).fill(segments[0].value);

		const targets: number[] = [];
		for (let i = 0; i < count; i++) {
			const t = count === 1 ? 0 : i / (count - 1);
			const segIdx = t * (segments.length - 1);
			const lo = Math.floor(segIdx);
			const hi = Math.min(lo + 1, segments.length - 1);
			const frac = segIdx - lo;
			targets.push(segments[lo].value * (1 - frac) + segments[hi].value * frac);
		}
		return targets;
	}

	/** Determine deviation color for a point. */
	function deviationColor(actual: number | null, target: number | null): string {
		if (actual === null || target === null) return 'rgba(64, 224, 208, 0.9)';
		const dev = Math.abs(actual - target);
		if (dev <= 0.15) return 'rgba(102, 187, 106, 0.9)';   // green — good fit
		if (dev <= 0.3) return 'rgba(255, 183, 77, 0.9)';     // yellow — acceptable
		return 'rgba(255, 107, 107, 0.9)';                     // red — poor fit
	}

	function buildChartData() {
		const labels = tracks.map((_, i) => String(i + 1));
		const actualValues = tracks.map((t) => normalizeEnergy(t.energy));
		const targetValues = parseEnergyProfile(energyProfile, tracks.length);
		const hasTarget = targetValues.some((v) => v !== null);

		// Point colors based on deviation from target
		const pointColors = actualValues.map((actual, i) => deviationColor(actual, targetValues[i]));

		// Segment colors for the line between points
		const segmentColors = actualValues.map((actual, i) => deviationColor(actual, targetValues[i]));

		// Selected point styling
		const pointRadii = actualValues.map((_, i) => (i === selectedIndex ? 7 : 3));
		const pointBorderWidths = actualValues.map((_, i) => (i === selectedIndex ? 2 : 0));

		const datasets: any[] = [];

		// Actual energy curve
		datasets.push({
			label: 'Actual',
			data: actualValues,
			borderColor: segmentColors,
			backgroundColor: pointColors,
			segment: {
				borderColor: (ctx: any) => {
					const i = ctx.p0DataIndex;
					return deviationColor(actualValues[i], targetValues[i]);
				},
			},
			borderWidth: 2,
			pointRadius: pointRadii,
			pointHoverRadius: 6,
			pointBackgroundColor: pointColors,
			pointBorderColor: actualValues.map((_, i) => (i === selectedIndex ? '#fff' : 'transparent')),
			pointBorderWidth: pointBorderWidths,
			tension: 0.3,
			fill: false,
			order: 1,
		});

		// Target energy curve (only if profile exists)
		if (hasTarget) {
			datasets.push({
				label: 'Target',
				data: targetValues,
				borderColor: 'rgba(255, 255, 255, 0.35)',
				borderWidth: 1.5,
				borderDash: [6, 4],
				pointRadius: 0,
				pointHoverRadius: 0,
				tension: 0.3,
				fill: false,
				order: 2,
			});
		}

		return { labels, datasets };
	}

	function createChart() {
		if (!canvas) return;
		const { labels, datasets } = buildChartData();
		const targetValues = parseEnergyProfile(energyProfile, tracks.length);

		chart = new Chart(canvas, {
			type: 'line',
			data: { labels, datasets },
			options: {
				responsive: true,
				maintainAspectRatio: false,
				animation: {
					duration: 300,
				},
				interaction: {
					mode: 'index',
					intersect: false,
				},
				onClick: (_event, elements) => {
					if (elements.length > 0 && onTrackClick) {
						onTrackClick(elements[0].index);
					}
				},
				plugins: {
					legend: {
						display: targetValues.some((v) => v !== null),
						position: 'bottom',
						labels: {
							color: '#A0A1A7',
							font: { size: 10 },
							padding: 8,
							boxWidth: 16,
							boxHeight: 2,
							usePointStyle: false,
						},
					},
					tooltip: {
						mode: 'index',
						intersect: false,
						backgroundColor: 'rgba(20, 20, 25, 0.95)',
						titleColor: '#F5F5F0',
						bodyColor: '#A0A1A7',
						borderColor: 'rgba(255,255,255,0.1)',
						borderWidth: 1,
						padding: 10,
						cornerRadius: 6,
						callbacks: {
							title: (items) => {
								const idx = items[0]?.dataIndex;
								if (idx === undefined || idx >= tracks.length) return '';
								const t = tracks[idx];
								return t.title ?? `Track ${idx + 1}`;
							},
							afterTitle: (items) => {
								const idx = items[0]?.dataIndex;
								if (idx === undefined || idx >= tracks.length) return '';
								const t = tracks[idx];
								return t.artist ?? '';
							},
							label: (ctx) => {
								if (ctx.datasetIndex === 0) {
									const idx = ctx.dataIndex;
									const t = tracks[idx];
									const lines: string[] = [];
									const val = ctx.parsed.y;
									if (val !== null) lines.push(`Energy: ${(val * 9).toFixed(0)}/9`);
									if (t.bpm) lines.push(`BPM: ${t.bpm}`);
									if (t.key) lines.push(`Key: ${t.key}`);
									if (t.transition_score !== null && t.transition_score !== undefined) {
										lines.push(`Transition: ${(t.transition_score * 100).toFixed(0)}%`);
									}
									return lines;
								}
								// Target dataset
								const val = ctx.parsed.y;
								if (val !== null) return `Target: ${val.toFixed(2)}`;
								return '';
							},
						},
					},
				},
				scales: {
					x: {
						grid: { color: 'rgba(63, 65, 74, 0.3)' },
						ticks: {
							color: '#555',
							font: { size: 10 },
						},
						title: {
							display: true,
							text: 'Track #',
							color: '#666',
							font: { size: 10 },
						},
					},
					y: {
						min: 0,
						max: 1,
						grid: { color: 'rgba(63, 65, 74, 0.3)' },
						ticks: {
							color: '#555',
							font: { size: 10 },
							stepSize: 0.25,
							callback: (value) => {
								const v = Number(value);
								if (v === 0) return '0';
								if (v === 0.25) return '2';
								if (v === 0.5) return '5';
								if (v === 0.75) return '7';
								if (v === 1) return '9';
								return '';
							},
						},
						title: {
							display: true,
							text: 'Energy',
							color: '#666',
							font: { size: 10 },
						},
					},
				},
			},
		});
	}

	function updateChart() {
		if (!chart) return;
		const { labels, datasets } = buildChartData();
		chart.data.labels = labels;
		chart.data.datasets = datasets;
		chart.update('default');
	}

	// Initial mount and cleanup
	$effect(() => {
		createChart();

		return () => {
			if (chart) {
				chart.destroy();
				chart = null;
			}
		};
	});

	// Reactive updates when tracks, profile, or selection changes
	$effect(() => {
		// Touch reactive dependencies
		void tracks;
		void energyProfile;
		void selectedIndex;

		if (chart) {
			updateChart();
		}
	});
</script>

<div class="energy-flow-chart">
	<h3 class="chart-title">Energy Flow</h3>
	{#if tracks.length === 0}
		<div class="empty">No tracks to chart</div>
	{:else}
		<div class="chart-container">
			<canvas bind:this={canvas}></canvas>
		</div>
	{/if}
</div>

<style>
	.energy-flow-chart {
		background: var(--bg-secondary);
		border-radius: 8px;
		padding: 12px 16px;
		display: flex;
		flex-direction: column;
	}

	.chart-title {
		font-size: 13px;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.5px;
		color: var(--text-secondary);
		margin-bottom: 8px;
	}

	.chart-container {
		position: relative;
		height: 180px;
	}

	.empty {
		display: flex;
		align-items: center;
		justify-content: center;
		height: 100px;
		font-size: 13px;
		color: var(--text-dim);
	}
</style>
