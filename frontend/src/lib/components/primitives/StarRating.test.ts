/**
 * Tests for StarRating — the control that writes the DJ's curation signal, which
 * feeds `track_quality` in scoring. A misreported rating quietly changes what
 * gets suggested.
 *
 * The stars are ARIA radios, so they are queried as radios: asserting the role
 * here is what caught the container being a plain `group` rather than a
 * `radiogroup`, which meant assistive tech never treated the five as one control.
 */

import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import StarRating from './StarRating.svelte';

describe('StarRating', () => {
	it('is a radiogroup of five stars', () => {
		render(StarRating, { props: { rating: 0 } });

		expect(screen.getByRole('radiogroup', { name: 'Track rating' })).toBeInTheDocument();
		expect(screen.getAllByRole('radio')).toHaveLength(5);
	});

	it('marks the current rating as checked, and only that one', () => {
		render(StarRating, { props: { rating: 3 } });
		const checked = screen.getAllByRole('radio').filter((r) => r.getAttribute('aria-checked') === 'true');

		expect(checked).toHaveLength(1);
		expect(checked[0]).toHaveAccessibleName('3 stars');
	});

	it('names one star in the singular', () => {
		render(StarRating, { props: { rating: 0 } });

		expect(screen.getByRole('radio', { name: '1 star' })).toBeInTheDocument();
	});

	it('reports the star that was clicked', () => {
		const onchange = vi.fn();
		render(StarRating, { props: { rating: 0, onchange } });

		screen.getByRole('radio', { name: '4 stars' }).click();

		expect(onchange).toHaveBeenCalledWith(4);
	});

	it('clicking the current rating clears it', () => {
		// Re-clicking is how a DJ un-rates a track; without this they would be
		// stuck at one star with no way back to unrated.
		const onchange = vi.fn();
		render(StarRating, { props: { rating: 3, onchange } });

		screen.getByRole('radio', { name: '3 stars' }).click();

		expect(onchange).toHaveBeenCalledWith(0);
	});

	it('disables its stars when readonly', () => {
		render(StarRating, { props: { rating: 3, readonly: true } });

		for (const star of screen.getAllByRole('radio')) {
			expect(star).toBeDisabled();
		}
	});

	it('does not report changes when readonly', () => {
		const onchange = vi.fn();
		render(StarRating, { props: { rating: 3, readonly: true, onchange } });

		screen.getAllByRole('radio').forEach((r) => r.click());

		expect(onchange).not.toHaveBeenCalled();
	});

	it('renders a compact form without five separate controls', () => {
		render(StarRating, { props: { rating: 4, display: 'compact' } });

		expect(screen.queryAllByRole('radio')).toHaveLength(0);
	});
});
