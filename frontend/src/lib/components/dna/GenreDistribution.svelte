<script lang="ts">
	import {
		Chart,
		DoughnutController,
		ArcElement,
		Tooltip,
		Legend,
	} from 'chart.js';
	import { getLibraryStats } from '$lib/api/stats';
	import type { LibraryStats } from '$lib/types';

	Chart.register(DoughnutController, ArcElement, Tooltip, Legend);

	const FAMILY_COLORS: Record<string, string> = {
		Techno: '#40E0D0',
		House: '#FF7F50',
		Groove: '#66BB6A',
		Trance: '#9575CD',
		Breaks: '#FFB74D',
		Electronic: '#42A5F5',
		Other: '#95a5a6',
	};

	const GENRE_TO_FAMILY: Record<string, string> = {
		'Techno': 'Techno',
		'Minimal / Deep Tech': 'Techno',
		'Hard Techno': 'Techno',
		'Industrial Techno': 'Techno',
		'Acid Techno': 'Techno',
		'House': 'House',
		'Deep House': 'House',
		'Tech House': 'House',
		'Progressive House': 'House',
		'Afro House': 'House',
		'Melodic House & Techno': 'House',
		'Organic House / Downtempo': 'House',
		'Funky / Groove / Jackin\' House': 'Groove',
		'Disco / Nu-Disco': 'Groove',
		'Funk / Soul': 'Groove',
		'Indie Dance': 'Groove',
		'Electronica': 'Electronic',
		'Downtempo': 'Electronic',
		'Ambient': 'Electronic',
		'Trance': 'Trance',
		'Psy-Trance': 'Trance',
		'Progressive Trance': 'Trance',
		'Breaks': 'Breaks',
		'Breakbeat': 'Breaks',
		'UK Garage': 'Breaks',
		'Drum & Bass': 'Breaks',
	};

	let canvas: HTMLCanvasElement;
	let chart: Chart | null = null;
	let loading = $state(true);
	let error = $state<string | null>(null);
	let stats = $state<LibraryStats | null>(null);

	let teachingNote = $derived.by(() => {
		if (!stats) return '';
		const familyCounts = aggregateFamilies(stats.genres);
		const sorted = Object.entries(familyCounts).sort((a, b) => b[1] - a[1]);
		if (sorted.length === 0) return '';
		const dominant = sorted[0][0];
		const pct = Math.round((sorted[0][1] / stats.total_tracks) * 100);
		const weakest = sorted[sorted.length - 1];
		return `${dominant} dominates at ${pct}% — exploring more ${weakest[0]} could widen your mix palette`;
	});

	function aggregateFamilies(genres: Record<string, number>): Record<string, number> {
		const families: Record<string, number> = {};
		for (const [genre, count] of Object.entries(genres)) {
			const family = GENRE_TO_FAMILY[genre] ?? 'Other';
			families[family] = (families[family] ?? 0) + count;
		}
		return families;
	}

	$effect(() => {
		let destroyed = false;

		(async () => {
			try {
				loading = true;
				error = null;
				const data = await getLibraryStats();

				if (destroyed) return;
				stats = data;

				const familyCounts = aggregateFamilies(data.genres);
				const sorted = Object.entries(familyCounts).sort((a, b) => b[1] - a[1]);
				const labels = sorted.map(([f]) => f);
				const values = sorted.map(([, c]) => c);
				const colors = labels.map((f) => FAMILY_COLORS[f] ?? FAMILY_COLORS.Other);

				chart = new Chart(canvas, {
					type: 'doughnut',
					data: {
						labels,
						datasets: [{
							data: values,
							backgroundColor: colors,
							borderColor: 'rgba(13, 13, 13, 0.8)',
							borderWidth: 2,
						}],
					},
					options: {
						responsive: true,
						maintainAspectRatio: true,
						cutout: '55%',
						plugins: {
							legend: {
								display: true,
								position: 'bottom',
								labels: {
									color: '#F5F5F0',
									font: { size: 11 },
									padding: 12,
									boxWidth: 12,
								},
							},
							tooltip: {
								callbacks: {
									label: (ctx) => {
										const total = values.reduce((a, b) => a + b, 0);
										const pct = total > 0 ? Math.round((ctx.raw as number) / total * 100) : 0;
										return `${ctx.label}: ${ctx.raw} tracks (${pct}%)`;
									},
								},
							},
						},
					},
					plugins: [{
						id: 'centerText',
						beforeDraw: (chartInstance) => {
							const { ctx: drawCtx, chartArea } = chartInstance;
							if (!chartArea) return;
							const centerX = (chartArea.left + chartArea.right) / 2;
							const centerY = (chartArea.top + chartArea.bottom) / 2;

							drawCtx.save();
							drawCtx.textAlign = 'center';
							drawCtx.textBaseline = 'middle';

							drawCtx.font = 'bold 22px -apple-system, BlinkMacSystemFont, sans-serif';
							drawCtx.fillStyle = '#F5F5F0';
							drawCtx.fillText(String(data.total_tracks), centerX, centerY - 8);

							drawCtx.font = '11px -apple-system, BlinkMacSystemFont, sans-serif';
							drawCtx.fillStyle = '#A0A1A7';
							drawCtx.fillText('tracks', centerX, centerY + 12);

							drawCtx.restore();
						},
					}],
				});
			} catch (e) {
				if (!destroyed) {
					error = e instanceof Error ? e.message : "Couldn't load genre data — try refreshing";
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

<div class="genre-distribution">
	<h3 class="chart-title">Genre Families</h3>
	<p class="teaching-note">How your collection clusters into genre families — balance means versatility</p>
	{#if loading}
		<div class="loading">Mapping your genres...</div>
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
	.genre-distribution {
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

	.insight {
		font-size: 11px;
		color: var(--accent);
		margin-top: 8px;
		line-height: 1.4;
	}
</style>
