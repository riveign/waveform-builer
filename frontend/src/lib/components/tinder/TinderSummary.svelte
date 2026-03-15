<script lang="ts">
	import { getTinderStore } from '$lib/stores/tinder.svelte';

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
		<button class="retrain-btn" onclick={() => store.triggerRetrain()} disabled={store.retraining}>
			{store.retraining ? 'Retraining...' : `Retrain model with ${store.sessionConfirmed + store.sessionOverridden} new approvals`}
		</button>
	{/if}

	<button class="restart-btn" onclick={onrestart}>Review more tracks</button>
</div>

<style>
	.summary { max-width: 400px; margin: 40px auto; text-align: center; }
	h2 { font-size: 20px; color: var(--text-primary); margin: 0 0 4px; }
	.subtitle { font-size: 14px; color: var(--text-secondary); margin: 0 0 24px; }
	.stats-grid { display: flex; gap: 16px; justify-content: center; margin-bottom: 24px; }
	.stat { flex: 1; padding: 12px; background: var(--bg-secondary); border-radius: 8px; }
	.stat-num { font-size: 28px; font-weight: 700; }
	.confirmed .stat-num { color: #2ecc71; }
	.overridden .stat-num { color: #f39c12; }
	.skipped .stat-num { color: var(--text-dim); }
	.stat-label { font-size: 11px; color: var(--text-dim); margin-top: 4px; }
	.retrain-btn { width: 100%; padding: 12px; background: var(--accent); color: var(--bg-primary); border-radius: 8px; font-size: 14px; font-weight: 600; cursor: pointer; margin-bottom: 8px; }
	.retrain-btn:hover { opacity: 0.9; }
	.retrain-btn:disabled { opacity: 0.5; cursor: not-allowed; }
	.retrain-result { padding: 12px; background: var(--bg-secondary); border-radius: 8px; margin-bottom: 12px; }
	.retrain-result h3 { font-size: 14px; margin: 0 0 4px; color: #2ecc71; }
	.retrain-result p { font-size: 12px; color: var(--text-secondary); margin: 2px 0; }
	.restart-btn { width: 100%; padding: 10px; background: var(--bg-secondary); color: var(--text-secondary); border-radius: 8px; font-size: 13px; cursor: pointer; }
	.restart-btn:hover { background: var(--bg-hover); }
</style>
