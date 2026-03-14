<script lang="ts">
	import { onMount } from 'svelte';
	import type { SetWaveformTrack } from '$lib/types';
	import { decodeFloat32, formatTime } from '$lib/utils/waveform';
	import { getCamelotColor } from '$lib/utils/camelot';

	let {
		tracks,
		mode = 'linear',
		onTransitionClick,
	}: {
		tracks: SetWaveformTrack[];
		mode?: 'linear' | 'staircase';
		onTransitionClick?: (index: number) => void;
	} = $props();

	let canvas: HTMLCanvasElement;
	let hoveredTransition = $state<number | null>(null);

	const TRACK_COLORS = [
		'#00bcd4', '#e94560', '#2ecc71', '#f39c12',
		'#9b59b6', '#1abc9c', '#e67e22', '#3498db',
	];

	// Track boundary positions for click detection
	let trackBoundaries: { x: number; width: number; position: number }[] = [];
	let transitionZones: { x: number; width: number; index: number }[] = [];

	$effect(() => {
		if (canvas && tracks.length > 0) {
			drawTimeline();
		}
	});

	function drawTimeline() {
		const ctx = canvas.getContext('2d');
		if (!ctx) return;

		const dpr = window.devicePixelRatio || 1;
		const rect = canvas.getBoundingClientRect();
		canvas.width = rect.width * dpr;
		canvas.height = rect.height * dpr;
		ctx.scale(dpr, dpr);

		const W = rect.width;
		const H = rect.height;

		ctx.fillStyle = '#111';
		ctx.fillRect(0, 0, W, H);

		if (mode === 'linear') {
			drawLinear(ctx, W, H);
		} else {
			drawStaircase(ctx, W, H);
		}
	}

	function drawLinear(ctx: CanvasRenderingContext2D, W: number, H: number) {
		const totalDuration = tracks.reduce((sum, t) => sum + (t.duration_sec ?? 300), 0);
		const headerH = 28;
		const waveH = H - headerH - 20;
		const waveY = headerH;

		trackBoundaries = [];
		transitionZones = [];
		let cumX = 0;

		for (let i = 0; i < tracks.length; i++) {
			const t = tracks[i];
			const dur = t.duration_sec ?? 300;
			const trackW = (dur / totalDuration) * W;
			const color = TRACK_COLORS[i % TRACK_COLORS.length];

			trackBoundaries.push({ x: cumX, width: trackW, position: t.position });

			// Draw waveform
			if (t.waveform_overview) {
				const peaks = decodeFloat32(t.waveform_overview);
				const step = peaks.length / trackW;
				let maxPeak = 0;
				for (let j = 0; j < peaks.length; j++) {
					if (peaks[j] > maxPeak) maxPeak = peaks[j];
				}
				if (maxPeak === 0) maxPeak = 1;

				ctx.fillStyle = color + '40';
				ctx.strokeStyle = color;
				ctx.lineWidth = 0.5;
				ctx.beginPath();

				for (let px = 0; px < trackW; px++) {
					const sampleIdx = Math.floor(px * step);
					const val = (peaks[sampleIdx] ?? 0) / maxPeak;
					const barH = val * waveH * 0.8;
					const x = cumX + px;
					const y = waveY + (waveH - barH) / 2;
					if (px === 0) ctx.moveTo(x, waveY + waveH / 2 + barH / 2);
					ctx.lineTo(x, waveY + waveH / 2 - barH / 2);
				}
				for (let px = Math.floor(trackW) - 1; px >= 0; px--) {
					const sampleIdx = Math.floor(px * step);
					const val = (peaks[sampleIdx] ?? 0) / maxPeak;
					const barH = val * waveH * 0.8;
					const x = cumX + px;
					ctx.lineTo(x, waveY + waveH / 2 + barH / 2);
				}
				ctx.closePath();
				ctx.fill();
				ctx.stroke();
			}

			// Track label in header
			ctx.fillStyle = color;
			ctx.font = '11px -apple-system, sans-serif';
			ctx.textAlign = 'center';
			const label = `${t.position}. ${t.title ?? '?'}`;
			const maxLabelW = trackW - 8;
			const truncated = truncateText(ctx, label, maxLabelW);
			ctx.fillText(truncated, cumX + trackW / 2, 12);

			// BPM + Key under title
			ctx.fillStyle = '#999';
			ctx.font = '10px -apple-system, sans-serif';
			const meta = `${t.bpm ? Math.round(t.bpm) : '?'} BPM | ${t.key ?? '?'}`;
			ctx.fillText(truncateText(ctx, meta, maxLabelW), cumX + trackW / 2, 24);

			// Transition boundary line
			if (i > 0) {
				ctx.strokeStyle = '#e94560';
				ctx.lineWidth = 1;
				ctx.setLineDash([3, 3]);
				ctx.beginPath();
				ctx.moveTo(cumX, waveY);
				ctx.lineTo(cumX, waveY + waveH);
				ctx.stroke();
				ctx.setLineDash([]);

				// Transition score
				const score = t.transition_score;
				if (score != null) {
					ctx.fillStyle = '#f39c12';
					ctx.font = 'bold 10px -apple-system, sans-serif';
					ctx.textAlign = 'center';
					ctx.fillText(score.toFixed(2), cumX, waveY + waveH + 14);
				}

				// Clickable zone
				transitionZones.push({ x: cumX - 15, width: 30, index: i - 1 });
			}

			cumX += trackW;
		}
	}

	function drawStaircase(ctx: CanvasRenderingContext2D, W: number, H: number) {
		const laneH = Math.min(80, (H - 20) / tracks.length);
		const totalDuration = tracks.reduce((sum, t) => sum + (t.duration_sec ?? 300), 0);
		const overlapFraction = 0.1;

		trackBoundaries = [];
		transitionZones = [];

		// Compute start positions with overlap
		const starts: number[] = [0];
		for (let i = 1; i < tracks.length; i++) {
			const prevDur = tracks[i - 1].duration_sec ?? 300;
			starts.push(starts[i - 1] + prevDur * (1 - overlapFraction));
		}
		const lastEnd = starts[starts.length - 1] + (tracks[tracks.length - 1].duration_sec ?? 300);
		const pxPerSec = W / lastEnd;

		for (let i = 0; i < tracks.length; i++) {
			const t = tracks[i];
			const dur = t.duration_sec ?? 300;
			const color = TRACK_COLORS[i % TRACK_COLORS.length];
			const xStart = starts[i] * pxPerSec;
			const trackW = dur * pxPerSec;
			const yTop = i * laneH;

			trackBoundaries.push({ x: xStart, width: trackW, position: t.position });

			// Draw waveform in lane
			if (t.waveform_overview) {
				const peaks = decodeFloat32(t.waveform_overview);
				const step = peaks.length / trackW;
				let maxPeak = 0;
				for (let j = 0; j < peaks.length; j++) {
					if (peaks[j] > maxPeak) maxPeak = peaks[j];
				}
				if (maxPeak === 0) maxPeak = 1;

				ctx.fillStyle = color + '30';
				ctx.strokeStyle = color;
				ctx.lineWidth = 0.5;
				ctx.beginPath();

				for (let px = 0; px < trackW; px++) {
					const sampleIdx = Math.floor(px * step);
					const val = (peaks[sampleIdx] ?? 0) / maxPeak;
					const barH = val * (laneH - 18) * 0.9;
					const x = xStart + px;
					if (px === 0) ctx.moveTo(x, yTop + laneH - 2);
					ctx.lineTo(x, yTop + laneH - 2 - barH);
				}
				for (let px = Math.floor(trackW) - 1; px >= 0; px--) {
					ctx.lineTo(xStart + px, yTop + laneH - 2);
				}
				ctx.closePath();
				ctx.fill();
				ctx.stroke();
			}

			// Lane label
			ctx.fillStyle = color;
			ctx.font = '11px -apple-system, sans-serif';
			ctx.textAlign = 'left';
			ctx.fillText(
				truncateText(ctx, `${t.position}. ${t.title ?? '?'}`, trackW - 4),
				xStart + 4,
				yTop + 12,
			);

			// Overlap zone highlight
			if (i < tracks.length - 1) {
				const nextStart = starts[i + 1] * pxPerSec;
				const overlapEnd = xStart + trackW;
				if (nextStart < overlapEnd) {
					ctx.fillStyle = 'rgba(243, 156, 18, 0.08)';
					ctx.fillRect(nextStart, yTop, overlapEnd - nextStart, laneH);

					const score = tracks[i + 1].transition_score;
					if (score != null) {
						ctx.fillStyle = '#f39c12';
						ctx.font = 'bold 10px -apple-system, sans-serif';
						ctx.textAlign = 'center';
						ctx.fillText(score.toFixed(2), (nextStart + overlapEnd) / 2, yTop + laneH / 2 + 4);
					}

					transitionZones.push({
						x: nextStart,
						width: overlapEnd - nextStart,
						index: i,
					});
				}
			}

			// Lane separator
			if (i > 0) {
				ctx.strokeStyle = '#2a2a4a';
				ctx.lineWidth = 1;
				ctx.setLineDash([2, 4]);
				ctx.beginPath();
				ctx.moveTo(0, yTop);
				ctx.lineTo(W, yTop);
				ctx.stroke();
				ctx.setLineDash([]);
			}
		}
	}

	function truncateText(ctx: CanvasRenderingContext2D, text: string, maxW: number): string {
		if (maxW < 20) return '';
		if (ctx.measureText(text).width <= maxW) return text;
		let t = text;
		while (t.length > 3 && ctx.measureText(t + '...').width > maxW) {
			t = t.slice(0, -1);
		}
		return t + '...';
	}

	function handleClick(e: MouseEvent) {
		if (!onTransitionClick) return;
		const rect = canvas.getBoundingClientRect();
		const x = e.clientX - rect.left;
		for (const zone of transitionZones) {
			if (x >= zone.x && x <= zone.x + zone.width) {
				onTransitionClick(zone.index);
				return;
			}
		}
	}

	function handleMouseMove(e: MouseEvent) {
		const rect = canvas.getBoundingClientRect();
		const x = e.clientX - rect.left;
		let found = false;
		for (const zone of transitionZones) {
			if (x >= zone.x && x <= zone.x + zone.width) {
				hoveredTransition = zone.index;
				canvas.style.cursor = 'pointer';
				found = true;
				break;
			}
		}
		if (!found) {
			hoveredTransition = null;
			canvas.style.cursor = 'default';
		}
	}
</script>

<canvas
	bind:this={canvas}
	class="timeline-canvas"
	onclick={handleClick}
	onmousemove={handleMouseMove}
	onmouseleave={() => { hoveredTransition = null; canvas.style.cursor = 'default'; }}
></canvas>

<style>
	.timeline-canvas {
		width: 100%;
		height: 100%;
		display: block;
	}
</style>
