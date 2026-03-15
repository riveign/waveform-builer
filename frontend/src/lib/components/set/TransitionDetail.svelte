<script lang="ts">
	import type WaveSurfer from 'wavesurfer.js';
	import type { TransitionDetail as TransitionData } from '$lib/types';
	import { getCamelotColor } from '$lib/utils/camelot';
	import WavesurferPlayer from '../waveform/WavesurferPlayer.svelte';
	import ScoreBreakdown from './ScoreBreakdown.svelte';
	import HarmonicBadge from './HarmonicBadge.svelte';
	import BpmBadge from './BpmBadge.svelte';
	import CrossfadePreview from './CrossfadePreview.svelte';

	let {
		transition,
		hasPrev = false,
		hasNext = false,
		onPrev,
		onNext,
	}: {
		transition: TransitionData;
		hasPrev?: boolean;
		hasNext?: boolean;
		onPrev?: () => void;
		onNext?: () => void;
	} = $props();

	let a = $derived(transition.track_a);
	let b = $derived(transition.track_b);

	let wsA = $state<WaveSurfer | null>(null);
	let wsB = $state<WaveSurfer | null>(null);
</script>

<div class="transition-detail">
	<div class="transition-header">
		<button class="nav-btn" disabled={!hasPrev} onclick={() => onPrev?.()} title="Previous transition">
			<svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2">
				<polyline points="10,3 5,8 10,13" />
			</svg>
		</button>
		<h3 class="transition-title">
			Transition {transition.position + 1}
		</h3>
		<button class="nav-btn" disabled={!hasNext} onclick={() => onNext?.()} title="Next transition">
			<svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2">
				<polyline points="6,3 11,8 6,13" />
			</svg>
		</button>
	</div>

	<div class="insights-row">
		<HarmonicBadge keyA={transition.key_a} keyB={transition.key_b} />
		<BpmBadge bpmA={transition.bpm_a} bpmB={transition.bpm_b} />
	</div>

	<div class="tracks-comparison">
		<div class="track-card">
			<div class="track-label">Playing</div>
			<div class="track-name">{a.title ?? '?'}</div>
			<div class="track-meta-row">
				<span class="artist">{a.artist ?? '?'}</span>
				<span class="badge" style="color: {getCamelotColor(transition.key_a)}">{transition.key_a ?? '?'}</span>
				<span class="badge">{transition.bpm_a ? Math.round(transition.bpm_a) : '?'} BPM</span>
			</div>
			{#if transition.waveform_a_overview && a.duration_sec}
				<WavesurferPlayer
					trackId={a.track_id}
					peaks={transition.waveform_a_overview}
					duration={a.duration_sec}
					height={80}
					waveColor="#00CED1"
					progressColor="#00A8AB"
					onready={(ws) => { wsA = ws; }}
				/>
			{/if}
		</div>

		<div class="score-column">
			<ScoreBreakdown breakdown={transition.score_breakdown} keyA={transition.key_a} keyB={transition.key_b} />
		</div>

		<div class="track-card">
			<div class="track-label">Coming up</div>
			<div class="track-name">{b.title ?? '?'}</div>
			<div class="track-meta-row">
				<span class="artist">{b.artist ?? '?'}</span>
				<span class="badge" style="color: {getCamelotColor(transition.key_b)}">{transition.key_b ?? '?'}</span>
				<span class="badge">{transition.bpm_b ? Math.round(transition.bpm_b) : '?'} BPM</span>
			</div>
			{#if transition.waveform_b_overview && b.duration_sec}
				<WavesurferPlayer
					trackId={b.track_id}
					peaks={transition.waveform_b_overview}
					duration={b.duration_sec}
					height={80}
					waveColor="#FF6B6B"
					progressColor="#CC5555"
					onready={(ws) => { wsB = ws; }}
				/>
			{/if}
		</div>
	</div>

	<CrossfadePreview {wsA} {wsB} bpmA={transition.bpm_a} bpmB={transition.bpm_b} />
</div>

<style>
	.transition-detail {
		padding: 16px;
	}

	.transition-header {
		display: flex;
		align-items: center;
		gap: 8px;
		margin-bottom: 12px;
	}

	.transition-title {
		font-size: 14px;
		font-weight: 600;
		color: var(--text-primary);
	}

	.nav-btn {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 28px;
		height: 28px;
		border: 1px solid var(--border);
		border-radius: 6px;
		background: var(--bg-secondary);
		color: var(--text-primary);
		cursor: pointer;
		padding: 0;
		transition: background 0.1s, opacity 0.1s;
	}

	.nav-btn:hover:not(:disabled) {
		background: var(--bg-tertiary);
	}

	.nav-btn:disabled {
		opacity: 0.25;
		cursor: default;
	}

	.insights-row {
		display: flex;
		gap: 12px;
		flex-wrap: wrap;
		margin-bottom: 12px;
	}

	.tracks-comparison {
		display: grid;
		grid-template-columns: 1fr 240px 1fr;
		gap: 16px;
		align-items: start;
	}

	.track-card {
		background: var(--bg-secondary);
		border-radius: 6px;
		padding: 12px;
		display: flex;
		flex-direction: column;
		gap: 6px;
	}

	.track-label {
		font-size: 10px;
		text-transform: uppercase;
		letter-spacing: 1px;
		color: var(--text-dim);
	}

	.track-name {
		font-size: 15px;
		font-weight: 600;
	}

	.track-meta-row {
		display: flex;
		gap: 8px;
		align-items: center;
		flex-wrap: wrap;
	}

	.artist {
		font-size: 12px;
		color: var(--text-secondary);
	}

	.badge {
		font-size: 11px;
		font-weight: 600;
		padding: 1px 6px;
		background: var(--bg-tertiary);
		border-radius: 3px;
	}

	.score-column {
		padding-top: 24px;
	}
</style>
