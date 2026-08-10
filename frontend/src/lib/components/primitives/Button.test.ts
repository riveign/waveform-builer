import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import { createRawSnippet } from 'svelte';
import Button from './Button.svelte';

const label = (text: string) =>
	createRawSnippet(() => ({ render: () => `<span>${text}</span>` }));

describe('Button', () => {
	it('renders its label', () => {
		render(Button, { props: { children: label('Build set') } });
		expect(screen.getByRole('button')).toHaveTextContent('Build set');
	});

	it('calls onclick', async () => {
		const onclick = vi.fn();
		render(Button, { props: { children: label('Go'), onclick } });
		screen.getByRole('button').click();
		expect(onclick).toHaveBeenCalledOnce();
	});
});
