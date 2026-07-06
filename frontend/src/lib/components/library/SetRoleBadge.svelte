<script lang="ts">
	import SetRoleIcon, { SET_ROLES, ROLE_LABEL } from './SetRoleIcon.svelte';

	let {
		roles = [],
		variant = 'full',
	}: {
		roles: string[];
		/** full: icon + label for 1 role, icon-cluster for 2–3. icononly: icon(s) in
		 *  a tone box (tighter tiers). pip: bare gold icon(s), no box (compact/table). */
		variant?: 'full' | 'icononly' | 'pip';
	} = $props();

	// Canonical order (opener, closer, break); ignore unknowns defensively.
	const shown = $derived(SET_ROLES.filter((r) => roles?.includes(r)));
	// A role is always a SINGLE element — 2–3 roles collapse to one icon cluster,
	// so the row's footprint and the card height never change with role count.
	const showLabel = $derived(variant === 'full' && shown.length === 1);
	const tip = $derived(
		shown.length === 1
			? `You marked this a great ${shown[0]}`
			: `You marked this: ${shown.join(' · ')}`,
	);
</script>

{#if shown.length}
	{#if variant === 'pip'}
		<span class="set-role-pip" title={tip} role="img" aria-label={tip}>
			{#each shown as role}<SetRoleIcon {role} />{/each}
		</span>
	{:else}
		<span
			class="set-role-badge"
			class:set-role-badge--iconsonly={!showLabel}
			title={tip}
			role="img"
			aria-label={tip}
		>
			{#each shown as role}<SetRoleIcon {role} />{/each}
			{#if showLabel}<span class="set-role-badge__label">{ROLE_LABEL[shown[0]]}</span>{/if}
		</span>
	{/if}
{/if}

<style>
	/* Reuses the Chip mode="tone" recipe: --chip-color=gold flows into the shared
	   --chip-tone-* tokens, so the badge tracks cerceta and never hardcodes hex. */
	.set-role-badge {
		--chip-color: var(--role);
		display: inline-flex;
		align-items: center;
		gap: var(--space-xs);
		flex-shrink: 0;
		box-sizing: border-box;
		height: var(--chip-height-md);
		padding: 0 var(--chip-pad-x-md);
		border: 1px solid var(--chip-tone-border);
		border-radius: var(--chip-radius);
		background: var(--chip-tone-bg);
		color: var(--chip-tone-fg);
		font-size: var(--chip-font-md);
		font-weight: var(--font-weight-medium);
		line-height: 1;
		white-space: nowrap;
	}
	.set-role-badge--iconsonly {
		gap: var(--space-2xs);
		padding: 0 var(--space-xs);
	}
	/* icons ride full-gold; the label stays the readable tone fg. */
	.set-role-badge :global(.set-role-icon) {
		width: 13px;
		height: 13px;
		color: var(--role);
	}
	.set-role-badge__label {
		color: var(--chip-tone-fg);
	}
	/* bare pip(s) for the compact icon row + dense table cell — no box. */
	.set-role-pip {
		display: inline-flex;
		align-items: center;
		gap: var(--space-2xs);
		flex-shrink: 0;
		color: var(--role);
	}
	.set-role-pip :global(.set-role-icon) {
		width: 15px;
		height: 15px;
	}
</style>
