<script lang="ts">
	import { onMount } from 'svelte';
	import WaveSurfer from 'wavesurfer.js';
	import { decodeFloat32, formatTime } from '$lib/utils/waveform';
	import { getWaveformBands } from '$lib/api/waveforms';
	import { API_BASE } from '$lib/api/client';
	import { spectrumBands, token } from '$lib/styles/canvasPalette';

	/**
	 * Resolve a theme token to a concrete color at runtime. WaveSurfer paints to a
	 * canvas and needs a literal color, not a `var()` — and tokens chain through
	 * several `var()` indirections (--accent → --accent-9 → --teal-600). A probe
	 * element with `color: var(...)` lets the browser flatten the whole chain to a
	 * used rgb() value, so the waveform follows the app accent with no hardcoded hex.
	 */
	function resolveColor(expr: string, fallback: string): string {
		if (typeof window === 'undefined') return fallback;
		const probe = document.createElement('span');
		probe.style.color = expr;
		probe.style.display = 'none';
		document.body.appendChild(probe);
		const used = getComputedStyle(probe).color;
		probe.remove();
		return used || fallback;
	}

	// Band colors (unplayed / played) come from the centralized canvas palette —
	// a documented domain palette, so a future retint is a one-file change and
	// the legend below reads the SAME source.
	const BAND_COLORS = spectrumBands();

	let {
		trackId,
		peaks,
		duration,
		beats = null,
		height = 128,
		waveColor,
		progressColor,
		spectral = true,
		autoplay = false,
		/** When true, render waveform without loading audio — visual display only. */
		visualOnly = false,
		/** External playback progress (0-1) to sync cursor position when visualOnly is true. */
		externalProgress = 0,
		onfinish,
		onready,
		/** Fired when the user clicks the waveform in visualOnly mode (fraction 0-1). */
		onseek,
	}: {
		trackId: number;
		peaks: string;
		duration: number;
		beats?: string | null;
		height?: number;
		/** Wave color. Defaults to the app accent token resolved at runtime. */
		waveColor?: string;
		/** Progress (played) color. Defaults to the accent hover token. */
		progressColor?: string;
		/** When true, fetch band data and render spectral (multi-color) waveform if available. */
		spectral?: boolean;
		autoplay?: boolean;
		/** When true, render waveform without loading audio — visual display only. */
		visualOnly?: boolean;
		/** External playback progress (0-1) to sync cursor position when visualOnly is true. */
		externalProgress?: number;
		onfinish?: () => void;
		onready?: (ws: WaveSurfer) => void;
		onseek?: (fraction: number) => void;
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

	// Concrete colors for the canvas: caller-supplied literal, else the resolved
	// app accent tokens (so the waveform follows the theme flip). The SSR/probe
	// fallback comes from the shared palette's teal ramp, not an inline hex.
	const waveColorResolved = $derived(
		waveColor ?? resolveColor('var(--accent)', token('--teal-600', '#008A84')),
	);
	const progressColorResolved = $derived(
		progressColor ?? resolveColor('var(--accent-hover)', token('--teal-400', '#00B1B8')),
	);

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
				waveColor: spectralActive ? 'transparent' : waveColorResolved,
				progressColor: spectralActive ? 'rgba(255,255,255,0.2)' : progressColorResolved,
				cursorColor: '#fff',
				cursorWidth: 1,
				barWidth: 2,
				barGap: 1,
				barRadius: 1,
				normalize: !spectralActive, // spectral renderer handles its own scaling
				backend: 'MediaElement',
				peaks: wsPeaks,
				duration,
				// In visualOnly mode, skip loading audio — waveform is purely visual
				...(visualOnly ? {} : { url: `${API_BASE}/api/audio/${trackId}` }),
				...(renderFunction ? { renderFunction } : {}),
			});

			if (!visualOnly) {
				ws.on('timeupdate', (time) => {
					currentTime = time;
				});

				ws.on('play', () => { isPlaying = true; });
				ws.on('pause', () => { isPlaying = false; });
				ws.on('finish', () => { onfinish?.(); });
			} else {
				// Visual-only: clicks can't seek local audio (there is none), so
				// forward the clicked position to the owner (the global player).
				ws.on('click', (relativeX: number) => { onseek?.(relativeX); });
			}

			onready?.(ws);

			if (autoplay && !visualOnly) {
				ws.once('ready', () => { ws?.play(); });
			}
		}

		init();

		return () => {
			ws?.destroy();
		};
	});

	// Sync cursor position from external progress when in visual-only mode
	$effect(() => {
		if (visualOnly && ws && externalProgress >= 0) {
			ws.seekTo(Math.max(0, Math.min(1, externalProgress)));
			currentTime = externalProgress * duration;
		}
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
			waveColor: spectralActive ? 'transparent' : waveColorResolved,
			progressColor: spectralActive ? 'rgba(255,255,255,0.2)' : progressColorResolved,
			cursorColor: '#fff',
			cursorWidth: 1,
			barWidth: 2,
			barGap: 1,
			barRadius: 1,
			normalize: !spectralActive,
			backend: 'MediaElement',
			peaks: wsPeaks,
			duration,
			...(visualOnly ? {} : { url: `${API_BASE}/api/audio/${trackId}` }),
			...(renderFunction ? { renderFunction } : {}),
		});

		if (!visualOnly) {
			ws.on('timeupdate', (t) => { currentTime = t; });
			ws.on('play', () => { isPlaying = true; });
			ws.on('pause', () => { isPlaying = false; });
			ws.on('finish', () => { onfinish?.(); });
		} else {
			ws.on('click', (relativeX: number) => { onseek?.(relativeX); });
		}

		onready?.(ws);

		if (!visualOnly) {
			ws.once('ready', () => {
				ws?.seekTo(duration > 0 ? time / duration : 0);
				if (wasPlaying) ws?.play();
			});
		}
	}
