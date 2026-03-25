<script lang="ts">
	import {
		Chart,
		RadarController,
		RadialLinearScale,
		PointElement,
		LineElement,
		Filler,
		Tooltip,
	} from 'chart.js';
	import { getLibraryStats, getEnhancedStats } from '$lib/api/stats';
	import type { LibraryStats, EnhancedStatsResponse } from '$lib/types';

	Chart.register(RadarController, RadialLinearScale, PointElement, LineElement, Filler, Tooltip);

	let canvas: HTMLCanvasElement;
	let chart: Chart | null = null;
	let loading = $state(true);
	let error = $state<string | null>(null);
	let teachingNote = $state('');

	const AXES = [
		'Energy Range',
		'BPM Range',
		'Harmonic Diversity',
		'Genre Breadth',
		'Curation Depth',
		'Library Coverage',
	];

	function computeAxes(stats: LibraryStats, enhanced: EnhancedStatsResponse): number[] {
		// Energy range: zones with >10 tracks / 5
		const energyZonesActive = Object.values(enhanced.energy_zones).filter((z) => z.count > 10).length;
		const energyRange = Math.min(energyZonesActive / 5, 1);

		// BPM range: (max - min) / 100, capped at 1
		const bpmMin = stats.bpm_min ?? 0;
		const bpmMax = stats.bpm_max ?? 0;
		const bpmRange = Math.min((bpmMax - bpmMin) / 100, 1);

		// Harmonic diversity: Camelot positions with >5 tracks / 24
		const keyPositions = Object.values(stats.keys).filter((c) => c > 5).length;
		const harmonicDiv = Math.min(keyPositions / 24, 1);

		// Genre breadth: families with >10 tracks / 7
		const familyCounts = new Map<string, number>();
		for (const count of Object.values(stats.genres)) {
			// Each genre entry already counted — we count distinct genres with >10
			// But we want families. Since we don't have family mapping here, use genre count as proxy.
		}
		// Use bpm_per_genre keys as genre families (enhanced stats groups by family)
		const familiesActive = Object.values(enhanced.bpm_per_genre).filter((g) => g.count > 10).length;
		const genreBreadth = Math.min(familiesActive / 7, 1);

		// Curation depth: coverage.rating / 100
		const curationDepth = Math.min(enhanced.coverage.rating / 100, 1);

		// Library coverage: coverage.features / 100
		const libCoverage = Math.min(enhanced.coverage.features / 100, 1);

		return [energyRange, bpmRange, harmonicDiv, genreBreadth, curationDepth, libCoverage];
	}

	function findStrongestWeakest(values: number[]): { strongest: string; weakest: string } {
		let maxIdx = 0;
		let minIdx = 0;
		for (let i = 1; i < values.length; i++) {
			if (values[i] > values[maxIdx]) maxIdx = i;
			if (values[i] < values[minIdx]) minIdx = i;
		}
		return { strongest: AXES[maxIdx], weakest: AXES[minIdx] };
	}

	$effect(() => {
		let destroyed = false;

		(async () => {
			try {
				loading = true;
				error = null;

				const [stats, enhanced] = await Promise.all([
					getLibraryStats(),
					getEnhancedStats(),
				]);

				if (destroyed) return;

				const values = computeAxes(stats, enhanced);
				const { strongest, weakest } = findStrongestWeakest(values);
				teachingNote = `Strongest: ${strongest} — weakest: ${weakest}. A rounder shape means a more versatile collection.`;

				chart = new Chart(canvas, {
					type: 'radar',
					data: {
						labels: AXES,
						datasets: [{
							data: values,
							backgroundColor: 'rgba(64, 224, 208, 0.15)',
							borderColor: 'rgba(64, 224, 208, 0.8)',
							borderWidth: 2,
							pointBackgroundColor: 'rgba(64, 224, 208, 1)',
							pointBorderColor: '#0D0D0D',
							pointBorderWidth: 1,
							pointRadius: 4,
							pointHoverRadius: 6,
							fill: true,
						}],
					},
					options: {
						responsive: true,
						maintainAspectRatio: false,
						plugins: {
							legend: { display: false },
							tooltip: {
								callbacks: {
									label: (ctx) => {
										const val = ctx.raw as number;
										return `${ctx.label}: ${Math.round(val * 100)}%`;
									},
								},
								backgroundColor: '#0D0D0D',
								borderColor: '#3F414A',
								borderWidth: 1,
							},
						},
						scales: {
							r: {
								min: 0,
								max: 1,
								ticks: {
									stepSize: 0.25,
									color: '#555',
									backdropColor: 'transparent',
									font: { size: 9 },
								},
								grid: {
									color: 'rgba(63, 65, 74, 0.5)',
								},
								angleLines: {
									color: 'rgba(63, 65, 74, 0.5)',
								},
								pointLabels: {
									color: '#A0A1A7',
									font: { size: 11 },
								},
							},
						},
					},
				});
			} catch (e) {
				if (!destroyed) {
					error = e instanceof Error ? e.message : "Couldn't build your taste profile — try refreshing";
				}
			} finally {
				if (!destroyed) loading = false;
			}
		})();

		return () => {
			destroyed = true;
			if (chart) {
				chart.destroy();
				chart = null;
			}
		};
	});
</script>

<div class="taste-radar">
	<div class="radar-header">
		<h3 class="chart-title">Taste Radar</h3>
		<p class="teaching-note">Your collection's shape — a rounder profile means more versatile mixing</p>
	</div>
	{#if loading}
		<div class="loading">Reading your taste profile...</div>
	{:else if error}
		<div class="error">{error}</div>
	{/if}
	<div class="chart-container" class:hidden={loading || !!error}>
		<canvas bind:this={canvas}></canvas>
	</div>
	{#if teachingNote && !loading && !error}
		<p class="insight">{teachingNote}</p>
	{/if}
</div>

<style>
	.taste-radar {
		background: var(--bg-secondary);
		border-radius: 8px;
		padding: 16px;
		display: flex;
		flex-direction: column;
		min-height: 320px;
	}

	.radar-header {
		margin-bottom: 4px;
	}

	.chart-title {
		font-size: 16px;
		font-weight: 700;
		color: var(--text-primary);
		margin-bottom: 2px;
	}

	.teaching-note {
		font-size: 11px;
		color: var(--text-dim);
		margin-bottom: 8px;
	}

	.chart-container {
		flex: 1;
		position: relative;
		min-height: 280px;
	}

	.chart-container.hidden {
		display: none;
	}

	.loading, .error {
		display: flex;
		align-items: center;
		justify-content: center;
		flex: 1;
		font-size: 13px;
		color: var(--text-secondary);
	}

	.error {
		color: var(--energy-high);
	}

	.insight {
		font-size: 11px;
		color: var(--accent);
		margin-top: 8px;
		line-height: 1.4;
	}
</style>
