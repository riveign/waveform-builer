<script lang="ts">
	import type { Snippet } from 'svelte';

	let {
		open = $bindable(false),
		x = 0,
		y = 0,
		onclose,
		children,
	}: {
		open: boolean;
		x: number;
		y: number;
		onclose?: () => void;
		children?: Snippet;
	} = $props();

	let menuEl = $state<HTMLDivElement | null>(null);
	let clampedX = $state(0);
	let clampedY = $state(0);

	$effect(() => {
		if (!open || !menuEl) return;
		const { innerWidth, innerHeight } = window;
		const { offsetWidth: w, offsetHeight: h } = menuEl;
		clampedX = Math.min(x, innerWidth - w - 8);
		clampedY = Math.min(y, innerHeight - h - 8);
	});

	$effect(() => {
		if (!open) return;
		function handleOutsideClick(e: MouseEvent) {
			if (menuEl && !menuEl.contains(e.target as Node)) {
				open = false;
				onclose?.();
			}
		}
		function handleEscape(e: KeyboardEvent) {
			if (e.key === 'Escape') {
				open = false;
				onclose?.();
			}
		}
		// Use setTimeout to avoid the triggering right-click from immediately closing
		const timer = setTimeout(() => {
			document.addEventListener('mousedown', handleOutsideClick);
		}, 0);
		document.addEventListener('keydown', handleEscape);
		return () => {
			clearTimeout(timer);
			document.removeEventListener('mousedown', handleOutsideClick);
			document.removeEventListener('keydown', handleEscape);
		};
	});
</script>

{#if open}
	<div
		bind:this={menuEl}
		class="context-menu"
		role="menu"
		tabindex="-1"
		style="left: {clampedX}px; top: {clampedY}px;"
		oncontextmenu={(e) => e.preventDefault()}
	>
		{@render children?.()}
	</div>
{/if}

<style>
	.context-menu {
		position: fixed;
		z-index: 500;
		background: var(--bg-primary);
		border: 1px solid var(--border);
		border-radius: 8px;
		padding: 4px;
		min-width: 180px;
		box-shadow: 0 4px 16px rgba(0, 0, 0, 0.4);
		display: flex;
		flex-direction: column;
		gap: 1px;
		animation: menu-appear 0.1s ease-out;
	}
	@keyframes menu-appear {
		from { opacity: 0; transform: scale(0.97) translateY(-2px); }
		to   { opacity: 1; transform: scale(1)    translateY(0); }
	}
</style>
