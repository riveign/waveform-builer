<script lang="ts">
	import type { Track } from '$lib/types';
	import { getCamelotColor } from '$lib/utils/camelot';
	import { formatTime } from '$lib/utils/waveform';
	import { energyColor, normalizeEnergy } from '$lib/utils/energy';
	import { getPlayerStore } from '$lib/stores/player.svelte';
	import { preloadOnHover } from '$lib/utils/audio-preload';
	import { prefetchPeaks } from '$lib/api/waveforms';
	import { updateTrackRating } from '$lib/api/tracks';
	import ContextMenu from '../ContextMenu.svelte';
	import TrackContextMenu from './TrackContextMenu.svelte';
	import StarRating from './StarRating.svelte';

	const player = getPlayerStore();

	function handleHover(track: Track) {
		preloadOnHover(track.id);
		prefetchPeaks(track.id);
	}

	let {
		tracks,
		selectedId = null,
		onselect,
	}: {
		tracks: Track[];
		selectedId?: number | null;
		onselect: (track: Track) => void;
	} = $props();

	let contextMenuTrack = $state<Track | null>(null);
	let contextMenuX = $state(0);
	let contextMenuY = $state(0);
	let contextMenuOpen = $state(false);

	function handlePlay(e: MouseEvent, track: Track) {
		e.stopPropagation();
		if (player.isPlaying && player.currentTrack?.id === track.id) {
			player.pause();
		} else {
			player.play(track);
		}
	}

	async function handleRatingChange(track: Track, rating: number) {
		const prev = track.rating;
		track.rating = rating;
		try {
			await updateTrackRating(track.id, rating);
		} catch {
			track.rating = prev;
		}
	}
</script>

