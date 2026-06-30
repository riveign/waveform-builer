<script lang="ts">
	import { onMount } from 'svelte';
	import type { Track } from '$lib/types';
	import { getAlbumTracks, getAlbumCoverUrl, type Album } from '$lib/api/albums';
	import { getPlayerStore } from '$lib/stores/player.svelte';
	import Button from '../primitives/Button.svelte';
	import MusicBrainzMatchModal from './MusicBrainzMatchModal.svelte';
	import FixMetadataModal from './FixMetadataModal.svelte';

	let {
		albumKey,
		onback,
		onselect,
	}: {
		albumKey: string;
		onback: () => void;
		onselect: (track: Track) => void;
	} = $props();

	const player = getPlayerStore();

	let album = $state<Album | null>(null);
	let tracks = $state<Track[]>([]);
	let loading = $state(false);
	let error = $state<string | null>(null);
	let mbModalOpen = $state(false);
	let fixModalOpen = $state(false);

	async function load() {
		loading = true;
		error = null;
		try {
			const res = await getAlbumTracks(albumKey);
			album = res.album;
			tracks = res.tracks;
		} catch (e) {
			error = e instanceof Error ? e.message : 'Could not load album';
		} finally {
			loading = false;
		}
	}

	function hashKey(key: string): number {
		let h = 0;
		for (let i = 0; i < key.length; i++) h = (h * 31 + key.charCodeAt(i)) | 0;
		return Math.abs(h);
	}

	function playAlbum(startIndex = 0) {
		if (tracks.length === 0) return;
		// Negative synthetic set id to avoid colliding with real sets
		const syntheticId = -hashKey(albumKey);
		player.playSet(syntheticId, tracks, startIndex);
	}

	function positionLabel(t: Track): string {
		const trackNo = t.track_number;
		const discNo = t.disc_number;
		if (!trackNo) return '·';
		if (discNo && discNo > 1) return `${discNo}.${String(trackNo).padStart(2, '0')}`;
		return String(trackNo).padStart(2, '0');
	}

	function coverSourceLabel(source: string): string {
		const labels: Record<string, string> = {
			itunes: 'iTunes',
			deezer: 'Deezer',
			caa: 'Cover Art Archive',
		};
		return labels[source] ?? source;
	}

	function formatDuration(sec: number | null | undefined): string {
		if (!sec || sec <= 0) return '';
		const m = Math.floor(sec / 60);
		const s = Math.floor(sec % 60);
		return `${m}:${String(s).padStart(2, '0')}`;
	}

	function onMBApplied() {
		mbModalOpen = false;
		load();
	}

	function onFixApplied() {
		load();
	}

	onMount(load);
</script>

