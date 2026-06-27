<script lang="ts">
	import { getPlaybackStore } from '$lib/stores/playback.svelte';
	import { formatTime } from '$lib/utils/waveform';
	import Button from '$lib/components/primitives/Button.svelte';

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
				<Button
					iconOnly
					shape="round"
					variant="secondary"
					size="sm"
					ariaLabel="Previous track"
					title="Previous (ArrowLeft)"
					onclick={() => pb.previous()}
					disabled={pb.currentIndex <= 0}
				>
					{#snippet icon()}&#x23EE;{/snippet}
				</Button>

				<Button
					iconOnly
					shape="round"
					variant="primary"
					size="md"
					ariaLabel={pb.status === 'playing' || pb.status === 'transitioning' ? 'Pause' : 'Play'}
					title="Play/Pause (Space)"
					onclick={() => pb.togglePlayPause()}
				>
					{#snippet icon()}{pb.status === 'playing' || pb.status === 'transitioning' ? '\u23F8' : '\u25B6'}{/snippet}
				</Button>

				<Button
					iconOnly
					shape="round"
					variant="secondary"
					size="sm"
					ariaLabel="Next track"
					title="Next (ArrowRight)"
					onclick={() => pb.next()}
					disabled={pb.currentIndex >= pb.tracks.length - 1}
				>
					{#snippet icon()}&#x23ED;{/snippet}
				</Button>

				<Button
					iconOnly
					shape="round"
					variant="danger"
					size="sm"
					ariaLabel="Stop playback"
					title="Stop (Escape)"
					onclick={() => pb.stop()}
				>
					{#snippet icon()}&#x23F9;{/snippet}
				</Button>
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
		gap: var(--space-xl);
		padding: var(--space-md) var(--space-xl);
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
		font-size: var(--text-2xs);
		font-weight: var(--font-weight-semibold);
		text-transform: uppercase;
		letter-spacing: 0.5px;
		padding: var(--space-2xs) var(--space-sm);
		border-radius: var(--radius-xs);
		background: var(--accent);
		color: var(--on-accent);
		white-space: nowrap;
	}

	.track-info {
		display: flex;
		flex-direction: column;
		min-width: 0;
	}

	.track-title {
		font-size: var(--text-sm);
		font-weight: var(--font-weight-semibold);
		color: var(--text-primary);
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.track-artist {
		font-size: var(--text-xs);
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
		gap: var(--space-xs);
		min-width: 0;
	}

	.transport {
		display: flex;
		align-items: center;
		gap: var(--space-md);
	}

	.progress-row {
		display: flex;
		align-items: center;
		gap: var(--space-md);
		width: 100%;
		max-width: 400px;
	}

	.progress-track {
		flex: 1;
		height: 4px;
		background: var(--bg-tertiary);
		border-radius: var(--radius-xs);
		overflow: hidden;
	}

	.progress-fill {
		height: 100%;
		background: var(--accent);
		border-radius: var(--radius-xs);
		transition: width var(--dur-base) linear;
	}

	.time {
		font-size: var(--text-2xs);
		color: var(--text-dim);
		font-variant-numeric: tabular-nums;
		min-width: 32px;
		text-align: center;
	}

	.bar-right {
		display: flex;
		align-items: center;
		gap: var(--space-lg);
		flex-shrink: 0;
	}

	.builder-btn {
		padding: var(--space-xs) var(--space-md);
		font-size: var(--text-xs);
		font-weight: var(--font-weight-semibold);
		border-radius: var(--radius-sm);
		border: 1px solid var(--border);
		transition: background var(--dur-fast) var(--ease-standard);
	}

	.builder-btn.keep {
		background: var(--accent);
		color: var(--on-accent);
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
		gap: var(--space-xs);
		font-size: var(--text-xs);
		color: var(--text-secondary);
		cursor: pointer;
		white-space: nowrap;
	}

	.bpm-match-toggle input[type="checkbox"] {
		accent-color: var(--accent);
	}

	.set-progress {
		display: flex;
		gap: var(--space-2xs);
		align-items: center;
	}

	.dot {
		width: 6px;
		height: 6px;
		border-radius: var(--radius-full);
		background: var(--bg-tertiary);
		transition: all var(--dur-base);
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
		background: var(--score-excellent);
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
