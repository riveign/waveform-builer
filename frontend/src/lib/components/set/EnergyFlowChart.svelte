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
	import { getTrackEnergyNumeric } from '$lib/utils/energy';
	import { formatKey } from '$lib/utils/camelot';
	import { deviationColors, chartChrome, rgba, token } from '$lib/styles/canvasPalette';

	Chart.register(LineController, LineElement, PointElement, CategoryScale, LinearScale, Tooltip, Legend, Filler);

	interface Props {
		tracks: SetWaveformTrack[];
		energyProfile?: string | null;
		selectedIndex?: number;
		onTrackClick?: (index: number) => void;
		plannedCurve?: number[] | null;
	}

	let { tracks, energyProfile, selectedIndex, onTrackClick, plannedCurve = null }: Props = $props();

	let canvas = $state<HTMLCanvasElement>(null!);
	let chart: Chart | null = null;

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

	/** Fit verdict for a point, derived from how far it sits from the target. */
	type FitVerdict = 'good' | 'acceptable' | 'poor' | 'no-target';

	function deviationVerdict(actual: number | null, target: number | null): FitVerdict {
		if (actual === null || target === null) return 'no-target';
		const dev = Math.abs(actual - target);
		if (dev <= 0.15) return 'good';
		if (dev <= 0.3) return 'acceptable';
		return 'poor';
	}

	/** Determine deviation color for a point — reads the in-book --score-* ramp. */
	function deviationColor(actual: number | null, target: number | null): string {
		const colors = deviationColors();
		const verdict = deviationVerdict(actual, target);
		const hex =
			verdict === 'good'
				? colors.good
				: verdict === 'acceptable'
					? colors.acceptable
					: verdict === 'poor'
						? colors.poor
						: colors.noTarget;
		// Tokens resolve to a #rrggbb; render at 0.9 alpha to match the prior look.
		return rgba(hex, 0.9);
	}

	/**
	 * Non-color cue paired with each fit color, so the verdict survives for
	 * colorblind DJs (color-only is not the only signal). Chart.js point styles:
	 * circle = good fit, rect = drifting, triangle = off the arc.
	 */
	function deviationPointStyle(actual: number | null, target: number | null): string {
		switch (deviationVerdict(actual, target)) {
			case 'poor':
				return 'triangle';
			case 'acceptable':
				return 'rect';
			default:
				return 'circle';
		}
	}

	/** Words shown in the tooltip / summary so the fit verdict is readable text. */
	function verdictLabel(v: FitVerdict): string {
		switch (v) {
			case 'good':
				return 'on the arc';
			case 'acceptable':
				return 'drifting';
			case 'poor':
				return 'off the arc';
			default:
				return 'no target set';
		}
	}

	function buildChartData() {
		const labels = tracks.map((_, i) => String(i + 1));
		const actualValues = tracks.map((t) => getTrackEnergyNumeric(t.energy_value, t.energy));
		const targetValues = parseEnergyProfile(energyProfile, tracks.length);
		const hasTarget = targetValues.some((v) => v !== null);

		// Point colors based on deviation from target
		const pointColors = actualValues.map((actual, i) => deviationColor(actual, targetValues[i]));

		// Segment colors for the line between points
		const segmentColors = actualValues.map((actual, i) => deviationColor(actual, targetValues[i]));

		// Selected point styling
		const pointRadii = actualValues.map((_, i) => (i === selectedIndex ? 7 : 3));
		const pointBorderWidths = actualValues.map((_, i) => (i === selectedIndex ? 2 : 0));

		// Non-color cue: point SHAPE also encodes fit (color is not the only signal).
		const pointStyles = actualValues.map((actual, i) => deviationPointStyle(actual, targetValues[i]));

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
			pointStyle: pointStyles,
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
				label: 'Target — dashed',
				data: targetValues,
				borderColor: rgba(chartChrome().text, 0.35),
				borderWidth: 1.5,
				borderDash: [6, 4],
				pointRadius: 0,
				pointHoverRadius: 0,
				tension: 0.3,
				fill: false,
				order: 2,
			});
		}

		// Planned curve overlay (played-vs-planned comparison)
		if (plannedCurve && plannedCurve.length === tracks.length) {
			datasets.push({
				label: 'Planned — dotted',
				data: plannedCurve,
				borderColor: rgba(token('--energy-mid', '#BA94BA'), 0.8),
				borderWidth: 1.5,
				borderDash: [2, 3],
				pointRadius: 0,
				pointHoverRadius: 0,
				tension: 0.3,
				fill: false,
				order: 3,
			});
		}

		return { labels, datasets };
	}

	function createChart() {
		if (!canvas) return;
		const { labels, datasets } = buildChartData();
		const targetValues = parseEnergyProfile(energyProfile, tracks.length);
		const chrome = chartChrome();

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
						display: targetValues.some((v) => v !== null) || (plannedCurve?.length ?? 0) > 0,
						position: 'bottom',
						labels: {
							color: chrome.label,
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
						backgroundColor: rgba(chrome.surface, 0.95),
						titleColor: chrome.text,
						bodyColor: chrome.label,
						borderColor: rgba(chrome.text, 0.1),
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
									const verdict = deviationVerdict(val, targetValues[idx]);
									if (verdict !== 'no-target') lines.push(`Fit: ${verdictLabel(verdict)}`);
									if (t.bpm) lines.push(`BPM: ${t.bpm}`);
									if (t.key) lines.push(`Key: ${formatKey(t.key)}`);
									if (t.transition_score !== null && t.transition_score !== undefined) {
										lines.push(`Transition: ${(t.transition_score * 100).toFixed(0)}%`);
									}
									return lines;
								}
								// Target / Planned overlay datasets
								const val = ctx.parsed.y;
								if (val !== null) return `${ctx.dataset.label ?? 'Target'}: ${val.toFixed(2)}`;
								return '';
							},
						},
					},
				},
				scales: {
					x: {
						grid: { color: rgba(chrome.border, 0.3) },
						ticks: {
							color: chrome.muted,
							font: { size: 10 },
						},
						title: {
							display: true,
							text: 'Track #',
							color: chrome.tick,
							font: { size: 10 },
						},
					},
					y: {
						min: 0,
						max: 1,
						grid: { color: rgba(chrome.border, 0.3) },
						ticks: {
							color: chrome.muted,
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
							color: chrome.tick,
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
		const targetValues = parseEnergyProfile(energyProfile, tracks.length);
		if (chart.options.plugins?.legend) {
			chart.options.plugins.legend.display =
				targetValues.some((v) => v !== null) || (plannedCurve?.length ?? 0) > 0;
		}
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
		void plannedCurve;

		if (chart) {
			updateChart();
		}
	});

	/**
	 * Screen-reader path for the canvas: a per-track table + a one-line headline.
	 * Mirrors the EnergyGenreHeatmap per-cell aria pattern — the chart's data is
	 * the lesson, so a blind DJ gets the same arc the sighted one sees.
	 */
	interface SummaryRow {
		index: number;
		title: string;
		energyLabel: string;
		verdict: string;
	}

	let summaryRows = $derived.by<SummaryRow[]>(() => {
		const targets = parseEnergyProfile(energyProfile, tracks.length);
		return tracks.map((t, i) => {
			const actual = getTrackEnergyNumeric(t.energy_value, t.energy);
			const verdict = deviationVerdict(actual, targets[i]);
			return {
				index: i + 1,
				title: t.title ?? `Track ${i + 1}`,
				energyLabel: actual === null ? 'no reading' : `${Math.round(actual * 9)}/9`,
				verdict: verdictLabel(verdict),
			};
		});
	});

	let chartSummary = $derived.by(() => {
		if (tracks.length === 0) return '';
		const targets = parseEnergyProfile(energyProfile, tracks.length);
		const hasTarget = targets.some((v) => v !== null);
		const energies = tracks
			.map((t) => getTrackEnergyNumeric(t.energy_value, t.energy))
			.filter((v): v is number => v !== null);
		const start = energies.length ? Math.round(energies[0] * 9) : null;
		const end = energies.length ? Math.round(energies[energies.length - 1] * 9) : null;
		const arc =
			start !== null && end !== null
				? start < end
					? `building from ${start}/9 to ${end}/9`
					: start > end
						? `easing from ${start}/9 down to ${end}/9`
						: `holding around ${start}/9`
				: 'energy not yet read';
		const offCount = hasTarget
			? tracks.filter(
					(t, i) =>
						deviationVerdict(getTrackEnergyNumeric(t.energy_value, t.energy), targets[i]) === 'poor',
				).length
			: 0;
		const fitNote = !hasTarget
			? 'no target arc set'
			: offCount === 0
				? 'every track on the arc'
				: `${offCount} track${offCount === 1 ? '' : 's'} off the arc`;
		return `Energy flow across ${tracks.length} track${tracks.length === 1 ? '' : 's'}: ${arc}, ${fitNote}.`;
	});
</script>

<div class="energy-flow-chart">
	<h3 class="chart-title">Energy Flow</h3>
	{#if tracks.length === 0}
		<div class="empty">Add tracks to see the set's arc</div>
	{:else}
		<!-- The canvas is a visual duplicate of the sr-only summary + table below,
		     which is the real accessible representation; hide the canvas from AT. -->
		<div class="chart-container">
			<canvas bind:this={canvas} aria-hidden="true"></canvas>
		</div>
		<div class="sr-only" role="img" aria-label={chartSummary}>
			<p>{chartSummary}</p>
			<table>
				<caption>Energy by track. Fit shows how each track sits against the target arc.</caption>
				<thead>
					<tr>
						<th scope="col">#</th>
						<th scope="col">Track</th>
						<th scope="col">Energy</th>
						<th scope="col">Fit</th>
					</tr>
				</thead>
				<tbody>
					{#each summaryRows as row (row.index)}
						<tr>
							<td>{row.index}</td>
							<td>{row.title}</td>
							<td>{row.energyLabel}</td>
							<td>{row.verdict}</td>
						</tr>
					{/each}
				</tbody>
			</table>
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
