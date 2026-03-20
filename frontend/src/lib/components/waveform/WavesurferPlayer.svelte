<script lang="ts">
	import { onMount } from 'svelte';
	import WaveSurfer from 'wavesurfer.js';
	import { decodeFloat32, formatTime } from '$lib/utils/waveform';
	import { getWaveformBands } from '$lib/api/waveforms';
	import { API_BASE } from '$lib/api/client';

	// Band colors: unplayed / played (darker)
	const BAND_COLORS = [
		{ unplayed: '#e74c3c', played: '#c0392b' }, // bass — red
		{ unplayed: '#e67e22', played: '#d35400' }, // mid-low — orange
		{ unplayed: '#2ecc71', played: '#27ae60' }, // mid-high — green
		{ unplayed: '#3498db', played: '#2980b9' }, // high — blue
	] as const;

	let {
		trackId,
		peaks,
		duration,
		beats = null,
		height = 128,
		waveColor = '#00CED1',
		progressColor = '#00A8AB',
		spectral = true,
		autoplay = false,
		onfinish,
		onready,
	}: {
		trackId: number;
		peaks: string;
		duration: number;
		beats?: string | null;
		height?: number;
		waveColor?: string;
		progressColor?: string;
		/** When true, fetch band data and render spectral (multi-color) waveform if available. */
		spectral?: boolean;
		autoplay?: boolean;
		onfinish?: () => void;
		onready?: (ws: WaveSurfer) => void;
	} = $props();

	let container: HTMLDivElement;
	let ws: WaveSurfer | null = null;
	let currentTime = $state(0);
	let isPlaying = $state(false);
	/** Whether the spectral view is currently active (may be false even if spectral=true when band data is unavailable). */
	let spectralActive = $state(false);
	/** Cached band arrays: [low, midlow, midhigh, high] */
	let bandArrays = $state<Float32Array[] | null>(null);

	/**
	 * Build a WaveSurfer renderFunction that draws stacked frequency-band bars.
	 * Each bar is split vertically into 4 colored segments proportional to band energy.
	 * The played (progress) portion uses darker color variants.
	 *
	 * WaveSurfer calls this with the full canvas — progress overlay is handled
	 * separately via the built-in cursor/progress mechanism. We render once;
	 * WaveSurfer composites the progress mask on top.
	 */
	function buildSpectralRenderer(bands: Float32Array[]) {
		return (_peaks: Array<Float32Array | number[]>, ctx: CanvasRenderingContext2D) => {
			const [low, midlow, midhigh, high] = bands;
			const { width, height: h } = ctx.canvas;
			const n = low.length;
			if (n === 0) return;

			// Find peak total energy across all bars for normalization
			let maxTotal = 0;
			for (let i = 0; i < n; i++) {
				const t = low[i] + midlow[i] + midhigh[i] + high[i];
				if (t > maxTotal) maxTotal = t;
			}
			if (maxTotal < 0.001) return;

			const barW = width / n;
			const mid = h / 2; // center line — mirror up and down like classic waveform
			ctx.clearRect(0, 0, width, h);

			for (let i = 0; i < n; i++) {
				const lo = low[i];
				const ml = midlow[i];
				const mh = midhigh[i];
				const hi = high[i];
				const total = lo + ml + mh + hi;
				if (total < 0.001) continue;

				// Half-height of bar (will be mirrored above and below center)
				const halfH = Math.max(1, (total / maxTotal) * mid);
				const x = i * barW;
				const bw = Math.max(1, barW - 1);

				const segs: [number, string][] = [
					[lo, BAND_COLORS[0].unplayed],
					[ml, BAND_COLORS[1].unplayed],
					[mh, BAND_COLORS[2].unplayed],
					[hi, BAND_COLORS[3].unplayed],
				];

				// Draw upper half: bass near center, highs at top
				let yUp = mid;
				for (const [val, color] of segs) {
					if (val < 0.0001) continue;
					const segH = (val / total) * halfH;
					yUp -= segH;
					ctx.fillStyle = color;
					ctx.fillRect(x, yUp, bw, segH);
				}

				// Draw lower half (mirror): bass near center, highs at bottom
				let yDown = mid;
				for (const [val, color] of segs) {
					if (val < 0.0001) continue;
					const segH = (val / total) * halfH;
					ctx.fillStyle = color;
					ctx.fillRect(x, yDown, bw, segH);
					yDown += segH;
				}
			}
		};
	}

	onMount(() => {
		const peakData = decodeFloat32(peaks);

		async function init() {
			let renderFunction: ((peaks: Array<Float32Array | number[]>, ctx: CanvasRenderingContext2D) => void) | undefined;
			let wsPeaks: Array<Float32Array | number[]> = [peakData];

			// Attempt to fetch band data when spectral mode is requested
			if (spectral) {
				try {
					const bandsData = await getWaveformBands(trackId);
					bandArrays = [
						decodeFloat32(bandsData.low),
						decodeFloat32(bandsData.midlow),
						decodeFloat32(bandsData.midhigh),
						decodeFloat32(bandsData.high),
					];
					renderFunction = buildSpectralRenderer(bandArrays);
					// Pass band arrays as peaks so renderFunction receives them
					wsPeaks = bandArrays;
					spectralActive = true;
				} catch {
					// Band data not available — fall back to single-color rendering
					spectralActive = false;
				}
			}

			ws = WaveSurfer.create({
				container,
				height,
				waveColor: spectralActive ? 'transparent' : waveColor,
				progressColor: spectralActive ? 'rgba(255,255,255,0.2)' : progressColor,
				cursorColor: '#fff',
				cursorWidth: 1,
				barWidth: 2,
				barGap: 1,
				barRadius: 1,
				normalize: !spectralActive, // spectral renderer handles its own scaling
				backend: 'MediaElement',
				peaks: wsPeaks,
				duration,
				url: `${API_BASE}/api/audio/${trackId}`,
				...(renderFunction ? { renderFunction } : {}),
			});

			ws.on('timeupdate', (time) => {
				currentTime = time;
			});

			ws.on('play', () => { isPlaying = true; });
			ws.on('pause', () => { isPlaying = false; });
			ws.on('finish', () => { onfinish?.(); });

			onready?.(ws);

			if (autoplay) {
				ws.once('ready', () => { ws?.play(); });
			}
		}

		init();

		return () => {
			ws?.destroy();
		};
	});

	function togglePlay() {
		ws?.playPause();
	}

	/** Toggle between spectral and classic rendering. Requires re-creating the WaveSurfer instance. */
	async function toggleSpectral() {
		if (!ws) return;

		const wasPlaying = isPlaying;
		const time = ws.getCurrentTime();
		ws.destroy();
		ws = null;

		spectralActive = !spectralActive;

		let renderFunction: ((peaks: Array<Float32Array | number[]>, ctx: CanvasRenderingContext2D) => void) | undefined;
		let wsPeaks: Array<Float32Array | number[]> = [decodeFloat32(peaks)];

		if (spectralActive && bandArrays) {
			renderFunction = buildSpectralRenderer(bandArrays);
			wsPeaks = bandArrays;
		}

		ws = WaveSurfer.create({
			container,
			height,
			waveColor: spectralActive ? 'transparent' : waveColor,
			progressColor: spectralActive ? 'rgba(255,255,255,0.2)' : progressColor,
			cursorColor: '#fff',
			cursorWidth: 1,
			barWidth: 2,
			barGap: 1,
			barRadius: 1,
			normalize: !spectralActive,
			backend: 'MediaElement',
			peaks: wsPeaks,
			duration,
			url: `${API_BASE}/api/audio/${trackId}`,
			...(renderFunction ? { renderFunction } : {}),
		});

		ws.on('timeupdate', (t) => { currentTime = t; });
		ws.on('play', () => { isPlaying = true; });
		ws.on('pause', () => { isPlaying = false; });
		ws.on('finish', () => { onfinish?.(); });

		onready?.(ws);

		ws.once('ready', () => {
			ws?.seekTo(duration > 0 ? time / duration : 0);
			if (wasPlaying) ws?.play();
		});
	}
