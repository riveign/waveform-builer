<script lang="ts">
	import {
		getRelease,
		getReleaseDigital,
		linkSide,
		unlinkSide,
		patchSide,
		apiMessage,
		type VinylReleaseSummary,
		type VinylSide,
	} from '$lib/api/vinyl';
	import { searchTracks } from '$lib/api/tracks';
	import { getPlayerStore } from '$lib/stores/player.svelte';
	import type { Track } from '$lib/types';
	import { formatKey, getCamelotColor } from '$lib/utils/camelot';

	let { release, open = false, ontoggle, onremove, onchanged }: {
		release: VinylReleaseSummary;
		open?: boolean;
		ontoggle: () => void;
		onremove: () => void;
		onchanged?: () => void;
	} = $props();

	let sides = $state<VinylSide[]>([]);
	let loading = $state(false);
	let error = $state('');
	/** track_id -> the box's current contents while it's being edited. */
	let drafts = $state<Record<number, string>>({});

	const player = getPlayerStore();
	/** The record's files in pressing order — fetched on first play, dropped on any link change. */
	let digitalTracks: Track[] | null = null;
	/** The side whose "link a file" search is open, and what it has found. */
	let linking = $state<number | null>(null);
	let linkQuery = $state('');
	let linkResults = $state<Track[]>([]);
	let linkTimer: ReturnType<typeof setTimeout> | undefined;

	const linked = $derived(sides.filter((s) => s.digital));
	/** A negative id keeps the record's queue from colliding with a real set (AlbumDetail does the same). */
	const queueId = $derived(-(1_000_000 + release.id));

	const catalogue = $derived(
		[release.label, release.catalog_number, release.year].filter(Boolean).join(' · '),
	);
	const complete = $derived(release.sides > 0 && release.plannable === release.sides);
	const allDigital = $derived(release.sides > 0 && release.digital === release.sides);
	/** 'Vinyl, LP, Album, Reissue, Remastered, Stereo' is a catalogue entry, not a
	 *  label. The format and the size are what you'd say out loud. */
	const shortFormat = $derived(
		(release.format ?? '').split(',').slice(0, 2).map((s) => s.trim()).filter(Boolean).join(' '),
	);

	$effect(() => {
		if (open && !sides.length && !loading) void loadSides();
	});

	async function loadSides() {
		loading = true;
		error = '';
		try {
			sides = (await getRelease(release.id)).sides;
		} catch (e) {
			error = apiMessage(e);
		} finally {
			loading = false;
		}
	}

	async function commit(side: VinylSide) {
		const raw = drafts[side.track_id];
		if (raw === undefined) return;
		const bpm = Number(raw);
		if (!raw.trim() || !Number.isFinite(bpm) || bpm <= 0) {
			// Nothing usable typed — put the box back to what's stored.
			const { [side.track_id]: _drop, ...rest } = drafts;
			drafts = rest;
			return;
		}
		if (bpm === side.bpm) return;
		try {
			const updated = await patchSide(side.track_id, { bpm });
			sides = sides.map((s) => (s.track_id === updated.track_id ? updated : s));
			const { [side.track_id]: _done, ...rest } = drafts;
			drafts = rest;
			onchanged?.();
		} catch (e) {
			error = apiMessage(e);
		}
	}

	async function playFrom(side?: VinylSide) {
		const fileId = side?.digital?.track_id;
		if (fileId && player.currentTrack?.id === fileId) {
			player.togglePlay();
			return;
		}
		try {
			digitalTracks ??= await getReleaseDigital(release.id);
			if (!digitalTracks.length) return;
			const start = fileId ? digitalTracks.findIndex((t) => t.id === fileId) : 0;
			player.playSet(queueId, digitalTracks, Math.max(0, start));
		} catch (e) {
			error = apiMessage(e);
		}
	}

	async function applyTwin(change: Promise<VinylSide>) {
		try {
			const updated = await change;
			sides = sides.map((s) => (s.track_id === updated.track_id ? updated : s));
			digitalTracks = null;
			linking = null;
			onchanged?.();
		} catch (e) {
			error = apiMessage(e);
		}
	}

	function openLinkSearch(side: VinylSide) {
		linking = side.track_id;
		linkQuery = side.title ?? '';
		linkResults = [];
		void runLinkSearch();
	}

	function onLinkInput(value: string) {
		linkQuery = value;
		clearTimeout(linkTimer);
		linkTimer = setTimeout(runLinkSearch, 250);
	}

	async function runLinkSearch() {
		const q = linkQuery.trim();
		if (!q) {
			linkResults = [];
			return;
		}
		try {
			linkResults = (await searchTracks({ search: q, medium: 'digital', limit: 6 })).items;
		} catch (e) {
			error = apiMessage(e);
		}
	}

	/** What a number is worth knowing about: where it came from. */
	function sourceLabel(s: VinylSide): string {
		if (!s.bpm) return 'no BPM yet — the builder can’t reach this side';
		if (s.bpm_source === 'manual') return 'you set this';
		if (s.bpm_source === 'library') return 'from your own file';
		if (s.bpm_source === 'unlinked') return 'from a file you unlinked — check it';
		if (s.bpm_source === 'preview') return 'estimated from a 30s preview';
		return s.bpm_source ?? '';
	}
