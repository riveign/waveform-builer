<script lang="ts">
	import { onMount } from 'svelte';
	import WaveSurfer from 'wavesurfer.js';
	import { decodeFloat32, formatTime } from '$lib/utils/waveform';
	import { API_BASE } from '$lib/api/client';

	let {
		trackId,
		peaks,
		duration,
		beats = null,
		height = 128,
		waveColor = '#00CED1',
		progressColor = '#00A8AB',
	}: {
		trackId: number;
		peaks: string;
		duration: number;
		beats?: string | null;
		height?: number;
		waveColor?: string;
		progressColor?: string;
	} = $props();

	let container: HTMLDivElement;
	let ws: WaveSurfer | null = null;
	let currentTime = $state(0);
	let isPlaying = $state(false);

	onMount(() => {
		const peakData = decodeFloat32(peaks);

		ws = WaveSurfer.create({
			container,
			height,
			waveColor,
			progressColor,
			cursorColor: '#fff',
			cursorWidth: 1,
			barWidth: 2,
			barGap: 1,
			barRadius: 1,
			normalize: true,
			backend: 'MediaElement',
			peaks: [peakData],
			duration,
			url: `${API_BASE}/api/audio/${trackId}`,
		});

		ws.on('timeupdate', (time) => {
			currentTime = time;
		});

		ws.on('play', () => { isPlaying = true; });
		ws.on('pause', () => { isPlaying = false; });

		return () => {
			ws?.destroy();
		};
	});

	function togglePlay() {
		ws?.playPause();
	}
</script>

<div class="wavesurfer-player">
	<div class="controls">
		<button class="play-btn" onclick={togglePlay}>
			{isPlaying ? '⏸' : '▶'}
		</button>
		<span class="time">{formatTime(currentTime)} / {formatTime(duration)}</span>
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
</style>
