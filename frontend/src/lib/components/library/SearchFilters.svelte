<script lang="ts">
	import type { SearchParams } from '$lib/api/tracks';
	import { autocompleteArtists, autocompleteLabels } from '$lib/api/tracks';
	import { fetchJson } from '$lib/api/client';
	import { CAMELOT_COLORS } from '$lib/utils/camelot';
	import Typeahead from './Typeahead.svelte';

	interface GenreFamily {
		family_name: string;
		genres: string[];
		compatible_with: string[];
	}

	let { onsearch }: { onsearch: (params: SearchParams) => void } = $props();

	// ── Filter state ──
	let searchText = $state('');
	let selectedArtists = $state<string[]>([]);
	let selectedLabels = $state<string[]>([]);
	let selectedGenres = $state<Set<string>>(new Set());
	let selectedKeys = $state<Set<string>>(new Set());
	let bpmMin = $state<number | null>(null);
	let bpmMax = $state<number | null>(null);
	let energy = $state('');
	let energyZone = $state('');
	let ratingMin = $state('');
	let sortRecent = $state(false);

	// ── UI state ──
	let showAdvanced = $state(false);
	let expandedFamilies = $state<Set<string>>(new Set());

	// ── Genre families from API ──
	let genreFamilies = $state<GenreFamily[]>([]);
	let genreFamiliesLoaded = $state(false);

	async function loadGenreFamilies() {
		if (genreFamiliesLoaded) return;
		try {
			genreFamilies = await fetchJson<GenreFamily[]>('/api/config/genre-families');
			genreFamiliesLoaded = true;
		} catch {
			// Silently fail — genre chips won't show
		}
	}

	// ── Camelot key grid data ──
	const camelotKeys = Array.from({ length: 12 }, (_, i) => i + 1);

	// ── Build params from state ──
	function buildParams(): SearchParams {
		const params: SearchParams = {};
		if (searchText.trim()) {
			params.search = searchText.trim();
		}
		if (selectedArtists.length > 0) params.artist = selectedArtists;
		if (selectedLabels.length > 0) params.label = selectedLabels;
		if (selectedGenres.size > 0) params.genre = [...selectedGenres];
		if (selectedKeys.size > 0) params.key = [...selectedKeys];
		if (bpmMin !== null) params.bpm_min = bpmMin;
		if (bpmMax !== null) params.bpm_max = bpmMax;
		if (energy) params.energy = energy;
		if (energyZone) params.energy_zone = energyZone;
		if (ratingMin) params.rating_min = Number(ratingMin);
		if (sortRecent) params.sort = 'recent';
		return params;
	}

	// ── Debounced text search ──
	let textTimer: ReturnType<typeof setTimeout> | undefined;

	function onTextInput() {
		clearTimeout(textTimer);
		textTimer = setTimeout(() => {
			onsearch(buildParams());
		}, 300);
	}

	// ── Immediate search for non-text filters ──
	function searchNow() {
		clearTimeout(textTimer);
		onsearch(buildParams());
	}

	// ── Genre toggles ──
	function toggleGenre(genre: string) {
		const next = new Set(selectedGenres);
		if (next.has(genre)) next.delete(genre);
		else next.add(genre);
		selectedGenres = next;
		searchNow();
	}

	function toggleFamily(family: GenreFamily) {
		const allSelected = family.genres.every((g) => selectedGenres.has(g));
		const next = new Set(selectedGenres);
		if (allSelected) {
			family.genres.forEach((g) => next.delete(g));
		} else {
			family.genres.forEach((g) => next.add(g));
		}
		selectedGenres = next;
		searchNow();
	}

	function toggleFamilyExpand(familyName: string) {
		const next = new Set(expandedFamilies);
		if (next.has(familyName)) next.delete(familyName);
		else next.add(familyName);
		expandedFamilies = next;
	}

	// ── Key toggles ──
	function toggleKey(key: string) {
		const next = new Set(selectedKeys);
		if (next.has(key)) next.delete(key);
		else next.add(key);
		selectedKeys = next;
		searchNow();
	}

	// ── Active filter helpers ──
	let hasActiveFilters = $derived(
		selectedArtists.length > 0 ||
		selectedLabels.length > 0 ||
		selectedGenres.size > 0 ||
		selectedKeys.size > 0 ||
		(bpmMin !== null || bpmMax !== null) ||
		energy !== '' ||
		energyZone !== '' ||
		ratingMin !== '' ||
		sortRecent
	);

	function removeGenre(g: string) {
		const next = new Set(selectedGenres);
		next.delete(g);
		selectedGenres = next;
		searchNow();
	}

	function removeKey(k: string) {
		const next = new Set(selectedKeys);
		next.delete(k);
		selectedKeys = next;
		searchNow();
	}

	function clearBpm() {
		bpmMin = null;
		bpmMax = null;
		searchNow();
	}

	function clearAllFilters() {
		searchText = '';
		selectedArtists = [];
		selectedLabels = [];
		selectedGenres = new Set();
		selectedKeys = new Set();
		bpmMin = null;
		bpmMax = null;
		energy = '';
		energyZone = '';
		ratingMin = '';
		sortRecent = false;
		onsearch({});
	}

	function toggleRecent() {
		sortRecent = !sortRecent;
		searchNow();
	}

	// ── Toggle advanced + lazy load genres ──
	function toggleAdvanced() {
		showAdvanced = !showAdvanced;
		if (showAdvanced) loadGenreFamilies();
	}

	// ── Watch artist/label changes (bound from Typeahead) ──
	let prevArtistKey = $derived(JSON.stringify(selectedArtists));
	let prevLabelKey = $derived(JSON.stringify(selectedLabels));
	let lastArtistKey = '';
	let lastLabelKey = '';
	$effect(() => {
		const aKey = prevArtistKey;
		const lKey = prevLabelKey;
		if (aKey !== lastArtistKey || lKey !== lastLabelKey) {
			const isInit = lastArtistKey === '' && lastLabelKey === '';
			lastArtistKey = aKey;
			lastLabelKey = lKey;
			if (!isInit) searchNow();
		}
	});

	// ── Select change handlers ──
	function onEnergyChange() { searchNow(); }
	function onEnergyZoneChange() { searchNow(); }
	function onRatingChange() { searchNow(); }
	function onBpmChange() {
		clearTimeout(textTimer);
		textTimer = setTimeout(() => searchNow(), 300);
	}
