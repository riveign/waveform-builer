<script lang="ts">
	import type { IconSize } from './icon-types';

	let {
		size = 'sm',
		label = 'BPM',
		title = 'Beats per minute',
	}: {
		/** One of the shared --icon-size-* steps (content-conventions §6). */
		size?: IconSize;
		/** Accessible name; defaults to "BPM" so the tempo meaning survives even
		 *  when the literal text label is dropped from the chip. */
		label?: string;
		/** Tooltip text; defaults to the long-form meaning. */
		title?: string;
	} = $props();
</script>

<!-- 24×24 viewBox, currentColor so it inherits the chip/theme color. A metronome
     silhouette — trapezoid body + a swung pendulum arm — reads as "tempo" without
     the literal "BPM" text (content-conventions §6: meaning-bearing icon + a11y
     label, color never the only signal). -->
<svg
	class="metronome-icon metronome-icon--{size}"
	viewBox="0 0 24 24"
	role="img"
	aria-label={label}
	stroke="currentColor"
	stroke-linecap="round"
	stroke-linejoin="round"
	fill="none"
>
	<title>{title}</title>
	<!-- body: trapezoid, wide base, narrow top -->
	<path d="M9 4 L15 4 L19 20 L5 20 Z" />
	<!-- base shelf -->
	<line x1="5" y1="20" x2="19" y2="20" />
	<!-- pendulum arm, swung to one side -->
	<line x1="12" y1="18" x2="15.5" y2="6.5" />
	<!-- pendulum weight -->
	<circle cx="13.8" cy="12.5" r="1.4" fill="currentColor" stroke="none" />
</svg>

<style>
	.metronome-icon {
		display: inline-block;
		flex-shrink: 0;
		vertical-align: middle;
		/* color comes from the parent (chip/theme) via currentColor. */
		stroke-width: var(--icon-stroke);
	}
	.metronome-icon--sm {
		width: var(--icon-size-sm);
		height: var(--icon-size-sm);
	}
	.metronome-icon--md {
		width: var(--icon-size-md);
		height: var(--icon-size-md);
	}
	.metronome-icon--lg {
		width: var(--icon-size-lg);
		height: var(--icon-size-lg);
	}
</style>
