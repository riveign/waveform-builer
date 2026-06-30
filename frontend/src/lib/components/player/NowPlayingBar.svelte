<script lang="ts">
	import { onMount } from 'svelte';
	import WaveSurfer from 'wavesurfer.js';
	import { formatTime, decodeFloat32 } from '$lib/utils/waveform';
	import { API_BASE } from '$lib/api/client';
	import { getPlayerStore } from '$lib/stores/player.svelte';
	import { getWaveformOverview } from '$lib/api/waveforms';
	import { consumePreloadedAudio } from '$lib/utils/audio-preload';
	import Button from '$lib/components/primitives/Button.svelte';

	const player = getPlayerStore();

	/** Flatten a theme token (which chains through several var() indirections) to a
	 * concrete color for the WaveSurfer canvas. A probe element lets the browser
	 * resolve the full var() chain to a used color, so the waveform follows the
	 * app accent without a hardcoded hex. */
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

	// ── WaveSurfer (owned by this component, registered with store) ──
	let waveformContainer = $state<HTMLDivElement>(null!);
	let ws: WaveSurfer | null = null;
	let cleanup: (() => void) | null = null;

	/** Track ID currently loaded in our WaveSurfer — avoids reloading the same track */
	let loadedTrackId: number | null = null;

	let visible = $derived(player.hasTrack);

	// When the store's currentTrack changes, create/recreate WaveSurfer
	$effect(() => {
		const track = player.currentTrack;
		if (!track) {
			destroyPlayer();
			return;
		}

		// Only recreate if track actually changed
		if (track.id === loadedTrackId) return;
		loadedTrackId = track.id;
		createPlayer(track.id, track.duration_sec ?? 0);
	});

	function destroyPlayer() {
		if (cleanup) {
			cleanup();
			cleanup = null;
		}
		if (ws) {
			ws.destroy();
			ws = null;
		}
		loadedTrackId = null;
	}

	async function createPlayer(trackId: number, trackDuration: number) {
		if (!waveformContainer) return;

		// ── Optimization 2: Parallel fetch ──
		// Start audio buffering immediately (or use hover-preloaded element)
		// while peaks are fetched in parallel
		const preloaded = consumePreloadedAudio(trackId);
		const audioEl = preloaded ?? new Audio();
		if (!preloaded) {
			audioEl.preload = 'auto';
			audioEl.src = `${API_BASE}/api/audio/${trackId}`;
		}

		// Fetch peaks in parallel with audio buffering
		let peakData: Float32Array | undefined;
		try {
			const waveformData = await getWaveformOverview(trackId);
			peakData = decodeFloat32(waveformData.envelope);
			if (waveformData.duration_sec > 0) {
				trackDuration = waveformData.duration_sec;
			}
		} catch {
			// Waveform data not available — WaveSurfer will render from audio
		}

		// Guard: track may have changed while we awaited peaks
		if (loadedTrackId !== trackId) {
			// Clean up the audio element we started
			audioEl.src = '';
			audioEl.load();
			return;
		}

		const audioUrl = `${API_BASE}/api/audio/${trackId}`;

		// ── Optimization 4: WaveSurfer reuse ──
		// Reuse existing WaveSurfer instance when possible — avoids DOM/canvas teardown+rebuild.
		// ws.load() takes a URL string; the browser HTTP cache will serve data from the
		// already-buffering preloaded Audio element.
		if (ws) {
			// Unregister old event listeners before loading new content
			if (cleanup) { cleanup(); cleanup = null; }
			// Re-register event listeners BEFORE load so onReady is never missed
			cleanup = player.registerPlayer(ws);
			// Load new audio + peaks into existing instance (single load path)
			ws.load(
				audioUrl,
				peakData ? [peakData] : undefined,
				trackDuration
			);
			return;
		}

		// First-time creation: build WaveSurfer from scratch
		// Use the preloaded/prefetching audio element directly via `media` option
		ws = WaveSurfer.create({
			container: waveformContainer,
			height: 40,
			waveColor: resolveColor('var(--accent)', '#008A84'),
			progressColor: resolveColor('var(--accent-hover)', '#00B1B8'),
			cursorColor: 'rgba(255,255,255,0.5)',
			cursorWidth: 1,
			barWidth: 2,
			barGap: 1,
			barRadius: 1,
			normalize: true,
			backend: 'MediaElement',
			media: audioEl,
			duration: trackDuration,
			// Pre-computed peaks: waveform draws immediately, audio streams via MediaElement
			...(peakData ? { peaks: [peakData] } : {}),
		});

		// Register with global store — this binds play/pause/timeupdate/finish events
		cleanup = player.registerPlayer(ws);
	}

	function handleVolumeChange(e: Event) {
		const val = Number((e.target as HTMLInputElement).value);
		player.setVolume(val);
	}

	/** Clamp a seek time into the valid [0, duration] range. Guards duration=0/NaN. */
	function clampSeek(t: number): number {
		const dur = player.duration;
		if (!Number.isFinite(dur) || dur <= 0) return 0;
		return Math.max(0, Math.min(t, dur));
	}

	/** Seek via progress bar click */
	function handleProgressClick(e: MouseEvent) {
		const bar = e.currentTarget;
		if (!(bar instanceof HTMLElement)) return;
		const rect = bar.getBoundingClientRect();
		if (rect.width <= 0) return;
		const pct = (e.clientX - rect.left) / rect.width;
		player.seek(clampSeek(pct * player.duration));
	}

	/** Keyboard seek for the progress slider — parallel path into the same player.seek(). */
	function handleProgressKeydown(e: KeyboardEvent) {
		switch (e.key) {
			case 'ArrowRight':
			case 'ArrowUp':
				e.preventDefault();
				player.seek(clampSeek(player.currentTime + 5));
				break;
			case 'ArrowLeft':
			case 'ArrowDown':
				e.preventDefault();
				player.seek(clampSeek(player.currentTime - 5));
				break;
			case 'PageUp':
				e.preventDefault();
				player.seek(clampSeek(player.currentTime + 15));
				break;
			case 'PageDown':
				e.preventDefault();
				player.seek(clampSeek(player.currentTime - 15));
				break;
			case 'Home':
				e.preventDefault();
				player.seek(0);
				break;
			case 'End':
				e.preventDefault();
				player.seek(clampSeek(player.duration));
				break;
		}
	}

	let progressPct = $derived(player.progress * 100);

	onMount(() => {
		return () => {
			destroyPlayer();
		};
	});
