<script lang="ts">
	import { onMount } from 'svelte';
	import { listAlbums, getAlbumCoverUrl, type Album } from '$lib/api/albums';

	let { onselect }: { onselect: (album: Album) => void } = $props();

	type SortMode = 'artist' | 'year' | 'recent';

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

	// Sections preserve the order in `albums` (backend already sorted).
	let sections = $derived.by(() => {
		if (!grouped) return [];
		const out: { label: string; albums: Album[] }[] = [];
		for (const a of albums) {
			const label = sectionLabelFor(a, sort);
			const last = out[out.length - 1];
			if (last && last.label === label) {
				last.albums.push(a);
			} else {
				out.push({ label, albums: [a] });
			}
		}
		return out;
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
		const header = scrollEl.querySelector(`[data-section="${cssEscape(label)}"]`);
		if (header) {
			(header as HTMLElement).scrollIntoView({ behavior: 'smooth', block: 'start' });
		}
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
		<div class="sort">
			<button class:active={sort === 'artist'} onclick={() => changeSort('artist')}>Artist</button>
			<button class:active={sort === 'year'} onclick={() => changeSort('year')}>Year</button>
			<button class:active={sort === 'recent'} onclick={() => changeSort('recent')}>Recent</button>
		</div>
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
						<div class="section-header" data-section={section.label}>
							<span class="section-label">{section.label}</span>
							<span class="section-count">{section.albums.length}</span>
						</div>
						<div class="grid">
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
					{/each}
				{:else}
					<div class="grid">
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
							<button onclick={loadMore} disabled={loading}>
								{loading ? 'Listening...' : `Load ${Math.min(PAGE_LIMIT, total - albums.length)} more`}
							</button>
						</div>
					{/if}
				{/if}
			</div>

			{#if grouped && sections.length > 1}
				<nav class="rail" aria-label="Jump to section">
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
	}
	.search {
		flex: 1 1 auto;
		min-width: 200px;
		background: var(--bg-secondary, #1a1a1d);
		border: 1px solid var(--border);
		border-radius: 6px;
		color: var(--text-primary);
		padding: 6px 10px;
		font-size: 13px;
	}
	.search:focus { outline: none; border-color: var(--accent); }

	.sort {
		display: flex;
		gap: 4px;
	}
	.sort button {
		background: transparent;
		color: var(--text-secondary);
		border: 1px solid var(--border);
		border-radius: 6px;
		padding: 4px 10px;
		font-size: 11px;
		cursor: pointer;
	}
	.sort button.active {
		background: var(--accent);
		color: var(--bg-primary, #000);
		border-color: var(--accent);
	}

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
	}

	.section-header {
		position: sticky;
		top: 0;
		z-index: 2;
		display: flex;
		align-items: baseline;
		gap: 8px;
		padding: 6px 14px;
		background: var(--bg-primary, #0c0c0e);
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

	.grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
		gap: 14px;
		padding: 10px 12px 18px;
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
		background: var(--bg-secondary, #1a1a1d);
		border-radius: 6px;
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
		padding: 12px;
	}
	.load-more button {
		background: transparent;
		color: var(--text-secondary);
		border: 1px solid var(--border);
		border-radius: 6px;
		padding: 6px 14px;
		font-size: 12px;
		cursor: pointer;
	}
	.load-more button:hover:not(:disabled) {
		border-color: var(--accent);
		color: var(--text-primary);
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
		overflow-y: auto;
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
		background: rgba(255, 255, 255, 0.06);
	}
</style>
