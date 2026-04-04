<script lang="ts">
	import { getSoundCloudStore } from '$lib/stores/soundcloud.svelte';

	const sc = getSoundCloudStore();
</script>

<div class="sc-connect">
	{#if sc.connected}
		<div class="sc-profile">
			{#if sc.avatarUrl}
				<img src={sc.avatarUrl} alt="" class="avatar" />
			{/if}
			<span class="sc-username">{sc.username}</span>
			<button class="disconnect-btn" onclick={() => sc.disconnect()}>Disconnect</button>
		</div>
	{:else}
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

	.disconnect-btn {
		padding: 4px 10px;
		font-size: 11px;
		background: transparent;
		color: var(--text-dim);
		border: 1px solid var(--border);
		border-radius: 4px;
		cursor: pointer;
	}

	.disconnect-btn:hover {
		border-color: #ff5050;
		color: #ff5050;
	}
</style>