</script>

{#if visible}
	<div class="now-playing-bar" class:loading={player.status === 'loading'}>
		<!-- Left: Track Info -->
		<div class="bar-left">
			<div class="genre-dot" title={player.currentTrack?.genre ?? 'Unknown genre'}></div>
			<div class="track-info">
				<span class="track-artist">{player.currentTrack?.artist ?? 'Unknown'}</span>
				<span class="track-title">{player.currentTrack?.title ?? 'Untitled'}</span>
			</div>
		</div>

		<!-- Center: Transport + Waveform + Progress -->
		<div class="bar-center">
			<div class="transport">
				<Button
					iconOnly
					shape="round"
					variant="secondary"
					size="sm"
					ariaLabel="Previous track"
					title="Previous"
					onclick={() => player.previous()}
					disabled={!player.hasPrevious}
				>
					{#snippet icon()}&#x23EE;{/snippet}
				</Button>

				<Button
					iconOnly
					shape="round"
					variant="primary"
					size="md"
					ariaLabel={player.isPlaying ? 'Pause' : 'Play'}
					title={player.isPlaying ? 'Pause' : 'Play'}
					loading={player.status === 'loading'}
					onclick={() => player.togglePlay()}
				>
					{#snippet icon()}{player.isPlaying ? '\u23F8' : '\u25B6'}{/snippet}
				</Button>

				<Button
					iconOnly
					shape="round"
					variant="secondary"
					size="sm"
					ariaLabel="Next track"
					title="Next"
					onclick={() => player.next()}
					disabled={!player.hasNext}
				>
					{#snippet icon()}&#x23ED;{/snippet}
				</Button>
			</div>

			<div class="waveform-section">
				<span class="time">{formatTime(player.currentTime)}</span>
				<div class="waveform-wrapper">
					<div class="waveform-container" bind:this={waveformContainer}></div>
					<!-- Fallback progress bar shown on narrow screens or when waveform is hidden -->
					<div
						class="progress-fallback"
						role="slider"
						tabindex="0"
						aria-label="Seek"
						aria-valuemin={0}
						aria-valuemax={Math.round(player.duration)}
						aria-valuenow={Math.round(player.currentTime)}
						aria-valuetext={`${formatTime(player.currentTime)} of ${formatTime(player.duration)}`}
						onclick={handleProgressClick}
						onkeydown={handleProgressKeydown}
					>
						<div class="progress-fill" style="width: {progressPct}%"></div>
					</div>
				</div>
				<span class="time">{formatTime(player.duration)}</span>
			</div>
		</div>

		<!-- Right: Volume -->
		<div class="bar-right">
			<button class="volume-btn" onclick={() => player.toggleMute()} aria-label={player.isMuted ? 'Unmute' : 'Mute'} title={player.isMuted ? 'Unmute' : 'Mute'}>
				{#if player.isMuted || player.volume === 0}
					<svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
						<path d="M16.5 12c0-1.77-1.02-3.29-2.5-4.03v2.21l2.45 2.45c.03-.2.05-.41.05-.63zm2.5 0c0 .94-.2 1.82-.54 2.64l1.51 1.51C20.63 14.91 21 13.5 21 12c0-4.28-2.99-7.86-7-8.77v2.06c2.89.86 5 3.54 5 6.71zM4.27 3L3 4.27 7.73 9H3v6h4l5 5v-6.73l4.25 4.25c-.67.52-1.42.93-2.25 1.18v2.06c1.38-.31 2.63-.95 3.69-1.81L19.73 21 21 19.73l-9-9L4.27 3zM12 4L9.91 6.09 12 8.18V4z"/>
					</svg>
				{:else if player.volume < 0.5}
					<svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
						<path d="M18.5 12c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02zM5 9v6h4l5 5V4L9 9H5z"/>
					</svg>
				{:else}
					<svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
						<path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02zM14 3.23v2.06c2.89.86 5 3.54 5 6.71s-2.11 5.85-5 6.71v2.06c4.01-.91 7-4.49 7-8.77s-2.99-7.86-7-8.77z"/>
					</svg>
				{/if}
			</button>
			<input
				type="range"
				class="volume-slider"
				min="0"
				max="1"
				step="0.05"
				value={player.volume}
				oninput={handleVolumeChange}
				aria-label="Volume"
				title="Volume"
			/>
		</div>
	</div>
{/if}

<style>
	.now-playing-bar {
		position: fixed;
		bottom: 0;
		left: 0;
		right: 0;
		height: 72px;
		display: flex;
		align-items: center;
		gap: var(--space-xl);
		padding: 0 var(--space-xl);
		background: var(--bg-secondary);
		border-top: 1px solid var(--border);
		z-index: 1000;
		transition: transform var(--dur-slow) ease, opacity var(--dur-slow) ease;
		animation: slide-up var(--dur-slow) ease forwards;
	}

	@keyframes slide-up {
		from {
			transform: translateY(100%);
			opacity: 0;
		}
		to {
			transform: translateY(0);
			opacity: 1;
		}
	}

	/* ── Left: Track Info ── */
	.bar-left {
		display: flex;
		align-items: center;
		gap: 10px;
		min-width: 180px;
		max-width: 240px;
		flex-shrink: 0;
	}

	.genre-dot {
		width: 8px;
		height: 8px;
		border-radius: var(--radius-full);
		background: var(--accent);
		flex-shrink: 0;
	}

	.track-info {
		display: flex;
		flex-direction: column;
		min-width: 0;
	}

	.track-artist {
		font-size: var(--text-sm);
		font-weight: var(--font-weight-semibold);
		color: var(--text-primary);
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.track-title {
		font-size: var(--text-xs);
		color: var(--text-secondary);
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	/* ── Center: Transport + Waveform ── */
	.bar-center {
		flex: 1;
		display: flex;
		align-items: center;
		gap: var(--space-lg);
		min-width: 0;
	}

	.transport {
		display: flex;
		align-items: center;
		gap: var(--space-sm);
		flex-shrink: 0;
	}

	/* ── Waveform section ── */
	.waveform-section {
		flex: 1;
		display: flex;
		align-items: center;
		gap: var(--space-md);
		min-width: 0;
	}

	.time {
		font-size: var(--text-2xs);
		color: var(--text-dim);
		font-variant-numeric: tabular-nums;
		min-width: 32px;
		text-align: center;
		flex-shrink: 0;
	}

	.waveform-wrapper {
		flex: 1;
		min-width: 0;
		position: relative;
	}

	.waveform-container {
		width: 100%;
		height: 40px;
	}

	/* Fallback progress bar: hidden on wide screens, shown on narrow */
	.progress-fallback {
		display: none;
		height: 4px;
		background: var(--bg-tertiary);
		border-radius: var(--radius-xs);
		overflow: hidden;
		cursor: pointer;
	}

	.progress-fallback .progress-fill {
		height: 100%;
		background: var(--accent);
		border-radius: var(--radius-xs);
		transition: width var(--dur-base) linear;
	}

	/* ── Right: Volume ── */
	.bar-right {
		display: flex;
		align-items: center;
		gap: var(--space-sm);
		flex-shrink: 0;
	}

	.volume-btn {
		width: 28px;
		height: 28px;
		display: flex;
		align-items: center;
		justify-content: center;
		color: var(--text-secondary);
		border-radius: var(--radius-full);
		transition: color var(--dur-fast) var(--ease-standard);
	}

	.volume-btn:hover {
		color: var(--text-primary);
	}

	.volume-slider {
		width: 80px;
		accent-color: var(--accent);
		height: 4px;
		background: transparent;
		border: none;
		padding: 0;
	}

	/* ── Responsive: narrow screens ── */
	@media (max-width: 640px) {
		.now-playing-bar {
			height: 60px;
			padding: 0 10px;
			gap: 8px;
		}

		.bar-left {
			min-width: 0;
			max-width: 120px;
		}

		/* Hide waveform, show simple progress bar */
		.waveform-container {
			display: none;
		}

		.progress-fallback {
			display: block;
		}

		.bar-right {
			display: none;
		}
	}

	@media (max-width: 480px) {
		.waveform-section {
			display: none;
		}

		.bar-left {
			flex: 1;
		}
	}
</style>
