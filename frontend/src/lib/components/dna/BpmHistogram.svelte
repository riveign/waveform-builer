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
	import { familyColors, chartChrome } from '$lib/styles/canvasPalette';

	Chart.register(BarController, BarElement, CategoryScale, LinearScale, Tooltip, Legend);

	let canvas: HTMLCanvasElement;
	let chart: Chart | null = null;
	let loading = $state(true);
	let error = $state<string | null>(null);
	/** Accessible summary of the tempo spread, for screen readers. */
	let summary = $state('');

	function buildSummary(bins: BpmBin[]): string {
		if (bins.length === 0) return 'No tempo data yet.';
		const centers = [...new Set(bins.map((b) => b.bin_center))].sort((a, b) => a - b);
		const totals = new Map<number, number>();
		for (const b of bins) totals.set(b.bin_center, (totals.get(b.bin_center) ?? 0) + b.count);
		let peakBpm = centers[0];
		let peakCount = 0;
		for (const [bpm, count] of totals) {
			if (count > peakCount) {
				peakCount = count;
				peakBpm = bpm;
			}
		}
		const total = [...totals.values()].reduce((a, b) => a + b, 0);
		return `BPM distribution across ${total} tracks, from ${centers[0]} to ${centers[centers.length - 1]} BPM. Most tracks cluster around ${peakBpm} BPM.`;
	}

	function buildStackedData(bins: BpmBin[]) {
		const colors = familyColors();
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
				backgroundColor: colors[family] ?? colors.Other,
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

				summary = buildSummary(data);
				const { labels, datasets } = buildStackedData(data);
				const chrome = chartChrome();

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
									color: chrome.text,
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
								grid: { color: chrome.grid },
								ticks: {
									color: chrome.tick,
									font: { size: 10 },
									maxRotation: 0,
									autoSkip: true,
									autoSkipPadding: 8,
								},
								title: {
									display: true,
									text: 'BPM',
									color: chrome.label,
									font: { size: 12 },
								},
							},
							y: {
								stacked: true,
								grid: { color: chrome.grid },
								ticks: {
									color: chrome.tick,
									font: { size: 10 },
								},
								title: {
									display: true,
									text: 'Tracks',
									color: chrome.label,
									font: { size: 12 },
								},
							},
						},
					},
				});
			} catch (e) {
				if (!destroyed) {
					error = e instanceof Error ? e.message : "Couldn't read your tempo data — try refreshing";
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
	<p class="teaching-note">Where your tempos cluster — wider spread means more set variety</p>
	{#if loading}
		<div class="loading">Measuring your tempos...</div>
	{:else if error}
		<div class="error">{error}</div>
	{/if}
	<div class="chart-container" class:hidden={loading || !!error}>
		<canvas bind:this={canvas} aria-hidden="true"></canvas>
		<p class="sr-only" role="img" aria-label={summary}>{summary}</p>
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

	.sr-only {
		position: absolute;
		width: 1px;
		height: 1px;
		padding: 0;
		margin: -1px;
		overflow: hidden;
		clip: rect(0, 0, 0, 0);
		white-space: nowrap;
		border: 0;
	}
</style>
