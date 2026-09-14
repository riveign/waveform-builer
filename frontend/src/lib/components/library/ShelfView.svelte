<script lang="ts">
	import { onMount, tick } from 'svelte';
	import { page } from '$app/state';
	import Spinner from '../Spinner.svelte';
	import Button from '../primitives/Button.svelte';
	import EmptyState from '../primitives/EmptyState.svelte';
	import AddRecordModal from './AddRecordModal.svelte';
	import ShelfRecord from './ShelfRecord.svelte';
	import {
		listReleases,
		removeRelease,
		apiMessage,
		type VinylReleaseSummary,
	} from '$lib/api/vinyl';

	let releases = $state<VinylReleaseSummary[]>([]);
	let loading = $state(true);
	let error = $state('');
	let adding = $state(false);
	let openId = $state<number | null>(null);
	let filter = $state('');
	/** 86 records in, the useful question stopped being "what do I own?" and
	 *  became "what can't the builder reach yet?" */
	let onlyUnfinished = $state(false);
	let onlyDigital = $state(false);

	/** The shelf's own arithmetic: a record you can't plan with is a record Kiku
	 *  can't reach, so the count that matters is sides with a BPM. */
	const sides = $derived(releases.reduce((n, r) => n + r.sides, 0));
	const plannable = $derived(releases.reduce((n, r) => n + r.plannable, 0));
	const unfinished = $derived(releases.filter((r) => r.plannable < r.sides).length);
	const withDigital = $derived(releases.filter((r) => r.digital > 0).length);

	const shown = $derived.by(() => {
		const q = filter.trim().toLowerCase();
		return releases.filter((r) => {
			if (onlyUnfinished && r.plannable >= r.sides) return false;
			if (onlyDigital && !r.digital) return false;
			if (!q) return true;
			return [r.title, r.artist, r.label, r.catalog_number, r.year]
				.filter(Boolean)
				.join(' ')
				.toLowerCase()
				.includes(q);
		});
	});

	async function load() {
		loading = true;
		error = '';
		try {
			releases = await listReleases();
		} catch (e) {
			error = apiMessage(e);
		} finally {
			loading = false;
		}
	}

	async function handleRemove(r: VinylReleaseSummary) {
		const label = [r.title, r.artist].filter(Boolean).join(' — ');
		if (!confirm(`Take ${label || 'this record'} off the shelf? Its sides go with it.`)) return;
		try {
			await removeRelease(r.id);
			if (openId === r.id) openId = null;
			await load();
		} catch (e) {
			error = apiMessage(e);
		}
	}

	/** "on vinyl · A1" in the library lands here with ?open=<record>. */
	async function openFromLink() {
		const id = Number(page.url.searchParams.get('open'));
		if (!id || !releases.some((r) => r.id === id)) return;
		filter = '';
		onlyUnfinished = false;
		onlyDigital = false;
		openId = id;
		await tick();
		document.getElementById(`record-${id}`)?.scrollIntoView({ block: 'start', behavior: 'smooth' });
	}

	onMount(async () => {
		await load();
		await openFromLink();
	});
</script>

