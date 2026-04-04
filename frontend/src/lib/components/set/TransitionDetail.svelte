<script lang="ts">
	import type WaveSurfer from 'wavesurfer.js';
	import type { TransitionDetail as TransitionData, TransitionAnalysis } from '$lib/types';
	import { getCamelotColor } from '$lib/utils/camelot';
	import WavesurferPlayer from '../waveform/WavesurferPlayer.svelte';
	import CueOverlay from '../waveform/CueOverlay.svelte';
	import ScoreBreakdown from './ScoreBreakdown.svelte';
	import HarmonicBadge from './HarmonicBadge.svelte';
	import BpmBadge from './BpmBadge.svelte';
	import CrossfadePreview from './CrossfadePreview.svelte';

	let {
		transition,
		setId,
		analysisTransition = null,
		hasPrev = false,
		hasNext = false,
		onPrev,
		onNext,
		onBack,
	}: {
		transition: TransitionData;
		setId: number;
		analysisTransition?: TransitionAnalysis | null;
		hasPrev?: boolean;
		hasNext?: boolean;
		onPrev?: () => void;
		onNext?: () => void;
		onBack?: () => void;
	} = $props();

	let a = $derived(transition.track_a);
	let b = $derived(transition.track_b);

	let wsA = $state<WaveSurfer | null>(null);
	let wsB = $state<WaveSurfer | null>(null);
</script>

