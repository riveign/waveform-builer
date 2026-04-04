<script lang="ts">
	import { getTrackArtworkUrl } from '$lib/api/tracks';

	let { trackId }: { trackId: number } = $props();

	let failed = $state(false);

	$effect(() => {
		// Reset on track change
		trackId;
		failed = false;
	});
</script>

{#if !failed}
	<img
		src={getTrackArtworkUrl(trackId)}
		alt="Album artwork"
		class="artwork"
		onerror={() => { failed = true; }}
	/>
{:else}
	<div class="artwork placeholder" aria-label="No artwork">
		<svg viewBox="0 0 80 80" fill="none" xmlns="http://www.w3.org/2000/svg">
			<circle cx="32" cy="40" r="18" stroke="var(--text-dim)" stroke-width="1.5" opacity="0.4" />
			<circle cx="48" cy="40" r="18" stroke="var(--text-dim)" stroke-width="1.5" opacity="0.4" />
		</svg>
	</div>
{/if}

<style>
	.artwork {
		width: 80px;
		height: 80px;
		border-radius: 6px;
		object-fit: cover;
		flex-shrink: 0;
	}

	.placeholder {
		background: var(--bg-tertiary);
		display: flex;
		align-items: center;
		justify-content: center;
	}

	.placeholder svg {
		width: 48px;
		height: 48px;
	}
</style>
