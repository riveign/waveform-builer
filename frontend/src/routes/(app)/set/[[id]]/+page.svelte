<script lang="ts">
	import { page } from '$app/state';
	import SetView, { type SetViewMode } from '$lib/components/set/SetView.svelte';
	import { numParam } from '$lib/nav';

	const VIEW_MODES: SetViewMode[] = ['list', 'compact', 'grid', 'ledger', 'spine', 'inspector'];

	const setId = $derived(page.params.id ? Number(page.params.id) : null);
	/** Which track inside the set is focused — a selection, so it rides in ?t. */
	const focusedTrackId = $derived(numParam(page.url, 't'));
	const viewMode = $derived.by(() => {
		const v = page.url.searchParams.get('view') as SetViewMode | null;
		return v && VIEW_MODES.includes(v) ? v : 'list';
	});
</script>

<SetView {setId} {focusedTrackId} {viewMode} />