</script>

<div class="wavesurfer-player">
	<div class="controls">
		{#if !visualOnly}
			<button class="play-btn" onclick={togglePlay} aria-label={isPlaying ? 'Pause' : 'Play'}>
				{isPlaying ? '⏸' : '▶'}
			</button>
		{/if}
		<span class="time">{formatTime(currentTime)} / {formatTime(duration)}</span>
		{#if spectral && bandArrays}
			<button
				class="spectral-toggle"
				class:active={spectralActive}
				onclick={toggleSpectral}
				aria-pressed={spectralActive}
				aria-label={spectralActive ? 'Switch to classic waveform' : 'Switch to spectral waveform'}
				title={spectralActive ? 'Switch to classic view' : 'Switch to spectral view'}
			>
				<span class="spectral-icon" aria-hidden="true">
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
	<div
		class="waveform-container"
		bind:this={container}
		role="img"
		aria-label={spectralActive
			? `Spectral waveform, ${formatTime(duration)} long, position ${formatTime(currentTime)}. Bars are split into four frequency bands: bass, low-mid, high-mid and high.`
			: `Audio waveform, ${formatTime(duration)} long, position ${formatTime(currentTime)}.`}
	></div>
	{#if spectralActive}
		<ul class="band-legend" aria-label="Frequency band colors">
			{#each BAND_COLORS as band (band.name)}
				<li class="band-legend-item">
					<span class="band-legend-swatch" style="background: {band.unplayed}" aria-hidden="true"></span>
					{band.name}
				</li>
			{/each}
		</ul>
	{/if}
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
		color: var(--on-accent);
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
		border-color: var(--accent);
		color: var(--text, #fff);
	}

	.spectral-toggle.active {
		border-color: var(--accent);
		color: var(--accent-text);
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

	/* These mirror spectrumBands() in canvasPalette.ts (the domain spectrum
	   palette). Keep in sync if the band hues are retinted there. */
	.band-low     { background: #e74c3c; height: 12px; }
	.band-midlow  { background: #e67e22; height: 9px; }
	.band-midhigh { background: #2ecc71; height: 7px; }
	.band-high    { background: #3498db; height: 5px; }
	.band-classic { background: var(--accent); height: 10px; }

	/* Visible legend mapping band color → frequency name (so color is never the
	   only signal for the spectral view). */
	.band-legend {
		display: flex;
		flex-wrap: wrap;
		gap: 6px 12px;
		margin: 0;
		padding: 0 10px 8px;
		list-style: none;
		font-size: 11px;
		color: var(--text-secondary);
	}

	.band-legend-item {
		display: flex;
		align-items: center;
		gap: 5px;
	}

	.band-legend-swatch {
		display: inline-block;
		width: 10px;
		height: 10px;
		border-radius: 2px;
	}
</style>
