<script lang="ts">
	import { onMount } from 'svelte';
	import WaveSurfer from 'wavesurfer.js';
	import { decodeFloat32 } from '$lib/utils/waveform';
	import { API_BASE } from '$lib/api/client';
	import type { SetWaveformTrack } from '$lib/types';
	import type { DeckId } from '$lib/stores/playback.svelte';

	let {
		deck,
		track = null,
		onready,
		onfinish,
		ontimeupdate,
		onerror,
	}: {
		deck: DeckId;
		track: SetWaveformTrack | null;
		onready: (deck: DeckId, ws: WaveSurfer) => void;
		onfinish: (deck: DeckId) => void;
		ontimeupdate: (deck: DeckId, time: number) => void;
		onerror: (deck: DeckId, trackId: number) => void;
	} = $props();

	let container: HTMLDivElement;
	let ws: WaveSurfer | null = null;
	let loadedTrackId: number | null = null;

	onMount(() => {
		return () => {
			ws?.destroy();
			ws = null;
		};
	});

	// React to track changes — create or update wavesurfer
	$effect(() => {
		if (!track || !track.waveform_overview || !track.duration_sec) {
			// No track to load
			if (ws) { ws.pause(); }
			loadedTrackId = null;
			return;
		}

		// Already loaded this track
		if (loadedTrackId === track.track_id && ws) return;

		// Destroy old instance
		if (ws) {
			ws.destroy();
			ws = null;
		}

		const peakData = decodeFloat32(track.waveform_overview);

		ws = WaveSurfer.create({
			container,
			height: 0, // Hidden — audio only
			waveColor: 'transparent',
			progressColor: 'transparent',
			cursorWidth: 0,
			normalize: true,
			backend: 'MediaElement',
			peaks: [peakData],
			duration: track.duration_sec,
			url: `${API_BASE}/api/audio/${track.track_id}`,
		});

		const currentWs = ws;
		const currentDeck = deck;

		currentWs.on('timeupdate', (time) => {
			ontimeupdate(currentDeck, time);
		});

		currentWs.on('finish', () => {
			onfinish(currentDeck);
		});

		currentWs.once('ready', () => {
			onready(currentDeck, currentWs);
		});

		currentWs.on('error', () => {
			onerror(currentDeck, track!.track_id);
		});

		// Also catch media element errors (e.g. 404)
		const mediaEl = currentWs.getMediaElement?.();
		if (mediaEl) {
			mediaEl.addEventListener('error', () => {
				onerror(currentDeck, track!.track_id);
			}, { once: true });
		}

		loadedTrackId = track.track_id;
	});
</script>

<div class="playback-deck" bind:this={container} aria-hidden="true"></div>

<style>
	.playback-deck {
		position: absolute;
		width: 0;
		height: 0;
		overflow: hidden;
		pointer-events: none;
	}
</style>
