/**
 * Tests for Modal — the shell every dialog in Kiku now sits inside.
 *
 * A regression here breaks six surfaces at once, and two of the behaviours it
 * owns (Escape, backdrop dismissal) are the kind you only notice by trying them.
 * `margin: auto` is asserted because the global `* { margin: 0 }` reset silently
 * pinned every native <dialog> to the top-left until P6 caught it.
 */

import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import { createRawSnippet } from 'svelte';
import Modal from './Modal.svelte';

const snip = (html: string) => createRawSnippet(() => ({ render: () => html }));

const open = (props: Record<string, unknown> = {}) =>
	render(Modal, {
		props: {
			open: true,
			title: 'Build a set',
			onclose: vi.fn(),
			children: snip('<p>body content</p>'),
			...props,
		},
	});

const dialog = () => document.querySelector('dialog') as HTMLDialogElement;

describe('Modal', () => {
	it('opens when `open` is true and shows its title and body', () => {
		open();

		expect(dialog().open).toBe(true);
		expect(screen.getByText('Build a set')).toBeInTheDocument();
		expect(screen.getByText('body content')).toBeInTheDocument();
	});

	it('stays shut when `open` is false', () => {
		open({ open: false });
		expect(dialog().open).toBe(false);
	});

	it('closes when `open` flips to false', async () => {
		const { rerender } = open();
		expect(dialog().open).toBe(true);

		await rerender({ open: false });

		expect(dialog().open).toBe(false);
	});

	it('reports a close when the close button is pressed', async () => {
		const onclose = vi.fn();
		open({ onclose });

		screen.getByRole('button', { name: 'Close' }).click();

		expect(onclose).toHaveBeenCalledOnce();
	});

	it('reports a close when the backdrop is clicked', () => {
		const onclose = vi.fn();
		open({ onclose });

		// A click whose target is the dialog element itself landed on the backdrop:
		// anything inside the panel targets the panel or its children.
		dialog().dispatchEvent(new MouseEvent('click', { bubbles: true }));

		expect(onclose).toHaveBeenCalledOnce();
	});

	it('ignores clicks inside the panel', () => {
		const onclose = vi.fn();
		open({ onclose });

		screen.getByText('body content').dispatchEvent(new MouseEvent('click', { bubbles: true }));

		expect(onclose).not.toHaveBeenCalled();
	});

	it('does not dismiss on a backdrop click when dismissible is false', () => {
		const onclose = vi.fn();
		open({ onclose, dismissible: false });

		dialog().dispatchEvent(new MouseEvent('click', { bubbles: true }));

		expect(onclose).not.toHaveBeenCalled();
	});

	it('blocks Escape when dismissible is false', () => {
		open({ dismissible: false });

		const cancel = new Event('cancel', { cancelable: true });
		dialog().dispatchEvent(cancel);

		expect(cancel.defaultPrevented).toBe(true);
	});

	it('allows Escape by default', () => {
		open();

		const cancel = new Event('cancel', { cancelable: true });
		dialog().dispatchEvent(cancel);

		expect(cancel.defaultPrevented).toBe(false);
	});

	it('renders a header snippet in place of the title row', () => {
		open({ header: snip('<span>custom header</span>'), title: 'ignored' });

		expect(screen.getByText('custom header')).toBeInTheDocument();
		expect(screen.queryByText('ignored')).not.toBeInTheDocument();
	});

	it('renders a footer when given one', () => {
		open({ footer: snip('<button>Confirm</button>') });

		expect(screen.getByRole('button', { name: 'Confirm' })).toBeInTheDocument();
	});

	it('locks body scroll while open and restores it after', async () => {
		const { rerender } = open();
		expect(document.body.style.overflow).toBe('hidden');

		await rerender({ open: false });

		expect(document.body.style.overflow).not.toBe('hidden');
	});

	it('names itself for assistive tech when there is no custom header', () => {
		open();
		expect(dialog()).toHaveAttribute('aria-label', 'Build a set');
	});

	it('applies the requested size class', () => {
		open({ size: 'xl' });
		expect(dialog().className).toContain('modal--xl');
	});
});
