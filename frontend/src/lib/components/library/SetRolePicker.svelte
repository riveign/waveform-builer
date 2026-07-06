<script lang="ts">
	import MenuItem from '$lib/components/primitives/MenuItem.svelte';
	import SetRoleIcon, { SET_ROLES, ROLE_LABEL, ROLE_TIP } from './SetRoleIcon.svelte';

	let {
		current = [],
		ontoggle,
	}: {
		current: string[];
		ontoggle: (role: string) => void;
	} = $props();
</script>

<div class="role-picker" role="menu" aria-label="Set role">
	<p class="role-hint">Mark where this track earns its place. Pick as many as fit.</p>
	{#each SET_ROLES as role}
		{@const on = current.includes(role)}
		<MenuItem onselect={() => ontoggle(role)}>
			{#snippet icon()}
				<span class="role-glyph" class:on><SetRoleIcon {role} label={ROLE_LABEL[role]} /></span>
			{/snippet}
			<span class="role-row" class:on title={ROLE_TIP[role]}>
				<span class="role-name">{ROLE_LABEL[role]}</span>
				{#if on}<span class="role-check" aria-hidden="true">✓</span>{/if}
			</span>
		</MenuItem>
	{/each}
</div>

<style>
	.role-picker {
		display: flex;
		flex-direction: column;
		gap: var(--space-2xs);
	}
	.role-hint {
		margin: 0;
		padding: var(--space-2xs) var(--space-sm) var(--space-xs);
		max-width: 220px;
		font-size: var(--text-xs);
		color: var(--text-3);
		line-height: 1.35;
	}
	.role-glyph {
		display: inline-flex;
		font-size: 15px;
		color: var(--text-3);
	}
	.role-glyph.on {
		color: var(--role);
	}
	.role-row {
		display: inline-flex;
		align-items: center;
		gap: var(--space-sm);
		width: 100%;
	}
	.role-row.on {
		color: var(--role);
	}
	.role-name {
		flex: 1;
	}
	.role-check {
		flex-shrink: 0;
		font-size: var(--text-sm);
		color: var(--role);
	}
</style>
