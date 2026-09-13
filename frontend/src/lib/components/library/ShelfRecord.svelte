<script lang="ts">
	import { getRelease, patchSide, apiMessage, type VinylReleaseSummary, type VinylSide } from '$lib/api/vinyl';
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

	const catalogue = $derived(
		[release.label, release.catalog_number, release.year].filter(Boolean).join(' · '),
	);
	const complete = $derived(release.sides > 0 && release.plannable === release.sides);
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

	/** What a number is worth knowing about: where it came from. */
	function sourceLabel(s: VinylSide): string {
		if (!s.bpm) return 'no BPM yet — the builder can’t reach this side';
		if (s.bpm_source === 'manual') return 'you set this';
		if (s.bpm_source === 'library') return 'from your own file';
		if (s.bpm_source === 'preview') return 'estimated from a 30s preview';
		return s.bpm_source ?? '';
	}
</script>

<article class="record" class:open>
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
			</span>
		</span>
	</button>

	{#if open}
		<div class="sides">
			{#if error}<p class="err" role="alert">{error}</p>{/if}
			{#if loading}
				<p class="loading">Reading the sides…</p>
			{:else}
				{#each sides as s (s.track_id)}
					<div class="side">
						<span class="pos">{s.position ?? '—'}</span>
						<span class="name">
							{s.title ?? '—'}
							<em class="src" class:warn={!s.bpm}>{sourceLabel(s)}</em>
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
	.loading, .err, .actions { grid-column: 1 / -1; }
	.loading, .err { margin: 0; padding: var(--space-md) var(--space-lg); font-size: var(--text-sm); color: var(--text-3); }
	.err { color: var(--zone-drive); }

	.side {
		display: grid;
		grid-template-columns: 2.4rem minmax(0, 1fr) 4.8rem 2.8rem;
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
	.src {
		display: block;
		font-size: var(--text-2xs);
		font-style: normal;
		color: var(--text-4);
		margin-top: 1px;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	.src.warn { color: var(--zone-drive); }

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
