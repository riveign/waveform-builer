<script lang="ts">
	import {
		Chart,
		BarController,
		BarElement,
		CategoryScale,
		LinearScale,
		Tooltip,
		Legend,
	} from 'chart.js';
	import { getBpmHistogram } from '$lib/api/stats';
	import type { BpmBin } from '$lib/types';

	Chart.register(BarController, BarElement, CategoryScale, LinearScale, Tooltip, Legend);

	const FAMILY_COLORS: Record<string, string> = {
		Techno: '#00d2ff',
		House: '#e94560',
		Groove: '#2ecc71',
		Trance: '#9b59b6',
		Breaks: '#f39c12',
		Electronic: '#3498db',
		Other: '#95a5a6',
	};

	let canvas: HTMLCanvasElement;
	let chart: Chart | null = null;
	let loading = $state(true);
	let error = $state<string | null>(null);

	function buildStackedData(bins: BpmBin[]) {
		const families = [...new Set(bins.map((b) => b.family))].sort();
		const bpmLabels = [...new Set(bins.map((b) => b.bin_center))].sort((a, b) => a - b);
		const labelStrings = bpmLabels.map((v) => String(v));

		const countMap = new Map<string, Map<number, number>>();
		for (const fam of families) {
			countMap.set(fam, new Map());
		}
		for (const bin of bins) {
			countMap.get(bin.family)!.set(bin.bin_center, bin.count);
		}

		const datasets = families.map((family) => {
			const famMap = countMap.get(family)!;
			return {
				label: family,
				data: bpmLabels.map((bpm) => famMap.get(bpm) ?? 0),
				backgroundColor: FAMILY_COLORS[family] ?? '#95a5a6',
				borderColor: 'transparent',
				borderWidth: 0,
			};
		});

		return { labels: labelStrings, datasets };
	}

	$effect(() => {
		let destroyed = false;

		(async () => {
			try {
				loading = true;
				error = null;
				const data = await getBpmHistogram();

				if (destroyed) return;

				const { labels, datasets } = buildStackedData(data);

				chart = new Chart(canvas, {
					type: 'bar',
					data: { labels, datasets },
					options: {
						responsive: true,
						maintainAspectRatio: false,
						plugins: {
							legend: {
								display: true,
								position: 'bottom',
								labels: {
									color: '#e0e0e0',
									font: { size: 11 },
									padding: 12,
									boxWidth: 12,
								},
							},
							tooltip: {
								mode: 'index',
								intersect: false,
								callbacks: {
									title: (items) => `${items[0]?.label} BPM`,
								},
							},
						},
						scales: {
							x: {
								stacked: true,
								grid: { color: 'rgba(102, 102, 102, 0.2)' },
								ticks: {
									color: '#666',
									font: { size: 10 },
									maxRotation: 0,
									autoSkip: true,
									autoSkipPadding: 8,
								},
								title: {
									display: true,
									text: 'BPM',
									color: '#999',
									font: { size: 12 },
								},
							},
							y: {
								stacked: true,
								grid: { color: 'rgba(102, 102, 102, 0.2)' },
								ticks: {
									color: '#666',
									font: { size: 10 },
								},
								title: {
									display: true,
									text: 'Tracks',
									color: '#999',
									font: { size: 12 },
								},
							},
						},
					},
				});
			} catch (e) {
				if (!destroyed) {
					error = e instanceof Error ? e.message : 'Failed to load BPM data';
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

<div class="bpm-histogram">
	<h3 class="chart-title">BPM Distribution</h3>
	{#if loading}
		<div class="loading">Loading BPM data...</div>
	{:else if error}
		<div class="error">{error}</div>
	{/if}
	<div class="chart-container" class:hidden={loading || !!error}>
		<canvas bind:this={canvas}></canvas>
	</div>
</div>

<style>
	.bpm-histogram {
		background: var(--bg-secondary);
		border-radius: 8px;
		padding: 16px;
		display: flex;
		flex-direction: column;
		min-height: 300px;
	}

	.chart-title {
		font-size: 14px;
		font-weight: 600;
		color: var(--text-primary);
		margin-bottom: 12px;
	}

	.chart-container {
		flex: 1;
		position: relative;
		min-height: 250px;
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
</style>