</script>

<article class="record" class:open id="record-{release.id}">
	<button class="face" type="button" onclick={ontoggle} aria-expanded={open}>
		<span class="sleeve">
			{#if release.cover_url}
				<img src={release.cover_url} alt="" loading="lazy" />
			{:else}
				<span class="no-art" aria-hidden="true">
					<svg viewBox="0 0 40 40" width="34" height="34" fill="none">
						<circle cx="20" cy="20" r="17" stroke="currentColor" stroke-width="1.5" />
						<circle cx="20" cy="20" r="7" stroke="currentColor" stroke-width="1" opacity=".6" />
						<circle cx="20" cy="20" r="2" fill="currentColor" />
					</svg>
				</span>
			{/if}
		</span>
		<span class="meta">
			<span class="title">{release.title ?? 'Untitled'}</span>
			<span class="artist">{release.artist ?? '—'}</span>
			{#if catalogue}<span class="cat">{catalogue}</span>{/if}
			<span class="tags">
				{#if shortFormat}<span class="tag" title={release.format ?? ''}>{shortFormat}</span>{/if}
				<span class="tag" class:ready={complete} class:short={!complete}>
					{release.plannable}/{release.sides} ready
				</span>
				{#if release.digital}
					<span
						class="tag digital"
						class:partial={!allDigital}
						title={allDigital ? 'You own every track on this record as a file too' : 'Some tracks on this record are on your drive'}
					>
						<span class="twin-dot" aria-hidden="true"></span>
						{allDigital ? 'digital too' : `${release.digital} of ${release.sides} digital`}
					</span>
				{/if}
			</span>
		</span>
	</button>

	{#if open}
		<div class="sides">
			{#if error}<p class="err" role="alert">{error}</p>{/if}
			{#if loading}
				<p class="loading">Reading the sides…</p>
			{:else}
				{#if linked.length}
					<div class="play-bar">
						<button type="button" class="play-all" onclick={() => playFrom()}>
							<svg viewBox="0 0 10 10" width="10" height="10" aria-hidden="true"><path d="M1 0l9 5-9 5z" fill="currentColor" /></svg>
							Play the {linked.length} digital {linked.length === 1 ? 'track' : 'tracks'}
						</button>
						{#if linked.length < sides.length}
							<span class="hint">in pressing order · vinyl-only sides are skipped</span>
						{/if}
					</div>
				{/if}
				{#each sides as s (s.track_id)}
					{@const nowPlaying = !!s.digital && player.currentTrack?.id === s.digital.track_id && player.isPlaying}
					<div class="side-cell">
						<div class="side" class:suggested={!!s.suggestion}>
							{#if s.digital}
								<button
									type="button"
									class="twin-play"
									class:playing={nowPlaying}
									onclick={() => playFrom(s)}
									aria-label="{nowPlaying ? 'Pause' : 'Play'} {s.title ?? 'this side'} from your file"
									title="{nowPlaying ? 'Pause' : 'Play'} your file"
								>
									{#if nowPlaying}
										<svg viewBox="0 0 10 10" width="9" height="9" aria-hidden="true"><path d="M1 0h3v10H1zM6 0h3v10H6z" fill="currentColor" /></svg>
									{:else}
										<svg viewBox="0 0 10 10" width="9" height="9" aria-hidden="true"><path d="M1 0l9 5-9 5z" fill="currentColor" /></svg>
									{/if}
								</button>
							{:else}
								<span class="twin-play off" aria-hidden="true">{s.suggestion ? '?' : ''}</span>
							{/if}
							<span class="pos">{s.position ?? '—'}</span>
							<span class="name">
								{s.title ?? '—'}
								{#if s.digital}
									<em class="src twin">
										your file{s.digital.album ? ` · ${s.digital.album}` : ''}
										<button type="button" class="inline" onclick={() => applyTwin(unlinkSide(s.track_id, s.digital!.track_id))}>unlink</button>
									</em>
								{:else if s.suggestion}
									<em class="src ask">
										looks like your “{s.suggestion.title}”{s.suggestion.artist ? ` by ${s.suggestion.artist}` : ' (no artist tag)'}
										<button type="button" class="inline yes" onclick={() => applyTwin(linkSide(s.track_id, s.suggestion!.track_id))}>Link</button>
										<button type="button" class="inline" onclick={() => applyTwin(unlinkSide(s.track_id, s.suggestion!.track_id))}>Not it</button>
									</em>
								{:else}
									<em class="src" class:warn={!s.bpm}>
										{sourceLabel(s)}
										<button type="button" class="inline" onclick={() => (linking === s.track_id ? (linking = null) : openLinkSearch(s))}>link a file…</button>
									</em>
								{/if}
							</span>
							<input
								id="side-bpm-{s.track_id}"
								class="bpm"
								type="text"
								inputmode="decimal"
								placeholder="BPM"
								aria-label="BPM for {s.title ?? 'this side'}"
								value={drafts[s.track_id] ?? (s.bpm ?? '')}
								oninput={(e) => (drafts = { ...drafts, [s.track_id]: e.currentTarget.value })}
								onblur={() => commit(s)}
								onkeydown={(e) => e.key === 'Enter' && e.currentTarget.blur()}
							/>
							<span class="key" style:color={s.key ? getCamelotColor(s.key) : undefined}>
								{s.key ? formatKey(s.key) : '—'}
							</span>
						</div>
						{#if linking === s.track_id}
							<div class="link-search">
								<input
									id="link-search-{s.track_id}"
									type="search"
									value={linkQuery}
									oninput={(e) => onLinkInput(e.currentTarget.value)}
									onkeydown={(e) => e.key === 'Escape' && (linking = null)}
									placeholder="Search your files"
									aria-label="Search your files for {s.title ?? 'this side'}"
									autocomplete="off"
								/>
								{#if linkResults.length}
									<ul>
										{#each linkResults as t (t.id)}
											<li>
												<button type="button" onclick={() => applyTwin(linkSide(s.track_id, t.id))}>
													<span class="hit-title">{t.title ?? '—'}</span>
													<span class="hit-meta">{[t.artist, t.album].filter(Boolean).join(' · ')}</span>
												</button>
											</li>
										{/each}
									</ul>
								{:else if linkQuery.trim()}
									<p class="hint">No file by that name — try the artist, or a word from the title.</p>
								{/if}
							</div>
						{/if}
					</div>
				{/each}
				<div class="actions">
					<button type="button" class="remove" onclick={onremove}>Take off the shelf</button>
				</div>
			{/if}
		</div>
	{/if}
</article>

<style>
	.record {
		background: var(--surface-2);
		border: 1px solid var(--border-subtle);
		border-radius: var(--radius-md);
		overflow: hidden;
		display: flex;
		flex-direction: column;
	}
	/* An open record stops being a tile and becomes a row: a 168px column can't
	   hold a tracklist, and squeezing one in wrapped every title to a word a line. */
	.record.open {
		border-color: var(--accent);
		grid-column: 1 / -1;
	}
	.record.open .face { flex-direction: row; align-items: stretch; }
	.record.open .sleeve { width: 132px; }
	.record.open .meta { justify-content: center; padding: var(--space-lg); }
	.record.open .title { font-size: var(--text-lg); }

	.face {
		display: flex;
		flex-direction: column;
		gap: 0;
		background: none;
		border: 0;
		padding: 0;
		text-align: left;
		color: inherit;
		font: inherit;
		cursor: pointer;
	}
	.face:hover { background: var(--surface-hover); }
	.face:focus-visible { outline: 2px solid var(--accent); outline-offset: -2px; }

	/* An aspect-ratio box is a flex item here, so it must be told not to shrink —
	   otherwise the column's height wins and the sleeve flattens to a strip. */
	.sleeve {
		flex: none;
		width: 100%;
		aspect-ratio: 1 / 1;
		background: var(--surface-3);
		display: block;
		position: relative;
		overflow: hidden;
	}
	.sleeve img { width: 100%; height: 100%; object-fit: cover; display: block; }
	.no-art {
		position: absolute;
		inset: 0;
		display: grid;
		place-items: center;
		color: var(--text-4);
	}

	.meta {
		flex: none;
		display: flex;
		flex-direction: column;
		gap: 2px;
		padding: var(--space-md) var(--space-lg) var(--space-lg);
		min-width: 0;
	}
	.title {
		font-size: var(--text-md);
		font-weight: var(--font-weight-semibold);
		line-height: 1.25;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	.artist {
		font-size: var(--text-sm);
		color: var(--text-2);
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	.cat {
		font-size: var(--text-xs);
		color: var(--text-4);
		font-variant-numeric: tabular-nums;
		margin-top: 2px;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	.tags { display: flex; flex-wrap: wrap; gap: var(--space-xs); margin-top: var(--space-md); }
	.tag {
		font-size: var(--text-2xs);
		padding: 2px 6px;
		border-radius: var(--radius-xs);
		border: 1px solid var(--border-default);
		color: var(--text-3);
		white-space: nowrap;
	}
	.tag.ready { border-color: var(--accent); color: var(--accent-text); }
	.tag.short { border-style: dashed; }
	/* The one new badge: filled when every track is also a file, dashed when some are. */
	.tag.digital {
		display: inline-flex;
		align-items: center;
		gap: 4px;
		background: var(--teal-950);
		border-color: var(--accent);
		color: var(--accent-text);
	}
	.tag.digital.partial { background: none; border-style: dashed; }
	.twin-dot { width: 6px; height: 6px; border-radius: 50%; background: currentColor; }
	.tag.digital.partial .twin-dot { background: none; border: 1px solid currentColor; }

	/* Sides flow into as many columns as fit — a 2xLP is 21 of them, and one
	   long list would push the next record off the screen. */
	.sides {
		border-top: 1px solid var(--border-subtle);
		padding: var(--space-md) var(--space-sm);
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(310px, 1fr));
		gap: 0 var(--space-lg);
		align-items: start;
	}
	.loading, .err, .actions, .play-bar { grid-column: 1 / -1; }

	.play-bar {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: var(--space-md);
		padding: var(--space-xs) var(--space-md) var(--space-md);
	}
	.play-all {
		display: inline-flex;
		align-items: center;
		gap: var(--space-sm);
		background: var(--accent);
		color: var(--accent-contrast);
		border: 0;
		border-radius: var(--radius-sm);
		padding: var(--space-xs) var(--space-lg);
		font: inherit;
		font-size: var(--text-sm);
		font-weight: var(--font-weight-semibold);
		cursor: pointer;
	}
	.play-all:hover { background: var(--accent-hover); }
	.play-all:focus-visible { outline: 2px solid var(--accent-text); outline-offset: 2px; }
	.hint { margin: 0; font-size: var(--text-xs); color: var(--text-3); }

	.side-cell { min-width: 0; }
	.loading, .err { margin: 0; padding: var(--space-md) var(--space-lg); font-size: var(--text-sm); color: var(--text-3); }
	.err { color: var(--zone-drive); }

	.side {
		display: grid;
		grid-template-columns: 1.7rem 2.2rem minmax(0, 1fr) 4.8rem 2.8rem;
		gap: var(--space-md);
		align-items: center;
		padding: var(--space-sm) var(--space-md);
		border-radius: var(--radius-sm);
	}
	.side:hover { background: var(--surface-3); }
	.pos { font-size: var(--text-xs); color: var(--text-3); font-variant-numeric: tabular-nums; }
	.name {
		font-size: var(--text-sm);
		min-width: 0;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	/* Wraps rather than clips: every source line now carries an action (Link,
	   Not it, unlink), and an ellipsis would swallow exactly that. */
	.src {
		display: block;
		font-size: var(--text-2xs);
		font-style: normal;
		color: var(--text-4);
		margin-top: 1px;
		white-space: normal;
		overflow-wrap: anywhere;
	}
	.src.warn { color: var(--zone-drive); }
	.src.twin { color: var(--accent-text); }
	/* A guess is the DJ's call, so it reads differently from anything settled. */
	.src.ask { color: var(--text-2); }
	.side.suggested {
		outline: 1px dashed var(--border-default);
		outline-offset: -1px;
	}

	.twin-play {
		width: 1.6rem;
		height: 1.6rem;
		border-radius: 50%;
		border: 1px solid var(--accent);
		background: transparent;
		color: var(--accent-text);
		display: grid;
		place-items: center;
		padding: 0;
		cursor: pointer;
		font-size: var(--text-2xs);
	}
	.twin-play:hover, .twin-play.playing { background: var(--accent); color: var(--accent-contrast); }
	.twin-play:focus-visible { outline: 2px solid var(--accent-text); outline-offset: 2px; }
	.twin-play.off { border: 1px dashed var(--border-default); color: var(--text-4); cursor: default; background: none; }

	.inline {
		background: none;
		border: 0;
		padding: 0;
		margin-left: var(--space-sm);
		font: inherit;
		color: var(--text-3);
		text-decoration: underline;
		cursor: pointer;
	}
	.inline:hover { color: var(--text-1); }
	.inline.yes { color: var(--accent-text); font-weight: var(--font-weight-semibold); }
	.inline:focus-visible { outline: 2px solid var(--accent); outline-offset: 1px; }

	.link-search {
		margin: 0 var(--space-md) var(--space-md) calc(1.7rem + 2.2rem + 2 * var(--space-md));
		display: flex;
		flex-direction: column;
		gap: var(--space-xs);
	}
	.link-search input {
		background: var(--surface-3);
		border: 1px solid var(--border-default);
		border-radius: var(--radius-sm);
		color: var(--text-1);
		padding: var(--space-xs) var(--space-md);
		font: inherit;
		font-size: var(--text-sm);
	}
	.link-search input:focus-visible { outline: 2px solid var(--accent); outline-offset: -1px; }
	.link-search ul { list-style: none; margin: 0; padding: 0; }
	.link-search li button {
		display: flex;
		flex-direction: column;
		width: 100%;
		text-align: left;
		background: none;
		border: 0;
		border-radius: var(--radius-sm);
		padding: var(--space-xs) var(--space-md);
		font: inherit;
		color: inherit;
		cursor: pointer;
	}
	.link-search li button:hover, .link-search li button:focus-visible { background: var(--surface-hover); outline: none; }
	.hit-title { font-size: var(--text-sm); }
	.hit-meta { font-size: var(--text-2xs); color: var(--text-4); }

	.bpm {
		width: 100%;
		text-align: right;
		font-variant-numeric: tabular-nums;
		background: var(--surface-3);
		border: 1px solid var(--border-default);
		border-radius: var(--radius-sm);
		color: var(--text-1);
		padding: var(--space-xs) var(--space-sm);
		font: inherit;
		font-size: var(--text-sm);
	}
	.bpm:focus-visible { outline: 2px solid var(--accent); outline-offset: -1px; }
	.key { font-size: var(--text-xs); text-align: right; font-variant-numeric: tabular-nums; }

	.actions { padding: var(--space-lg) var(--space-md) var(--space-xs); }
	.remove {
		background: none;
		border: 0;
		padding: 0;
		font: inherit;
		font-size: var(--text-xs);
		color: var(--text-4);
		text-decoration: underline;
		cursor: pointer;
	}
	.remove:hover { color: var(--zone-drive); }
</style>
