<script lang="ts">
	import { page } from '$app/state';
	import SetView from '$lib/components/set/SetView.svelte';
	import { numParam } from '$lib/nav';

	const setId = $derived(page.params.id ? Number(page.params.id) : null);
	/** Which track inside the set is focused — a selection, so it rides in ?t. */
	const focusedTrackId = $derived(numParam(page.url, 't'));
	const viewMode = $derived(page.url.searchParams.get('view') === 'grid' ? 'grid' : 'list');
</script>

<SetView {setId} {focusedTrackId} {viewMode} />
