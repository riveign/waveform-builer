<script lang="ts" module>
	// Set-role tags — a DJ curation axis (spec 027). Shared metadata + inline SVG
	// glyphs, drawn in currentColor so each call site controls the hue.
	export const SET_ROLES = ['opener', 'closer', 'break'] as const;
	export type SetRole = (typeof SET_ROLES)[number];

	export const ROLE_LABEL: Record<string, string> = {
		opener: 'Opener',
		closer: 'Closer',
		break: 'Break',
	};
	export const ROLE_TIP: Record<string, string> = {
		opener: 'A track you reach for to open — it sets the room, whatever its energy',
		closer: 'A track that sends people home — the last-track feeling',
		break: 'A breather mid-set — a moment to reset the room',
	};
</script>

<script lang="ts">
	let { role, label }: { role: string; label?: string } = $props();
</script>

<svg
	class="set-role-icon"
	viewBox="0 0 24 24"
	fill="none"
	stroke="currentColor"
	stroke-width="2"
	stroke-linecap="round"
	stroke-linejoin="round"
	role="img"
	aria-label={label ?? ROLE_LABEL[role] ?? role}
>
	{#if role === 'opener'}
		<!-- sunrise: the doors open -->
		<path d="M17 18a5 5 0 0 0-10 0" />
		<line x1="12" y1="2" x2="12" y2="7" />
		<line x1="4.2" y1="9.2" x2="5.6" y2="10.6" />
		<line x1="18.4" y1="10.6" x2="19.8" y2="9.2" />
		<line x1="2" y1="18" x2="22" y2="18" />
		<polyline points="8.5 6.5 12 3 15.5 6.5" />
	{:else if role === 'closer'}
		<!-- moon: the last word -->
		<path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z" />
	{:else if role === 'break'}
		<!-- pause bars: a breather -->
		<line x1="9" y1="5" x2="9" y2="19" />
		<line x1="15" y1="5" x2="15" y2="19" />
	{/if}
</svg>

<style>
	.set-role-icon {
		width: 1em;
		height: 1em;
		display: inline-block;
		flex-shrink: 0;
	}
</style>
