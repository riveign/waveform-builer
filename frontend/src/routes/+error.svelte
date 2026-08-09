<script lang="ts">
	import { page } from '$app/state';
</script>

<div class="error-page">
	<span class="kanji">聴</span>
	<h1>{page.status === 404 ? 'Nothing here' : 'Something went wrong'}</h1>
	<p>{page.error?.message ?? 'That page could not be loaded.'}</p>
	<a href="/track">Back to your library</a>
</div>

<style>
	.error-page {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		gap: var(--space-md);
		height: 100vh;
		padding: var(--space-3xl);
		text-align: center;
		background: var(--bg-primary);
		color: var(--text-primary);
	}

	.kanji {
		font-size: var(--text-3xl);
		color: var(--accent);
		line-height: 1;
	}

	h1 {
		font-size: var(--text-xl);
		font-weight: var(--font-weight-semibold);
	}

	p {
		color: var(--text-dim);
		max-width: 42ch;
	}

	a {
		color: var(--accent);
	}
</style>
