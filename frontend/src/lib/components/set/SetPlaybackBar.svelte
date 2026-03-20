<script lang="ts">
	import { getPlaybackStore } from '$lib/stores/playback.svelte';
	import { formatTime } from '$lib/utils/waveform';

	const pb = getPlaybackStore();

	let trackDuration = $derived(pb.currentTrack?.duration_sec ?? 0);
	let progressPct = $derived(trackDuration > 0 ? (pb.currentTime / trackDuration) * 100 : 0);
</script>

{#if pb.isActive}
	<div class="playback-bar">
		<div class="bar-left">
			<span class="mode-badge">{pb.mode === 'express' ? 'Express' : 'Live Builder'}</span>
			{#if pb.currentTrack}
				<span class="track-info">
					<span class="track-title">{pb.currentTrack.title ?? 'Untitled'}</span>
					<span class="track-artist">{pb.currentTrack.artist ?? ''}</span>
				</span>
			{/if}
		</div>

		<div class="bar-center">
			<div class="transport">
				<button
					class="transport-btn"
					onclick={() => pb.previous()}
					disabled={pb.currentIndex <= 0}
					title="Previous (ArrowLeft)"
				>
					&#x23EE;
				</button>

				<button
					class="transport-btn play"
					onclick={() => pb.togglePlayPause()}
					title="Play/Pause (Space)"
				>
					{pb.status === 'playing' || pb.status === 'transitioning' ? '\u23F8' : '\u25B6'}
				</button>

				<button
					class="transport-btn"
					onclick={() => pb.next()}
					disabled={pb.currentIndex >= pb.tracks.length - 1}
					title="Next (ArrowRight)"
				>
					&#x23ED;
				</button>

				<button
					class="transport-btn stop"
					onclick={() => pb.stop()}
					title="Stop (Escape)"
				>
					&#x23F9;
				</button>
			</div>

			<div class="progress-row">
				<span class="time">{formatTime(pb.currentTime)}</span>
				<div class="progress-track">
					<div class="progress-fill" style="width: {progressPct}%"></div>
				</div>
				<span class="time">{formatTime(trackDuration)}</span>
			</div>
		</div>

		<div class="bar-right">
			{#if pb.mode === 'builder'}
				<button class="builder-btn keep" onclick={() => pb.keep()} title="Keep (K)">
					Keep
				</button>
				<button class="builder-btn skip" onclick={() => pb.skip()} title="Skip">
					Skip
				</button>
			{/if}

			<label class="bpm-match-toggle" title="Pitch-match BPMs during transitions">
				<input
					type="checkbox"
					checked={pb.bpmMatch}
					onchange={(e) => { pb.bpmMatch = (e.target as HTMLInputElement).checked; }}
				/>
				<span>BPM Match</span>
			</label>

			<div class="set-progress">
				{#each pb.tracks as track, i}
					<div
						class="dot"
						class:active={i === pb.currentIndex}
						class:played={i < pb.currentIndex}
						class:confirmed={pb.confirmed.has(track.track_id)}
						title="{track.title ?? 'Track'} ({i + 1}/{pb.tracks.length})"
					></div>
				{/each}
			</div>

			<label class="volume-control">
				<input
					type="range"
					min="0"
					max="1"
					step="0.05"
					value={pb.volume}
					oninput={(e) => { pb.volume = Number((e.target as HTMLInputElement).value); }}
				/>
			</label>
		</div>
	</div>
{/if}

<style>
	.playback-bar {
		display: flex;
		align-items: center;
		gap: 16px;
		padding: 8px 16px;
		background: var(--bg-secondary);
		border-top: 1px solid var(--border);
		flex-shrink: 0;
		min-height: 56px;
	}

	.bar-left {
		display: flex;
		align-items: center;
		gap: 10px;
		min-width: 180px;
		flex-shrink: 0;
	}

	.mode-badge {
		font-size: 10px;
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0.5px;
		padding: 2px 6px;
		border-radius: 3px;
		background: var(--accent);
		color: #000;
		white-space: nowrap;
	}

	.track-info {
		display: flex;
		flex-direction: column;
		min-width: 0;
	}

	.track-title {
		font-size: 12px;
		font-weight: 600;
		color: var(--text-primary);
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.track-artist {
		font-size: 11px;
		color: var(--text-secondary);
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.bar-center {
		flex: 1;
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 4px;
		min-width: 0;
	}

	.transport {
		display: flex;
		align-items: center;
		gap: 8px;
	}

	.transport-btn {
		width: 28px;
		height: 28px;
		border-radius: 50%;
		background: var(--bg-tertiary);
		color: var(--text-primary);
		font-size: 12px;
		display: flex;
		align-items: center;
		justify-content: center;
		transition: background 0.15s;
		border: 1px solid var(--border);
	}

	.transport-btn:hover:not(:disabled) {
		background: var(--bg-hover);
	}

	.transport-btn:disabled {
		opacity: 0.3;
		cursor: default;
	}

	.transport-btn.play {
		width: 34px;
		height: 34px;
		background: var(--accent);
		color: #000;
		font-size: 14px;
		border-color: var(--accent);
	}

	.transport-btn.play:hover {
		opacity: 0.85;
	}

	.transport-btn.stop {
		font-size: 10px;
	}

	.progress-row {
		display: flex;
		align-items: center;
		gap: 8px;
		width: 100%;
		max-width: 400px;
	}

	.progress-track {
		flex: 1;
		height: 4px;
		background: var(--bg-tertiary);
		border-radius: 2px;
		overflow: hidden;
	}

	.progress-fill {
		height: 100%;
		background: var(--accent);
		border-radius: 2px;
		transition: width 0.2s linear;
	}

	.time {
		font-size: 10px;
		color: var(--text-dim);
		font-variant-numeric: tabular-nums;
		min-width: 32px;
		text-align: center;
	}

	.bar-right {
		display: flex;
		align-items: center;
		gap: 12px;
		flex-shrink: 0;
	}

	.builder-btn {
		padding: 4px 10px;
		font-size: 11px;
		font-weight: 600;
		border-radius: 4px;
		border: 1px solid var(--border);
		transition: all 0.15s;
	}

	.builder-btn.keep {
		background: var(--accent);
		color: #000;
		border-color: var(--accent);
	}

	.builder-btn.keep:hover {
		opacity: 0.85;
	}

	.builder-btn.skip {
		background: var(--bg-tertiary);
		color: var(--text-primary);
	}

	.builder-btn.skip:hover {
		background: var(--bg-hover);
	}

	.bpm-match-toggle {
		display: flex;
		align-items: center;
		gap: 4px;
		font-size: 11px;
		color: var(--text-secondary);
		cursor: pointer;
		white-space: nowrap;
	}

	.bpm-match-toggle input[type="checkbox"] {
		accent-color: var(--accent);
	}

	.set-progress {
		display: flex;
		gap: 3px;
		align-items: center;
	}

	.dot {
		width: 6px;
		height: 6px;
		border-radius: 50%;
		background: var(--bg-tertiary);
		transition: all 0.2s;
	}

	.dot.played {
		background: var(--text-dim);
	}

	.dot.active {
		background: var(--accent);
		width: 8px;
		height: 8px;
	}

	.dot.confirmed {
		background: #4ade80;
	}

	.volume-control {
		display: flex;
		align-items: center;
	}

	.volume-control input[type="range"] {
		width: 60px;
		accent-color: var(--accent);
		height: 4px;
	}
</style>
