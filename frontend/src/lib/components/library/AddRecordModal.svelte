<script lang="ts">
	import Modal from '../primitives/Modal.svelte';
	import Button from '../primitives/Button.svelte';
	import Spinner from '../Spinner.svelte';
	import {
		searchPressings,
		previewRelease,
		importRelease,
		apiMessage,
		type VinylSearchResult,
		type VinylPreview,
	} from '$lib/api/vinyl';

	let { open = false, onclose, onimported }: {
		open?: boolean;
		onclose: () => void;
		onimported?: (summary: string) => void;
	} = $props();

	type Stage = 'find' | 'confirm';
	let stage = $state<Stage>('find');

	let query = $state('');
	let vinylOnly = $state(true);
	let results = $state<VinylSearchResult[]>([]);
	let kind = $state('empty');
	let searching = $state(false);
	let searched = $state(false);
	let error = $state('');

	let linkUrl = $state('');
	let preview = $state<VinylPreview | null>(null);
	let loadingPreview = $state(false);
	let importing = $state(false);
	/** Side position -> the number the DJ typed or accepted. */
	let edits = $state<Record<string, string>>({});

	let searchTimer: ReturnType<typeof setTimeout> | undefined;
	let searchCtl: AbortController | undefined;

	/** What Kiku thinks you typed — shown so the search never feels like a guess. */
	const KIND_LABEL: Record<string, string> = {
		catno: 'catalogue number',
		barcode: 'barcode',
		artist_title: 'artist – title',
		text: 'free text',
		url: 'a link',
		empty: '',
	};

	function reset() {
		stage = 'find';
		query = '';
		results = [];
		searched = false;
		error = '';
		linkUrl = '';
		preview = null;
		edits = {};
	}

	function close() {
		searchCtl?.abort();
		clearTimeout(searchTimer);
		reset();
		onclose();
	}

	function onQueryInput() {
		clearTimeout(searchTimer);
		error = '';
		if (!query.trim()) {
			results = [];
			searched = false;
			return;
		}
		searchTimer = setTimeout(runSearch, 350);
	}

	async function runSearch() {
		const q = query.trim();
		if (!q) return;
		searchCtl?.abort();
		searchCtl = new AbortController();
		searching = true;
		error = '';
		try {
			const res = await searchPressings(q, { vinylOnly }, searchCtl.signal);
			results = res.results;
			kind = res.kind;
			searched = true;
		} catch (e) {
			if ((e as Error).name === 'AbortError') return;
			error = apiMessage(e);
			results = [];
			searched = true;
		} finally {
			searching = false;
		}
	}

	async function choose(target: { releaseId?: string; url?: string }) {
		loadingPreview = true;
		error = '';
		stage = 'confirm';
		try {
			preview = await previewRelease(target);
			edits = {};
			for (const row of preview.rows) {
				// Everything Kiku found starts filled in. A suggestion does not —
				// it names a different track, so accepting it has to be a choice.
				if (row.position && row.bpm != null && row.bpm_source !== 'suggestion') {
					edits[row.position] = String(row.bpm);
				}
			}
		} catch (e) {
			error = apiMessage(e);
			stage = 'find';
		} finally {
			loadingPreview = false;
		}
	}

	function acceptSuggestion(position: string, bpm: number) {
		edits = { ...edits, [position]: String(bpm) };
	}

	function rejectSuggestion(position: string) {
		const next = { ...edits };
		delete next[position];
		edits = next;
		if (preview) {
			preview.rows = preview.rows.map((r) =>
				r.position === position
					? { ...r, bpm: null, bpm_source: 'none', bpm_note: 'this one’s yours' }
					: r,
			);
		}
	}

	const filledCount = $derived(
		preview ? preview.rows.filter((r) => r.position && edits[r.position]?.trim()).length : 0,
	);

	async function doImport() {
		if (!preview) return;
		importing = true;
		error = '';
		try {
			const sides = preview.rows
				.filter((r) => r.position && edits[r.position]?.trim())
				.map((r) => ({
					position: r.position as string,
					bpm: Number(edits[r.position as string]),
					key: r.key ?? null,
				}))
				.filter((s) => Number.isFinite(s.bpm) && s.bpm > 0);

			const res = await importRelease({
				release_id: preview.source === 'discogs' ? preview.source_id : undefined,
				url: preview.source === 'discogs' ? undefined : linkUrl || undefined,
				sides,
			});
			onimported?.(
				`${res.release.title ?? 'That record'} is on the shelf — ` +
					`${res.sides_written} sides, ${res.release.plannable} ready to plan.`,
			);
			close();
		} catch (e) {
			error = apiMessage(e);
		} finally {
			importing = false;
		}
	}