<div class="shelf">
	<header class="bar">
		<div class="count">
			{#if !loading && releases.length}
				<b>{releases.length}</b>
				{releases.length === 1 ? 'record' : 'records'}
				<span class="dim">· {plannable} of {sides} sides ready to plan</span>
			{:else if !loading}
				<span class="dim">Nothing on the shelf yet</span>
			{/if}
		</div>
		{#if releases.length > 6}
			<input
				id="shelf-filter"
				class="filter"
				type="text"
				bind:value={filter}
				placeholder="Find a record"
				aria-label="Find a record on the shelf"
				autocomplete="off"
			/>
			{#if unfinished}
				<button
					type="button"
					class="needs"
					class:on={onlyUnfinished}
					aria-pressed={onlyUnfinished}
					onclick={() => (onlyUnfinished = !onlyUnfinished)}
				>
					{unfinished} need a BPM
				</button>
			{/if}
			{#if withDigital}
				<button
					type="button"
					class="needs"
					class:on={onlyDigital}
					aria-pressed={onlyDigital}
					onclick={() => (onlyDigital = !onlyDigital)}
					title="Records with tracks you also own as files"
				>
					{withDigital} also digital
				</button>
			{/if}
		{/if}
		<Button variant="secondary" size="sm" onclick={() => (adding = true)}>Add a record</Button>
	</header>

	{#if error}
		<p class="error" role="alert">{error}</p>
	{/if}

	{#if loading}
		<div class="status"><Spinner label="Reading the shelf..." /></div>
	{:else if !releases.length}
		<EmptyState
			title="No records yet"
			hint="Kiku knows whatever Rekordbox knows, which means whatever exists as a file. Add the records you own and the set builder can reach them too."
		>
			{#snippet action()}
				<Button variant="primary" onclick={() => (adding = true)}>Add your first record</Button>
			{/snippet}
		</EmptyState>
	{:else if !shown.length}
		<p class="none">
			{#if onlyDigital && !filter.trim()}
				None of these records are on your drive too.
			{:else if onlyUnfinished}
				Every record matching that has a BPM on every side.
			{:else}
				Nothing on the shelf matches “{filter}”.
			{/if}
		</p>
	{:else}
		<div class="scroll">
			<div class="grid">
				{#each shown as r (r.id)}
					<ShelfRecord
						release={r}
						open={openId === r.id}
						ontoggle={() => (openId = openId === r.id ? null : r.id)}
						onremove={() => handleRemove(r)}
						onchanged={load}
					/>
				{/each}
			</div>
		</div>
	{/if}
</div>

<AddRecordModal
	open={adding}
	onclose={() => (adding = false)}
	onimported={() => {
		adding = false;
		load();
	}}
/>

<style>
	.shelf {
		display: flex;
		flex-direction: column;
		flex: 1;
		min-height: 0;
		overflow: hidden;
	}

	.bar {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: var(--space-lg);
		padding: var(--space-lg) var(--space-2xl);
		border-bottom: 1px solid var(--border-subtle);
		flex: none;
	}
	.count { font-size: var(--text-sm); color: var(--text-2); margin-right: auto; }

	.filter {
		background: var(--surface-3);
		border: 1px solid var(--border-default);
		border-radius: var(--radius-sm);
		color: var(--text-1);
		padding: var(--space-xs) var(--space-md);
		font: inherit;
		font-size: var(--text-sm);
		width: 12rem;
		flex: none;
	}
	.filter:focus-visible { outline: 2px solid var(--accent); outline-offset: -1px; }

	.needs {
		background: transparent;
		border: 1px dashed var(--border-default);
		border-radius: var(--radius-sm);
		color: var(--text-3);
		font: inherit;
		font-size: var(--text-xs);
		padding: var(--space-xs) var(--space-md);
		cursor: pointer;
		flex: none;
		white-space: nowrap;
	}
	.needs:hover { color: var(--text-1); border-color: var(--border-strong); }
	.needs.on {
		border-style: solid;
		border-color: var(--accent);
		color: var(--accent-contrast);
		background: var(--accent);
	}

	.none {
		padding: var(--space-5xl) var(--space-2xl);
		text-align: center;
		color: var(--text-3);
		font-size: var(--text-sm);
	}
	.count b { color: var(--text-1); font-weight: var(--font-weight-semibold); }
	.dim { color: var(--text-4); }

	.error {
		margin: var(--space-lg) var(--space-2xl) 0;
		padding: var(--space-md) var(--space-lg);
		border-left: 2px solid var(--zone-drive);
		background: var(--surface-2);
		border-radius: var(--radius-sm);
		font-size: var(--text-sm);
		color: var(--text-2);
	}

	.status { padding: var(--space-6xl) 0; text-align: center; }

	/* The scroller and the grid are separate boxes on purpose. Making one element
	   do both put the grid's auto rows under a constrained flex height, and the
	   cards' aspect-ratio sleeves collapsed to slivers. */
	.scroll {
		flex: 1 1 auto;
		min-height: 0;
		overflow-y: auto;
	}

	.grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(168px, 1fr));
		gap: var(--space-xl);
		padding: var(--space-2xl);
		align-content: start;
	}
</style>
