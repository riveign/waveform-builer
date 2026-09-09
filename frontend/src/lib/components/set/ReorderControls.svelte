<script lang="ts">
	/**
	 * The reorder cluster: a grab handle and the ↑/↓ nudges beside it.
	 *
	 * Handle and nudges sit side by side, never stacked — stacking all three set a
	 * 48px floor under every row, which the 42px Ledger row cannot pay.
	 *
	 * Reveal-on-hover is driven by two inherited custom properties rather than a
	 * `:global` reach-in, so each layout decides what "hovered" means for its own
	 * rows: set `--reorder-handle-op` / `--reorder-nudge-op` on the row.
	 */
	let {
		index,
		count,
		lifted = false,
		disabled = false,
		dense = false,
		draggable = true,
		onnudge,
		onkeydown,
		onblur,
	}: {
		index: number;
		/** Total rows — the last one can't move down. */
		count: number;
		lifted?: boolean;
		/** Another write is in flight; moving now would race it. */
		disabled?: boolean;
		/** Compact sizing for the thin rows (Compact view, Ledger). */
		dense?: boolean;
		/** False where the layout has no drop zone — the copy must not promise one. */
		draggable?: boolean;
		onnudge?: (dir: -1 | 1) => void;
		onkeydown?: (e: KeyboardEvent) => void;
		onblur?: () => void;
	} = $props();
</script>

<div class="reorder-controls" class:active={lifted} class:dense class:static={!draggable}>
	<button
		class="drag-handle"
		data-handle
		data-idx={index}
		onkeydown={(e) => onkeydown?.(e)}
		onblur={() => onblur?.()}
		title={lifted
			? 'Moving — ↑/↓ to move, Space to drop, Esc to cancel'
			: draggable
				? 'Drag to reorder, or Space to move with ↑/↓'
				: 'Space to move with ↑/↓'}
		aria-label={lifted
			? 'Moving track — arrow keys to move, space to drop, escape to cancel'
			: draggable
				? 'Reorder track — drag, or press space to move with arrow keys'
				: 'Reorder track — press space to move with arrow keys'}
		aria-pressed={lifted}
	>
		<svg width={dense ? 9 : 12} height={dense ? 14 : 18} viewBox="0 0 12 18" fill="currentColor">
			<circle cx="3" cy="3" r="1.5" /><circle cx="9" cy="3" r="1.5" />
			<circle cx="3" cy="9" r="1.5" /><circle cx="9" cy="9" r="1.5" />
			<circle cx="3" cy="15" r="1.5" /><circle cx="9" cy="15" r="1.5" />
		</svg>
	</button>
	<div class="nudge-col">
		<button
			class="move-btn"
			data-move="up"
			data-idx={index}
			onclick={(e) => { e.stopPropagation(); onnudge?.(-1); }}
			disabled={index === 0 || lifted || disabled}
			title="Move up"
			aria-label="Move up one slot"
		>
			<svg width="10" height="10" viewBox="0 0 10 10" fill="none" stroke="currentColor" stroke-width="1.6">
				<path d="M1.5 6.5 5 3l3.5 3.5" />
			</svg>
		</button>
		<button
			class="move-btn"
			data-move="down"
			data-idx={index}
			onclick={(e) => { e.stopPropagation(); onnudge?.(1); }}
			disabled={index === count - 1 || lifted || disabled}
			title="Move down"
			aria-label="Move down one slot"
		>
			<svg width="10" height="10" viewBox="0 0 10 10" fill="none" stroke="currentColor" stroke-width="1.6">
				<path d="M1.5 3.5 5 7l3.5-3.5" />
			</svg>
		</button>
	</div>
</div>

<style>
	.reorder-controls {
		display: flex;
		align-items: center;
		gap: 1px;
		flex-shrink: 0;
	}

	.nudge-col {
		display: flex;
		flex-direction: column;
		gap: 1px;
	}

	.drag-handle {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 18px;
		flex-shrink: 0;
		border: none;
		background: none;
		padding: 0;
		color: var(--text-dim);
		cursor: grab;
		/* The row raises this on hover; see the component docstring. */
		opacity: var(--reorder-handle-op, 0.4);
		border-radius: 3px;
		transition: opacity 0.1s, color 0.1s, background 0.1s;
	}

	.move-btn {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 16px;
		height: 12px;
		flex-shrink: 0;
		border: none;
		background: none;
		padding: 0;
		color: var(--text-dim);
		cursor: pointer;
		border-radius: 3px;
		opacity: var(--reorder-nudge-op, 0);
		transition: opacity 0.1s, color 0.1s, background 0.1s;
	}

	.reorder-controls:focus-within .move-btn {
		opacity: 0.8;
	}

	.move-btn:hover:not(:disabled) {
		background: var(--bg-tertiary);
		color: var(--accent);
	}

	.move-btn:disabled {
		cursor: default;
		opacity: 0.15;
	}

	.drag-handle:focus-visible,
	.move-btn:focus-visible {
		outline: 1px solid var(--accent);
		outline-offset: 1px;
		opacity: 1;
	}

	/* No drop zone here, so the grab cursor would be a lie. */
	.reorder-controls.static .drag-handle {
		cursor: pointer;
	}

	/* Lifted: the track is following the arrow keys until it's dropped. */
	.reorder-controls.active .drag-handle,
	.reorder-controls.active .move-btn {
		opacity: 1;
		color: var(--accent);
	}

	.reorder-controls.active .drag-handle {
		background: color-mix(in srgb, var(--accent) 18%, transparent);
		cursor: grabbing;
	}

	/* ── Dense: the thin rows (Compact, Ledger) ── */
	.reorder-controls.dense .drag-handle {
		width: 12px;
	}
	.reorder-controls.dense .move-btn {
		width: 14px;
		height: 11px;
	}
</style>
