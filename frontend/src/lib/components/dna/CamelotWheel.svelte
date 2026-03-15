<script lang="ts">
	import {
		Chart,
		PolarAreaController,
		RadialLinearScale,
		ArcElement,
		Tooltip,
		Legend,
	} from 'chart.js';
	import { getCamelotStats } from '$lib/api/stats';

	Chart.register(PolarAreaController, RadialLinearScale, ArcElement, Tooltip, Legend);

	let canvas: HTMLCanvasElement;
	let chart: Chart | null = null;
	let loading = $state(true);
	let error = $state<string | null>(null);

	const CAMELOT_LABELS = Array.from({ length: 12 }, (_, i) => String(i + 1));

	$effect(() => {
		let destroyed = false;

		(async () => {
			try {
				loading = true;
				error = null;
				const data = await getCamelotStats();

				if (destroyed) return;

				const minorCounts = CAMELOT_LABELS.map((k) => data[k]?.A ?? 0);
				const majorCounts = CAMELOT_LABELS.map((k) => data[k]?.B ?? 0);

				chart = new Chart(canvas, {
					type: 'polarArea',
					data: {
						labels: CAMELOT_LABELS.map((k) => `${k}A / ${k}B`),
						datasets: [
							{
								label: 'Minor (A)',
								data: minorCounts,
								backgroundColor: CAMELOT_LABELS.map(
									() => 'rgba(64, 224, 208, 0.6)'
								),
								borderColor: 'rgba(64, 224, 208, 0.8)',
								borderWidth: 1,
							},
							{
								label: 'Major (B)',
								data: majorCounts,
								backgroundColor: CAMELOT_LABELS.map(
									() => 'rgba(255, 127, 80, 1.0)'
								),
								borderColor: 'rgba(255, 127, 80, 0.8)',
								borderWidth: 1,
							},
						],
					},
					options: {
						responsive: true,
						maintainAspectRatio: true,
						plugins: {
							legend: {
								display: true,
								position: 'bottom',
								labels: {
									color: '#F5F5F0',
									font: { size: 12 },
									padding: 16,
								},
							},
							tooltip: {
								callbacks: {
									title: (items) => {
										const idx = items[0]?.dataIndex;
										if (idx == null) return '';
										return `Key ${CAMELOT_LABELS[idx]}`;
									},
									label: (item) => {
										const idx = item.dataIndex;
										const key = CAMELOT_LABELS[idx];
										const dsLabel = item.dataset.label ?? '';
										const suffix = dsLabel.includes('Minor') ? 'A' : 'B';
										return `${key}${suffix}: ${item.raw} tracks`;
									},
								},
							},
						},
						scales: {
							r: {
								grid: { color: 'rgba(63, 65, 74, 0.5)' },
								ticks: {
									color: '#666',
									backdropColor: 'transparent',
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
					error = e instanceof Error ? e.message : "Couldn't read your key data — try refreshing";
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

<div class="camelot-wheel">
	<h3 class="chart-title">Camelot Key Distribution</h3>
	<p class="teaching-note">Your harmonic coverage — gaps here mean fewer mix options in those keys</p>
	{#if loading}
		<div class="loading">Mapping your keys...</div>
	{:else if error}
		<div class="error">{error}</div>
	{/if}
	<div class="chart-container" class:hidden={loading || !!error}>
		<canvas bind:this={canvas}></canvas>
	</div>
</div>

<style>
	.camelot-wheel {
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
</style>
