<script lang="ts">
	import type { Track, TrackFeatures, WaveformDetailData } from '$lib/types';
	import { getTrackFeatures } from '$lib/api/tracks';
	import { getWaveformDetail } from '$lib/api/waveforms';
	import { getCamelotColor } from '$lib/utils/camelot';
	import { formatTime } from '$lib/utils/waveform';
	import WavesurferPlayer from './WavesurferPlayer.svelte';

	let { track }: { track: Track } = $props();

	let waveformData = $state<WaveformDetailData | null>(null);
	let features = $state<TrackFeatures | null>(null);
	let loadingWaveform = $state(false);
	let loadingFeatures = $state(false);
	let error = $state<string | null>(null);

	$effect(() => {
		if (track.id) {
			loadTrackData(track.id);
		}
	});

	async function loadTrackData(id: number) {
		error = null;
		waveformData = null;
		features = null;

		if (track.has_waveform) {
			loadingWaveform = true;
			try {
				waveformData = await getWaveformDetail(id);
			} catch (e) {
				error = e instanceof Error ? e.message : String(e);
			} finally {
				loadingWaveform = false;
			}
		}

		if (track.has_features) {
			loadingFeatures = true;
			try {
				features = await getTrackFeatures(id);
			} catch {
				// non-critical
			} finally {
				loadingFeatures = false;
			}
		}
	}
</script>

<div class="track-view">
	<div class="track-header">
		<div class="track-info">
			<h2 class="track-title">{track.title ?? 'Unknown'}</h2>
			<span class="track-artist">{track.artist ?? 'Unknown'}</span>
		</div>
		<div class="track-meta">
			<span class="meta-badge" style="color: {getCamelotColor(track.key)}">
				{track.key ?? '?'}
			</span>
			<span class="meta-badge">{track.bpm ? Math.round(track.bpm) : '?'} BPM</span>
			<span class="meta-badge">{track.energy ?? '?'}</span>
			{#if track.duration_sec}
				<span class="meta-badge dim">{formatTime(track.duration_sec)}</span>
			{/if}
		</div>
	</div>

	{#if error}
		<div class="error-msg">{error}</div>
	{/if}

	{#if loadingWaveform}
		<div class="loading">Loading waveform...</div>
	{:else if waveformData}
		<WavesurferPlayer
			trackId={track.id}
			peaks={waveformData.envelope}
			duration={waveformData.duration_sec}
			beats={waveformData.beats}
		/>
	{:else if !track.has_waveform}
		<div class="no-data">
			No waveform data. Run <code>djset analyze</code> to generate.
		</div>
	{/if}

	{#if features}
		<div class="features-panel">
			<h3 class="section-title">Audio Features</h3>
			<div class="feature-grid">
				<div class="feature">
					<span class="feature-label">Energy</span>
					<div class="feature-bar">
						<div class="bar-fill" style="width: {(features.energy ?? 0) * 100}%"></div>
					</div>
					<span class="feature-value">{features.energy?.toFixed(2) ?? '?'}</span>
				</div>
				<div class="feature">
					<span class="feature-label">Danceability</span>
					<div class="feature-bar">
						<div class="bar-fill dance" style="width: {(features.danceability ?? 0) * 100}%"></div>
					</div>
					<span class="feature-value">{features.danceability?.toFixed(2) ?? '?'}</span>
				</div>
				{#if features.mood_happy != null}
					<div class="feature">
						<span class="feature-label">Mood</span>
						<div class="mood-bars">
							<span class="mood" title="Happy">H:{features.mood_happy.toFixed(1)}</span>
							<span class="mood" title="Sad">S:{features.mood_sad?.toFixed(1)}</span>
							<span class="mood" title="Aggressive">A:{features.mood_aggressive?.toFixed(1)}</span>
							<span class="mood" title="Relaxed">R:{features.mood_relaxed?.toFixed(1)}</span>
						</div>
					</div>
				{/if}
				{#if features.energy_intro != null}
					<div class="feature">
						<span class="feature-label">Energy Curve</span>
						<div class="mood-bars">
							<span class="mood">Intro:{features.energy_intro.toFixed(2)}</span>
							<span class="mood">Body:{features.energy_body?.toFixed(2)}</span>
							<span class="mood">Outro:{features.energy_outro?.toFixed(2)}</span>
						</div>
					</div>
				{/if}
			</div>
		</div>
	{/if}
</div>

<style>
	.track-view {
		padding: 16px;
		display: flex;
		flex-direction: column;
		gap: 12px;
	}

	.track-header {
		display: flex;
		justify-content: space-between;
		align-items: flex-start;
		gap: 12px;
	}

	.track-title {
		font-size: 18px;
		font-weight: 600;
	}

	.track-artist {
		font-size: 14px;
		color: var(--text-secondary);
	}

	.track-meta {
		display: flex;
		gap: 8px;
		align-items: center;
		flex-shrink: 0;
	}

	.meta-badge {
		font-size: 12px;
		font-weight: 600;
		padding: 2px 8px;
		background: var(--bg-tertiary);
		border-radius: 4px;
	}

	.meta-badge.dim {
		color: var(--text-dim);
	}

	.loading, .no-data, .error-msg {
		padding: 20px;
		text-align: center;
		font-size: 13px;
		color: var(--text-secondary);
	}

	.error-msg {
		color: var(--energy-high);
	}

	.no-data code {
		background: var(--bg-tertiary);
		padding: 2px 6px;
		border-radius: 3px;
		font-size: 12px;
	}

	.features-panel {
		background: var(--bg-secondary);
		border-radius: 6px;
		padding: 12px;
	}

	.section-title {
		font-size: 12px;
		text-transform: uppercase;
		letter-spacing: 0.5px;
		color: var(--text-secondary);
		margin-bottom: 10px;
	}

	.feature-grid {
		display: flex;
		flex-direction: column;
		gap: 8px;
	}

	.feature {
		display: flex;
		align-items: center;
		gap: 8px;
	}

	.feature-label {
		width: 90px;
		font-size: 12px;
		color: var(--text-secondary);
		flex-shrink: 0;
	}

	.feature-bar {
		flex: 1;
		height: 6px;
		background: var(--bg-tertiary);
		border-radius: 3px;
		overflow: hidden;
	}

	.bar-fill {
		height: 100%;
		background: var(--accent);
		border-radius: 3px;
		transition: width 0.3s;
	}

	.bar-fill.dance {
		background: var(--energy-mid);
	}

	.feature-value {
		width: 36px;
		text-align: right;
		font-size: 12px;
		font-variant-numeric: tabular-nums;
		color: var(--text-secondary);
	}

	.mood-bars {
		display: flex;
		gap: 8px;
		font-size: 11px;
		color: var(--text-secondary);
	}

	.mood {
		font-variant-numeric: tabular-nums;
	}
</style>