</script>

<div class="wavesurfer-player">
	<div class="controls">
		<button class="play-btn" onclick={togglePlay}>
			{isPlaying ? '⏸' : '▶'}
		</button>
		<span class="time">{formatTime(currentTime)} / {formatTime(duration)}</span>
		{#if spectral && bandArrays}
			<button
				class="spectral-toggle"
				class:active={spectralActive}
				onclick={toggleSpectral}
				title={spectralActive ? 'Switch to classic view' : 'Switch to spectral view'}
			>
				<span class="spectral-icon">
					{#if spectralActive}
						<span class="band band-low"></span>
						<span class="band band-midlow"></span>
						<span class="band band-midhigh"></span>
						<span class="band band-high"></span>
					{:else}
						<span class="band band-classic"></span>
					{/if}
				</span>
				{spectralActive ? 'Spectral' : 'Classic'}
			</button>
		{/if}
	</div>
	<div class="waveform-container" bind:this={container}></div>
</div>

<style>
	.wavesurfer-player {
		background: var(--waveform-bg);
		border-radius: 4px;
		overflow: hidden;
	}

	.controls {
		display: flex;
		align-items: center;
		gap: 10px;
		padding: 6px 10px;
	}

	.play-btn {
		width: 32px;
		height: 32px;
		border-radius: 50%;
		background: var(--accent);
		color: #000;
		font-size: 14px;
		display: flex;
		align-items: center;
		justify-content: center;
	}

	.play-btn:hover {
		background: var(--accent-dim);
	}

	.time {
		font-size: 12px;
		color: var(--text-secondary);
		font-variant-numeric: tabular-nums;
	}

	.waveform-container {
		padding: 0 10px 10px;
	}

	/* Spectral toggle button */
	.spectral-toggle {
		margin-left: auto;
		display: flex;
		align-items: center;
		gap: 5px;
		padding: 3px 8px;
		border-radius: 12px;
		border: 1px solid var(--border, #333);
		background: transparent;
		color: var(--text-secondary);
		font-size: 11px;
		cursor: pointer;
		transition: border-color 0.15s, color 0.15s;
	}

	.spectral-toggle:hover {
		border-color: var(--accent, #00CED1);
		color: var(--text, #fff);
	}

	.spectral-toggle.active {
		border-color: var(--accent, #00CED1);
		color: var(--accent, #00CED1);
	}

	.spectral-icon {
		display: flex;
		align-items: flex-end;
		gap: 1px;
		height: 12px;
	}

	.band {
		display: inline-block;
		width: 3px;
		border-radius: 1px;
	}

	.band-low     { background: #e74c3c; height: 12px; }
	.band-midlow  { background: #e67e22; height: 9px; }
	.band-midhigh { background: #2ecc71; height: 7px; }
	.band-high    { background: #3498db; height: 5px; }
	.band-classic { background: #00CED1; height: 10px; }
</style>