</script>

<!-- Basic bar: search + toggle -->
<div class="filters">
	<div class="basic-row">
		<div class="search-box">
			<span class="search-icon">&#x1F50D;</span>
			<input
				type="text"
				placeholder="Search tracks..."
				class="search-input"
				bind:value={searchText}
				oninput={onTextInput}
			/>
			{#if searchText}
				<button
					class="search-clear"
					type="button"
					onclick={() => { searchText = ''; searchNow(); }}
					aria-label="Clear search"
				>&times;</button>
			{/if}
		</div>
		<button
			class="adv-toggle"
			class:adv-toggle-active={showAdvanced}
			type="button"
			onclick={toggleAdvanced}
			aria-label="Toggle advanced filters"
			title="Advanced filters"
		>
			<svg width="16" height="16" viewBox="0 0 16 16" fill="none">
				<path d="M2 4h12M4 8h8M6 12h4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
			</svg>
		</button>
	</div>

	<!-- Quick filters -->
	<div class="quick-filters">
		<button
			class="quick-btn"
			class:quick-btn-active={sortRecent}
			type="button"
			onclick={toggleRecent}
		>
			<svg width="12" height="12" viewBox="0 0 16 16" fill="none">
				<circle cx="8" cy="8" r="6" stroke="currentColor" stroke-width="1.5" fill="none"/>
				<path d="M8 4.5V8l2.5 1.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
			</svg>
			Recent
		</button>
	</div>

	<!-- Active filter chips -->
	{#if hasActiveFilters}
		<div class="active-chips">
			{#each selectedArtists as a}
				<button class="chip chip-artist" type="button" onclick={() => { selectedArtists = selectedArtists.filter(x => x !== a); }}>
					{a} <span class="chip-x">&times;</span>
				</button>
			{/each}
			{#each selectedLabels as lb}
				<button class="chip chip-label" type="button" onclick={() => { selectedLabels = selectedLabels.filter(x => x !== lb); }}>
					{lb} <span class="chip-x">&times;</span>
				</button>
			{/each}
			{#each [...selectedGenres] as g}
				<button class="chip chip-genre" type="button" onclick={() => removeGenre(g)}>
					{g} <span class="chip-x">&times;</span>
				</button>
			{/each}
			{#each [...selectedKeys] as k}
				<button class="chip chip-key" type="button" onclick={() => removeKey(k)} style="border-color: {CAMELOT_COLORS[k] ?? '#666'}">
					{k} <span class="chip-x">&times;</span>
				</button>
			{/each}
			{#if bpmMin !== null || bpmMax !== null}
				<button class="chip" type="button" onclick={clearBpm}>
					BPM {bpmMin ?? '?'}-{bpmMax ?? '?'} <span class="chip-x">&times;</span>
				</button>
			{/if}
			{#if energy}
				<button class="chip" type="button" onclick={() => { energy = ''; searchNow(); }}>
					{energy} <span class="chip-x">&times;</span>
				</button>
			{/if}
			{#if energyZone}
				<button class="chip" type="button" onclick={() => { energyZone = ''; searchNow(); }}>
					{energyZone} <span class="chip-x">&times;</span>
				</button>
			{/if}
			{#if ratingMin}
				<button class="chip" type="button" onclick={() => { ratingMin = ''; searchNow(); }}>
					{ratingMin}+ stars <span class="chip-x">&times;</span>
				</button>
			{/if}
			{#if sortRecent}
				<button class="chip" type="button" onclick={() => { sortRecent = false; searchNow(); }}>
					Recent <span class="chip-x">&times;</span>
				</button>
			{/if}
			<button class="clear-all" type="button" onclick={clearAllFilters}>Clear all</button>
		</div>
	{/if}

	<!-- Advanced panel -->
	{#if showAdvanced}
		<div class="advanced">
			<!-- Artist + Label typeaheads -->
			<div class="section typeahead-row">
				<div class="field-group typeahead-field">
					<span class="section-label">Artist</span>
					<Typeahead
						placeholder="Type to find..."
						bind:selected={selectedArtists}
						fetchSuggestions={autocompleteArtists}
					/>
				</div>
				<div class="field-group typeahead-field">
					<span class="section-label">Label</span>
					<Typeahead
						placeholder="Type to find..."
						bind:selected={selectedLabels}
						fetchSuggestions={autocompleteLabels}
					/>
				</div>
			</div>

			<!-- Genre chips -->
			<div class="section">
				<div class="section-header">
					<span class="section-label">Genre</span>
					{#if selectedGenres.size > 0}
						<button class="section-clear" type="button" onclick={() => { selectedGenres = new Set(); searchNow(); }}>Clear</button>
					{/if}
				</div>
				{#if genreFamilies.length > 0}
					<div class="genre-families">
						{#each genreFamilies as family}
							<div class="genre-family">
								<button
									class="genre-family-label"
									class:genre-family-active={family.genres.some((g) => selectedGenres.has(g))}
									type="button"
									onclick={() => toggleFamily(family)}
									ondblclick={() => toggleFamilyExpand(family.family_name)}
									title="Click to toggle all, double-click to expand"
								>
									{family.family_name}
									<span class="family-expand" class:family-expanded={expandedFamilies.has(family.family_name)}>&#9656;</span>
								</button>
								{#if expandedFamilies.has(family.family_name)}
									<div class="genre-chips">
										{#each family.genres as genre}
											<button
												class="genre-chip"
												class:genre-chip-active={selectedGenres.has(genre)}
												type="button"
												onclick={() => toggleGenre(genre)}
											>
												{genre}
											</button>
										{/each}
									</div>
								{/if}
							</div>
						{/each}
					</div>
				{:else}
					<span class="subtext">Exploring genres...</span>
				{/if}
			</div>

			<!-- Camelot key grid -->
			<div class="section">
				<div class="section-header">
					<span class="section-label">Key (Camelot)</span>
					{#if selectedKeys.size > 0}
						<button class="section-clear" type="button" onclick={() => { selectedKeys = new Set(); searchNow(); }}>Clear</button>
					{/if}
				</div>
				<div class="key-grid">
					<div class="key-row">
						{#each camelotKeys as n}
							{@const k = `${n}A`}
							<button
								class="key-cell"
								class:key-cell-active={selectedKeys.has(k)}
								type="button"
								onclick={() => toggleKey(k)}
								style="--key-color: {CAMELOT_COLORS[k]}"
							>{k}</button>
						{/each}
					</div>
					<div class="key-row">
						{#each camelotKeys as n}
							{@const k = `${n}B`}
							<button
								class="key-cell"
								class:key-cell-active={selectedKeys.has(k)}
								type="button"
								onclick={() => toggleKey(k)}
								style="--key-color: {CAMELOT_COLORS[k]}"
							>{k}</button>
						{/each}
					</div>
				</div>
			</div>

			<!-- BPM + Energy + Rating row -->
			<div class="section bottom-row">
				<div class="field-group">
					<span class="section-label">BPM</span>
					<div class="bpm-inputs">
						<input
							type="number"
							class="small-input"
							placeholder="Min"
							min={60}
							max={200}
							bind:value={bpmMin}
							oninput={onBpmChange}
						/>
						<span class="bpm-sep">&ndash;</span>
						<input
							type="number"
							class="small-input"
							placeholder="Max"
							min={60}
							max={200}
							bind:value={bpmMax}
							oninput={onBpmChange}
						/>
					</div>
				</div>
				<div class="field-group">
					<span class="section-label">Folder energy</span>
					<select class="small-select" bind:value={energy} onchange={onEnergyChange}>
						<option value="">Any</option>
						<option value="Low">Low</option>
						<option value="Warmup">Warmup</option>
						<option value="Mid">Mid</option>
						<option value="Dance">Dance</option>
						<option value="Up">Up</option>
						<option value="High">High</option>
						<option value="Peak">Peak</option>
						<option value="Fast">Fast</option>
					</select>
				</div>
				<div class="field-group">
					<span class="section-label">Zone</span>
					<select class="small-select" bind:value={energyZone} onchange={onEnergyZoneChange}>
						<option value="">Any</option>
						<option value="warmup">Warmup</option>
						<option value="build">Build</option>
						<option value="drive">Drive</option>
						<option value="peak">Peak</option>
						<option value="close">Close</option>
					</select>
				</div>
				<div class="field-group">
					<span class="section-label">Rating</span>
					<select class="small-select" bind:value={ratingMin} onchange={onRatingChange}>
						<option value="">Any</option>
						<option value="1">1+</option>
						<option value="2">2+</option>
						<option value="3">3+</option>
						<option value="4">4+</option>
						<option value="5">5</option>
					</select>
				</div>
			</div>
		</div>
	{/if}
</div>

<style>
	.filters {
		display: flex;
		flex-direction: column;
		border-bottom: 1px solid var(--border);
	}

	/* ── Basic row ── */
	.basic-row {
		display: flex;
		gap: 6px;
		padding: 8px 10px;
		align-items: center;
	}

	.search-box {
		flex: 1;
		display: flex;
		align-items: center;
		background: var(--bg-tertiary);
		border: 1px solid var(--border);
		border-radius: 6px;
		padding: 0 8px;
		gap: 6px;
	}

	.search-box:focus-within {
		border-color: var(--accent);
	}

	.search-icon {
		font-size: 12px;
		opacity: 0.5;
		flex-shrink: 0;
	}

	.search-input {
		flex: 1;
		border: none;
		background: none;
		padding: 7px 0;
		font-size: 13px;
		color: var(--text-primary);
		outline: none;
		min-width: 0;
	}

	.search-input::placeholder {
		color: var(--text-dim);
	}

	.search-clear {
		font-size: 16px;
		color: var(--text-dim);
		padding: 0 2px;
		line-height: 1;
		flex-shrink: 0;
	}

	.search-clear:hover {
		color: var(--text-primary);
	}

	.adv-toggle {
		width: 32px;
		height: 32px;
		display: flex;
		align-items: center;
		justify-content: center;
		border-radius: 6px;
		color: var(--text-secondary);
		background: var(--bg-tertiary);
		border: 1px solid var(--border);
		flex-shrink: 0;
		transition: all 0.1s;
	}

	.adv-toggle:hover {
		background: var(--bg-hover);
		color: var(--text-primary);
	}

	.adv-toggle-active {
		border-color: var(--accent);
		color: var(--accent);
	}

	/* ── Quick filters ── */
	.quick-filters {
		display: flex;
		gap: 4px;
		padding: 0 10px 6px;
	}

	.quick-btn {
		display: inline-flex;
		align-items: center;
		gap: 4px;
		font-size: 11px;
		padding: 3px 10px;
		border-radius: 12px;
		color: var(--text-secondary);
		background: var(--bg-tertiary);
		border: 1px solid var(--border);
		cursor: pointer;
		transition: all 0.1s;
	}

	.quick-btn:hover {
		border-color: var(--accent);
		color: var(--text-primary);
	}

	.quick-btn-active {
		background: var(--accent);
		border-color: var(--accent);
		color: #000;
		font-weight: 500;
	}

	.quick-btn-active:hover {
		background: var(--accent-dim);
		border-color: var(--accent-dim);
		color: #000;
	}

	/* ── Active filter chips ── */
	.active-chips {
		display: flex;
		flex-wrap: wrap;
		gap: 4px;
		padding: 0 10px 8px;
		align-items: center;
	}

	.chip {
		display: inline-flex;
		align-items: center;
		gap: 4px;
		font-size: 10px;
		padding: 2px 8px;
		border-radius: 10px;
		background: var(--bg-tertiary);
		border: 1px solid var(--border);
		color: var(--text-secondary);
		cursor: pointer;
		transition: all 0.1s;
	}

	.chip:hover {
		border-color: var(--accent-coral);
		color: var(--accent-coral);
	}

	.chip-genre {
		background: rgba(var(--accent-rgb, 0, 255, 136), 0.1);
		border-color: var(--accent);
		color: var(--accent);
	}

	.chip-artist {
		border-color: var(--accent-blue, #42a5f5);
		color: var(--accent-blue, #42a5f5);
	}

	.chip-label {
		border-color: var(--accent-coral, #ff6b6b);
		color: var(--accent-coral, #ff6b6b);
	}

	.chip-x {
		font-size: 12px;
		line-height: 1;
		opacity: 0.7;
	}

	.clear-all {
		font-size: 10px;
		color: var(--text-dim);
		padding: 2px 6px;
		margin-left: 4px;
	}

	.clear-all:hover {
		color: var(--accent-coral);
	}

	/* ── Advanced panel ── */
	.advanced {
		display: flex;
		flex-direction: column;
		gap: 10px;
		padding: 0 10px 10px;
	}

	.typeahead-row {
		flex-direction: row;
		gap: 10px;
	}

	.typeahead-field {
		flex: 1;
		min-width: 0;
	}

	.section {
		display: flex;
		flex-direction: column;
		gap: 5px;
	}

	.section-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
	}

	.section-label {
		font-size: 10px;
		font-weight: 600;
		color: var(--text-dim);
		text-transform: uppercase;
		letter-spacing: 0.5px;
	}

	.section-clear {
		font-size: 9px;
		color: var(--text-dim);
		padding: 1px 5px;
		border-radius: 3px;
	}

	.section-clear:hover {
		color: var(--accent-coral);
	}

	.subtext {
		font-size: 10px;
		color: var(--text-dim);
	}

	/* ── Genre families ── */
	.genre-families {
		display: flex;
		flex-direction: column;
		gap: 4px;
		max-height: 160px;
		overflow-y: auto;
		padding: 6px;
		background: var(--bg-tertiary);
		border: 1px solid var(--border);
		border-radius: 6px;
	}

	.genre-family {
		display: flex;
		flex-direction: column;
		gap: 3px;
	}

	.genre-family-label {
		display: flex;
		align-items: center;
		gap: 4px;
		font-size: 10px;
		font-weight: 600;
		color: var(--text-dim);
		text-transform: uppercase;
		letter-spacing: 0.3px;
		padding: 3px 6px;
		border-radius: 3px;
		text-align: left;
		transition: all 0.1s;
		cursor: pointer;
	}

	.genre-family-label:hover {
		color: var(--text-secondary);
		background: var(--bg-hover);
	}

	.genre-family-active {
		color: var(--accent);
	}

	.family-expand {
		font-size: 8px;
		transition: transform 0.15s;
	}

	.family-expanded {
		transform: rotate(90deg);
	}

	.genre-chips {
		display: flex;
		flex-wrap: wrap;
		gap: 3px;
		padding-left: 12px;
	}

	.genre-chip {
		font-size: 10px;
		padding: 2px 7px;
		border-radius: 10px;
		color: var(--text-secondary);
		background: var(--bg-secondary);
		border: 1px solid var(--border);
		transition: all 0.1s;
		cursor: pointer;
	}

	.genre-chip:hover {
		border-color: var(--accent);
		color: var(--text-primary);
	}

	.genre-chip-active {
		background: var(--accent);
		border-color: var(--accent);
		color: #000;
		font-weight: 500;
	}

	.genre-chip-active:hover {
		background: var(--accent-dim);
		border-color: var(--accent-dim);
		color: #000;
	}

	/* ── Camelot key grid ── */
	.key-grid {
		display: flex;
		flex-direction: column;
		gap: 2px;
	}

	.key-row {
		display: grid;
		grid-template-columns: repeat(12, 1fr);
		gap: 2px;
	}

	.key-cell {
		font-size: 9px;
		font-weight: 600;
		padding: 5px 0;
		text-align: center;
		border-radius: 3px;
		color: var(--text-secondary);
		background: var(--bg-tertiary);
		border: 1.5px solid transparent;
		cursor: pointer;
		transition: all 0.1s;
	}

	.key-cell:hover {
		background: color-mix(in srgb, var(--key-color) 20%, var(--bg-tertiary));
		border-color: var(--key-color);
		color: var(--text-primary);
	}

	.key-cell-active {
		background: color-mix(in srgb, var(--key-color) 30%, var(--bg-tertiary));
		border-color: var(--key-color);
		color: var(--text-primary);
		box-shadow: 0 0 4px color-mix(in srgb, var(--key-color) 40%, transparent);
	}

	/* ── Bottom row: BPM, Energy, Rating ── */
	.bottom-row {
		flex-direction: row;
		gap: 10px;
		flex-wrap: wrap;
	}

	.field-group {
		display: flex;
		flex-direction: column;
		gap: 3px;
		min-width: 0;
	}

	.field-group:first-child {
		flex: 1.2;
	}

	.field-group:not(:first-child) {
		flex: 1;
	}

	.bpm-inputs {
		display: flex;
		align-items: center;
		gap: 4px;
	}

	.bpm-sep {
		color: var(--text-dim);
		font-size: 12px;
		flex-shrink: 0;
	}

	.small-input {
		flex: 1;
		min-width: 0;
		padding: 5px 6px;
		font-size: 12px;
		background: var(--bg-tertiary);
		border: 1px solid var(--border);
		border-radius: 4px;
		color: var(--text-primary);
	}

	.small-input:focus {
		outline: none;
		border-color: var(--accent);
	}

	.small-input::placeholder {
		color: var(--text-dim);
	}

	.small-select {
		padding: 5px 6px;
		font-size: 12px;
		background: var(--bg-tertiary);
		border: 1px solid var(--border);
		border-radius: 4px;
		color: var(--text-primary);
	}

	.small-select:focus {
		outline: none;
		border-color: var(--accent);
	}
</style>
