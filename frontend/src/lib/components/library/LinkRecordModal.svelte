<script lang="ts">
	import Modal from '../primitives/Modal.svelte';
	import Button from '../primitives/Button.svelte';
	import {
		listReleases,
		proposePairing,
		saveLinks,
		apiMessage,
		type VinylPairing,
		type VinylReleaseSummary,
	} from '$lib/api/vinyl';
	import type { Track } from '$lib/types';

	/**
	 * "This album is that record." The library's own names can be wrong, which is
	 * exactly when automatic matching can't find the pair — so the DJ says which
	 * record it is, Kiku proposes which file is which side, and the DJ confirms.
	 */
	let {
		open,
		albumTitle,
		albumArtist,
		tracks,
		onclose,
		onlinked,
	}: {
		open: boolean;
		albumTitle: string;
		albumArtist: string | null;
		/** The album's files. Vinyl rows sharing the album name are ignored. */
		tracks: Track[];
		onclose: () => void;
		onlinked: () => void;
	} = $props();

	let releases = $state<VinylReleaseSummary[]>([]);
	let record = $state<VinylReleaseSummary | null>(null);
	let pairs = $state<VinylPairing[]>([]);
	let choice = $state<Record<number, number | null>>({});
	let query = $state('');
	let busy = $state(false);
	let error = $state('');

	const files = $derived(tracks.filter((t) => t.medium !== 'vinyl'));
	const fileById = $derived(new Map(files.map((t) => [t.id, t])));

	function words(s: string | null | undefined): Set<string> {
		return new Set(
			(s ?? '')
				.normalize('NFKD')
				.replace(/[̀-ͯ]/g, '')
				.toLowerCase()
				.split(/[^0-9a-z]+/)
				.filter((w) => w.length > 1 && !['ep', 'lp', 'the', 'vol'].includes(w)),
		);
	}

	/** Records that share words with the album float up; the rest stay reachable by search. */
	const ranked = $derived.by(() => {
		const want = words(`${albumTitle} ${albumArtist ?? ''}`);
		const q = query.trim().toLowerCase();
		return releases
			.filter((r) =>
				!q ||
				[r.title, r.artist, r.label, r.catalog_number].filter(Boolean).join(' ').toLowerCase().includes(q),
			)
			.map((r) => {
				let shared = 0;
				for (const w of words(`${r.title} ${r.artist ?? ''}`)) if (want.has(w)) shared++;
				return { r, shared };
			})
			.sort((a, b) => b.shared - a.shared || (a.r.title ?? '').localeCompare(b.r.title ?? ''))
			.map((x) => x.r);
	});

	const counts = $derived.by(() => {
		const c = new Map<number, number>();
		for (const id of Object.values(choice)) if (id) c.set(id, (c.get(id) ?? 0) + 1);
		return c;
	});
	const doubled = $derived([...counts.values()].some((n) => n > 1));
	const toLink = $derived(Object.values(choice).filter(Boolean).length);

	$effect(() => {
		if (open) void start();
	});

	async function start() {
		record = null;
		pairs = [];
		query = '';
		error = '';
		try {
			releases = await listReleases();
			// Already paired with a record? Go straight to it.
			const linkedTo = tracks.find((t) => t.vinyl_twin)?.vinyl_twin?.release_id;
			const existing = releases.find((r) => r.id === linkedTo);
			if (existing) await pick(existing);
		} catch (e) {
			error = apiMessage(e);
		}
	}

	async function pick(r: VinylReleaseSummary) {
		busy = true;
		error = '';
		try {
			record = r;
			pairs = await proposePairing(r.id, files.map((t) => t.id));
			choice = Object.fromEntries(pairs.map((p) => [p.vinyl_track_id, p.digital_track_id ?? null]));
		} catch (e) {
			error = apiMessage(e);
			record = null;
		} finally {
			busy = false;
		}
	}

	async function save() {
		if (!record) return;
		busy = true;
		error = '';
		try {
			await saveLinks(
				record.id,
				pairs.map((p) => ({ vinyl_track_id: p.vinyl_track_id, digital_track_id: choice[p.vinyl_track_id] ?? null })),
			);
			onlinked();
			onclose();
		} catch (e) {
			error = apiMessage(e);
		} finally {
			busy = false;
		}
	}

	function fileLabel(t: Track): string {
		const n = t.track_number ? `${String(t.track_number).padStart(2, '0')}  ` : '';
		return `${n}${t.title ?? '—'}`;
	}

	function reasonLabel(p: VinylPairing): string {
		const now = choice[p.vinyl_track_id] ?? null;
		if (now === null) return '';
		if (now !== p.digital_track_id) return 'your pick';
		if (p.reason === 'linked') return 'linked';
		if (p.reason === 'title') return 'titles agree';
		if (p.reason === 'order') return 'by order — check it';
		return '';
	}
