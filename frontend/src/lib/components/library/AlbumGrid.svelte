<script lang="ts">
	import { onMount } from 'svelte';
	import { listAlbums, getAlbumCoverUrl, type Album } from '$lib/api/albums';
	import Button from '../primitives/Button.svelte';
	import SegmentedControl, { type SegmentOption } from '../primitives/SegmentedControl.svelte';

	let { onselect }: { onselect: (album: Album) => void } = $props();

	type SortMode = 'artist' | 'year' | 'recent';

	const SORT_OPTIONS: SegmentOption<SortMode>[] = [
		{ value: 'artist', label: 'Artist' },
		{ value: 'year', label: 'Year' },
		{ value: 'recent', label: 'Recent' },
	];

	let albums = $state<Album[]>([]);
	let total = $state(0);
	let loading = $state(false);
	let error = $state<string | null>(null);
	let search = $state('');
	let sort = $state<SortMode>('artist');
	let offset = $state(0);
	const PAGE_LIMIT = 60;
	const GROUPED_LIMIT = 5000; // load everything for grouped views

	let scrollEl: HTMLDivElement | undefined = $state();
	let debounceTimer: ReturnType<typeof setTimeout> | null = null;

	let grouped = $derived(sort !== 'recent');

	function sectionLabelFor(album: Album, mode: SortMode): string {
		if (mode === 'year') {
			return album.year ? String(album.year) : '?';
		}
		const name = (album.artist ?? '').trim();
		if (!name) return '#';
		const ch = name[0].toUpperCase();
		if (ch >= 'A' && ch <= 'Z') return ch;
		return '#';
	}

	// Sections preserve first-seen order in `albums` (backend already sorted),
	// but collapse all non-contiguous runs of the same label into one bucket —
	// otherwise non-ASCII artists like "ÅMRTÜM" sort after Z and create a second
	// '#' section, violating the keyed {#each}.
	let sections = $derived.by(() => {
		if (!grouped) return [];
		const buckets = new Map<string, Album[]>();
		for (const a of albums) {
			const label = sectionLabelFor(a, sort);
			const existing = buckets.get(label);
			if (existing) existing.push(a);
			else buckets.set(label, [a]);
		}
		return Array.from(buckets, ([label, albums]) => ({ label, albums }));
	});

	async function load(reset = true) {
		loading = true;
		error = null;
		try {
			if (reset) offset = 0;
			const res = await listAlbums({
				search: search || undefined,
				sort,
				limit: grouped ? GROUPED_LIMIT : PAGE_LIMIT,
				offset: grouped ? 0 : offset,
			});
			albums = reset ? res.items : [...albums, ...res.items];
			total = res.total;
		} catch (e) {
			error = e instanceof Error ? e.message : 'Could not load albums';
		} finally {
			loading = false;
		}
	}

	function onSearchInput(value: string) {
		search = value;
		if (debounceTimer) clearTimeout(debounceTimer);
		debounceTimer = setTimeout(() => load(true), 250);
	}

	function changeSort(next: SortMode) {
		sort = next;
		load(true);
	}

	function loadMore() {
		offset += PAGE_LIMIT;
		load(false);
	}

	function jumpTo(label: string) {
		if (!scrollEl) return;
		const header = scrollEl.querySelector<HTMLElement>(`[data-section="${cssEscape(label)}"]`);
		// Measure the non-sticky section wrapper, not the sticky header — a stuck
		// header reports the bottom of its section, which would overshoot.
		const section = header?.closest<HTMLElement>('.album-section');
		if (!section) return;
		const delta = section.getBoundingClientRect().top - scrollEl.getBoundingClientRect().top;
		scrollEl.scrollTo({ top: scrollEl.scrollTop + delta, behavior: 'smooth' });
	}

	function cssEscape(s: string): string {
		return s.replace(/"/g, '\\"');
	}

	onMount(() => load(true));
</script>

<div class="album-grid-wrap">
	<div class="controls">
		<input
			class="search"
			type="text"
			placeholder="Search albums..."
			value={search}
			oninput={(e) => onSearchInput((e.currentTarget as HTMLInputElement).value)}
		/>
		<SegmentedControl
			options={SORT_OPTIONS}
			value={sort}
			onchange={changeSort}
			ariaLabel="Sort albums"
		/>
	</div>

	{#if loading && albums.length === 0}
		<div class="status">Reading your library...</div>
	{:else if error}
		<div class="status error">{error}</div>
	{:else if albums.length === 0}
		<div class="status">No albums yet — sync your library to see them here.</div>
	{:else}
		<div class="meta">{albums.length} of {total} albums</div>
		<div class="body">
			<div class="scroll" bind:this={scrollEl}>
				{#if grouped}
					{#each sections as section (section.label)}
						<section class="album-section">
							<div class="section-header" data-section={section.label}>
								<span class="section-label">{section.label}</span>
								<span class="section-count">{section.albums.length}</span>
							</div>
							<div class="grid grid-12 grid-12--content">
								{#each section.albums as album (album.album_key)}
									<button class="card" onclick={() => onselect(album)}>
										<div class="cover">
											<img
												src={getAlbumCoverUrl(album.album_key)}
												alt=""
												loading="lazy"
												onerror={(e) => ((e.currentTarget as HTMLImageElement).style.display = 'none')}
											/>
										</div>
										<div class="info">
											<div class="title" title={album.album}>{album.album}</div>
											<div class="artist" title={album.artist}>{album.artist}</div>
											<div class="meta-line">
												{#if album.year}{album.year} ·{/if}
												{album.track_count} track{album.track_count === 1 ? '' : 's'}
												{#if album.is_compilation} · compilation{/if}
											</div>
										</div>
									</button>
								{/each}
							</div>
						</section>
					{/each}
				{:else}
					<div class="grid grid-12 grid-12--content">
						{#each albums as album (album.album_key)}
							<button class="card" onclick={() => onselect(album)}>
								<div class="cover">
									<img
										src={getAlbumCoverUrl(album.album_key)}
										alt=""
										loading="lazy"
										onerror={(e) => ((e.currentTarget as HTMLImageElement).style.display = 'none')}
									/>
								</div>
								<div class="info">
									<div class="title" title={album.album}>{album.album}</div>
									<div class="artist" title={album.artist}>{album.artist}</div>
									<div class="meta-line">
										{#if album.year}{album.year} ·{/if}
										{album.track_count} track{album.track_count === 1 ? '' : 's'}
										{#if album.is_compilation} · compilation{/if}
									</div>
								</div>
							</button>
						{/each}
					</div>
					{#if albums.length < total}
						<div class="load-more">
							<Button variant="secondary" size="sm" loading={loading} onclick={loadMore}>
								{loading ? 'Listening...' : `Load ${Math.min(PAGE_LIMIT, total - albums.length)} more`}
							</Button>
						</div>
					{/if}
				{/if}
			</div>

			{#if grouped && sections.length > 1}
				<nav
					class="rail"
					aria-label="Jump to section"
					onwheel={(e) => {
						if (scrollEl) {
							scrollEl.scrollTop += e.deltaY;
							e.preventDefault();
						}
					}}
				>
					{#each sections as section (section.label)}
						<button
							class="rail-item"
							onclick={() => jumpTo(section.label)}
							title={`Jump to ${section.label}`}
						>{section.label}</button>
					{/each}
				</nav>
			{/if}
		</div>
	{/if}
</div>

<style>
	.album-grid-wrap {
		display: flex;
		flex-direction: column;
		flex: 1 1 auto;
		min-height: 0;
	}

	.controls {
		display: flex;
		gap: 8px;
		padding: 10px;
		border-bottom: 1px solid var(--border);
		align-items: center;
		flex-wrap: wrap;
		flex-shrink: 0;
		background: var(--surface-1);
	}
	.search {
		flex: 1 1 auto;
		min-width: 200px;
		background: var(--surface-3);
		border: 1px solid var(--border);
		border-radius: var(--radius-md);
		color: var(--text-primary);
		padding: var(--space-sm) var(--space-md);
		font-size: var(--text-base);
	}
	.search:focus { outline: none; border-color: var(--accent); }

	.meta {
		padding: 6px 10px;
		font-size: 11px;
		color: var(--text-dim);
	}

	.body {
		display: flex;
		flex: 1 1 auto;
		min-height: 0;
		overflow: hidden;
	}
	.scroll {
		flex: 1 1 auto;
		overflow-y: auto;
		padding-bottom: 16px;
		position: relative; /* containing block for the sticky section headers */
		container-type: inline-size; /* query container for the album card grid reflow */
	}

	/* Per-section wrapper: each header's containing block, so sticky headers
	   un-stick at their section boundary instead of stacking at the top. */
	.album-section {
		display: block;
	}

	.section-header {
		position: sticky;
		top: 0;
		z-index: 2;
		display: flex;
		align-items: baseline;
		gap: 8px;
		padding: 6px 14px;
		background: var(--surface-1);
		border-bottom: 1px solid var(--border);
		font-size: 13px;
		font-weight: 700;
		color: var(--text-primary);
	}
	.section-label {
		letter-spacing: 0.02em;
	}
	.section-count {
		font-size: 11px;
		color: var(--text-dim);
		font-weight: 400;
	}

	/* 12-col content grid: equal column-multiple album cards. Smaller art → span 3
	   (4-up) at full width, reflowing to 3-up then 2-up via container queries. */
	.grid {
		padding: 10px 12px 18px;
	}
	.grid > .card {
		grid-column: span 3; /* 4-up at full content width */
	}

	@container (max-width: 720px) {
		.grid > .card {
			grid-column: span 4; /* 3-up */
		}
	}

	@container (max-width: 520px) {
		.grid > .card {
			grid-column: span 6; /* 2-up */
		}
	}
	.card {
		appearance: none;
		background: transparent;
		border: none;
		padding: 0;
		text-align: left;
		cursor: pointer;
		display: flex;
		flex-direction: column;
		gap: 8px;
	}
	.card:hover .title { color: var(--accent); }

	.cover {
		width: 100%;
		aspect-ratio: 1 / 1;
		background: var(--surface-2);
		border-radius: var(--radius-md);
		overflow: hidden;
		box-shadow: 0 2px 8px rgba(0, 0, 0, 0.4);
		display: flex;
		align-items: center;
		justify-content: center;
		font-size: 48px;
		color: var(--text-dim);
		position: relative;
	}
	.cover::before {
		content: '♪';
		position: absolute;
		inset: 0;
		display: flex;
		align-items: center;
		justify-content: center;
		font-size: 48px;
		color: var(--text-dim);
	}
	.cover img {
		position: relative;
		z-index: 1;
		width: 100%;
		height: 100%;
		object-fit: cover;
		display: block;
	}
	.info {
		display: flex;
		flex-direction: column;
		gap: 2px;
		min-width: 0;
	}
	.title {
		font-size: 13px;
		font-weight: 600;
		color: var(--text-primary);
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
		transition: color 0.15s;
	}
	.artist {
		font-size: 12px;
		color: var(--text-secondary);
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}
	.meta-line {
		font-size: 11px;
		color: var(--text-dim);
	}

	.load-more {
		display: flex;
		justify-content: center;
		padding: var(--space-lg);
	}

	.status {
		padding: 20px;
		text-align: center;
		color: var(--text-secondary);
		font-size: 13px;
	}
	.status.error {
		color: var(--energy-high);
	}

	.rail {
		flex: 0 0 auto;
		display: flex;
		flex-direction: column;
		align-items: stretch;
		gap: 1px;
		padding: 8px 4px;
		border-left: 1px solid var(--border);
		background: var(--bg-secondary, transparent);
	}
	.rail-item {
		appearance: none;
		background: transparent;
		border: none;
		color: var(--text-secondary);
		font-size: 10px;
		font-weight: 600;
		font-variant-numeric: tabular-nums;
		padding: 2px 8px;
		cursor: pointer;
		border-radius: 4px;
		min-width: 28px;
		text-align: center;
	}
	.rail-item:hover {
		color: var(--accent);
		background: var(--surface-hover);
	}
</style>
