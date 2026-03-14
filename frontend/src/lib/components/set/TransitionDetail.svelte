<script lang="ts">
	import type { TransitionDetail as TransitionData } from '$lib/types';
	import { getCamelotColor } from '$lib/utils/camelot';
	import WavesurferPlayer from '../waveform/WavesurferPlayer.svelte';
	import ScoreBreakdown from './ScoreBreakdown.svelte';

	let { transition }: { transition: TransitionData } = $props();

	let a = $derived(transition.track_a);
	let b = $derived(transition.track_b);
</script>

<div class="transition-detail">
	<div class="transition-header">
		<h3 class="transition-title">
			Transition {transition.position + 1}
		</h3>
	</div>

	<div class="tracks-comparison">
		<div class="track-card">
			<div class="track-label">A (Outgoing)</div>
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
					waveColor="#00bcd4"
					progressColor="#00838f"
				/>
			{/if}
		</div>

		<div class="score-column">
			<ScoreBreakdown breakdown={transition.score_breakdown} />
		</div>

		<div class="track-card">
			<div class="track-label">B (Incoming)</div>
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
					waveColor="#e94560"
					progressColor="#b71c40"
				/>
			{/if}
		</div>
	</div>
</div>

<style>
	.transition-detail {
		padding: 16px;
	}

	.transition-header {
		margin-bottom: 12px;
	}

	.transition-title {
		font-size: 14px;
		font-weight: 600;
		color: var(--text-primary);
	}

	.tracks-comparison {
		display: grid;
		grid-template-columns: 1fr 200px 1fr;
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
