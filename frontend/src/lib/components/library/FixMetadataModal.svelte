<script lang="ts">
	import type { Track } from '$lib/types';
	import {
		listMetadataSources,
		matchAlbumSource,
		applyAlbumCorrection,
		type SourceInfo,
		type CorrectionPreview,
	} from '$lib/api/albums';
	import Button from '$lib/components/primitives/Button.svelte';

	let {
		open = $bindable(false),
		albumKey,
		albumName,
		onapply,
	}: {
		open: boolean;
		albumKey: string;
		albumName: string;
		onapply: () => void;
	} = $props();

	const FIELD_LABELS: Record<string, string> = {
		title: 'Title',
		artist: 'Artist',
		album: 'Album',
		label: 'Label',
		release_year: 'Year',
		track_number: 'Track #',
		disc_number: 'Disc #',
	};

	let dialogEl: HTMLDialogElement | undefined = $state();
	let stage = $state<'source' | 'checking' | 'review' | 'applying' | 'done' | 'error'>('source');
	let error = $state('');
	let sources = $state<SourceInfo[]>([]);
	let chosen = $state<string>('');
	let url = $state('');
	let query = $state('');
	let preview = $state<CorrectionPreview | null>(null);
	let checked = $state<Record<string, boolean>>({});
	let appliedCount = $state(0);

	const chosenSource = $derived(sources.find((s) => s.name === chosen));
	const lookupMode = $derived(chosenSource?.lookup_mode ?? 'search');

	// Fields that actually change somewhere in the preview, in canonical order.
	const changedFields = $derived.by(() => {
		if (!preview) return [] as string[];
		const order = Object.keys(FIELD_LABELS);
		const present = new Set<string>();
		for (const it of preview.items)
			for (const ch of it.changes) if (ch.changed) present.add(ch.field);
		return order.filter((f) => present.has(f));
	});

	const tracksWithChanges = $derived(
		preview ? preview.items.filter((it) => it.changes.some((c) => c.changed)) : [],
	);

	$effect(() => {
		if (open && dialogEl) {
			dialogEl.showModal();
			void loadSources();
		} else if (!open && dialogEl?.open) {
			dialogEl.close();
		}
	});

	async function loadSources() {
		stage = 'source';
		error = '';
		preview = null;
		url = '';
		query = albumName;
		try {
			const res = await listMetadataSources();
			sources = res.sources;
			chosen = sources.find((s) => s.available)?.name ?? sources[0]?.name ?? '';
		} catch (e) {
			error = e instanceof Error ? e.message : "Couldn't load sources";
			stage = 'error';
		}
	}

	async function check() {
		if (!chosen) return;
		stage = 'checking';
		error = '';
		try {
			preview = await matchAlbumSource(albumKey, chosen, {
				url: lookupMode === 'url' ? url : undefined,
				query: lookupMode === 'search' ? query : undefined,
			});
			if (!preview || preview.track_count === 0 || tracksWithChanges.length === 0) {
				stage = 'review'; // review screen shows the empty/no-change state warmly
			} else {
				checked = Object.fromEntries(changedFields.map((f) => [f, true]));
				stage = 'review';
			}
		} catch (e) {
			error = e instanceof Error ? e.message : "That source couldn't find this release";
			stage = 'error';
		}
	}

	function confidenceClass(c: number): string {
		if (c >= 0.85) return 'green';
		if (c >= 0.7) return 'yellow';
		return 'red';
	}

	function changeFor(item: CorrectionPreview['items'][number], field: string) {
		return item.changes.find((c) => c.field === field && c.changed) ?? null;
	}

	async function apply() {
		if (!preview) return;
		const fields = changedFields.filter((f) => checked[f]);
		if (fields.length === 0) return;
		stage = 'applying';
		try {
			const items = preview.items
				.map((it) => {
					const values: Record<string, string | number | null> = {};
					for (const ch of it.changes)
						if (ch.changed && checked[ch.field]) values[ch.field] = ch.new;
					return { track_id: it.track_id, values };
				})
				.filter((it) => Object.keys(it.values).length > 0);
			const res = await applyAlbumCorrection(albumKey, {
				source: preview.source,
				source_ref: preview.source_ref,
				fields,
				items,
			});
			appliedCount = res.updated_count;
			stage = 'done';
			onapply();
		} catch (e) {
			error = e instanceof Error ? e.message : 'Apply failed';
			stage = 'error';
		}
	}

	function close() {
		open = false;
		stage = 'source';
		error = '';
		preview = null;
	}
