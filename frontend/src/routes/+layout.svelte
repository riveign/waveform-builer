<script>
	import '../app.css';
	let { children } = $props();
</script>

<div class="app-shell">
	<header class="app-header">
		<h1 class="app-title">DJ Set Builder</h1>
	</header>
	<div class="app-body">
		{@render children()}
	</div>
</div>

<style>
	.app-shell {
		display: flex;
		flex-direction: column;
		height: 100vh;
		overflow: hidden;
	}

	.app-header {
		height: var(--header-height);
		display: flex;
		align-items: center;
		padding: 0 16px;
		background: var(--bg-secondary);
		border-bottom: 1px solid var(--border);
		flex-shrink: 0;
	}

	.app-title {
		font-size: 15px;
		font-weight: 600;
		letter-spacing: 0.5px;
		color: var(--accent);
	}

	.app-body {
		flex: 1;
		overflow: hidden;
	}
</style>
