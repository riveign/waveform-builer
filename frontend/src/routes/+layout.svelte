<script lang="ts">
	import '../app.css';
	import NowPlayingBar from '$lib/components/player/NowPlayingBar.svelte';
	import { getPlayerStore } from '$lib/stores/player.svelte';

	let { children } = $props();

	const player = getPlayerStore();
</script>

<svelte:window onkeydown={(e) => {
	// Skip if user is typing in an input/textarea/select
	const tag = (e.target as HTMLElement)?.tagName;
	if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return;

	if (e.key === ' ' && player.hasTrack) {
		e.preventDefault();
		player.togglePlay();
	} else if (e.key === 'ArrowLeft' && player.hasTrack) {
		e.preventDefault();
		player.seek(Math.max(0, player.currentTime - 5));
	} else if (e.key === 'ArrowRight' && player.hasTrack) {
		e.preventDefault();
		player.seek(Math.min(player.duration, player.currentTime + 5));
	}
}} />

<div class="app-shell">
	<header class="app-header">
		<div class="app-logo">
			<span class="app-kanji">聴</span>
			<h1 class="app-title">Kiku</h1>
		</div>
	</header>
	<div class="app-body" class:has-player={player.hasTrack}>
		{@render children()}
	</div>
</div>

<NowPlayingBar />

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

	.app-body.has-player {
		padding-bottom: 72px;
	}
</style>
