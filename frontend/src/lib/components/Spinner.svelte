<script lang="ts">
	let { size = 20, label = '' }: { size?: number; label?: string } = $props();
</script>

<div class="spinner-wrap">
	<div class="spinner" style="width: {size}px; height: {size}px; border-width: {Math.max(2, size / 10)}px;"></div>
	{#if label}
		<span class="spinner-label">{label}</span>
	{/if}
</div>

<style>
	.spinner-wrap {
		display: flex;
		align-items: center;
		gap: 10px;
		justify-content: center;
		padding: 12px 0;
	}

	.spinner {
		border-style: solid;
		border-color: var(--border);
		border-top-color: var(--accent);
		border-radius: 50%;
		animation: spin 0.8s linear infinite;
	}

	@keyframes spin {
		to { transform: rotate(360deg); }
	}

	.spinner-label {
		font-size: 12px;
		color: var(--text-dim);
	}
</style>