</script>

<Modal {open} size="lg" title={record ? `${albumTitle} → ${record.title}` : 'Which record is this album?'} {onclose}>
	{#if error}<p class="err" role="alert">{error}</p>{/if}

	{#if !record}
		<p class="lede">
			Pick the record on your shelf that <b>{albumTitle}</b> is. The names don't have to agree —
			that's usually why it wasn't linked on its own.
		</p>
		<input
			id="link-record-search"
			class="search"
			type="search"
			bind:value={query}
			placeholder="Find a record — title, artist, label, cat#"
			aria-label="Find a record on your shelf"
			autocomplete="off"
		/>
		<ul class="records">
			{#each ranked as r (r.id)}
				<li>
					<button type="button" class="rec" onclick={() => pick(r)} disabled={busy}>
						<span class="sleeve">{#if r.cover_url}<img src={r.cover_url} alt="" loading="lazy" />{/if}</span>
						<span class="rec-meta">
							<span class="rec-title">{r.title ?? 'Untitled'}</span>
							<span class="rec-sub">{[r.artist, r.label, r.catalog_number, r.year].filter(Boolean).join(' · ')}</span>
						</span>
						{#if r.digital}<span class="chip">{r.digital}/{r.sides} linked</span>{/if}
					</button>
				</li>
			{:else}
				<li class="none">No record on the shelf matches “{query}”.</li>
			{/each}
		</ul>
	{:else}
		<p class="lede">
			Which file is each side? Kiku paired what it could — by title first, then by running order
			where the titles don't help. Change anything that's wrong.
		</p>
		<div class="pairs" role="table" aria-label="Sides and their files">
			{#each pairs as p (p.vinyl_track_id)}
				{@const pickedId = choice[p.vinyl_track_id] ?? null}
				<div class="pair" role="row" class:twice={pickedId !== null && (counts.get(pickedId) ?? 0) > 1}>
					<span class="pos" role="cell">{p.position ?? '—'}</span>
					<span class="side-title" role="cell">{p.title ?? '—'}</span>
					<span class="arrow" aria-hidden="true">→</span>
					<select
						id="pair-{p.vinyl_track_id}"
						role="cell"
						aria-label="File for {p.position ?? ''} {p.title ?? ''}"
						value={pickedId ?? ''}
						onchange={(e) => {
							const v = e.currentTarget.value;
							choice = { ...choice, [p.vinyl_track_id]: v ? Number(v) : null };
						}}
					>
						<option value="">— not on this album —</option>
						{#each files as f (f.id)}
							<option value={f.id}>{fileLabel(f)}</option>
						{/each}
					</select>
					<span class="why" role="cell" class:check={reasonLabel(p).startsWith('by order')}>
						{#if pickedId !== null && (counts.get(pickedId) ?? 0) > 1}used twice{:else}{reasonLabel(p)}{/if}
					</span>
				</div>
			{/each}
		</div>
		{#if pairs.length && fileById.size > pairs.length}
			<p class="note">This album has {fileById.size} files and the record {pairs.length} sides — a few files won't have a side.</p>
		{/if}
	{/if}

	{#snippet footer()}
		{#if record}
			<Button variant="ghost" size="sm" onclick={() => (record = null)} disabled={busy}>← Another record</Button>
			<Button variant="primary" size="sm" onclick={save} disabled={busy || doubled}>
				{doubled ? 'One file is on two sides' : toLink ? `Link ${toLink} ${toLink === 1 ? 'side' : 'sides'}` : 'Clear the links'}
			</Button>
		{:else}
			<Button variant="secondary" size="sm" onclick={onclose}>Cancel</Button>
		{/if}
	{/snippet}
</Modal>

<style>
	.lede { margin: 0 0 var(--space-lg); font-size: var(--text-sm); color: var(--text-2); max-width: 64ch; }
	.lede b { color: var(--text-1); font-weight: var(--font-weight-semibold); }
	.err { margin: 0 0 var(--space-md); color: var(--zone-drive); font-size: var(--text-sm); }
	.note { margin: var(--space-md) 0 0; font-size: var(--text-xs); color: var(--text-3); }

	.search {
		width: 100%;
		background: var(--surface-3);
		border: 1px solid var(--border-default);
		border-radius: var(--radius-sm);
		color: var(--text-1);
		padding: var(--space-sm) var(--space-md);
		font: inherit;
		font-size: var(--text-sm);
		margin-bottom: var(--space-md);
	}
	.search:focus-visible, select:focus-visible { outline: 2px solid var(--accent); outline-offset: -1px; }

	.records { list-style: none; margin: 0; padding: 0; max-height: 50vh; overflow-y: auto; }
	.rec {
		display: grid;
		grid-template-columns: 40px minmax(0, 1fr) auto;
		gap: var(--space-md);
		align-items: center;
		width: 100%;
		background: none;
		border: 0;
		border-radius: var(--radius-sm);
		padding: var(--space-xs) var(--space-sm);
		color: inherit;
		font: inherit;
		text-align: left;
		cursor: pointer;
	}
	.rec:hover, .rec:focus-visible { background: var(--surface-hover); outline: none; }
	.sleeve { width: 40px; height: 40px; border-radius: var(--radius-xs); background: var(--surface-3); overflow: hidden; }
	.sleeve img { width: 100%; height: 100%; object-fit: cover; display: block; }
	.rec-meta { display: flex; flex-direction: column; min-width: 0; }
	.rec-title { font-size: var(--text-sm); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
	.rec-sub { font-size: var(--text-2xs); color: var(--text-4); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
	.chip {
		font-size: var(--text-2xs);
		padding: 2px 6px;
		border-radius: var(--radius-xs);
		border: 1px dashed var(--accent);
		color: var(--accent-text);
		white-space: nowrap;
	}
	.none { padding: var(--space-lg); color: var(--text-3); font-size: var(--text-sm); }

	.pairs { display: flex; flex-direction: column; gap: 2px; max-height: 55vh; overflow-y: auto; }
	.pair {
		display: grid;
		grid-template-columns: 2.4rem minmax(0, 1fr) 1rem minmax(0, 1.2fr) 8rem;
		gap: var(--space-md);
		align-items: center;
		padding: var(--space-xs) var(--space-sm);
		border-radius: var(--radius-sm);
	}
	.pair:hover { background: var(--surface-2); }
	.pair.twice { outline: 1px dashed var(--zone-drive); outline-offset: -1px; }
	.pos { font-size: var(--text-xs); color: var(--text-3); font-variant-numeric: tabular-nums; }
	.side-title { font-size: var(--text-sm); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
	.arrow { color: var(--text-4); text-align: center; }
	select {
		min-width: 0;
		width: 100%;
		background: var(--surface-3);
		border: 1px solid var(--border-default);
		border-radius: var(--radius-sm);
		color: var(--text-1);
		padding: var(--space-xs) var(--space-sm);
		font: inherit;
		font-size: var(--text-sm);
	}
	.why { font-size: var(--text-2xs); color: var(--text-4); }
	.why.check { color: var(--zone-build); }
	.pair.twice .why { color: var(--zone-drive); }

	@media (max-width: 640px) {
		.pair { grid-template-columns: 2.4rem minmax(0, 1fr); }
		.arrow { display: none; }
		.pair select, .pair .why { grid-column: 2; }
	}
</style>