<div class="album-detail">
	<div class="header-bar">
		<Button variant="secondary" size="sm" onclick={onback} ariaLabel="Back to albums">← Albums</Button>
	</div>

	{#if loading && !album}
		<div class="status">Reading the album...</div>
	{:else if error}
		<div class="status error" role="alert">
			Couldn't open this album. Try heading back and picking it again.
		</div>
	{:else if album}
		<div class="album-header">
			<div class="cover-large">
				<img
					src={getAlbumCoverUrl(album.album_key)}
					alt=""
					onerror={(e) => ((e.currentTarget as HTMLImageElement).style.display = 'none')}
				/>
			</div>
			<div class="info">
				<div class="album-title">{album.album}</div>
				<div class="album-artist">{album.artist}</div>
				<div class="album-meta">
					{#if album.year}{album.year} ·{/if}
					{album.track_count} track{album.track_count === 1 ? '' : 's'}
					{#if album.label} · {album.label}{/if}
					{#if album.is_compilation} · compilation{/if}
				</div>

				<div class="actions">
					<Button variant="primary" size="sm" onclick={() => playAlbum(0)} disabled={tracks.length === 0}>
						▶ Play album
					</Button>
					<Button variant="secondary" size="sm" onclick={() => (mbModalOpen = true)}>
						Match on MusicBrainz
					</Button>
					<Button variant="secondary" size="sm" onclick={() => (fixModalOpen = true)}>
						Check &amp; fix metadata
					</Button>
				</div>

				{#if album.match_status === 'applied' && album.mb_release_id}
					<div class="mb-note">Matched on MusicBrainz</div>
				{/if}
				{#if album.cover_source && album.cover_source !== 'embedded'}
					<div class="art-credit">art via {coverSourceLabel(album.cover_source)}</div>
				{/if}
			</div>
		</div>

		<div class="track-list">
			{#each tracks as t, i (t.id)}
				<div class="track-row">
					<button
						class="play-btn"
						onclick={() => playAlbum(i)}
						title="Play from here"
					>▶</button>
					<span class="position">{positionLabel(t)}</span>
					<button class="title-cell" onclick={() => onselect(t)}>
						<span class="title">{t.title ?? '—'}</span>
						{#if album.is_compilation && t.artist}
							<span class="row-artist">{t.artist}</span>
						{/if}
					</button>
					<span class="duration">{formatDuration(t.duration_sec)}</span>
				</div>
			{/each}
		</div>
	{/if}
</div>

<MusicBrainzMatchModal
	bind:open={mbModalOpen}
	{albumKey}
	kikuTracks={tracks}
	onapply={onMBApplied}
/>

<FixMetadataModal
	bind:open={fixModalOpen}
	{albumKey}
	albumName={album?.album ?? ''}
	onapply={onFixApplied}
/>

<style>
	.album-detail {
		display: flex;
		flex-direction: column;
		flex: 1 1 auto;
		overflow-y: auto;
	}

	.header-bar {
		display: flex;
		align-items: center;
		min-height: var(--band-toolbar-h);
		padding: 0 var(--space-xl);
		border-bottom: 1px solid var(--border);
		position: sticky;
		top: 0;
		z-index: 5;
		background: var(--bg-primary);
	}

	.album-header {
		display: grid;
		grid-template-columns: 200px 1fr;
		gap: 18px;
		padding: 20px;
		border-bottom: 1px solid var(--border);
	}

	.cover-large {
		width: 200px;
		height: 200px;
		background: var(--surface-2);
		border-radius: var(--radius-lg);
		overflow: hidden;
		box-shadow: 0 4px 16px rgba(0, 0, 0, 0.5);
		position: relative;
	}
	.cover-large::before {
		content: '♪';
		position: absolute;
		inset: 0;
		display: flex;
		align-items: center;
		justify-content: center;
		font-size: 64px;
		color: var(--text-dim);
	}
	.cover-large img {
		position: relative;
		z-index: 1;
		width: 100%; height: 100%; object-fit: cover; display: block;
	}

	.info { display: flex; flex-direction: column; gap: 4px; min-width: 0; }
	.album-title {
		font-size: 22px;
		font-weight: 700;
		color: var(--text-primary);
		line-height: 1.2;
	}
	.album-artist {
		font-size: 15px;
		color: var(--text-secondary);
	}
	.album-meta {
		font-size: 12px;
		color: var(--text-dim);
		margin-top: 4px;
	}

	.actions {
		display: flex;
		gap: var(--space-md);
		margin-top: 14px;
	}

	.mb-note {
		font-size: 11px;
		color: var(--text-dim);
		margin-top: 8px;
		font-style: italic;
	}

	.art-credit {
		font-size: 11px;
		color: var(--text-dim);
		margin-top: 4px;
		font-style: italic;
	}

	.track-list {
		display: flex;
		flex-direction: column;
		padding: 4px 0 24px;
	}

	.track-row {
		display: grid;
		grid-template-columns: 28px 36px 1fr 50px;
		gap: 10px;
		align-items: center;
		padding: 6px 20px;
		font-size: 13px;
		border-bottom: 1px solid var(--border);
	}
	.track-row:hover { background: var(--surface-2); }

	.play-btn {
		appearance: none;
		background: transparent;
		border: none;
		color: var(--text-secondary);
		cursor: pointer;
		font-size: 11px;
		padding: 0;
	}
	.play-btn:hover { color: var(--accent); }

	.position {
		font-variant-numeric: tabular-nums;
		color: var(--text-dim);
		font-size: 12px;
	}

	.title-cell {
		appearance: none;
		background: transparent;
		border: none;
		text-align: left;
		color: var(--text-primary);
		cursor: pointer;
		padding: 0;
		overflow: hidden;
		display: flex;
		flex-direction: column;
		gap: 2px;
	}
	.title-cell:hover .title { color: var(--accent); }
	.title {
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}
	.row-artist {
		font-size: 11px;
		color: var(--text-dim);
	}

	.duration {
		text-align: right;
		color: var(--text-dim);
		font-variant-numeric: tabular-nums;
		font-size: 12px;
	}

	.status {
		padding: 20px;
		text-align: center;
		color: var(--text-secondary);
		font-size: 13px;
	}
	.status.error { color: var(--energy-high); }
</style>
