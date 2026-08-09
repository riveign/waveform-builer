<script lang="ts">
	import '../app.css';
	import NowPlayingBar from '$lib/components/player/NowPlayingBar.svelte';
	import { getPlayerStore } from '$lib/stores/player.svelte';

	let { children } = $props<{ children: import('svelte').Snippet }>();

	const player = getPlayerStore();
</script>

<!-- Transport shortcuts belong to the player, which outlives any one surface, so
     they live at the root rather than inside the workspace shell. -->
<svelte:window
	onkeydown={(e) => {
		const tag = (e.target as HTMLElement)?.tagName;
		if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return;
		if (!player.hasTrack) return;

		if (e.key === ' ') {
			e.preventDefault();
			player.togglePlay();
		} else if (e.key === 'ArrowLeft') {
			e.preventDefault();
			player.seek(Math.max(0, player.currentTime - 5));
		} else if (e.key === 'ArrowRight') {
			e.preventDefault();
			player.seek(Math.min(player.duration, player.currentTime + 5));
		}
	}}
/>

{@render children()}

<NowPlayingBar />
