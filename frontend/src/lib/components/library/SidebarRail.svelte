<script lang="ts">
	import Button from '../primitives/Button.svelte';
	import { getUiStore } from '$lib/stores/ui.svelte';
	import { focusAfterFold, LIBRARY_TOGGLE } from './sidebarFocus';

	const ui = getUiStore();
</script>

<!-- What's left of the library when it folds away: bring it back, or search it.
     Inert unless it's the thing on screen, so Tab never lands on a hidden rail. -->
<div class="rail" inert={!ui.sidebarCollapsed || ui.sidebarPeeking}>
	<div class="rail-band toolbar" data-rail="toggle">
		<Button
			iconOnly
			size="sm"
			variant="ghost"
			ariaLabel="Show library"
			title="Show library  ["
			onclick={() => {
				ui.setSidebarCollapsed(false);
				focusAfterFold(LIBRARY_TOGGLE);
			}}
		>
			{#snippet icon()}
				<svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
					<rect x="1.75" y="2.75" width="12.5" height="10.5" rx="1.5" stroke="currentColor" stroke-width="1.3" />
					<path d="M5.75 3v10" stroke="currentColor" stroke-width="1.3" />
					<path d="M8.5 6l2 2-2 2" stroke="currentColor" stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round" />
				</svg>
			{/snippet}
		</Button>
	</div>
	<div class="rail-band secondary" data-rail="search">
		<Button
			iconOnly
			size="sm"
			variant="ghost"
			ariaLabel={ui.libraryFiltered ? 'Search tracks (filters are on)' : 'Search tracks'}
			title={ui.libraryFiltered ? 'Search tracks · filtered  /' : 'Search tracks  /'}
			onclick={() => ui.focusSearch()}
		>
			{#snippet icon()}
				<span class="glyph">
					<svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
						<circle cx="7" cy="7" r="4.75" stroke="currentColor" stroke-width="1.4" />
						<path d="M10.5 10.5L14 14" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" />
					</svg>
					{#if ui.libraryFiltered}<span class="dot" aria-hidden="true"></span>{/if}
				</span>
			{/snippet}
		</Button>
	</div>
</div>

<style>
	.rail {
		position: absolute;
		inset: 0 auto 0 0;
		width: var(--rail-width);
		display: flex;
		flex-direction: column;
		background: var(--bg-primary);
		border-right: 1px solid var(--border);
		z-index: 1;
	}

	/* Bands share the library's heights so the dividers run straight across. */
	.rail-band {
		display: grid;
		place-items: center;
		border-bottom: 1px solid var(--border);
	}
	.rail-band.toolbar { height: var(--band-toolbar-h); }
	.rail-band.secondary { height: var(--band-secondary-h); }

	.glyph {
		position: relative;
		display: grid;
		place-items: center;
	}

	/* A hidden filter should never surprise you. */
	.dot {
		position: absolute;
		top: -2px;
		right: -3px;
		width: 7px;
		height: 7px;
		border-radius: var(--radius-full);
		background: var(--accent-hover);
		box-shadow: 0 0 0 2px var(--bg-primary);
	}
</style>
