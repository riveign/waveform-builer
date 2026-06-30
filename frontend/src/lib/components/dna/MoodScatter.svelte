<script lang="ts">
	import { Chart, ScatterController, LinearScale, PointElement, Tooltip, Legend } from 'chart.js';
	import type { MoodPoint } from '$lib/types';
	import { getMoodScatter } from '$lib/api/stats';
	import { familyColors, chartChrome } from '$lib/styles/canvasPalette';

	Chart.register(ScatterController, LinearScale, PointElement, Tooltip, Legend);

	let canvas: HTMLCanvasElement | undefined = $state();
	let chart: Chart | null = $state(null);
	let data: MoodPoint[] | null = $state(null);
	let loading = $state(true);
	let error: string | null = $state(null);

	function buildChart(el: HTMLCanvasElement, points: MoodPoint[]) {
		const colors = familyColors();
		const chrome = chartChrome();
		const getFamilyColor = (family: string): string => colors[family] ?? colors.Other;

		// Group by genre family for datasets
		const grouped = new Map<string, MoodPoint[]>();
		for (const p of points) {
			const family = p.genre_family || 'Other';
			if (!grouped.has(family)) grouped.set(family, []);
			grouped.get(family)!.push(p);
		}

		const datasets = Array.from(grouped.entries()).map(([family, pts]) => ({
			label: family,
			data: pts.map((p) => ({
				x: p.x,
				y: p.y,
				title: p.title,
				artist: p.artist,
				energy: p.energy,
			})),
			backgroundColor: getFamilyColor(family) + 'cc',
			borderColor: getFamilyColor(family),
			borderWidth: 1,
			pointRadius: pts.map((p) => Math.max(4, p.energy * 14)),
			pointHoverRadius: pts.map((p) => Math.max(6, p.energy * 14 + 2)),
		}));

		return new Chart(el, {
			type: 'scatter',
			data: { datasets },
			options: {
				responsive: true,
				maintainAspectRatio: false,
				animation: { duration: 400 },
				scales: {
					x: {
						title: {
							display: true,
							text: 'Happy  \u2190\u2192  Sad',
							color: chrome.label,
							font: { size: 11 },
						},
						grid: { color: chrome.border },
						ticks: { color: chrome.tick, font: { size: 10 } },
						border: { color: chrome.border },
					},
					y: {
						title: {
							display: true,
							text: 'Aggressive  \u2190\u2192  Relaxed',
							color: chrome.label,
							font: { size: 11 },
						},
						grid: { color: chrome.border },
						ticks: { color: chrome.tick, font: { size: 10 } },
						border: { color: chrome.border },
					},
				},
				plugins: {
					tooltip: {
						callbacks: {
							label: (ctx) => {
								const raw = ctx.raw as { x: number; y: number; title: string; artist: string };
								return `${raw.title} - ${raw.artist} (${raw.x.toFixed(2)}, ${raw.y.toFixed(2)})`;
							},
						},
						backgroundColor: chrome.surface,
						borderColor: chrome.border,
						borderWidth: 1,
						titleFont: { size: 12 },
						bodyFont: { size: 11 },
						padding: 8,
					},
					legend: {
						position: 'bottom' as const,
						labels: {
							color: chrome.label,
							font: { size: 11 },
							usePointStyle: true,
							pointStyle: 'circle',
							padding: 16,
						},
					},
				},
			},
			plugins: [
				{
					id: 'crosshairs',
					beforeDraw: (chartInstance) => {
						const { ctx: drawCtx, chartArea } = chartInstance;
						if (!chartArea) return;
						const xScale = chartInstance.scales.x;
						const yScale = chartInstance.scales.y;
						const xZero = xScale.getPixelForValue(0);
						const yZero = yScale.getPixelForValue(0);

						drawCtx.save();
						drawCtx.setLineDash([4, 4]);
						drawCtx.strokeStyle = chrome.muted;
						drawCtx.lineWidth = 1;

						// Vertical crosshair at x=0
						if (xZero >= chartArea.left && xZero <= chartArea.right) {
							drawCtx.beginPath();
							drawCtx.moveTo(xZero, chartArea.top);
							drawCtx.lineTo(xZero, chartArea.bottom);
							drawCtx.stroke();
						}

						// Horizontal crosshair at y=0
						if (yZero >= chartArea.top && yZero <= chartArea.bottom) {
							drawCtx.beginPath();
							drawCtx.moveTo(chartArea.left, yZero);
							drawCtx.lineTo(chartArea.right, yZero);
							drawCtx.stroke();
						}

						// Quadrant labels
						drawCtx.setLineDash([]);
						drawCtx.font = '10px -apple-system, BlinkMacSystemFont, sans-serif';
						drawCtx.fillStyle = chrome.muted;
						drawCtx.textAlign = 'center';

						const padX = 60;
						const padY = 14;

						if (xZero >= chartArea.left && yZero >= chartArea.top) {
							// Top-right: Happy + Aggressive
							drawCtx.fillText('Happy + Aggressive', (xZero + chartArea.right) / 2, chartArea.top + padY);
							// Top-left: Sad + Aggressive
							drawCtx.fillText('Sad + Aggressive', (chartArea.left + xZero) / 2, chartArea.top + padY);
							// Bottom-right: Happy + Relaxed
							drawCtx.fillText('Happy + Relaxed', (xZero + chartArea.right) / 2, chartArea.bottom - padY + 6);
							// Bottom-left: Sad + Relaxed
							drawCtx.fillText('Sad + Relaxed', (chartArea.left + xZero) / 2, chartArea.bottom - padY + 6);
						}

						drawCtx.restore();
					},
				},
			],
		});
	}

	// Fetch data on mount
	$effect(() => {
		let cancelled = false;
		getMoodScatter()
			.then((result) => {
				if (!cancelled) {
					data = result;
					loading = false;
				}
			})
			.catch((err) => {
				if (!cancelled) {
					error = err instanceof Error ? err.message : "Couldn't load mood data — try refreshing";
					loading = false;
				}
			});
		return () => { cancelled = true; };
	});

	// Build/rebuild chart when canvas and data are both ready
	$effect(() => {
		if (!canvas || !data) return;
		if (chart) {
			chart.destroy();
			chart = null;
		}
		if (data.length > 0) {
			chart = buildChart(canvas, data);
		}
		return () => {
			if (chart) {
				chart.destroy();
				chart = null;
			}
		};
	});
