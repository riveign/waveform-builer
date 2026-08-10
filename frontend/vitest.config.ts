import { defineConfig } from 'vitest/config';
import { svelte } from '@sveltejs/vite-plugin-svelte';
import { svelteTesting } from '@testing-library/svelte/vite';
import path from 'node:path';

export default defineConfig({
	plugins: [svelte({ hot: false }), svelteTesting()],
	resolve: {
		alias: {
			// The tests run outside SvelteKit, so $lib has to be wired by hand.
			$lib: path.resolve('./src/lib'),
		},
		// Components under test use runes, so resolve Svelte's browser build.
		conditions: ['browser'],
	},
	test: {
		environment: 'jsdom',
		globals: true,
		setupFiles: ['./src/tests/setup.ts'],
		//  so tests that drive a resource with $state compile as
		// rune files — plain .ts cannot host runes.
		include: ['src/**/*.test.ts', 'src/**/*.test.svelte.ts'],
	},
});
