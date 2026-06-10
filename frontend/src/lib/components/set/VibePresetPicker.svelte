<script lang="ts">
	import { onMount } from 'svelte';
	import { fetchJson } from '$lib/api/client';
	import type { VibePreset } from '$lib/types';

	let {
		preset = $bindable<string | null>(null),
		intensity = $bindable(60),
	}: {
		preset: string | null;
		intensity: number;
	} = $props();

	// Hardcoded fallback mirrors the backend VIBE_PRESETS so the picker works
	// even if the presets endpoint is unreachable.
	const FALLBACK: VibePreset[] = [
		{ name: 'dark & deep', brightness: 0.15, density: 0.35, label: 'dark & rolling' },
		{ name: 'hypnotic', brightness: 0.3, density: 0.25, label: 'moody & spacious' },
		{ name: 'rolling', brightness: 0.5, density: 0.65, label: 'neutral & driving' },
		{ name: 'driving', brightness: 0.5, density: 0.8, label: 'neutral & busy' },
		{ name: 'melodic', brightness: 0.7, density: 0.45, label: 'bright & rolling' },
		{ name: 'euphoric', brightness: 0.9, density: 0.6, label: 'euphoric & driving' },
		{ name: 'raw / peak', brightness: 0.45, density: 0.9, label: 'moody & busy' },
	];

	let presets = $state<VibePreset[]>(FALLBACK);

	onMount(async () => {
		try {
			const data = await fetchJson<{ presets: VibePreset[] }>('/api/sets/vibe-presets');
			if (data.presets?.length) presets = data.presets;
		} catch {
			// Keep the fallback list.
		}
	});

	/** A color hint for a vibe: hue from dark-blue → amber, lit by brightness, saturated by density. */
	function vibeColor(brightness: number, density: number): string {
		const hue = 250 - brightness * 210; // dark → blue/purple, bright → amber
		const light = 28 + brightness * 42;
		const sat = 35 + density * 45;
		return `hsl(${hue.toFixed(0)}, ${sat.toFixed(0)}%, ${light.toFixed(0)}%)`;
	}

	function select(name: string) {
		preset = preset === name ? null : name; // click again to clear (vibe off)
	}
</script>

<div class="vibe-picker">
	<div class="vibe-chips">
		{#each presets as p (p.name)}
			<button
				type="button"
				class="vibe-chip"
				class:active={preset === p.name}
				onclick={() => select(p.name)}
				title={p.label}
			>
				<span
					class="vibe-dot"
					style="background: linear-gradient(135deg, {vibeColor(p.brightness, p.density)}, {vibeColor(
						Math.min(1, p.brightness + 0.15),
						p.density,
					)});"
				></span>
				{p.name}
			</button>
		{/each}
	</div>

	{#if preset}
		<div class="vibe-intensity">
			<div class="intensity-head">
				<span class="intensity-label">How strongly should "{preset}" steer the set?</span>
				<span class="intensity-val">{intensity}%</span>
			</div>
			<input type="range" class="intensity-slider" min={10} max={100} step={5} bind:value={intensity} />
			<div class="intensity-range">
				<span>A nudge</span>
				<span>The whole story</span>
			</div>
		</div>
	{:else}
		<span class="vibe-hint">Pick a feeling, or leave it open and let key &amp; energy lead.</span>
	{/if}
</div>

<style>
	.vibe-picker {
		display: flex;
		flex-direction: column;
		gap: 8px;
	}

	.vibe-chips {
		display: flex;
		flex-wrap: wrap;
		gap: 5px;
	}

	.vibe-chip {
		display: inline-flex;
		align-items: center;
		gap: 6px;
		font-size: 11px;
		padding: 4px 9px;
		border-radius: 12px;
		color: var(--text-secondary);
		background: var(--bg-secondary);
		border: 1px solid var(--border);
		transition: all 0.1s;
		cursor: pointer;
	}

	.vibe-chip:hover {
		border-color: var(--accent);
		color: var(--text-primary);
	}

	.vibe-chip.active {
		background: var(--accent);
		border-color: var(--accent);
		color: #000;
		font-weight: 600;
	}

	.vibe-dot {
		width: 11px;
		height: 11px;
		border-radius: 50%;
		flex-shrink: 0;
		box-shadow: 0 0 0 1px rgba(0, 0, 0, 0.2) inset;
	}

	.vibe-intensity {
		display: flex;
		flex-direction: column;
		gap: 3px;
		padding: 8px 10px;
		background: var(--bg-tertiary);
		border: 1px solid var(--border);
		border-radius: 6px;
	}

	.intensity-head {
		display: flex;
		align-items: center;
		justify-content: space-between;
	}

	.intensity-label {
		font-size: 11px;
		color: var(--text-secondary);
	}

	.intensity-val {
		font-size: 11px;
		font-weight: 600;
		color: var(--accent);
	}

	.intensity-slider {
		width: 100%;
		accent-color: var(--accent);
		cursor: pointer;
		height: 6px;
	}

	.intensity-range {
		display: flex;
		justify-content: space-between;
		font-size: 9px;
		color: var(--text-dim);
	}

	.vibe-hint {
		font-size: 10px;
		color: var(--text-dim);
	}
</style>