<div class="track-table-wrapper">
	<table class="track-table">
		<thead>
			<tr>
				<th class="col-play"></th>
				<th class="col-title">Title</th>
				<th class="col-artist">Artist</th>
				<th class="col-key">Key</th>
				<th class="col-bpm">BPM</th>
				<th class="col-energy">Energy</th>
				<th class="col-plays">Plays</th>
				<th class="col-rating">Rating</th>
			</tr>
		</thead>
		<tbody>
			{#each tracks as track (track.id)}
				{@const isCurrentTrack = player.currentTrack?.id === track.id}
				<tr
					class="track-row"
					class:selected={track.id === selectedId}
					class:has-waveform={track.has_waveform}
					class:now-playing={isCurrentTrack && player.isPlaying}
					onclick={() => onselect(track)}
					ondblclick={(e) => { e.preventDefault(); player.play(track); }}
					onmouseenter={() => handleHover(track)}
					oncontextmenu={(e) => {
						e.preventDefault();
						contextMenuTrack = track;
						contextMenuX = e.clientX;
						contextMenuY = e.clientY;
						contextMenuOpen = true;
					}}
					draggable="true"
					ondragstart={(e) => {
						e.dataTransfer?.setData('application/x-kiku-track', JSON.stringify({ id: track.id, title: track.title }));
						if (e.dataTransfer) e.dataTransfer.effectAllowed = 'copy';
					}}
				>
					<td class="col-play">
						<button
							class="play-btn"
							class:playing={isCurrentTrack && player.isPlaying}
							onclick={(e) => handlePlay(e, track)}
							title={isCurrentTrack && player.isPlaying ? 'Pause' : 'Play'}
						>
							{#if isCurrentTrack && player.isPlaying}
								&#x23F8;
							{:else}
								&#x25B6;
							{/if}
						</button>
					</td>
					<td class="col-title" title={track.title ?? ''}>
						{track.title ?? '?'}
					</td>
					<td class="col-artist" title={track.artist ?? ''}>
						{track.artist ?? '?'}
					</td>
					<td class="col-key">
						<span class="key-badge" style="color: {getCamelotColor(track.key)}">
							{track.key ?? '?'}
						</span>
					</td>
					<td class="col-bpm">
						{track.bpm ? Math.round(track.bpm) : '?'}
					</td>
					<td class="col-energy">
						<span class="energy-tag" style="color: {energyColor(normalizeEnergy(track.resolved_energy))}">{track.resolved_energy ?? '?'}</span>
					</td>
					<td class="col-plays">
						{#if (track.play_count ?? 0) + (track.kiku_play_count ?? 0) > 0}
							<span class="plays-count" title="Rekordbox: {track.play_count ?? 0} · Kiku: {track.kiku_play_count ?? 0}">{(track.play_count ?? 0) + (track.kiku_play_count ?? 0)}</span>
						{:else}
							<span class="dim">--</span>
						{/if}
					</td>
					<td class="col-rating" onclick={(e) => e.stopPropagation()}>
						<StarRating
							rating={track.rating ?? 0}
							size="sm"
							onchange={(r) => handleRatingChange(track, r)}
						/>
					</td>
				</tr>
			{/each}
		</tbody>
	</table>
</div>

{#if contextMenuTrack}
	<ContextMenu bind:open={contextMenuOpen} x={contextMenuX} y={contextMenuY}>
		<TrackContextMenu
			track={contextMenuTrack}
			onclose={() => contextMenuOpen = false}
			ontrackupdated={(updates) => {
				if (contextMenuTrack) Object.assign(contextMenuTrack, updates);
			}}
		/>
	</ContextMenu>
{/if}

<style>
	.track-table-wrapper {
		overflow-y: auto;
		flex: 1;
	}

	.track-table {
		width: 100%;
		border-collapse: collapse;
		font-size: 12px;
	}

	thead {
		position: sticky;
		top: 0;
		z-index: 1;
	}

	th {
		background: var(--bg-tertiary);
		padding: 6px 8px;
		text-align: left;
		font-weight: 600;
		color: var(--text-secondary);
		font-size: 11px;
		text-transform: uppercase;
		letter-spacing: 0.5px;
		border-bottom: 1px solid var(--border);
	}

	td {
		padding: 5px 8px;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
		border-bottom: 1px solid var(--bg-tertiary);
	}

	.track-row {
		cursor: grab;
		transition: background 0.1s;
	}

	.track-row:active {
		cursor: grabbing;
	}

	.track-row:hover {
		background: var(--bg-hover);
	}

	.track-row.selected {
		background: var(--bg-active);
		border-left: 2px solid var(--accent);
	}

	.track-row.now-playing {
		background: rgba(0, 206, 209, 0.08);
	}

	.track-row.has-waveform .col-title {
		color: var(--accent);
	}

	.col-play { width: 28px; text-align: center; padding: 0 2px; }
	.col-title { max-width: 140px; }
	.col-artist { max-width: 100px; color: var(--text-secondary); }
	.col-key { width: 40px; text-align: center; }
	.col-bpm { width: 40px; text-align: right; }
	.col-energy { width: 60px; }
	.col-plays { width: 36px; text-align: right; }
	.col-rating { width: 60px; }

	.play-btn {
		width: 22px;
		height: 22px;
		border-radius: 50%;
		background: transparent;
		color: var(--text-dim);
		font-size: 9px;
		display: flex;
		align-items: center;
		justify-content: center;
		transition: all 0.15s;
		border: none;
		cursor: pointer;
		opacity: 0;
	}

	.track-row:hover .play-btn,
	.play-btn.playing {
		opacity: 1;
	}

	.play-btn.playing {
		color: var(--accent);
	}

	.play-btn:hover {
		background: var(--bg-tertiary);
		color: var(--accent);
	}

	.key-badge {
		font-weight: 600;
		font-size: 11px;
	}

	.energy-tag {
		font-size: 11px;
		color: var(--text-secondary);
		text-transform: capitalize;
	}

	.plays-count {
		color: var(--text-secondary);
		font-size: 11px;
	}

	.dim {
		color: var(--text-dim);
	}
</style>
