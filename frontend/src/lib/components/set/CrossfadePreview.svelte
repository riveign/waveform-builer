<script lang="ts">
	import type WaveSurfer from 'wavesurfer.js';

	let {
		wsA = null,
		wsB = null,
		bpmA = null,
		bpmB = null,
	}: {
		wsA?: WaveSurfer | null;
		wsB?: WaveSurfer | null;
		bpmA?: number | null;
		bpmB?: number | null;
	} = $props();

	let overlapBars = $state(4);
	let matchBpm = $state(true);
	let previewing = $state(false);
	let gainA = $state(1);
	let gainB = $state(0);

	/** Convert bars to seconds using A's BPM (the outgoing track sets the tempo) */
	function barsToSec(bars: number, bpm: number | null): number {
		if (!bpm || bpm <= 0) return bars * 2; // fallback ~120 BPM
		return (bars * 4 * 60) / bpm;
	}

	/** Overlap duration in seconds, derived from bars + BPM */
	let overlapSec = $derived(barsToSec(overlapBars, bpmA));

	/** Playback rate to pitch-match B to A's tempo */
	let rateB = $derived.by(() => {
		if (!matchBpm || !bpmA || !bpmB || bpmB === 0) return 1;
		const ratio = bpmA / bpmB;
		// Clamp to ±12% — beyond that it sounds unnatural
		return Math.max(0.88, Math.min(1.12, ratio));
	});

	let ctx: AudioContext | null = null;
	let gainNodeA: GainNode | null = null;
	let gainNodeB: GainNode | null = null;
	let sourceA: MediaElementAudioSourceNode | null = null;
	let sourceB: MediaElementAudioSourceNode | null = null;
	let connectedElA: HTMLAudioElement | null = null;
	let connectedElB: HTMLAudioElement | null = null;
	let animFrame: number | null = null;
	let fadeTimer: ReturnType<typeof setTimeout> | null = null;

	function getMediaElement(ws: WaveSurfer): HTMLAudioElement | null {
		const media = ws.getMediaElement?.();
		return media instanceof HTMLAudioElement ? media : null;
	}

	function connectNodes() {
		if (!wsA || !wsB) return false;
		const elA = getMediaElement(wsA);
		const elB = getMediaElement(wsB);
		if (!elA || !elB) return false;

		if (!ctx) {
			ctx = new AudioContext();
		}

		// Reconnect if the underlying <audio> element changed (new WaveSurfer instance)
		if (connectedElA !== elA) {
			if (sourceA) { sourceA.disconnect(); sourceA = null; }
			if (gainNodeA) { gainNodeA.disconnect(); gainNodeA = null; }
			connectedElA = null;
		}
		if (connectedElB !== elB) {
			if (sourceB) { sourceB.disconnect(); sourceB = null; }
			if (gainNodeB) { gainNodeB.disconnect(); gainNodeB = null; }
			connectedElB = null;
		}

		if (!sourceA) {
			sourceA = ctx.createMediaElementSource(elA);
			gainNodeA = ctx.createGain();
			sourceA.connect(gainNodeA);
			gainNodeA.connect(ctx.destination);
			connectedElA = elA;
		}

		if (!sourceB) {
			sourceB = ctx.createMediaElementSource(elB);
			gainNodeB = ctx.createGain();
			sourceB.connect(gainNodeB);
			gainNodeB.connect(ctx.destination);
			connectedElB = elB;
		}

		return true;
	}

	function startPreview() {
		if (!wsA || !wsB) return;
		if (!connectNodes()) return;

		previewing = true;

		// Seek A near end, B to start
		const durA = wsA.getDuration();
		const fadeDuration = overlapSec;
		const seekA = Math.max(0, durA - fadeDuration - 2);
		wsA.setTime(seekA);
		wsB.setTime(0);

		// Set initial gains
		gainNodeA!.gain.value = 1;
		gainNodeB!.gain.value = 0;
		gainA = 1;
		gainB = 0;

		// Set playback rates: A at normal, B pitch-matched
		wsA.setPlaybackRate(1);
		wsB.setPlaybackRate(rateB);

		// Play A first
		wsA.play();

		// Start crossfade when A reaches the overlap zone
		const fadeStartTime = durA - fadeDuration;
		const waitMs = Math.max(0, (fadeStartTime - seekA) * 1000);

		fadeTimer = setTimeout(() => {
			if (!previewing || !wsA || !wsB || !gainNodeA || !gainNodeB) return;

			// Start B
			wsB.play();

			// Animate crossfade
			const startTime = performance.now();
			const fadeMs = fadeDuration * 1000;

			function animateFade() {
				if (!previewing) return;
				const elapsed = performance.now() - startTime;
				const progress = Math.min(elapsed / fadeMs, 1);

				const aGain = 1 - progress;
				const bGain = progress;

				gainNodeA!.gain.value = aGain;
				gainNodeB!.gain.value = bGain;
				gainA = aGain;
				gainB = bGain;

				if (progress < 1) {
					animFrame = requestAnimationFrame(animateFade);
				} else {
					// Fade complete — stop A
					wsA?.pause();
					previewing = false;
				}
			}

			animFrame = requestAnimationFrame(animateFade);
		}, waitMs);
	}

	function stopPreview() {
		previewing = false;
		if (fadeTimer) { clearTimeout(fadeTimer); fadeTimer = null; }
		if (animFrame) { cancelAnimationFrame(animFrame); animFrame = null; }

		wsA?.pause();
		wsB?.pause();
		wsA?.setPlaybackRate(1);
		wsB?.setPlaybackRate(1);

		if (gainNodeA) gainNodeA.gain.value = 1;
		if (gainNodeB) gainNodeB.gain.value = 1;
		gainA = 1;
		gainB = 0;
	}

	let disabled = $derived(!wsA || !wsB);
