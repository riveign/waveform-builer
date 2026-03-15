<script lang="ts">
	import type { TinderQueueItem, TinderDecision } from '$lib/types';
	import { getWaveformDetail } from '$lib/api/waveforms';
	import WavesurferPlayer from '../waveform/WavesurferPlayer.svelte';
	import MoodRadar from './MoodRadar.svelte';

	let {
		item,
		ondecide,
		teachingMoment = null,
	}: {
		item: TinderQueueItem;
		ondecide: (decision: TinderDecision, overrideZone?: string) => void;
		teachingMoment?: string | null;
	} = $props();

	let waveformPeaks = $state<string | null>(null);
	let waveformDuration = $state(0);
	let showOverrideMenu = $state(false);

	const ZONES = ['warmup', 'build', 'peak'] as const;

	const zoneColors: Record<string, string> = {
		warmup: '#4ecdc4',
		build: '#ffe66d',
		peak: '#ff6b6b',
	};

	$effect(() => {
		// Load waveform when item changes
		if (item.has_waveform) {
			getWaveformDetail(item.track.id)
				.then((wf) => {
					waveformPeaks = wf.envelope;
					waveformDuration = wf.duration_sec;
				})
				.catch(() => {
					waveformPeaks = null;
				});
		} else {
			waveformPeaks = null;
		}
		showOverrideMenu = false;
	});

	function handleOverride(zone: string) {
		showOverrideMenu = false;
		ondecide('override', zone);
	}

	function handleKeydown(e: KeyboardEvent) {
		const target = e.target as HTMLElement;
		if (target.tagName === 'INPUT' || target.tagName === 'SELECT' || target.tagName === 'TEXTAREA') return;
		if (e.key === 'ArrowRight' || e.key === 'y') { ondecide('confirm'); e.preventDefault(); }
		else if (e.key === 'ArrowUp' || e.key === 's') { ondecide('skip'); e.preventDefault(); }
		else if (e.key === 'ArrowLeft' || e.key === 'o') { showOverrideMenu = !showOverrideMenu; e.preventDefault(); }
	}
</script>

<svelte:window onkeydown={handleKeydown} />

<div class="tinder-card">
	<!-- Track metadata -->
	<div class="card-header">
		<div class="title">{item.track.title ?? 'Unknown'}</div>
		<div class="artist">{item.track.artist ?? 'Unknown'}</div>
		<div class="meta">
			<span>{item.track.bpm ? `${Math.round(item.track.bpm)} BPM` : ''}</span>
			<span>{item.track.key ?? ''}</span>
			<span>{item.track.genre ?? ''}</span>
		</div>
	</div>

	<!-- Waveform player -->
	{#if waveformPeaks}
		<div class="waveform-container">
			<WavesurferPlayer
				trackId={item.track.id}
				peaks={waveformPeaks}
				duration={waveformDuration}
				height={80}
			/>
		</div>
	{:else}
		<div class="waveform-placeholder">No waveform data</div>
	{/if}

	<!-- Prediction + Mood -->
	<div class="prediction-row">
		<div class="prediction">
			<div class="zone-label" style="color: {zoneColors[item.energy_predicted ?? ''] ?? 'var(--text-primary)'}">
				{item.energy_predicted ?? '?'}
			</div>
			<div class="confidence-bar">
				<div class="confidence-fill" style="width: {(item.energy_confidence ?? 0) * 100}%"></div>
			</div>
			<div class="confidence-text">{((item.energy_confidence ?? 0) * 100).toFixed(0)}% confident</div>
		</div>
		{#if item.mood_happy != null || item.mood_sad != null || item.mood_aggressive != null || item.mood_relaxed != null}
			<MoodRadar
				happy={item.mood_happy ?? 0}
				sad={item.mood_sad ?? 0}
				aggressive={item.mood_aggressive ?? 0}
				relaxed={item.mood_relaxed ?? 0}
				size={100}
			/>
		{/if}
	</div>

	<!-- Teaching moment -->
	{#if teachingMoment}
		<div class="teaching-moment">{teachingMoment}</div>
	{/if}

	<!-- Actions -->
	<div class="actions">
		<div class="override-wrapper">
			<button class="action override" onclick={() => showOverrideMenu = !showOverrideMenu}>
				Override <span class="shortcut">&larr; / O</span>
			</button>
			{#if showOverrideMenu}
				<div class="override-menu">
					{#each ZONES as zone}
						<button class="zone-btn" style="color: {zoneColors[zone]}" onclick={() => handleOverride(zone)}>
							{zone}
						</button>
					{/each}
				</div>
			{/if}
		</div>
		<button class="action skip" onclick={() => ondecide('skip')}>
			Skip <span class="shortcut">&uarr; / S</span>
		</button>
		<button class="action confirm" onclick={() => ondecide('confirm')}>
			Confirm <span class="shortcut">&rarr; / Y</span>
		</button>
	</div>
</div>

<style>
	.tinder-card { max-width: 500px; margin: 0 auto; padding: 16px; }
	.card-header { margin-bottom: 12px; }
	.title { font-size: 18px; font-weight: 600; color: var(--text-primary); }
	.artist { font-size: 14px; color: var(--text-secondary); margin-top: 2px; }
	.meta { display: flex; gap: 12px; font-size: 12px; color: var(--text-dim); margin-top: 6px; }
	.waveform-container { margin: 12px 0; }
	.waveform-placeholder { height: 80px; display: flex; align-items: center; justify-content: center; color: var(--text-dim); font-size: 12px; background: var(--bg-secondary); border-radius: 4px; }
	.prediction-row { display: flex; align-items: center; justify-content: space-between; gap: 16px; margin: 16px 0; }
	.prediction { flex: 1; }
	.zone-label { font-size: 24px; font-weight: 700; text-transform: uppercase; }
	.confidence-bar { height: 6px; background: var(--bg-secondary); border-radius: 3px; margin: 6px 0 4px; overflow: hidden; }
	.confidence-fill { height: 100%; background: var(--accent); border-radius: 3px; transition: width 0.3s; }
	.confidence-text { font-size: 11px; color: var(--text-dim); }
	.teaching-moment { padding: 8px 12px; background: var(--bg-secondary); border-left: 3px solid var(--accent); border-radius: 4px; font-size: 12px; color: var(--text-secondary); margin-bottom: 12px; font-style: italic; }
	.actions { display: flex; gap: 8px; justify-content: center; }
	.action { padding: 10px 20px; border-radius: 8px; font-size: 14px; font-weight: 600; cursor: pointer; transition: all 0.15s; }
	.confirm { background: #2ecc71; color: #000; }
	.confirm:hover { background: #27ae60; }
	.skip { background: var(--bg-secondary); color: var(--text-secondary); }
	.skip:hover { background: var(--bg-hover); }
	.override { background: var(--bg-secondary); color: var(--text-secondary); }
	.override:hover { background: var(--bg-hover); }
	.shortcut { font-size: 10px; opacity: 0.6; margin-left: 4px; }
	.override-wrapper { position: relative; }
	.override-menu { position: absolute; bottom: 100%; left: 0; background: var(--bg-primary); border: 1px solid var(--border); border-radius: 6px; padding: 4px; display: flex; flex-direction: column; gap: 2px; margin-bottom: 4px; z-index: 10; }
	.zone-btn { padding: 6px 16px; font-size: 13px; font-weight: 600; text-transform: uppercase; cursor: pointer; border-radius: 4px; background: none; }
	.zone-btn:hover { background: var(--bg-hover); }
</style>
