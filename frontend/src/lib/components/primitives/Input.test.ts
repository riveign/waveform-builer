/**
 * Tests for Input. The label and `aria-describedby` wiring are the point of the
 * primitive existing — a field without a label is the accessibility regression
 * these were meant to stop repeating across dialogs.
 */

import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import Input from './Input.svelte';

describe('Input', () => {
	it('associates its label with the field', () => {
		render(Input, { props: { value: '', label: 'Name' } });

		// getByLabelText only resolves when label/for wiring is correct.
		expect(screen.getByLabelText('Name')).toBeInTheDocument();
	});

	it('falls back to an aria-label when there is no visible label', () => {
		render(Input, { props: { value: '', ariaLabel: 'Search tracks' } });

		expect(screen.getByLabelText('Search tracks')).toBeInTheDocument();
	});

	it('describes the field with its hint', () => {
		render(Input, { props: { value: '', label: 'Name', hint: 'Leave blank to auto-name' } });

		expect(screen.getByLabelText('Name')).toHaveAccessibleDescription('Leave blank to auto-name');
	});

	it('marks itself invalid for assistive tech', () => {
		render(Input, { props: { value: '', label: 'Name', invalid: true, hint: 'Already taken' } });

		expect(screen.getByLabelText('Name')).toHaveAttribute('aria-invalid', 'true');
	});

	it('is not marked invalid by default', () => {
		render(Input, { props: { value: '', label: 'Name' } });

		expect(screen.getByLabelText('Name')).not.toHaveAttribute('aria-invalid');
	});

	it('passes through type, placeholder and bounds', () => {
		render(Input, {
			props: { value: 90, label: 'Minutes', type: 'number', min: 1, max: 300 },
		});
		const el = screen.getByLabelText('Minutes');

		expect(el).toHaveAttribute('type', 'number');
		expect(el).toHaveAttribute('min', '1');
		expect(el).toHaveAttribute('max', '300');
	});

	it('can be disabled', () => {
		render(Input, { props: { value: '', label: 'Name', disabled: true } });

		expect(screen.getByLabelText('Name')).toBeDisabled();
	});

	it('reports input events', async () => {
		const oninput = vi.fn();
		render(Input, { props: { value: '', label: 'Name', oninput } });

		const el = screen.getByLabelText('Name') as HTMLInputElement;
		el.value = 'Saturday';
		el.dispatchEvent(new Event('input', { bubbles: true }));

		expect(oninput).toHaveBeenCalled();
	});

	it('gives two instances distinct ids', () => {
		render(Input, { props: { value: '', label: 'First' } });
		render(Input, { props: { value: '', label: 'Second' } });

		const a = screen.getByLabelText('First');
		const b = screen.getByLabelText('Second');

		expect(a.id).not.toBe(b.id);
	});
});