<div class="transition-detail">
	<div class="transition-header">
		<button class="back-btn" onclick={() => onBack?.()} title="Back to timeline">
			<svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2">
				<polyline points="10,3 5,8 10,13" />
			</svg>
			Timeline
		</button>
		<button class="nav-btn" disabled={!hasPrev} onclick={() => onPrev?.()} title="Previous transition">
			<svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2">
				<polyline points="10,3 5,8 10,13" />
			</svg>
		</button>
		<h3 class="transition-title">
			Transition {transition.position + 1}
		</h3>
		<button class="nav-btn" disabled={!hasNext} onclick={() => onNext?.()} title="Next transition">
			<svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2">
				<polyline points="6,3 11,8 6,13" />
			</svg>
		</button>
		<div class="header-badges">
			<HarmonicBadge keyA={transition.key_a} keyB={transition.key_b} />
			<BpmBadge bpmA={transition.bpm_a} bpmB={transition.bpm_b} />
		</div>
	</div>

	<div class="two-col">
		<!-- Column 1: Tracks with compact players -->
		<div class="tracks-col">
			<div class="track-card">
				<div class="track-header">
					<span class="track-label">Playing</span>
					<span class="badge" style="color: {getCamelotColor(transition.key_a)}">{transition.key_a ?? '?'}</span>
					<span class="badge">{transition.bpm_a ? Math.round(transition.bpm_a) : '?'} BPM</span>
				</div>
				<div class="track-name">{a.title ?? '?'}</div>
				<div class="artist">{a.artist ?? '?'}</div>
				{#if transition.waveform_a_overview && a.duration_sec}
					<WavesurferPlayer
						trackId={a.track_id}
						peaks={transition.waveform_a_overview}
						duration={a.duration_sec}
						height={56}
						waveColor="#00CED1"
						progressColor="#00A8AB"
						onready={(ws) => { wsA = ws; }}
					/>
					{#if wsA}
						<CueOverlay ws={wsA} {setId} trackId={a.track_id} position={transition.position} beats={transition.beats_a} />
					{/if}
				{/if}
			</div>

			<div class="track-card">
				<div class="track-header">
					<span class="track-label">Coming up</span>
					<span class="badge" style="color: {getCamelotColor(transition.key_b)}">{transition.key_b ?? '?'}</span>
					<span class="badge">{transition.bpm_b ? Math.round(transition.bpm_b) : '?'} BPM</span>
				</div>
				<div class="track-name">{b.title ?? '?'}</div>
				<div class="artist">{b.artist ?? '?'}</div>
				{#if transition.waveform_b_overview && b.duration_sec}
					<WavesurferPlayer
						trackId={b.track_id}
						peaks={transition.waveform_b_overview}
						duration={b.duration_sec}
						height={56}
						waveColor="#FF6B6B"
						progressColor="#CC5555"
						onready={(ws) => { wsB = ws; }}
					/>
					{#if wsB}
						<CueOverlay ws={wsB} {setId} trackId={b.track_id} position={transition.position + 1} beats={transition.beats_b} />
					{/if}
				{/if}
			</div>

			<CrossfadePreview {wsA} {wsB} bpmA={transition.bpm_a} bpmB={transition.bpm_b} />
		</div>

		<!-- Column 2: Score breakdowns side by side -->
		<div class="scores-col">
			<div class="score-panel">
				<div class="score-panel-label">Builder score</div>
				<ScoreBreakdown breakdown={transition.score_breakdown} keyA={transition.key_a} keyB={transition.key_b} />
			</div>
			{#if analysisTransition}
				<div class="score-panel analysis">
					<div class="score-panel-label">Context-aware score</div>
					<ScoreBreakdown breakdown={analysisTransition.scores} keyA={transition.key_a} keyB={transition.key_b} />
					{#if analysisTransition.teaching_moment}
						<div class="teaching-block">
							<span class="teaching-text">{analysisTransition.teaching_moment}</span>
						</div>
					{/if}
					{#if analysisTransition.suggestion}
						<div class="suggestion-block">
							{analysisTransition.suggestion}
						</div>
					{/if}
				</div>
			{/if}
		</div>
	</div>
</div>

<style>
	.transition-detail {
		padding: 12px;
	}

	.transition-header {
		display: flex;
		align-items: center;
		gap: 6px;
		margin-bottom: 10px;
	}

	.back-btn {
		display: flex;
		align-items: center;
		gap: 4px;
		padding: 4px 10px;
		font-size: 12px;
		color: var(--text-secondary);
		background: var(--bg-secondary);
		border: 1px solid var(--border);
		border-radius: 6px;
		cursor: pointer;
		transition: all 0.1s;
		margin-right: 4px;
	}

	.back-btn:hover {
		color: var(--text-primary);
		background: var(--bg-tertiary);
		border-color: var(--accent);
	}

	.transition-title {
		font-size: 13px;
		font-weight: 600;
		color: var(--text-primary);
	}

	.header-badges {
		display: flex;
		gap: 6px;
		margin-left: auto;
	}

	.nav-btn {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 24px;
		height: 24px;
		border: 1px solid var(--border);
		border-radius: 4px;
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

	/* ── Two-column layout ── */

	.two-col {
		display: grid;
		grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
		gap: 12px;
		align-items: start;
	}

	/* ── Column 1: Tracks ── */

	.tracks-col {
		display: flex;
		flex-direction: column;
		gap: 6px;
		min-width: 0;
	}

	.track-card {
		background: var(--bg-secondary);
		border-radius: 6px;
		padding: 8px 10px;
		display: flex;
		flex-direction: column;
		gap: 3px;
		min-width: 0;
	}

	.track-header {
		display: flex;
		align-items: center;
		gap: 6px;
	}

	.track-label {
		font-size: 9px;
		text-transform: uppercase;
		letter-spacing: 0.8px;
		color: var(--text-dim);
		margin-right: auto;
	}

	.track-name {
		font-size: 13px;
		font-weight: 600;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.artist {
		font-size: 11px;
		color: var(--text-secondary);
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.badge {
		font-size: 9px;
		font-weight: 600;
		padding: 1px 5px;
		background: var(--bg-tertiary);
		border-radius: 3px;
		flex-shrink: 0;
	}

	/* ── Column 2: Scores ── */

	.scores-col {
		display: flex;
		flex-direction: column;
		gap: 10px;
		min-width: 0;
		overflow-y: auto;
	}

	.score-panel {
		display: flex;
		flex-direction: column;
		gap: 4px;
	}

	.score-panel-label {
		font-size: 10px;
		text-transform: uppercase;
		letter-spacing: 0.5px;
		color: var(--text-dim);
		font-weight: 500;
	}

	.score-panel.analysis .score-panel-label {
		color: var(--accent);
	}

	.teaching-block {
		padding: 6px 10px;
		background: var(--bg-secondary);
		border-radius: 4px;
		font-size: 12px;
		color: var(--text-primary);
		font-style: italic;
		line-height: 1.4;
	}

	.suggestion-block {
		padding: 6px 10px;
		background: var(--bg-secondary);
		border-left: 3px solid var(--accent);
		border-radius: 2px;
		font-size: 11px;
		color: var(--text-secondary);
		font-style: italic;
	}
</style>