</script>

<div class="crossfade-preview">
	<div class="crossfade-controls">
		{#if previewing}
			<button class="cf-btn stop" onclick={stopPreview}>Stop</button>
		{:else}
			<button class="cf-btn" onclick={startPreview} {disabled}>Preview Crossfade</button>
		{/if}
		<label class="overlap-label">
			<span>Overlap</span>
			<input
				type="range"
				min="1"
				max="16"
				step="1"
				bind:value={overlapBars}
				disabled={previewing}
			/>
			<span class="overlap-val">{overlapBars} {overlapBars === 1 ? 'bar' : 'bars'}</span>
			<span class="overlap-sec">{overlapSec.toFixed(1)}s</span>
		</label>
		{#if bpmA && bpmB}
			<label class="bpm-match-label">
				<input type="checkbox" bind:checked={matchBpm} disabled={previewing} />
				<span>Match BPM</span>
				{#if matchBpm && rateB !== 1}
					<span class="rate-hint">{(rateB * 100).toFixed(1)}%</span>
				{/if}
			</label>
		{/if}
	</div>

	{#if previewing}
		<div class="gain-bars">
			<div class="gain-row">
				<span class="gain-label">A</span>
				<div class="gain-track">
					<div class="gain-fill a" style="width: {gainA * 100}%"></div>
				</div>
			</div>
			<div class="gain-row">
				<span class="gain-label">B</span>
				<div class="gain-track">
					<div class="gain-fill b" style="width: {gainB * 100}%"></div>
				</div>
			</div>
		</div>
	{/if}
</div>

<style>
	.crossfade-preview {
		padding: 8px 0;
	}

	.crossfade-controls {
		display: flex;
		align-items: center;
		gap: 16px;
	}

	.cf-btn {
		padding: 6px 14px;
		font-size: 12px;
		font-weight: 600;
		border-radius: 4px;
		background: var(--accent);
		color: #000;
		white-space: nowrap;
		transition: opacity 0.15s;
	}

	.cf-btn:hover:not(:disabled) {
		opacity: 0.85;
	}

	.cf-btn:disabled {
		opacity: 0.4;
		cursor: default;
	}

	.cf-btn.stop {
		background: var(--energy-high, #ff6b6b);
		color: #fff;
	}

	.overlap-label {
		display: flex;
		align-items: center;
		gap: 8px;
		font-size: 12px;
		color: var(--text-secondary);
	}

	.overlap-label input[type="range"] {
		width: 100px;
		accent-color: var(--accent);
	}

	.overlap-val {
		font-variant-numeric: tabular-nums;
		min-width: 40px;
	}

	.overlap-sec {
		font-size: 10px;
		color: var(--text-dim);
		font-variant-numeric: tabular-nums;
	}

	.bpm-match-label {
		display: flex;
		align-items: center;
		gap: 6px;
		font-size: 12px;
		color: var(--text-secondary);
		cursor: pointer;
	}

	.bpm-match-label input[type="checkbox"] {
		accent-color: var(--accent);
	}

	.rate-hint {
		font-size: 10px;
		color: var(--text-dim);
		font-variant-numeric: tabular-nums;
	}

	.gain-bars {
		display: flex;
		flex-direction: column;
		gap: 4px;
		margin-top: 8px;
	}

	.gain-row {
		display: flex;
		align-items: center;
		gap: 8px;
	}

	.gain-label {
		font-size: 11px;
		font-weight: 600;
		color: var(--text-secondary);
		width: 12px;
	}

	.gain-track {
		flex: 1;
		height: 6px;
		background: var(--bg-tertiary);
		border-radius: 3px;
		overflow: hidden;
	}

	.gain-fill {
		height: 100%;
		border-radius: 3px;
		transition: width 0.05s linear;
	}

	.gain-fill.a {
		background: #00CED1;
	}

	.gain-fill.b {
		background: #FF6B6B;
	}
</style>
