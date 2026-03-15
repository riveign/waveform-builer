<script>
	import '../app.css';
	let { children } = $props();
</script>

<div class="app-shell">
	<header class="app-header">
		<div class="app-logo">
			<span class="app-kanji">聴</span>
			<h1 class="app-title">Kiku</h1>
		</div>
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

	.app-logo {
		display: flex;
		align-items: center;
		gap: 6px;
		color: var(--accent);
	}

	.app-kanji {
		font-size: 20px;
		font-weight: 700;
		line-height: 1;
		color: var(--text-primary);
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
