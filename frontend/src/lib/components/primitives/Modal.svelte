<script lang="ts" module>
	export type ModalSize = 'sm' | 'md' | 'lg' | 'xl';
</script>

<script lang="ts">
	import type { Snippet } from 'svelte';

	/**
	 * The one dialog shell.
	 *
	 * Kiku had two competing idioms — four dialogs on native `<dialog>` and two
	 * hand-rolling a div overlay with `use:focusTrap` and a manual Escape handler —
	 * for about 2,700 lines of near-identical chrome (docs/notes/OBS-008/E5).
	 *
	 * This standardises on native `<dialog>` + `showModal()`, which gives the
	 * backdrop, Escape, focus trapping, `inert` background and top-layer stacking
	 * correctly and for free. The only things left to add by hand are body scroll
	 * lock and click-outside-to-dismiss.
	 */

	let {
		open = false,
		title = undefined,
		size = 'md',
		dismissible = true,
		onclose,
		header,
		children,
		footer,
	}: {
		open?: boolean;
		/** Heading text. Ignored when a `header` snippet is supplied. */
		title?: string;
		size?: ModalSize;
		/** Whether Escape and a backdrop click close the dialog. Turn off for a
		 *  modal mid-write, where dismissing would lose work. */
		dismissible?: boolean;
		onclose: () => void;
		/** Replaces the default title row — for headers that hold controls. */
		header?: Snippet;
		children: Snippet;
		/** Right-aligned action row along the bottom. */
		footer?: Snippet;
	} = $props();

	let dialogEl = $state<HTMLDialogElement | null>(null);

	$effect(() => {
		const el = dialogEl;
		if (!el) return;
		if (open && !el.open) el.showModal();
		else if (!open && el.open) el.close();
	});

	// Native <dialog> doesn't stop the page behind it from scrolling.
	$effect(() => {
		if (!open) return;
		const prev = document.body.style.overflow;
		document.body.style.overflow = 'hidden';
		return () => {
			document.body.style.overflow = prev;
		};
	});

	/** Fires for Escape and for `close()`, so it is the single exit path. */
	function handleClose() {
		onclose();
	}

	function handleCancel(e: Event) {
		// Escape raises `cancel` before `close`; block it when not dismissible.
		if (!dismissible) e.preventDefault();
	}

	/** A click landing on the dialog itself rather than its content is the backdrop. */
	function handleClick(e: MouseEvent) {
		if (dismissible && e.target === dialogEl) onclose();
	}
</script>

<dialog
	bind:this={dialogEl}
	class="modal modal--{size}"
	onclose={handleClose}
	oncancel={handleCancel}
	onclick={handleClick}
	aria-label={header ? undefined : title}
>
	<div class="modal-panel">
		{#if header}
			<div class="modal-header">{@render header()}</div>
		{:else if title}
			<div class="modal-header">
				<h2 class="modal-title">{title}</h2>
				<button class="modal-close" type="button" aria-label="Close" onclick={onclose}>×</button>
			</div>
		{/if}

		<div class="modal-body">{@render children()}</div>

		{#if footer}
			<div class="modal-footer">{@render footer()}</div>
		{/if}
	</div>
</dialog>

<style>
	.modal {
		/* The global reset zeroes every margin, which clobbers the UA's
		   `dialog { margin: auto }` and pins the dialog to the top-left corner.
		   Restore it here so every modal centres. */
		margin: auto;
		padding: 0;
		border: 1px solid var(--border-default);
		border-radius: var(--radius-lg, 10px);
		background: var(--surface-1);
		color: var(--text-1);
		max-height: 85vh;
		width: 90vw;
		overflow: hidden;
	}

	.modal::backdrop {
		/* Deliberately not a token: the scrim is a property of the overlay, not of
		   the surface palette, and must read the same in both themes. */
		background: rgb(0 0 0 / 0.6);
	}

	.modal--sm { max-width: 420px; }
	.modal--md { max-width: 640px; }
	.modal--lg { max-width: 860px; }
	.modal--xl { max-width: 1100px; }

	.modal-panel {
		display: flex;
		flex-direction: column;
		max-height: 85vh;
	}

	.modal-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: var(--space-md);
		padding: var(--space-md) var(--space-lg);
		border-bottom: 1px solid var(--border-subtle);
		flex-shrink: 0;
	}

	.modal-title {
		font-size: var(--text-md);
		font-weight: var(--font-weight-semibold);
		color: var(--text-1);
	}

	.modal-close {
		background: none;
		border: none;
		color: var(--text-3);
		font-size: var(--text-lg);
		line-height: 1;
		cursor: pointer;
		padding: var(--space-xs);
		border-radius: var(--radius-sm, 4px);
	}

	.modal-close:hover {
		color: var(--text-1);
		background: var(--surface-hover);
	}

	.modal-close:focus-visible {
		outline: 2px solid var(--accent);
		outline-offset: 2px;
	}

	/* The body is the only scroll region, so headers and footers stay put. */
	.modal-body {
		padding: var(--space-lg);
		overflow-y: auto;
		flex: 1;
		min-height: 0;
	}

	.modal-footer {
		display: flex;
		align-items: center;
		justify-content: flex-end;
		gap: var(--space-sm);
		padding: var(--space-md) var(--space-lg);
		border-top: 1px solid var(--border-subtle);
		flex-shrink: 0;
	}
</style>
