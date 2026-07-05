<script lang="ts">
	import type { TrackSetAppearance } from '$lib/types';
	import { getTrackSets } from '$lib/api/tracks';
	import { getUiStore } from '$lib/stores/ui.svelte';
	import Spinner from '../Spinner.svelte';
	import Button from '../primitives/Button.svelte';
	import AddToSetPicker from '../set/AddToSetPicker.svelte';

	let { trackId, trackTitle = 'track' }: { trackId: number; trackTitle?: string } = $props();

	const ui = getUiStore();

	let appearances = $state<TrackSetAppearance[]>([]);
	let loading = $state(true);
	let showPicker = $state(false);

	async function load() {
		loading = true;
		try {
			appearances = await getTrackSets(trackId);
		} catch {
			appearances = [];
		} finally {
			loading = false;
		}
	}

	// The panel is always visible now — there is no expand gesture to defer the
	// fetch behind — so load immediately whenever the track changes.
	$effect(() => {
		trackId;
		showPicker = false;
		load();
	});

	function navigateToSet(setId: number) {
		ui.selectedSetId = setId;
		ui.activeTab = 'set';
	}

	function handleAdded() {
		// A set just gained this track — refresh so it shows up in the list.
		showPicker = false;
		load();
	}
</script>

<section class="sets-card" aria-label="Sets featuring this track">
	{#if loading}
		<div class="state"><Spinner size={16} label="Checking your sets..." /></div>
	{:else if appearances.length === 0}
		<!-- Empty state — invite the DJ to place the track somewhere. Centered so it
		     fills the panel (matched to the waveform/stat-card block height) instead
		     of clinging to the top. -->
		<div class="empty">
			<span class="empty-icon" aria-hidden="true">
				<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
					<rect x="3" y="3" width="7" height="7" rx="1.5" stroke="currentColor" stroke-width="1.5"/>
					<rect x="14" y="3" width="7" height="7" rx="1.5" stroke="currentColor" stroke-width="1.5"/>
					<rect x="3" y="14" width="7" height="7" rx="1.5" stroke="currentColor" stroke-width="1.5"/>
					<rect x="14" y="14" width="7" height="7" rx="1.5" stroke="currentColor" stroke-width="1.5"/>
				</svg>
			</span>
			<p class="empty-title">Not in a set yet</p>
			<p class="empty-hint">Drop this track into a set — or start a new one.</p>
			<Button variant="secondary" size="sm" onclick={() => (showPicker = !showPicker)}>
				{#snippet icon()}<span aria-hidden="true">+</span>{/snippet}
				Add to a set
			</Button>
		</div>
	{:else}
		<!-- Populated — every set this track lives in, always visible. -->
		<ul class="set-list">
			{#each appearances as app (app.set_id)}
				<li>
					<button class="set-row" onclick={() => navigateToSet(app.set_id)} title="Open {app.set_name ?? 'set'}">
						<span class="set-name">{app.set_name ?? 'Untitled'}</span>
						<span class="set-pos" title="Position {app.position + 1} in the set">#{app.position + 1}</span>
					</button>
				</li>
			{/each}
		</ul>
		<div class="footer">
			<button class="add-link" onclick={() => (showPicker = !showPicker)}>+ Add to another set</button>
		</div>
	{/if}

	{#if showPicker}
		<div class="picker-popover">
			<AddToSetPicker {trackId} {trackTitle} onclose={() => (showPicker = false)} onadded={handleAdded} />
		</div>
	{/if}
</section>

<style>
	.sets-card {
		position: relative;
		display: flex;
		flex-direction: column;
		background: var(--surface-2);
		border: var(--space-px) solid var(--border-subtle);
		border-radius: var(--radius-lg);
		overflow: visible; /* let the add-to-set popover escape the card */
	}

	.state {
		padding: var(--space-lg) var(--space-xl);
	}

	/* ── Empty state — the invitation. Fills + centers within the panel (the card
	 * gets a block-height min in the wide tier) so it reads as an intentional third
	 * panel, not a short card clinging to the top. ── */
	.empty {
		flex: 1;
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		text-align: center;
		gap: var(--space-sm);
		padding: var(--space-xl);
	}
	.empty-icon {
		width: var(--space-4xl);
		height: var(--space-4xl);
		color: var(--text-4);
	}
	.empty-icon svg {
		width: 100%;
		height: 100%;
	}
	.empty-title {
		margin: 0;
		font-size: var(--text-sm);
		font-weight: var(--font-weight-medium);
		color: var(--text-2);
	}
	.empty-hint {
		margin: 0 0 var(--space-2xs);
		font-size: var(--text-xs);
		color: var(--text-3);
		line-height: var(--lh-md);
		max-width: 28ch;
	}

	/* ── Populated — always-visible list of appearances (rows read like a table:
	 * set name left, position right, a hairline between each). ── */
	.set-list {
		list-style: none;
		margin: 0;
		padding: var(--space-sm);
		display: flex;
		flex-direction: column;
	}
	.set-list li + li {
		border-top: var(--space-px) solid var(--border-subtle);
	}
	.set-row {
		display: flex;
		justify-content: space-between;
		align-items: center;
		gap: var(--space-sm);
		width: 100%;
		padding: var(--space-sm) var(--space-md);
		background: none;
		border: none;
		border-radius: var(--radius-sm);
		color: var(--text-1);
		font-size: var(--text-sm);
		cursor: pointer;
		text-align: left;
		transition: background var(--dur-fast) var(--ease-standard);
	}
	.set-row:hover {
		background: var(--surface-hover);
	}
	.set-name {
		flex: 1;
		min-width: 0;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	.set-pos {
		flex-shrink: 0;
		font-size: var(--text-xs);
		color: var(--text-3);
		font-variant-numeric: tabular-nums;
	}

	/* ── Footer add affordance (populated state). Anchored to the bottom so, when the
	 * panel is taller than a short list (wide tier min-height), the list stays at the
	 * top and the add-link sits at the foot instead of floating mid-card. ── */
	.footer {
		margin-top: auto;
		padding: 0 var(--space-md) var(--space-md);
	}
	.add-link {
		background: none;
		border: none;
		padding: var(--space-xs) var(--space-sm);
		font-size: var(--text-xs);
		color: var(--accent-text);
		cursor: pointer;
		border-radius: var(--radius-sm);
		transition: background var(--dur-fast) var(--ease-standard);
	}
	.add-link:hover {
		background: var(--surface-hover);
	}

	/* ── Add-to-set popover — drops below the card, floats over the content beneath
	 * (opened by either the empty-state CTA or the footer link). ── */
	.picker-popover {
		position: absolute;
		top: calc(100% + var(--space-xs));
		right: 0;
		background: var(--surface-1);
		border: var(--space-px) solid var(--border-subtle);
		border-radius: var(--radius-lg);
		box-shadow: var(--elev-3);
		z-index: 20;
		min-width: 220px;
	}
</style>
