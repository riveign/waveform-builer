<script lang="ts">
	import Button from '../primitives/Button.svelte';

	let {
		page,
		pageCount,
		total,
		pageSize,
		offset,
		onpage,
		onpagesize,
	}: {
		/** 1-based current page. */
		page: number;
		pageCount: number;
		total: number;
		pageSize: number;
		/** Index of the first track on this page, for the "showing" line. */
		offset: number;
		onpage: (page: number) => void;
		onpagesize: (size: number) => void;
	} = $props();

	const PAGE_SIZES = [25, 50, 100, 200];

	/** First and last page always show; the rest is a window around where you are,
	 *  with gaps marked so 87 pages don't become 87 buttons. */
	let steps = $derived.by((): (number | 'gap')[] => {
		if (pageCount <= 7) return Array.from({ length: pageCount }, (_, i) => i + 1);
		const near = new Set([1, pageCount, page, page - 1, page + 1]);
		if (page <= 3) [2, 3, 4].forEach((n) => near.add(n));
		if (page >= pageCount - 2) [pageCount - 3, pageCount - 2, pageCount - 1].forEach((n) => near.add(n));
		const shown = [...near].filter((n) => n >= 1 && n <= pageCount).sort((a, b) => a - b);
		const out: (number | 'gap')[] = [];
		let prev = 0;
		for (const n of shown) {
			if (prev && n - prev > 1) out.push('gap');
			out.push(n);
			prev = n;
		}
		return out;
	});

	/** Only rendered alongside a non-empty list, so there is always a first track. */
	let firstShown = $derived(offset + 1);
	let lastShown = $derived(Math.min(offset + pageSize, total));
	const fmt = (n: number) => n.toLocaleString();
</script>

<nav class="pagination" aria-label="Track pages">
	<span class="showing">{fmt(firstShown)}–{fmt(lastShown)} of {fmt(total)}</span>

	{#if pageCount > 1}
		<div class="pages">
			<Button
				size="sm"
				variant="ghost"
				disabled={page <= 1}
				onclick={() => onpage(page - 1)}
				ariaLabel="Previous page"
			>
				‹ Back
			</Button>

			{#each steps as step, i (typeof step === 'number' ? step : `gap-${i}`)}
				{#if step === 'gap'}
					<span class="gap" aria-hidden="true">…</span>
				{:else}
					<Button
						size="sm"
						variant="ghost"
						pressed={step === page}
						onclick={() => onpage(step)}
						ariaLabel="Page {step}{step === page ? ', current page' : ''}"
					>
						{step}
					</Button>
				{/if}
			{/each}

			<Button
				size="sm"
				variant="ghost"
				disabled={page >= pageCount}
				onclick={() => onpage(page + 1)}
				ariaLabel="Next page"
			>
				Next ›
			</Button>
		</div>
	{/if}

	<label class="per-page">
		<span class="per-page-label">Per page</span>
		<select
			class="per-page-select"
			value={pageSize}
			onchange={(e) => onpagesize(Number(e.currentTarget.value))}
		>
			{#each PAGE_SIZES as size}
				<option value={size}>{size}</option>
			{/each}
		</select>
	</label>
</nav>

<style>
	.pagination {
		display: flex;
		align-items: center;
		gap: var(--space-md);
		padding: var(--space-sm) var(--space-lg);
		border-top: 1px solid var(--border);
		background: var(--bg-secondary);
		font-size: var(--text-xs);
		color: var(--text-dim);
		/* Many pages outgrow a narrow sidebar — scroll rather than wrap the band
		   onto a second line and break the list's bottom edge. */
		overflow-x: auto;
		scrollbar-width: none;
	}

	.pagination::-webkit-scrollbar {
		display: none;
	}

	.showing {
		flex-shrink: 0;
		white-space: nowrap;
	}

	.pages {
		display: flex;
		align-items: center;
		gap: 2px;
		margin-inline: auto;
	}

	.pages > :global(*) {
		flex-shrink: 0;
	}

	.gap {
		padding: 0 var(--space-2xs);
		color: var(--text-dim);
	}

	.per-page {
		display: flex;
		align-items: center;
		gap: var(--space-xs);
		flex-shrink: 0;
	}

	.per-page-label {
		white-space: nowrap;
	}

	.per-page-select {
		padding: 2px var(--space-xs);
		font-size: var(--text-xs);
		background: var(--bg-tertiary);
		border: 1px solid var(--border);
		border-radius: 4px;
		color: var(--text-primary);
	}

	.per-page-select:focus {
		outline: none;
		border-color: var(--accent);
	}
</style>
