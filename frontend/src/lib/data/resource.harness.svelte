<script lang="ts">
	// createResource uses $effect and onDestroy, so it can only be built inside a
	// component instance. This harness exists purely to give tests one.
	let { build }: { build: () => unknown } = $props();

	// Read through a closure so Svelte doesn't warn about capturing a prop's
	// initial value — the harness is built exactly once, on purpose.
	$effect.pre(() => {});
	(() => build())();
</script>