</script>

<div class="scatter-container">
	<h3 class="chart-title">Mood Scatter</h3>
	<p class="teaching-note">Emotional fingerprint — position shows mood, size shows energy</p>
	{#if loading}
		<div class="loading">
			<div class="loading-pulse"></div>
		</div>
	{:else if error}
		<div class="error-state">{error}</div>
	{:else if !data || data.length === 0}
		<div class="empty-state">No mood data yet</div>
	{:else}
		<div class="chart-wrapper">
			<canvas bind:this={canvas}></canvas>
		</div>
	{/if}
</div>

<style>
	.scatter-container {
		background: var(--bg-secondary);
		border-radius: 8px;
		padding: 16px;
	}

	.chart-title {
		font-size: 13px;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.5px;
		color: var(--text-secondary);
		margin-bottom: 2px;
	}

	.teaching-note {
		font-size: 11px;
		color: var(--text-dim);
		margin-bottom: 8px;
	}

	.chart-wrapper {
		position: relative;
		height: 320px;
	}

	.loading {
		display: flex;
		align-items: center;
		justify-content: center;
		height: 320px;
	}

	.loading-pulse {
		width: 40px;
		height: 40px;
		border-radius: 50%;
		background: var(--accent);
		opacity: 0.3;
		animation: pulse 1.2s ease-in-out infinite;
	}

	@keyframes pulse {
		0%, 100% { opacity: 0.15; transform: scale(0.8); }
		50% { opacity: 0.4; transform: scale(1); }
	}

	.error-state,
	.empty-state {
		display: flex;
		align-items: center;
		justify-content: center;
		height: 320px;
		color: var(--text-dim);
		font-size: 13px;
	}

	.error-state {
		color: var(--energy-high);
	}
</style>