</script>

<Modal {open} size="lg" onclose={close} dismissible={!importing}>
	{#snippet header()}
		<div class="head">
			<h2>{stage === 'find' ? 'Add a record' : (preview?.album ?? 'That record')}</h2>
			{#if stage === 'confirm' && preview}
				<p class="head-sub">
					{preview.artist ?? '—'} · {preview.label ?? '—'}
					{preview.catalog_number ?? ''} · {preview.year ?? '—'}
				</p>
			{/if}
		</div>
	{/snippet}

	{#if error}
		<p class="error" role="alert">{error}</p>
	{/if}

	{#if stage === 'find'}
		<div class="find">
			<div class="search-row">
				<input
					id="vinyl-q"
					type="text"
					bind:value={query}
					oninput={onQueryInput}
					placeholder="Catalogue number, barcode, artist, or a track you remember"
					autocomplete="off"
				/>
				<label class="only">
					<input id="vinyl-only" type="checkbox" bind:checked={vinylOnly} onchange={runSearch} />
					Vinyl only
				</label>
			</div>
			{#if query.trim() && KIND_LABEL[kind]}
				<p class="detect">Reading that as a <b>{KIND_LABEL[kind]}</b></p>
			{:else}
				<p class="detect dim">
					Vinyl only — the digital edition of a record isn’t a record.
				</p>
			{/if}

			{#if searching}
				<div class="status"><Spinner label="Looking through Discogs..." /></div>
			{:else if results.length}
				<div class="grid">
					{#each results as r (r.id)}
						<button class="rec" type="button" onclick={() => choose({ releaseId: r.id })}>
							<span class="sleeve">
								{#if r.cover_url}
									<img src={r.cover_url} alt="" loading="lazy" />
								{:else}
									<span class="no-art">no sleeve</span>
								{/if}
							</span>
							<span class="rec-body">
								<span class="rec-title">{r.title ?? '—'}</span>
								<span class="rec-artist">{r.artist ?? '—'}</span>
								<span class="rec-meta">
									{[r.label, r.catno, r.year].filter(Boolean).join(' · ')}
								</span>
								<span class="rec-tags">
									{#if r.format}<span class="tag">{r.format}</span>{/if}
									{#if r.already_owned}<span class="tag own">already yours</span>{/if}
									{#if r.pressings > 1}<span class="tag dash">{r.pressings} pressings</span>{/if}
								</span>
							</span>
						</button>
					{/each}
				</div>
			{:else if searched}
				<div class="empty">
					<h3>Nothing on Discogs for that</h3>
					<p>
						White labels and small pressings are often missing. Paste a link from wherever
						you did find it — Kiku reads Discogs and Bandcamp releases.
					</p>
					<div class="paste">
						<input
							id="vinyl-link"
							type="text"
							bind:value={linkUrl}
							placeholder="https://…"
							autocomplete="off"
						/>
						<Button
							variant="primary"
							disabled={!linkUrl.trim()}
							onclick={() => choose({ url: linkUrl.trim() })}
						>
							Read it
						</Button>
					</div>
				</div>
			{/if}
		</div>
	{:else}
		<div class="confirm">
			{#if loadingPreview}
				<div class="status">
					<Spinner label="Reading the sides, and listening for the BPMs..." />
					<p class="hint">A second or so per side when Kiku has to listen.</p>
				</div>
			{:else if preview}
				{#if !preview.is_pressing}
					<p class="warn">
						That’s the {preview.format} edition — its tracks have no sides. Go back and pick
						the vinyl pressing.
					</p>
				{/if}
				{#if preview.already_owned}
					<p class="note">You already have this pressing — this will update it, not duplicate it.</p>
				{/if}

				<table class="sides">
					<thead>
						<tr><th>Side</th><th>Title</th><th class="right">BPM</th><th class="right">Key</th></tr>
					</thead>
					<tbody>
						{#each preview.rows as row (row.position ?? row.title)}
							<tr class:suspect={row.bpm_source === 'suggestion'}>
								<td class="pos">{row.position ?? '—'}</td>
								<td>
									<div class="t">{row.title}</div>
									{#if row.bpm_note}
										<div class="src src--{row.bpm_source}">{row.bpm_note}</div>
									{/if}
								</td>
								<td class="right">
									{#if row.bpm_source === 'suggestion' && row.position}
										<div class="suggest">
											<span class="maybe">{row.bpm}?</span>
											<button type="button" class="mini" onclick={() => acceptSuggestion(row.position as string, row.bpm as number)}>use it</button>
											<button type="button" class="mini" onclick={() => rejectSuggestion(row.position as string)}>no</button>
										</div>
									{:else if row.position}
										<input
											id="bpm-{row.position}"
											class="bpm"
											class:from-lib={row.bpm_source === 'library'}
											class:from-prev={row.bpm_source === 'preview'}
											type="text"
											inputmode="decimal"
											placeholder="—"
											bind:value={edits[row.position]}
											aria-label="BPM for {row.title}"
										/>
									{/if}
								</td>
								<td class="right key">{row.key ?? '—'}</td>
							</tr>
						{/each}
					</tbody>
				</table>

				<p class="legend">
					<span class="k lib"></span> from your files ·
					<span class="k prev"></span> estimated from a preview ·
					<span class="k sus"></span> needs a look
				</p>
			{/if}
		</div>
	{/if}

	{#snippet footer()}
		{#if stage === 'confirm'}
			<span class="foot-note">
				{#if preview}
					{filledCount} of {preview.rows.length} sides have a BPM
					{#if filledCount < preview.rows.length}
						— the rest can’t be planned until they do
					{/if}
				{/if}
			</span>
			<Button variant="ghost" onclick={() => { stage = 'find'; preview = null; }}>Back</Button>
			<Button variant="primary" disabled={importing || loadingPreview || !preview} onclick={doImport}>
				{importing ? 'Adding…' : 'Put it on the shelf'}
			</Button>
		{:else}
			<Button variant="ghost" onclick={close}>Cancel</Button>
		{/if}
	{/snippet}
</Modal>

<style>
	.head h2 { margin: 0; font-size: var(--text-lg); font-weight: var(--font-weight-semibold); }
	.head-sub { margin: var(--space-2xs) 0 0; font-size: var(--text-sm); color: var(--text-2); }

	.error, .warn {
		margin: 0 0 var(--space-lg);
		padding: var(--space-md) var(--space-lg);
		border-radius: var(--radius-md);
		background: var(--surface-3);
		border-left: 2px solid var(--zone-drive);
		font-size: var(--text-sm);
		color: var(--text-2);
	}
	.note {
		margin: 0 0 var(--space-lg);
		font-size: var(--text-sm);
		color: var(--text-3);
	}

	.search-row { display: flex; gap: var(--space-md); align-items: center; flex-wrap: wrap; }
	.search-row input[type='text'] {
		flex: 1 1 260px;
		background: var(--surface-3);
		border: 1px solid var(--border-default);
		border-radius: var(--radius-md);
		color: var(--text-1);
		padding: var(--space-md) var(--space-lg);
		font: inherit;
		font-size: var(--text-base);
	}
	.search-row input:focus-visible { outline: 2px solid var(--accent); outline-offset: -1px; }
	.only { display: flex; align-items: center; gap: var(--space-sm); font-size: var(--text-sm); color: var(--text-2); white-space: nowrap; }

	.detect { margin: var(--space-md) 0 0; font-size: var(--text-xs); color: var(--accent-text); }
	.detect.dim { color: var(--text-4); }

	.status { padding: var(--space-4xl) 0; text-align: center; }
	.hint { margin: var(--space-md) 0 0; font-size: var(--text-xs); color: var(--text-4); }

	.grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
		gap: var(--space-lg);
		margin-top: var(--space-xl);
	}
	.rec {
		display: flex; flex-direction: column;
		background: var(--surface-2);
		border: 1px solid var(--border-default);
		border-radius: var(--radius-md);
		overflow: hidden; padding: 0; text-align: left;
		color: inherit; font: inherit; cursor: pointer;
	}
	.rec:hover { background: var(--surface-hover); border-color: var(--border-strong); }
	.rec:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
	.sleeve { aspect-ratio: 1; background: var(--surface-3); position: relative; }
	.sleeve img { width: 100%; height: 100%; object-fit: cover; display: block; }
	.no-art { position: absolute; inset: 0; display: grid; place-items: center; color: var(--text-4); font-size: var(--text-xs); }
	.rec-body { display: flex; flex-direction: column; gap: 2px; padding: var(--space-md); }
	.rec-title { font-size: var(--text-base); font-weight: var(--font-weight-semibold); }
	.rec-artist { font-size: var(--text-sm); color: var(--text-2); }
	.rec-meta { font-size: var(--text-xs); color: var(--text-4); font-variant-numeric: tabular-nums; }
	.rec-tags { display: flex; flex-wrap: wrap; gap: var(--space-xs); margin-top: var(--space-sm); }
	.tag {
		font-size: var(--text-2xs); padding: 2px 6px; border-radius: var(--radius-xs);
		border: 1px solid var(--border-default); color: var(--text-3); background: var(--surface-3);
	}
	.tag.own { border-color: var(--accent); color: var(--accent-text); }
	.tag.dash { border-style: dashed; }

	.empty { margin-top: var(--space-xl); padding: var(--space-xl); border: 1px dashed var(--border-default); border-radius: var(--radius-md); }
	.empty h3 { margin: 0 0 var(--space-sm); font-size: var(--text-md); }
	.empty p { margin: 0 0 var(--space-lg); color: var(--text-3); font-size: var(--text-sm); max-width: 56ch; }
	.paste { display: flex; gap: var(--space-md); flex-wrap: wrap; }
	.paste input {
		flex: 1 1 280px; background: var(--surface-3); border: 1px solid var(--border-default);
		border-radius: var(--radius-md); color: var(--text-1);
		padding: var(--space-md) var(--space-lg); font: inherit; font-size: var(--text-base);
	}

	.sides { width: 100%; border-collapse: collapse; font-size: var(--text-base); }
	.sides th {
		text-align: left; font-size: var(--text-2xs); letter-spacing: .1em;
		text-transform: uppercase; color: var(--text-4);
		padding: var(--space-sm) var(--space-md); border-bottom: 1px solid var(--border-subtle);
		font-weight: var(--font-weight-medium);
	}
	.sides td { padding: var(--space-md); border-bottom: 1px solid var(--surface-3); vertical-align: middle; }
	.sides tr.suspect { background: var(--surface-3); }
	.right { text-align: right; }
	.pos { color: var(--text-3); font-variant-numeric: tabular-nums; width: 3.5rem; }
	.t { line-height: 1.3; }
	.src { font-size: var(--text-xs); color: var(--text-4); margin-top: 2px; }
	.src--library { color: var(--accent-text); }
	.src--suggestion { color: var(--zone-drive); }
	.key { color: var(--text-2); font-size: var(--text-sm); width: 4rem; }

	.bpm {
		width: 5.5rem; text-align: right; font-variant-numeric: tabular-nums;
		background: var(--surface-3); border: 1px solid var(--border-default);
		border-radius: var(--radius-sm); color: var(--text-1);
		padding: var(--space-sm) var(--space-md); font: inherit; font-size: var(--text-md);
	}
	.bpm:focus-visible { outline: 2px solid var(--accent); outline-offset: -1px; }
	.bpm.from-lib { border-color: var(--accent); color: var(--accent-text); }
	.bpm.from-prev { border-style: dashed; }

	.suggest { display: inline-flex; align-items: center; gap: var(--space-xs); }
	.maybe { color: var(--zone-drive); font-variant-numeric: tabular-nums; font-size: var(--text-md); }
	.mini {
		background: transparent; border: 1px solid var(--border-default); color: var(--text-2);
		border-radius: var(--radius-sm); font: inherit; font-size: var(--text-xs);
		padding: 2px 6px; cursor: pointer;
	}
	.mini:hover { background: var(--surface-hover); color: var(--text-1); }

	.legend { margin: var(--space-lg) 0 0; font-size: var(--text-xs); color: var(--text-4); }
	.k { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 3px; vertical-align: 0; }
	.k.lib { background: var(--accent); }
	.k.prev { background: var(--text-3); }
	.k.sus { background: var(--zone-drive); }

	.foot-note { margin-right: auto; font-size: var(--text-xs); color: var(--text-4); }

	@media (max-width: 560px) {
		.sides th:nth-child(4), .sides td:nth-child(4) { display: none; }
	}
</style>
