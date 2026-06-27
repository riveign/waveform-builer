<script lang="ts">
	import { getTinderStore } from '$lib/stores/tinder.svelte';
	import Button from '../primitives/Button.svelte';

	const store = getTinderStore();

	let { onrestart }: { onrestart: () => void } = $props();

	function pct(n: number): string {
		if (store.sessionTotal === 0) return '0';
		return ((n / store.sessionTotal) * 100).toFixed(0);
	}
</script>

<div class="summary">
	<h2>Session complete</h2>
	<p class="subtitle">You reviewed {store.sessionTotal} tracks</p>

	<div class="stats-grid">
		<div class="stat confirmed">
			<div class="stat-num">{store.sessionConfirmed}</div>
			<div class="stat-label">Confirmed ({pct(store.sessionConfirmed)}%)</div>
		</div>
		<div class="stat overridden">
			<div class="stat-num">{store.sessionOverridden}</div>
			<div class="stat-label">Overridden ({pct(store.sessionOverridden)}%)</div>
		</div>
		<div class="stat skipped">
			<div class="stat-num">{store.sessionSkipped}</div>
			<div class="stat-label">Skipped ({pct(store.sessionSkipped)}%)</div>
		</div>
	</div>

	{#if store.retrainResult}
		<div class="retrain-result">
			<h3>Model retrained</h3>
			<p>Accuracy: {store.retrainResult.accuracy ? (store.retrainResult.accuracy * 100).toFixed(1) + '%' : 'N/A'}</p>
			<p>Training samples: {store.retrainResult.training_samples}</p>
		</div>
	{:else}
		<div class="retrain-row">
			<Button
				variant="primary"
				loading={store.retraining}
				disabled={store.retraining}
				onclick={() => store.triggerRetrain()}
			>
				{store.retraining ? 'Retraining...' : `Retrain model with ${store.sessionConfirmed + store.sessionOverridden} new approvals`}
			</Button>
		</div>
	{/if}

	<div class="restart-row">
		<Button variant="secondary" onclick={onrestart}>Review more tracks</Button>
	</div>
</div>

<style>
	/* Decision-outcome signal hues. No design-system tokens map to confirm-green /
	   override-amber (DS energy ramp is navy→lilac→magenta), so they're kept as
	   local vars to preserve the existing summary appearance. Candidates for
	   future --positive / --caution semantic tokens. */
	.summary { --tinder-confirm: #2ecc71; --tinder-override: #f39c12; max-width: 400px; margin: var(--space-4xl) auto; text-align: center; }
	h2 { font-size: var(--text-xl); color: var(--text-primary); margin: 0 0 var(--space-xs); }
	.subtitle { font-size: var(--text-md); color: var(--text-secondary); margin: 0 0 var(--space-3xl); }
	.stats-grid { display: flex; gap: var(--space-xl); justify-content: center; margin-bottom: var(--space-3xl); }
	.stat { flex: 1; padding: var(--space-lg); background: var(--bg-secondary); border-radius: var(--radius-lg); }
	.stat-num { font-size: 28px; font-weight: 700; }
	.confirmed .stat-num { color: var(--tinder-confirm); }
	.overridden .stat-num { color: var(--tinder-override); }
	.skipped .stat-num { color: var(--text-dim); }
	.stat-label { font-size: var(--text-xs); color: var(--text-dim); margin-top: var(--space-xs); }
	.retrain-row { margin-bottom: var(--space-md); }
	.retrain-row :global(.btn) { width: 100%; }
	.retrain-result { padding: var(--space-lg); background: var(--bg-secondary); border-radius: var(--radius-lg); margin-bottom: var(--space-lg); }
	.retrain-result h3 { font-size: var(--text-md); margin: 0 0 var(--space-xs); color: var(--tinder-confirm); }
	.retrain-result p { font-size: var(--text-sm); color: var(--text-secondary); margin: var(--space-2xs) 0; }
	.restart-row :global(.btn) { width: 100%; }
</style>
