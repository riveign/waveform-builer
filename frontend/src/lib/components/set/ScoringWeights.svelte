<script lang="ts">
	import type { ScoringWeights } from '$lib/types';

	const DEFAULTS: ScoringWeights = {
		harmonic: 25,
		energy_fit: 20,
		bpm_compat: 20,
		genre_coherence: 15,
		track_quality: 20,
	};

	const LABELS: Record<keyof ScoringWeights, string> = {
		harmonic: 'Key Match',
		energy_fit: 'Energy Flow',
		bpm_compat: 'Tempo Match',
		genre_coherence: 'Genre Fit',
		track_quality: 'Track Rating',
	};

	const KEYS: (keyof ScoringWeights)[] = [
		'harmonic',
		'energy_fit',
		'bpm_compat',
		'genre_coherence',
		'track_quality',
	];

	let {
		weights = $bindable({ ...DEFAULTS }),
	}: {
		weights: ScoringWeights;
	} = $props();

	let expanded = $state(false);

	let isDefault = $derived(
		KEYS.every((k) => Math.abs(weights[k] - DEFAULTS[k]) < 0.5)
	);

	function handleSliderChange(key: keyof ScoringWeights, rawValue: number) {
		const oldValue = weights[key];
		const newValue = Math.max(0, Math.min(100, rawValue));
		const delta = newValue - oldValue;

		if (Math.abs(delta) < 0.5) return;

		// Proportional redistribution among other sliders
		const otherKeys = KEYS.filter((k) => k !== key);
		const othersSum = otherKeys.reduce((sum, k) => sum + weights[k], 0);

		const updated = { ...weights };
		updated[key] = newValue;

		if (othersSum > 0) {
			// Redistribute proportionally
			for (const k of otherKeys) {
				const ratio = weights[k] / othersSum;
				updated[k] = Math.max(0, weights[k] - delta * ratio);
			}
		} else {
			// All others are zero — distribute evenly
			const share = (100 - newValue) / otherKeys.length;
			for (const k of otherKeys) {
				updated[k] = share;
			}
		}

		// Snap to integers and fix rounding
		let total = 0;
		for (const k of KEYS) {
			updated[k] = Math.round(updated[k]);
			total += updated[k];
		}
		// Correct rounding drift on the changed slider
		if (total !== 100) {
			updated[key] += 100 - total;
		}

		weights = updated;
	}

	function resetDefaults() {
		weights = { ...DEFAULTS };
	}
</script>

<div class="scoring-weights">
	<button
		class="weights-toggle"
		type="button"
		onclick={() => { expanded = !expanded; }}
	>
		<span class="toggle-label">Scoring weights</span>
		{#if !isDefault}
			<span class="custom-badge">custom</span>
		{/if}
		<span class="toggle-arrow" class:toggle-open={expanded}>&#9662;</span>
	</button>

	{#if expanded}
		<div class="weights-body">
			{#each KEYS as key (key)}
				<div class="weight-row">
					<label class="weight-label" for="weight-{key}">{LABELS[key]}</label>
					<input
						id="weight-{key}"
						type="range"
						class="weight-slider"
						min={0}
						max={100}
						step={1}
						value={weights[key]}
						oninput={(e) => handleSliderChange(key, Number(e.currentTarget.value))}
					/>
					<span class="weight-value">{Math.round(weights[key])}%</span>
				</div>
			{/each}
			{#if !isDefault}
				<button class="reset-btn" type="button" onclick={resetDefaults}>
					Reset to defaults
				</button>
			{/if}
		</div>
	{/if}
</div>

<style>
	.scoring-weights {
		display: flex;
		flex-direction: column;
		gap: 0;
	}

	.weights-toggle {
		display: flex;
		align-items: center;
		gap: 6px;
		padding: 6px 0;
		font-size: 11px;
		font-weight: 600;
		color: var(--text-secondary);
		text-transform: uppercase;
		letter-spacing: 0.5px;
		cursor: pointer;
		background: none;
		border: none;
		text-align: left;
	}

	.weights-toggle:hover {
		color: var(--text-primary);
	}

	.toggle-arrow {
		font-size: 9px;
		transition: transform 0.15s;
		margin-left: auto;
	}

	.toggle-open {
		transform: rotate(180deg);
	}

	.custom-badge {
		font-size: 9px;
		font-weight: 500;
		text-transform: lowercase;
		letter-spacing: 0;
		color: var(--accent);
		background: rgba(0, 206, 209, 0.1);
		padding: 1px 5px;
		border-radius: 3px;
	}

	.weights-body {
		display: flex;
		flex-direction: column;
		gap: 6px;
		padding: 8px 10px;
		background: var(--bg-tertiary);
		border: 1px solid var(--border);
		border-radius: 6px;
	}

	.weight-row {
		display: flex;
		align-items: center;
		gap: 8px;
	}

	.weight-label {
		font-size: 11px;
		color: var(--text-secondary);
		width: 90px;
		flex-shrink: 0;
	}

	.weight-slider {
		flex: 1;
		height: 4px;
		accent-color: var(--accent);
		cursor: pointer;
	}

	.weight-value {
		font-size: 11px;
		font-weight: 600;
		color: var(--text-primary);
		width: 32px;
		text-align: right;
		font-variant-numeric: tabular-nums;
	}

	.reset-btn {
		align-self: flex-end;
		font-size: 10px;
		color: var(--text-dim);
		padding: 2px 8px;
		border-radius: 3px;
		background: none;
		border: none;
		cursor: pointer;
		margin-top: 2px;
		transition: color 0.1s;
	}

	.reset-btn:hover {
		color: var(--accent);
	}
</style>
