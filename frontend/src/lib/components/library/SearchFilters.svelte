<script lang="ts">
	import type { SearchParams } from '$lib/api/tracks';
	import { autocompleteArtists, autocompleteLabels } from '$lib/api/tracks';
	import { fetchJson } from '$lib/api/client';
	import { CAMELOT_COLORS, formatKey } from '$lib/utils/camelot';
	import Typeahead from './Typeahead.svelte';
	import Button from '../primitives/Button.svelte';
	import SegmentedControl from '../primitives/SegmentedControl.svelte';
	import Chip from '../primitives/Chip.svelte';
	import SetRoleIcon from './SetRoleIcon.svelte';

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
	let setRoles = $state<Set<string>>(new Set());
	let playsFilter = $state('');

	// One sort at a time — the list has a single order, so the controls are
	// mutually exclusive rather than four independent toggles.
	type SortMode = '' | 'recent' | 'plays' | 'plays_asc' | 'rating' | 'rating_asc' | 'bpm' | 'bpm_asc';
	let sort = $state<SortMode>('');

	const SORT_LABELS: Record<Exclude<SortMode, ''>, string> = {
		recent: 'Recent',
		plays: 'Most played',
		plays_asc: 'Least played',
		rating: 'Highest rated',
		rating_asc: 'Lowest rated',
		bpm: 'Fastest first',
		bpm_asc: 'Slowest first',
	};

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

	// ── Key grid data ──
	// The grid is always the 12x2 Camelot wheel — the toggle only changes how each
	// position is *named* (8A or Am). Selection stays in Camelot codes either way,
	// and the backend matches every spelling of a position (kiku.setbuilder.camelot).
	const camelotKeys = Array.from({ length: 12 }, (_, i) => i + 1);

	type KeyNotation = 'camelot' | 'musical';
	const NOTATION_STORAGE_KEY = 'kiku:key-notation';

	function storedNotation(): KeyNotation {
		if (typeof localStorage === 'undefined') return 'camelot';
		return localStorage.getItem(NOTATION_STORAGE_KEY) === 'musical' ? 'musical' : 'camelot';
	}

	let keyNotation = $state<KeyNotation>(storedNotation());

	function setNotation(n: KeyNotation) {
		keyNotation = n;
		if (typeof localStorage !== 'undefined') localStorage.setItem(NOTATION_STORAGE_KEY, n);
	}

	/** Label a Camelot position in the notation the DJ is reading in. */
	function keyLabel(k: string): string {
		return keyNotation === 'musical' ? formatKey(k) : k;
	}

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
		if (setRoles.size > 0) params.set_role = [...setRoles];
		if (playsFilter === 'unplayed') params.plays_max = 0;
		else if (playsFilter === 'played') params.plays_min = 1;
		if (sort) params.sort = sort;
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
		setRoles.size > 0 ||
		playsFilter !== '' ||
		sort !== ''
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
		setRoles = new Set();
		playsFilter = '';
		sort = '';
		onsearch({});
	}

	function toggleRecent() {
		sort = sort === 'recent' ? '' : 'recent';
		searchNow();
	}

	/** One button, both directions: high-to-low → low-to-high → off. */
	function cycleSort(desc: SortMode, asc: SortMode) {
		sort = sort === desc ? asc : sort === asc ? '' : desc;
		searchNow();
	}

	/** Arrow showing which way the active sort runs (nothing when it's off). */
	function sortArrow(desc: SortMode, asc: SortMode): string {
		if (sort === desc) return '▼';
		if (sort === asc) return '▲';
		return '';
	}

	function togglePlaysFilter(mode: '' | 'unplayed' | 'played') {
		playsFilter = playsFilter === mode ? '' : mode;
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
	function toggleSetRole(role: string) {
		const next = new Set(setRoles);
		if (next.has(role)) next.delete(role);
		else next.add(role);
		setRoles = next;
		searchNow();
	}
	const SET_ROLE_LABELS: Record<string, string> = { opener: 'Openers', closer: 'Closers', break: 'Break tracks' };
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
		<Button
			iconOnly
			size="sm"
			variant="secondary"
			pressed={showAdvanced}
			onclick={toggleAdvanced}
			ariaLabel="Toggle advanced filters"
			title="Advanced filters"
		>
			{#snippet icon()}
				<svg width="16" height="16" viewBox="0 0 16 16" fill="none">
					<path d="M2 4h12M4 8h8M6 12h4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
				</svg>
			{/snippet}
		</Button>
	</div>

	<!-- Quick filters -->
	<div class="quick-filters">
		<Button size="sm" variant="ghost" pressed={sort === 'recent'} onclick={toggleRecent}>
			<span class="quick-glyph" aria-hidden="true">
				<svg width="12" height="12" viewBox="0 0 16 16" fill="none">
					<circle cx="8" cy="8" r="6" stroke="currentColor" stroke-width="1.5" fill="none"/>
					<path d="M8 4.5V8l2.5 1.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
				</svg>
			</span>
			Recent
		</Button>
		<Button
			size="sm"
			variant="ghost"
			pressed={sort === 'plays' || sort === 'plays_asc'}
			onclick={() => cycleSort('plays', 'plays_asc')}
			title="Click to cycle: Most played → Least played → Off"
		>
			<span class="quick-glyph" aria-hidden="true">{sortArrow('plays', 'plays_asc') || '♫'}</span>
			Plays
		</Button>
		<Button
			size="sm"
			variant="ghost"
			pressed={sort === 'rating' || sort === 'rating_asc'}
			onclick={() => cycleSort('rating', 'rating_asc')}
			title="Click to cycle: Highest rated → Lowest rated → Off"
		>
			<span class="quick-glyph" aria-hidden="true">{sortArrow('rating', 'rating_asc') || '★'}</span>
			Rating
		</Button>
		<Button
			size="sm"
			variant="ghost"
			pressed={sort === 'bpm' || sort === 'bpm_asc'}
			onclick={() => cycleSort('bpm', 'bpm_asc')}
			title="Click to cycle: Fastest → Slowest → Off"
		>
			<span class="quick-glyph" aria-hidden="true">{sortArrow('bpm', 'bpm_asc') || '♩'}</span>
			BPM
		</Button>
		<Button size="sm" variant="ghost" pressed={playsFilter === 'unplayed'} onclick={() => togglePlaysFilter('unplayed')}>
			Unplayed
		</Button>
		<Button size="sm" variant="ghost" pressed={playsFilter === 'played'} onclick={() => togglePlaysFilter('played')}>
			Played
		</Button>
	</div>

	<!-- Active filter chips -->
	{#if hasActiveFilters}
		<div class="active-chips">
			{#each selectedArtists as a}
				<Chip
					value={a}
					size="sm"
					title="Artist: {a}"
					removable
					removeLabel="Remove artist {a}"
					onremove={() => { selectedArtists = selectedArtists.filter(x => x !== a); }}
				/>
			{/each}
			{#each selectedLabels as lb}
				<Chip
					value={lb}
					size="sm"
					title="Label: {lb}"
					removable
					removeLabel="Remove label {lb}"
					onremove={() => { selectedLabels = selectedLabels.filter(x => x !== lb); }}
				/>
			{/each}
			{#each [...selectedGenres] as g}
				<Chip
					variant="genre"
					value={g}
					size="sm"
					title="Genre: {g}"
					removable
					removeLabel="Remove genre {g}"
					onremove={() => removeGenre(g)}
				/>
			{/each}
			{#each [...selectedKeys] as k}
				<Chip
					variant="key"
					value={keyLabel(k)}
					color={CAMELOT_COLORS[k]}
					size="sm"
					title="Key {k} · {formatKey(k)}"
					removable
					removeLabel="Remove key {keyLabel(k)}"
					onremove={() => removeKey(k)}
				/>
			{/each}
			{#if bpmMin !== null || bpmMax !== null}
				<Chip
					value="BPM {bpmMin ?? '?'}-{bpmMax ?? '?'}"
					size="sm"
					removable
					removeLabel="Clear BPM filter"
					onremove={clearBpm}
				/>
			{/if}
			{#if energy}
				<Chip value={energy} size="sm" removable removeLabel="Clear folder energy filter" onremove={() => { energy = ''; searchNow(); }} />
			{/if}
			{#if energyZone}
				<Chip value={energyZone} size="sm" removable removeLabel="Clear zone filter" onremove={() => { energyZone = ''; searchNow(); }} />
			{/if}
			{#if ratingMin}
				<Chip value="{ratingMin}+ stars" size="sm" removable removeLabel="Clear rating filter" onremove={() => { ratingMin = ''; searchNow(); }} />
			{/if}
			{#each [...setRoles] as role (role)}
				<Chip value={SET_ROLE_LABELS[role]} size="sm" removable removeLabel="Clear {SET_ROLE_LABELS[role]} filter" onremove={() => toggleSetRole(role)} />
			{/each}
			{#if playsFilter}
				<Chip
					value={playsFilter === 'unplayed' ? 'Unplayed' : 'Played'}
					size="sm"
					removable
					removeLabel="Clear plays filter"
					onremove={() => { playsFilter = ''; searchNow(); }}
				/>
			{/if}
			{#if sort}
				<Chip
					value={SORT_LABELS[sort]}
					size="sm"
					removable
					removeLabel="Clear {SORT_LABELS[sort]} sort"
					onremove={() => { sort = ''; searchNow(); }}
				/>
			{/if}
			<Button variant="ghost" size="sm" onclick={clearAllFilters}>Clear all</Button>
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
						<Button variant="ghost" size="sm" onclick={() => { selectedGenres = new Set(); searchNow(); }}>Clear</Button>
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

			<!-- Key grid — same wheel, your choice of notation -->
			<div class="section">
				<div class="section-header">
					<span class="section-label">Key</span>
					<div class="key-header-actions">
						<SegmentedControl
							dense
							ariaLabel="Key notation"
							value={keyNotation}
							onchange={setNotation}
							options={[
								{ value: 'camelot', label: 'Camelot' },
								{ value: 'musical', label: 'Keys' },
							]}
						/>
						{#if selectedKeys.size > 0}
							<Button variant="ghost" size="sm" onclick={() => { selectedKeys = new Set(); searchNow(); }}>Clear</Button>
						{/if}
					</div>
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
								title="{k} · {formatKey(k)}"
							>{keyLabel(k)}</button>
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
								title="{k} · {formatKey(k)}"
							>{keyLabel(k)}</button>
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
						<option value="intro">Intro</option>
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
				<div class="field-group field-group--role">
					<span class="section-label">Set role</span>
					<div class="role-toggles">
						<button type="button" class="role-toggle" class:on={setRoles.has('opener')} onclick={() => toggleSetRole('opener')} title="Tracks you'd open a set with"><SetRoleIcon role="opener" /> Openers</button>
						<button type="button" class="role-toggle" class:on={setRoles.has('closer')} onclick={() => toggleSetRole('closer')} title="Tracks that send people home"><SetRoleIcon role="closer" /> Closers</button>
						<button type="button" class="role-toggle" class:on={setRoles.has('break')} onclick={() => toggleSetRole('break')} title="Breather tracks for mid-set"><SetRoleIcon role="break" /> Break tracks</button>
					</div>
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

	/* ── Basic row (toolbar band) ── */
	/* The sidebar's first band. Fixed to --band-toolbar-h (48px) so its bottom divider
	   lands at the SAME y as the navbar bottom AND the Set view's "Choose a set…"
	   selector — the shared baseline that aligns the panes (spec 023 band rhythm). */
	.basic-row {
		display: flex;
		gap: var(--space-sm);
		padding: 0 var(--space-lg);
		height: var(--band-toolbar-h);
		align-items: center;
		border-bottom: 1px solid var(--border);
	}

	.search-box {
		flex: 1;
		display: flex;
		align-items: center;
		background: var(--bg-tertiary);
		border: 1px solid var(--border);
		border-radius: 6px;
		padding: 0 var(--space-md);
		gap: var(--space-sm);
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
		padding: var(--space-sm) 0;
		font-size: var(--text-base);
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

	/* ── Quick filters (secondary band) ── */
	/* The sidebar's second band (Recent/Plays/Unplayed/Played). Fixed to
	   --band-secondary-h (44px) + border-bottom so its divider lands at the SAME y
	   as the Set view's set name/actions row — second shared baseline. */
	.quick-filters {
		display: flex;
		gap: var(--space-xs);
		padding: 0 var(--space-lg);
		height: var(--band-secondary-h);
		align-items: center;
		border-bottom: 1px solid var(--border);
		/* Six controls outgrow a narrow sidebar — scroll them rather than squeeze
		   the labels, keeping the band on its shared 44px baseline (spec 023). */
		overflow-x: auto;
		overflow-y: hidden;
		scrollbar-width: none;
	}

	.quick-filters::-webkit-scrollbar {
		display: none;
	}

	.quick-filters > :global(*) {
		flex-shrink: 0;
	}

	/* Leading glyph inside a quick-filter Button label. */
	.quick-glyph {
		display: inline-flex;
		align-items: center;
		margin-right: var(--space-xs);
	}

	/* ── Active filter chips (Chip primitives) ── */
	.active-chips {
		display: flex;
		flex-wrap: wrap;
		gap: var(--space-xs);
		padding: 0 var(--space-lg) var(--space-md);
		align-items: center;
	}

	/* ── Advanced panel ── */
	.advanced {
		display: flex;
		flex-direction: column;
		gap: var(--space-lg);
		padding: 0 var(--space-lg) var(--space-lg);
	}

	.typeahead-row {
		flex-direction: row;
		gap: var(--space-lg);
	}

	.typeahead-field {
		flex: 1;
		min-width: 0;
	}

	.section {
		display: flex;
		flex-direction: column;
		gap: var(--space-sm);
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
		color: var(--on-accent);
		font-weight: 500;
	}

	.genre-chip-active:hover {
		background: var(--accent-dim);
		border-color: var(--accent-dim);
		color: var(--on-accent);
	}

	/* ── Key grid ── */
	.key-header-actions {
		display: flex;
		align-items: center;
		gap: var(--space-xs);
	}

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
		gap: var(--space-lg);
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
		gap: var(--space-xs);
	}

	.bpm-sep {
		color: var(--text-dim);
		font-size: 12px;
		flex-shrink: 0;
	}

	.small-input {
		flex: 1;
		min-width: 0;
		padding: var(--space-sm);
		font-size: var(--text-sm);
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
		padding: var(--space-sm);
		font-size: var(--text-sm);
		background: var(--bg-tertiary);
		border: 1px solid var(--border);
		border-radius: 4px;
		color: var(--text-primary);
	}

	.small-select:focus {
		outline: none;
		border-color: var(--accent);
	}
	.role-toggles {
		display: flex;
		gap: var(--space-xs);
		flex-wrap: wrap;
	}
	.role-toggle {
		display: inline-flex;
		align-items: center;
		gap: var(--space-2xs);
		height: 28px;
		padding: 0 var(--space-md);
		background: var(--surface-3);
		border: 1px solid transparent;
		border-radius: var(--radius-full, 999px);
		color: var(--text-3);
		font: inherit;
		font-size: var(--text-xs);
		font-weight: var(--font-weight-medium);
		cursor: pointer;
	}
	.role-toggle :global(.set-role-icon) {
		width: 13px;
		height: 13px;
	}
	.role-toggle:hover {
		color: var(--text-1);
		border-color: var(--role);
	}
	.role-toggle.on {
		--chip-color: var(--role);
		background: var(--chip-tone-bg);
		color: var(--chip-tone-fg);
		border-color: var(--role);
	}
	.role-toggle.on :global(.set-role-icon) {
		color: var(--role);
	}
</style>
