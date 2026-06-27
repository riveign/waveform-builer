<script lang="ts">
	import { getSoundCloudStore } from '$lib/stores/soundcloud.svelte';
	import Button from '$lib/components/primitives/Button.svelte';

	const sc = getSoundCloudStore();
</script>

<div class="sc-connect">
	{#if sc.connected}
		<div class="sc-profile">
			{#if sc.avatarUrl}
				<img src={sc.avatarUrl} alt="" class="avatar" />
			{/if}
			<span class="sc-username">{sc.username}</span>
			<Button variant="ghost" size="sm" onclick={() => sc.disconnect()}>Disconnect</Button>
		</div>
	{:else}
		<!-- SoundCloud-branded CTA: keeps the SC brand orange (genuine brand color,
		     not expressible via Button variants) — intentionally bespoke. -->
		<button class="connect-btn" onclick={() => sc.connect()}>
			Connect SoundCloud
		</button>
	{/if}
</div>

<style>
	.sc-connect {
		display: flex;
		align-items: center;
	}

	.sc-profile {
		display: flex;
		align-items: center;
		gap: 8px;
	}

	.avatar {
		width: 24px;
		height: 24px;
		border-radius: 50%;
	}

	.sc-username {
		font-size: 13px;
		color: var(--text-secondary);
	}

	/* SoundCloud brand orange — genuine brand identity color, deliberately not
	   tokenized onto the cerceta palette. */
	.connect-btn {
		padding: 6px 14px;
		font-size: 12px;
		font-weight: 600;
		background: #ff5500;
		color: #fff;
		border: none;
		border-radius: 6px;
		cursor: pointer;
	}

	.connect-btn:hover {
		background: #e64d00;
	}
</style>
