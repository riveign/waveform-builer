<script lang="ts">
	import type { Track } from '$lib/types';
	import { formatKey, getCamelotColor } from '$lib/utils/camelot';
	import { getPlayerStore } from '$lib/stores/player.svelte';
	import { preloadOnHover } from '$lib/utils/audio-preload';
	import { prefetchPeaks } from '$lib/api/waveforms';
	import { updateTrackRating } from '$lib/api/tracks';
	import Menu from '../primitives/Menu.svelte';
	import Button from '../primitives/Button.svelte';
	import TrackContextMenu from './TrackContextMenu.svelte';
	import StarRating from './StarRating.svelte';

	const player = getPlayerStore();

	/** Known energy zones → their semantic --zone-* token (single source of truth,
	 * matches EnergyZonePicker / EnergyConflictBadge). Unknown/empty falls back to dim. */
	const ENERGY_ZONES = ['intro', 'warmup', 'build', 'drive', 'peak', 'close'];
	function zoneColor(zone: string | null | undefined): string {
		return zone && ENERGY_ZONES.includes(zone) ? `var(--zone-${zone})` : 'var(--text-dim)';
	}

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
				<th class="col-play" aria-label="Play"></th>
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
				{@const totalPlays = (track.play_count ?? 0) + (track.kiku_play_count ?? 0)}
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
						<span class="play-slot" class:playing={isCurrentTrack && player.isPlaying}>
							<Button
								iconOnly
								shape="round"
								variant="ghost"
								size="sm"
								onclick={(e) => handlePlay(e, track)}
								ariaLabel={isCurrentTrack && player.isPlaying ? 'Pause' : 'Play'}
								title={isCurrentTrack && player.isPlaying ? 'Pause' : 'Play'}
							>
								{#snippet icon()}{#if isCurrentTrack && player.isPlaying}&#x23F8;{:else}&#x25B6;{/if}{/snippet}
							</Button>
						</span>
					</td>
					<td class="col-title" title={track.title ?? ''}>
						{track.title ?? '?'}
					</td>
					<td class="col-artist" title={track.artist ?? ''}>
						{track.artist ?? '?'}
					</td>
					<td class="col-key">
						{#if formatKey(track.key)}
							<span class="cell-key" style:color={getCamelotColor(track.key)} title="Camelot {formatKey(track.key)}">{formatKey(track.key)}</span>
						{:else}
							<span class="dim" title="Key unknown">—</span>
						{/if}
					</td>
					<td class="col-bpm">
						{#if track.bpm}
							<span class="cell-bpm" title="{Math.round(track.bpm)} BPM">{Math.round(track.bpm)}</span>
						{:else}
							<span class="dim" title="BPM unknown">—</span>
						{/if}
					</td>
					<td class="col-energy">
						{#if track.resolved_energy}
							<span class="cell-energy" style:color={zoneColor(track.resolved_energy)} title="Energy zone: {track.resolved_energy}">{track.resolved_energy}</span>
						{:else}
							<span class="dim" title="Energy unknown">—</span>
						{/if}
					</td>
					<td class="col-plays">
						{#if totalPlays > 0}
							<span class="plays-count" title="Rekordbox: {track.play_count ?? 0} · Kiku: {track.kiku_play_count ?? 0}">{totalPlays}</span>
						{:else}
							<span class="dim" title="Never played">—</span>
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
	<Menu bind:open={contextMenuOpen} x={contextMenuX} y={contextMenuY} label="Track actions">
		<TrackContextMenu
			track={contextMenuTrack}
			onclose={() => contextMenuOpen = false}
			ontrackupdated={(updates) => {
				if (contextMenuTrack) Object.assign(contextMenuTrack, updates);
			}}
		/>
	</Menu>
{/if}

<style>
	.track-table-wrapper {
		overflow-y: auto;
		flex: 1;
		/* Container query context — column priority responds to the LIST's own
		 * width, not the viewport, so the sidebar drops columns as it narrows. */
		container-type: inline-size;
		container-name: track-list;
	}

	.track-table {
		width: 100%;
		border-collapse: collapse;
		font-size: var(--text-sm);
	}

	/* Header + every body row share ONE grid template, so columns line up exactly.
	 * TITLE + ARTIST take the flexible space (minmax(0,1fr)) and ellipsize; the
	 * short/numeric cells stay fixed and never get crushed.
	 * Priority order built into the template: PLAYS (lowest) drops first at the
	 * narrow breakpoint, then ENERGY — header + body drop together since they
	 * share these vars. */
	.track-table thead tr,
	.track-row {
		display: grid;
		grid-template-columns:
			var(--list-col-play)
			minmax(0, 1.6fr)              /* TITLE — largest flexible */
			minmax(0, 1fr)               /* ARTIST — smaller flexible */
			var(--list-col-key)
			var(--list-col-bpm)
			var(--list-col-energy)
			var(--list-col-plays)
			var(--list-col-rating);
		align-items: center;
		column-gap: var(--list-row-gap);
		padding-inline: var(--list-row-pad-x);
	}

	thead {
		position: sticky;
		top: 0;
		z-index: 1;
	}

	/* SOLID opaque header background so scrolled rows are fully masked. The grid
	 * column-gap on `thead tr` would leave transparent slivers if only the th's
	 * were painted, so the background lives on the row container itself (full width,
	 * gaps included) AND on the th's for belt-and-suspenders. */
	.track-table thead tr {
		background: var(--bg-tertiary);
		border-bottom: 1px solid var(--border);
	}

	th {
		background: var(--bg-tertiary);
		padding: var(--list-row-pad-y) 0;
		min-height: var(--list-row-height);
		display: flex;
		align-items: center;
		text-align: left;
		font-weight: 600;
		color: var(--text-secondary);
		font-size: var(--text-2xs);
		letter-spacing: 0.3px;
	}

	td {
		padding: var(--list-row-pad-y) 0;
		min-height: var(--list-row-height);
		display: flex;
		align-items: center;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
		border-bottom: 1px solid var(--bg-tertiary);
	}

	.track-row {
		cursor: grab;
		transition: background 0.1s;
		border-bottom: 1px solid var(--bg-tertiary);
	}
	.track-row td { border-bottom: none; }

	.track-row:active {
		cursor: grabbing;
	}

	.track-row:hover {
		background: var(--bg-hover);
	}

	.track-row.selected {
		background: var(--bg-active);
		box-shadow: inset 2px 0 0 var(--accent);
	}

	.track-row.now-playing {
		background: color-mix(in srgb, var(--accent) 8%, transparent);
	}

	.track-row.has-waveform .col-title {
		color: var(--accent);
	}

	/* Title + artist: 1 line, ellipsis, full value lives in title= (recoverable
	 * truncation — content-conventions §2). */
	.col-play { justify-content: center; }
	.col-title { display: block; min-width: 0; line-height: var(--list-row-height); }
	.col-artist { display: block; min-width: 0; line-height: var(--list-row-height); color: var(--text-secondary); }
	.col-key { justify-content: flex-start; }
	.col-bpm { justify-content: flex-end; }
	.col-energy { justify-content: flex-start; }
	.col-plays { justify-content: flex-end; }
	.col-rating { justify-content: flex-start; }

	/* Header labels align to their body cells (Plays + BPM read as right-aligned
	 * numbers, so their th hugs the right too). */
	th.col-bpm,
	th.col-plays { justify-content: flex-end; }

	/* DENSE-TABLE cell convention: lightweight COLORED TEXT, no box/border/background.
	 * (Cards use the heavier <Chip> primitive; this list is dense, so text-only.) */
	.cell-key {
		font-weight: var(--font-weight-semibold);
		font-variant-numeric: tabular-nums;
		white-space: nowrap;
	}
	.cell-bpm {
		color: var(--text-secondary);
		font-variant-numeric: tabular-nums;
		white-space: nowrap;
	}
	.cell-energy {
		font-weight: var(--font-weight-semibold);
		white-space: nowrap;
		text-transform: capitalize;
	}

	/* The play control is a Button primitive (iconOnly round). Hover-reveal lives
	 * on this wrapper so the table owns row state. */
	.play-slot {
		display: inline-flex;
		opacity: 0;
		transition: opacity var(--dur-fast, 0.15s) var(--ease-standard, ease);
	}
	.play-slot :global(.btn--icon.btn--sm) {
		width: 22px;
		height: 22px;
		font-size: var(--text-2xs);
	}

	.track-row:hover .play-slot,
	.play-slot.playing {
		opacity: 1;
	}

	.play-slot.playing :global(.btn) {
		color: var(--accent);
	}

	.plays-count {
		color: var(--text-secondary);
		font-size: var(--text-xs);
	}

	.dim {
		color: var(--text-dim);
	}

	/* --- Responsive column priority (container query on the list width) ---
	 * Drop lowest-priority columns first; header + body share the template vars
	 * so they always drop together. Keep order: TITLE, ARTIST, KEY, BPM, RATING. */

	/* < ~380px: drop PLAYS (lowest priority). */
	@container track-list (max-width: 379px) {
		.track-table thead tr,
		.track-row {
			grid-template-columns:
				var(--list-col-play)
				minmax(0, 1.6fr)
				minmax(0, 1fr)
				var(--list-col-key)
				var(--list-col-bpm)
				var(--list-col-energy)
				var(--list-col-rating);
		}
		.col-plays { display: none; }
	}

	/* < ~320px: also drop ENERGY (next lowest). */
	@container track-list (max-width: 319px) {
		.track-table thead tr,
		.track-row {
			grid-template-columns:
				var(--list-col-play)
				minmax(0, 1.6fr)
				minmax(0, 1fr)
				var(--list-col-key)
				var(--list-col-bpm)
				var(--list-col-rating);
		}
		.col-energy { display: none; }
	}
</style>
