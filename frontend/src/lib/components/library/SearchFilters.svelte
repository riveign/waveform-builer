<script lang="ts">
	import type { SearchParams } from '$lib/api/tracks';

	let { onsearch }: { onsearch: (params: SearchParams) => void } = $props();

	let title = $state('');
	let artist = $state('');
	let genre = $state('');
	let key = $state('');
	let bpmRange = $state('');
	let energy = $state('');
	let energyZone = $state('');
	let ratingMin = $state('');

	function handleSubmit(e: Event) {
		e.preventDefault();
		const params: SearchParams = {};
		if (title) params.title = title;
		if (artist) params.artist = artist;
		if (genre) params.genre = genre;
		if (key) params.key = key;
		if (energy) params.energy = energy;
		if (energyZone) params.energy_zone = energyZone;
		if (ratingMin) params.rating_min = Number(ratingMin);
		if (bpmRange) {
			const parts = bpmRange.split('-');
			if (parts.length === 2) {
				params.bpm_min = Number(parts[0]);
				params.bpm_max = Number(parts[1]);
			} else {
				params.bpm_min = Number(bpmRange);
				params.bpm_max = Number(bpmRange);
			}
		}
		onsearch(params);
	}

	function handleClear() {
		title = '';
		artist = '';
		genre = '';
		key = '';
		bpmRange = '';
		energy = '';
		energyZone = '';
		ratingMin = '';
		onsearch({});
	}
</script>

<form class="filters" onsubmit={handleSubmit}>
	<div class="filter-row">
		<input type="text" placeholder="Title" bind:value={title} class="filter-input wide" />
		<input type="text" placeholder="Artist" bind:value={artist} class="filter-input wide" />
	</div>
	<div class="filter-row">
		<input type="text" placeholder="Genre" bind:value={genre} class="filter-input" />
		<input type="text" placeholder="Key" bind:value={key} class="filter-input narrow" />
		<input type="text" placeholder="BPM (e.g. 124-130)" bind:value={bpmRange} class="filter-input" />
	</div>
	<div class="filter-row">
		<select bind:value={energy} class="filter-input">
			<option value="">Folder energy...</option>
			<option value="Low">Low</option>
			<option value="Warmup">Warmup</option>
			<option value="Mid">Mid</option>
			<option value="Dance">Dance</option>
			<option value="Up">Up</option>
			<option value="High">High</option>
			<option value="Peak">Peak</option>
			<option value="Fast">Fast</option>
		</select>
		<select bind:value={energyZone} class="filter-input">
			<option value="">Energy zone...</option>
			<option value="warmup">Warmup</option>
			<option value="build">Build</option>
			<option value="drive">Drive</option>
			<option value="peak">Peak</option>
			<option value="close">Close</option>
		</select>
		<select bind:value={ratingMin} class="filter-input narrow">
			<option value="">Rating...</option>
			<option value="1">1+</option>
			<option value="2">2+</option>
			<option value="3">3+</option>
			<option value="4">4+</option>
			<option value="5">5</option>
		</select>
		<button type="submit" class="btn btn-search">Search</button>
		<button type="button" class="btn btn-clear" onclick={handleClear}>Clear</button>
	</div>
</form>

<style>
	.filters {
		padding: 10px;
		display: flex;
		flex-direction: column;
		gap: 6px;
		border-bottom: 1px solid var(--border);
	}

	.filter-row {
		display: flex;
		gap: 6px;
	}

	.filter-input {
		flex: 1;
		min-width: 0;
	}

	.filter-input.wide {
		flex: 2;
	}

	.filter-input.narrow {
		flex: 0.6;
	}

	.btn {
		padding: 6px 14px;
		border-radius: 4px;
		font-size: 13px;
		font-weight: 500;
	}

	.btn-search {
		background: var(--accent);
		color: #000;
	}

	.btn-search:hover {
		background: var(--accent-dim);
	}

	.btn-clear {
		color: var(--text-secondary);
	}

	.btn-clear:hover {
		color: var(--text-primary);
	}
</style>