</script>

<dialog bind:this={dialogEl} onclose={() => (open = false)} onkeydown={(e) => e.key === 'Escape' && close()}>
	<div class="dialog-content">
		<header>
			<h2>Check &amp; fix metadata</h2>
			<Button variant="ghost" size="sm" iconOnly ariaLabel="Close" onclick={close}>
				{#snippet icon()}×{/snippet}
			</Button>
		</header>

		{#if stage === 'source'}
			<p class="prompt">Where should we check <strong>{albumName}</strong> against?</p>
			<div class="sources">
				{#each sources as s (s.name)}
					<label class="source-opt" class:disabled={!s.available}>
						<input
							type="radio"
							name="source"
							value={s.name}
							checked={chosen === s.name}
							disabled={!s.available}
							onchange={() => (chosen = s.name)}
						/>
						<span class="source-name">{s.name}</span>
						{#if !s.available}
							<span class="source-hint">needs setup</span>
						{:else}
							<span class="source-hint">{s.lookup_mode === 'url' ? 'paste a URL' : s.lookup_mode === 'files' ? 'read the files' : 'search'}</span>
						{/if}
					</label>
				{/each}
			</div>

			{#if lookupMode === 'url'}
				<input class="text-input" placeholder="https://artist.bandcamp.com/album/…" bind:value={url} />
			{:else if lookupMode === 'search'}
				<input class="text-input" placeholder="Album name to search" bind:value={query} />
			{:else}
				<p class="note">Reads the album's own files on disk — no input needed.</p>
			{/if}

			<div class="footer">
				<Button variant="secondary" size="sm" onclick={close}>Cancel</Button>
				<Button variant="primary" size="sm" onclick={check} disabled={!chosen || (lookupMode === 'url' && !url)}>
					Check
				</Button>
			</div>
		{:else if stage === 'checking'}
			<div class="status">Reading {chosen}…</div>
		{:else if stage === 'error'}
			<div class="status error">{error}</div>
			<div class="footer">
				<Button variant="secondary" size="sm" onclick={() => (stage = 'source')}>Back</Button>
				<Button variant="primary" size="sm" onclick={check}>Try again</Button>
			</div>
		{:else if stage === 'review' && preview}
			{#if tracksWithChanges.length === 0}
				<p class="prompt">Good news — your {preview.track_count} track{preview.track_count === 1 ? '' : 's'} already match {preview.source}. Nothing to fix.</p>
				<div class="footer">
					<Button variant="secondary" size="sm" onclick={() => (stage = 'source')}>Back</Button>
					<Button variant="primary" size="sm" onclick={close}>Done</Button>
				</div>
			{:else}
				<p class="prompt">
					{preview.source} has <strong>{preview.album ?? '—'}</strong> by {preview.artist ?? '—'}{#if preview.year} ({preview.year}){/if}. Pick the fields to fix, then review.
				</p>
				<div class="field-toggles">
					{#each changedFields as f (f)}
						<label class="toggle">
							<input type="checkbox" checked={checked[f]} onchange={(e) => (checked = { ...checked, [f]: (e.currentTarget as HTMLInputElement).checked })} />
							{FIELD_LABELS[f]}
						</label>
					{/each}
				</div>
				<div class="diff">
					{#each tracksWithChanges as it (it.track_id)}
						<div class="diff-track">
							<div class="diff-head">
								<span class="diff-title" title={it.track_title ?? ''}>{it.track_title ?? '—'}</span>
								<span class="diff-conf {confidenceClass(it.confidence)}">{Math.round(it.confidence * 100)}%</span>
							</div>
							{#each changedFields as f (f)}
								{@const ch = changeFor(it, f)}
								{#if ch}
									<div class="diff-row" class:off={!checked[f]}>
										<span class="diff-field">{FIELD_LABELS[f]}</span>
										<span class="diff-old">{ch.old ?? '—'}</span>
										<span class="diff-arrow">→</span>
										<span class="diff-new">{ch.new}</span>
									</div>
								{/if}
							{/each}
						</div>
					{/each}
				</div>
				<div class="footer">
					<Button variant="secondary" size="sm" onclick={() => (stage = 'source')}>Back</Button>
					<Button variant="primary" size="sm" onclick={apply} disabled={changedFields.every((f) => !checked[f])}>
						Fix {tracksWithChanges.length} track{tracksWithChanges.length === 1 ? '' : 's'}
					</Button>
				</div>
			{/if}
		{:else if stage === 'applying'}
			<div class="status">Writing your changes…</div>
		{:else if stage === 'done'}
			<div class="status">Fixed {appliedCount} track{appliedCount === 1 ? '' : 's'}. ✓</div>
			<div class="footer">
				<Button variant="primary" size="sm" onclick={close}>Done</Button>
			</div>
		{/if}
	</div>
</dialog>

<style>
	dialog {
		border: 1px solid var(--border);
		border-radius: 10px;
		padding: 0;
		background: var(--bg-secondary);
		color: var(--text-primary);
		max-width: 640px;
		width: 92vw;
	}
	dialog::backdrop {
		background: rgba(0, 0, 0, 0.55);
	}
	.dialog-content {
		padding: 16px 18px;
	}
	header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		margin-bottom: 12px;
	}
	h2 {
		font-size: 15px;
		margin: 0;
	}
	.prompt {
		font-size: 13px;
		color: var(--text-secondary);
		margin: 0 0 12px;
	}
	.note {
		font-size: 12px;
		color: var(--text-tertiary);
		margin: 8px 0;
	}
	.sources {
		display: flex;
		flex-wrap: wrap;
		gap: 8px;
		margin-bottom: 12px;
	}
	.source-opt {
		display: inline-flex;
		align-items: center;
		gap: 6px;
		padding: 6px 10px;
		border: 1px solid var(--border);
		border-radius: 8px;
		cursor: pointer;
		font-size: 13px;
		text-transform: capitalize;
	}
	.source-opt.disabled {
		opacity: 0.45;
		cursor: not-allowed;
	}
	.source-hint {
		font-size: 11px;
		color: var(--text-tertiary);
		text-transform: none;
	}
	.text-input {
		width: 100%;
		box-sizing: border-box;
		padding: 8px 10px;
		border: 1px solid var(--border);
		border-radius: 8px;
		background: var(--bg-primary);
		color: inherit;
		font-size: 13px;
		margin-bottom: 12px;
	}
	.field-toggles {
		display: flex;
		flex-wrap: wrap;
		gap: 10px;
		margin-bottom: 12px;
	}
	.toggle {
		display: inline-flex;
		align-items: center;
		gap: 5px;
		font-size: 12px;
		cursor: pointer;
	}
	.diff {
		max-height: 46vh;
		overflow-y: auto;
		display: flex;
		flex-direction: column;
		gap: 10px;
	}
	.diff-track {
		border: 1px solid var(--border);
		border-radius: 8px;
		padding: 8px 10px;
	}
	.diff-head {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 6px;
	}
	.diff-title {
		font-size: 13px;
		font-weight: 600;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	.diff-conf {
		font-size: 11px;
		font-variant-numeric: tabular-nums;
	}
	.diff-conf.green {
		color: var(--score-excellent);
	}
	.diff-conf.yellow {
		color: var(--score-fair);
	}
	.diff-conf.red {
		color: var(--score-poor);
	}
	.diff-row {
		display: grid;
		grid-template-columns: 64px 1fr auto 1fr;
		gap: 8px;
		align-items: center;
		font-size: 12px;
		padding: 2px 0;
	}
	.diff-row.off {
		opacity: 0.35;
		text-decoration: line-through;
	}
	.diff-field {
		color: var(--text-tertiary);
	}
	.diff-old {
		color: var(--score-poor);
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	.diff-arrow {
		color: var(--text-tertiary);
	}
	.diff-new {
		color: var(--score-excellent);
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	.status {
		padding: 18px 4px;
		font-size: 13px;
		color: var(--text-secondary);
	}
	.status.error {
		color: var(--destructive);
	}
	.footer {
		display: flex;
		justify-content: flex-end;
		gap: 8px;
		margin-top: 14px;
	}
</style>
