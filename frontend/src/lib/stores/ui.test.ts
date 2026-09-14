/**
 * The library sidebar's fold state: collapsed is remembered, a peek never is,
 * and jumping to search peeks instead of unfolding.
 */

import { beforeEach, describe, expect, it } from 'vitest';
import { getUiStore } from './ui.svelte';

const ui = getUiStore();

beforeEach(() => {
	ui.setSidebarCollapsed(false);
	localStorage.clear();
});

describe('library sidebar', () => {
	it('folds and unfolds, and remembers it', () => {
		ui.toggleSidebar();
		expect(ui.sidebarCollapsed).toBe(true);
		expect(ui.libraryOpen).toBe(false);
		expect(localStorage.getItem('kiku:sidebar-collapsed')).toBe('1');

		ui.toggleSidebar();
		expect(ui.sidebarCollapsed).toBe(false);
		expect(ui.libraryOpen).toBe(true);
		expect(localStorage.getItem('kiku:sidebar-collapsed')).toBe('0');
	});

	it('peeks when you search a collapsed library, without unfolding it', () => {
		ui.setSidebarCollapsed(true);
		const before = ui.searchFocusRequested;

		ui.focusSearch();

		expect(ui.sidebarPeeking).toBe(true);
		expect(ui.sidebarCollapsed).toBe(true);
		expect(ui.libraryOpen).toBe(true);
		expect(ui.searchFocusRequested).toBe(before + 1);
		expect(localStorage.getItem('kiku:sidebar-collapsed')).toBe('1');
	});

	it('just focuses search when the library is already open', () => {
		const before = ui.searchFocusRequested;
		ui.focusSearch();
		expect(ui.sidebarPeeking).toBe(false);
		expect(ui.searchFocusRequested).toBe(before + 1);
	});

	it('ends a peek on close, and on any pin or unpin', () => {
		ui.setSidebarCollapsed(true);
		ui.focusSearch();
		ui.closePeek();
		expect(ui.sidebarPeeking).toBe(false);
		expect(ui.libraryOpen).toBe(false);

		ui.focusSearch();
		ui.toggleSidebar();
		expect(ui.sidebarPeeking).toBe(false);
		expect(ui.sidebarCollapsed).toBe(false);
	});
});
