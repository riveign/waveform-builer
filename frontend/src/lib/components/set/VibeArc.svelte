<script lang="ts">
	import { getTrackFeatures } from '$lib/api/tracks';
	import Chip from '$lib/components/primitives/Chip.svelte';

	let {
		trackAId,
		trackBId,
	}: {
		trackAId: number;
		trackBId: number;
	} = $props();

	type V = { brightness: number; density: number } | null;

	let vibeA = $state<V>(null);
	let vibeB = $state<V>(null);

	// Re-fetch whenever the pair changes.
	$effect(() => {
		const aId = trackAId;
		const bId = trackBId;
		vibeA = null;
		vibeB = null;
		let cancelled = false;
		Promise.all([getTrackFeatures(aId), getTrackFeatures(bId)])
			.then(([fa, fb]) => {
				if (cancelled) return;
				if (fa.vibe_brightness != null && fa.vibe_density != null)
					vibeA = { brightness: fa.vibe_brightness, density: fa.vibe_density };
				if (fb.vibe_brightness != null && fb.vibe_density != null)
					vibeB = { brightness: fb.vibe_brightness, density: fb.vibe_density };
			})
			.catch(() => {});
		return () => {
			cancelled = true;
		};
	});

	function brightnessWord(b: number): string {
		if (b < 0.3) return 'dark';
		if (b < 0.45) return 'moody';
		if (b < 0.6) return 'neutral';
		if (b < 0.78) return 'bright';
		return 'euphoric';
	}
	function densityWord(d: number): string {
		if (d < 0.3) return 'spacious';
		if (d < 0.5) return 'rolling';
		if (d < 0.72) return 'driving';
		return 'busy';
	}
	function label(v: NonNullable<V>): string {
		return `${brightnessWord(v.brightness)} & ${densityWord(v.density)}`;
	}
	function vibeColor(b: number, d: number): string {
		const hue = 250 - b * 210;
		const light = 28 + b * 42;
		const sat = 35 + d * 45;
		return `hsl(${hue.toFixed(0)}, ${sat.toFixed(0)}%, ${light.toFixed(0)}%)`;
	}

	let distance = $derived(
		vibeA && vibeB
			? Math.sqrt((vibeA.brightness - vibeB.brightness) ** 2 + (vibeA.density - vibeB.density) ** 2) /
					Math.SQRT2
			: 0,
	);

	// A teaching line tuned to what actually changed between the two tracks.
	let teaching = $derived.by(() => {
		if (!vibeA || !vibeB) return null;
		if (distance < 0.18) return null; // vibes already sit close — nothing to flag
		const db = vibeB.brightness - vibeA.brightness;
		const dd = vibeB.density - vibeA.density;
		const big = distance > 0.38;
		if (Math.abs(db) >= Math.abs(dd)) {
			if (db > 0)
				return big
					? 'A hard lift into the light — dark to bright. A deliberate lift, or a vibe clash?'
					: 'Brightening here. A gentle lift in mood.';
			return big
				? 'A plunge into the dark — bright to moody. Intentional drop, or a jolt?'
				: 'Pulling darker. Easing the mood down.';
		}
		if (dd > 0) return 'Thickening up — the groove gets busier. Building pressure?';
		return 'Opening up — the groove gets more spacious. Giving it room to breathe?';
	});
</script>

{#if vibeA && vibeB}
	<div class="vibe-arc">
		<div class="vibe-ends">
			<Chip
				variant="vibe"
				size="sm"
				value={label(vibeA)}
				title={label(vibeA)}
				color={vibeColor(vibeA.brightness, vibeA.density)}
			>
				{#snippet icon()}<span class="dot"></span>{/snippet}
			</Chip>
			<span class="arrow" class:clash={distance > 0.38}>→</span>
			<Chip
				variant="vibe"
				size="sm"
				value={label(vibeB)}
				title={label(vibeB)}
				color={vibeColor(vibeB.brightness, vibeB.density)}
			>
				{#snippet icon()}<span class="dot"></span>{/snippet}
			</Chip>
		</div>
		{#if teaching}
			<p class="vibe-teaching" class:clash={distance > 0.38}>{teaching}</p>
		{/if}
	</div>
{/if}

<style>
	.vibe-arc {
		display: flex;
		flex-direction: column;
		gap: 6px;
		padding: 10px 12px;
		background: var(--bg-tertiary);
		border: 1px solid var(--border);
		border-radius: 6px;
	}

	.vibe-ends {
		display: flex;
		align-items: center;
		gap: 8px;
		flex-wrap: wrap;
	}

	/* The vibe Chip carries the dot color via --chip-color (passed as `color`);
	 * the descriptor word stays readable (Chip's vibe variant). */
	.dot {
		width: 10px;
		height: 10px;
		border-radius: 50%;
		flex-shrink: 0;
		background: var(--chip-color);
		box-shadow: 0 0 0 1px rgba(0, 0, 0, 0.2) inset;
	}

	.arrow {
		color: var(--text-dim);
		font-size: 13px;
	}

	.arrow.clash {
		color: var(--accent-coral);
		font-weight: 700;
	}

	.vibe-teaching {
		margin: 0;
		font-size: 11px;
		line-height: 1.4;
		color: var(--text-secondary);
		font-style: italic;
	}

	.vibe-teaching.clash {
		color: var(--accent-coral);
	}
</style>
