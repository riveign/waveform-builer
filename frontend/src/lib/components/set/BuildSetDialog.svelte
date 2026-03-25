<script lang="ts">
	import type { SetBuildParams, ScoringWeights } from '$lib/types';
	import { getUiStore } from '$lib/stores/ui.svelte';
	import { fetchJson } from '$lib/api/client';
	import EnergyPresetPicker from './EnergyPresetPicker.svelte';
	import ScoringWeightsSliders from './ScoringWeights.svelte';
	import DiscoveryDensitySlider from './DiscoveryDensitySlider.svelte';

	interface GenreFamily {
		family_name: string;
		genres: string[];
		compatible_with: string[];
	}

	let {
		open = $bindable(false),
		onbuild,
	}: {
		open: boolean;
		onbuild?: (params: SetBuildParams) => void;
	} = $props();

	const ui = getUiStore();

	// ── Genre families from API ──
	let genreFamilies = $state<GenreFamily[]>([]);
	let genreFamiliesLoaded = $state(false);

	async function loadGenreFamilies() {
		if (genreFamiliesLoaded) return;
		try {
			genreFamilies = await fetchJson<GenreFamily[]>('/api/config/genre-families');
			genreFamiliesLoaded = true;
		} catch {
			// Fall back to empty — text input still works
		}
	}

	// ── Default scoring weights ──
	const DEFAULT_WEIGHTS: ScoringWeights = {
		harmonic: 25,
		energy_fit: 20,
		bpm_compat: 20,
		genre_coherence: 15,
		track_quality: 20,
	};

	// ── Form state ──
	let name = $state('');
	let durationMin = $state(60);
	let energyPreset = $state('journey');
	let selectedGenres = $state<Set<string>>(new Set());
	let bpmMin = $state<number | null>(null);
	let bpmMax = $state<number | null>(null);
	let useSeedTrack = $state(true);
	let beamWidth = $state(5);
	let scoringWeights = $state<ScoringWeights>({ ...DEFAULT_WEIGHTS });
	let discoveryDensity = $state(0);

	// ── Dialog element ref ──
	let dialogEl = $state<HTMLDialogElement | null>(null);

	// ── Sync dialog open/close with `open` prop ──
	$effect(() => {
		if (!dialogEl) return;
		if (open && !dialogEl.open) {
			resetForm();
			loadGenreFamilies();
			dialogEl.showModal();
		} else if (!open && dialogEl.open) {
			dialogEl.close();
		}
	});

	// ── Derived: seed track from library selection ──
	let seedTrack = $derived(useSeedTrack ? ui.selectedTrack : null);

	// ── Derived: form validity ──
	// Name is always valid — empty name gets a default on submit
	let bpmValid = $derived(
		(bpmMin === null && bpmMax === null) ||
		(bpmMin !== null && bpmMax !== null && bpmMin <= bpmMax) ||
		(bpmMin !== null && bpmMax === null) ||
		(bpmMin === null && bpmMax !== null)
	);
	let canSubmit = $derived(bpmValid);

	function toggleGenre(genre: string) {
		const next = new Set(selectedGenres);
		if (next.has(genre)) {
			next.delete(genre);
		} else {
			next.add(genre);
		}
		selectedGenres = next;
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
	}

	function resetForm() {
		name = '';
		durationMin = 60;
		energyPreset = 'journey';
		selectedGenres = new Set();
		bpmMin = null;
		bpmMax = null;
		useSeedTrack = true;
		beamWidth = 5;
		scoringWeights = { ...DEFAULT_WEIGHTS };
		discoveryDensity = 0;
	}

	function handleSubmit() {
		if (!canSubmit) return;

		// Swap BPM if min > max
		if (bpmMin !== null && bpmMax !== null && bpmMin > bpmMax) {
			[bpmMin, bpmMax] = [bpmMax, bpmMin];
		}

		// Clamp duration to valid range
		if (durationMin < 15) durationMin = 15;
		if (durationMin > 240) durationMin = 240;

		const finalName = name.trim() || `Set ${new Date().toLocaleDateString()}`;

		const params: SetBuildParams = {
			name: finalName,
			duration_min: durationMin,
			energy_preset: energyPreset,
			beam_width: beamWidth,
			weights: {
				harmonic: scoringWeights.harmonic / 100,
				energy_fit: scoringWeights.energy_fit / 100,
				bpm_compat: scoringWeights.bpm_compat / 100,
				genre_coherence: scoringWeights.genre_coherence / 100,
				track_quality: scoringWeights.track_quality / 100,
			},
		};
		params.discovery_density = discoveryDensity / 100;

		// Genre filter from selected chips
		if (selectedGenres.size > 0) {
			params.genre_filter = [...selectedGenres];
		}

		// BPM range
		if (bpmMin !== null) params.bpm_min = bpmMin;
		if (bpmMax !== null) params.bpm_max = bpmMax;

		// Seed track
		if (seedTrack) {
			params.seed_track_id = seedTrack.id;
		}

		onbuild?.(params);
		open = false;
	}

	function handleCancel() {
		open = false;
	}

	function handleBackdropClick(e: MouseEvent) {
		// Close if clicking the backdrop (the dialog element itself), not the content
		if (e.target === dialogEl) {
			open = false;
		}
	}

	function handleDialogClose() {
		open = false;
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Enter' && canSubmit && !e.shiftKey) {
			e.preventDefault();
			handleSubmit();
		}
	}
</script>

<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
<dialog
	bind:this={dialogEl}
	class="build-dialog"
	onclick={handleBackdropClick}
	onclose={handleDialogClose}
	onkeydown={handleKeydown}
>
	<!-- svelte-ignore a11y_no_static_element_interactions -->
	<!-- svelte-ignore a11y_click_events_have_key_events -->
	<div class="dialog-card" onclick={(e) => e.stopPropagation()}>
		<div class="dialog-header">
			<h2 class="dialog-title">Build a Set</h2>
			<button class="close-btn" onclick={handleCancel} type="button" aria-label="Close dialog">&times;</button>
		</div>

		<div class="dialog-body">
			<!-- Set Name -->
			<div class="field">
				<label class="field-label" for="set-name">Name</label>
				<input
					id="set-name"
					type="text"
					class="field-input"
					placeholder="Name your set..."
					bind:value={name}
				/>
				{#if !name.trim()}
					<span class="field-subtext">Leave blank for an auto-generated name</span>
				{/if}
			</div>

			<!-- Duration + Exploration Depth side by side -->
			<div class="field-row">
				<div class="field field-half">
					<label class="field-label" for="set-duration">Duration (minutes)</label>
					<input
						id="set-duration"
						type="number"
						class="field-input"
						min={15}
						max={240}
						step={15}
						bind:value={durationMin}
					/>
				</div>
				<div class="field field-half">
					<label class="field-label" for="beam-width">
						Exploration depth
						<span class="field-hint" title="Higher = more options explored, slower build">
							({beamWidth})
						</span>
					</label>
					<input
						id="beam-width"
						type="range"
						class="field-slider"
						min={1}
						max={10}
						step={1}
						bind:value={beamWidth}
					/>
					<div class="slider-range">
						<span>Faster</span>
						<span>Deeper</span>
					</div>
				</div>
			</div>

			<!-- Energy Preset -->
			<div class="field">
				<span class="field-label">Energy arc</span>
				<EnergyPresetPicker bind:value={energyPreset} />
			</div>

			<!-- Discovery / Density -->
			<div class="field">
				<DiscoveryDensitySlider bind:value={discoveryDensity} />
			</div>

			<!-- Genre Filter -->
			<div class="field">
				<div class="genre-header">
					<span class="field-label">Genre filter</span>
					{#if selectedGenres.size > 0}
						<button
							class="genre-clear-btn"
							type="button"
							onclick={() => { selectedGenres = new Set(); }}
						>
							Clear
						</button>
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
								>
									{family.family_name}
								</button>
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
							</div>
						{/each}
					</div>
				{:else}
					<span class="field-subtext">Loading genres...</span>
				{/if}
				{#if selectedGenres.size > 0}
					<span class="field-subtext">{selectedGenres.size} genre{selectedGenres.size > 1 ? 's' : ''} selected</span>
				{:else}
					<span class="field-subtext">No filter — all genres included</span>
				{/if}
			</div>

			<!-- BPM Range -->
			<div class="field">
				<span class="field-label">BPM range</span>
				<div class="bpm-row">
					<input
						type="number"
						class="field-input bpm-input"
						placeholder="Min"
						aria-label="Minimum BPM"
						min={60}
						max={200}
						step={1}
						bind:value={bpmMin}
					/>
					<span class="bpm-separator">&ndash;</span>
					<input
						type="number"
						class="field-input bpm-input"
						placeholder="Max"
						aria-label="Maximum BPM"
						min={60}
						max={200}
						step={1}
						bind:value={bpmMax}
					/>
				</div>
				{#if !bpmValid}
					<span class="field-error">Min BPM must be less than max</span>
				{/if}
			</div>

			<!-- Scoring Weights -->
			<ScoringWeightsSliders bind:weights={scoringWeights} />

			<!-- Seed Track -->
			<div class="field">
				<span class="field-label">Starting track</span>
				{#if seedTrack && useSeedTrack}
					<div class="seed-track">
						<span class="seed-track-info">
							{seedTrack.title ?? 'Untitled'} &mdash; {seedTrack.artist ?? 'Unknown'}
						</span>
						<button
							class="seed-clear-btn"
							onclick={() => { useSeedTrack = false; }}
							type="button"
							aria-label="Remove seed track"
						>
							&times;
						</button>
					</div>
				{:else}
					<div class="seed-empty">
						{#if ui.selectedTrack && !useSeedTrack}
							<span class="seed-empty-text">No starting track</span>
							<button
								class="seed-restore-btn"
								onclick={() => { useSeedTrack = true; }}
								type="button"
							>
								Use selected
							</button>
						{:else}
							<span class="seed-empty-text">Random start — select a track in the library to use as seed</span>
						{/if}
					</div>
				{/if}
			</div>
		</div>

		<div class="dialog-footer">
			<button class="btn-cancel" onclick={handleCancel} type="button">Cancel</button>
			<button
				class="btn-build"
				onclick={handleSubmit}
				disabled={!canSubmit}
				type="button"
			>
				Build Set
			</button>
		</div>
	</div>
</dialog>

<style>
	/* ── Dialog backdrop + container ── */
	.build-dialog {
		border: none;
		background: transparent;
		padding: 0;
		max-width: 100vw;
		max-height: 100vh;
		width: 100vw;
		height: 100vh;
		overflow: visible;
	}

	.build-dialog::backdrop {
		background: rgba(0, 0, 0, 0.6);
	}

	/* ── Card ── */
	.dialog-card {
		position: fixed;
		top: 50%;
		left: 50%;
		transform: translate(-50%, -50%);
		width: 520px;
		max-width: calc(100vw - 32px);
		max-height: calc(100vh - 64px);
		background: var(--bg-secondary);
		border: 1px solid var(--border);
		border-radius: 8px;
		display: flex;
		flex-direction: column;
		overflow: hidden;
		animation: dialog-in 0.15s ease-out;
	}

	@keyframes dialog-in {
		from {
			opacity: 0;
			transform: translate(-50%, -48%);
		}
		to {
			opacity: 1;
			transform: translate(-50%, -50%);
		}
	}

	/* ── Header ── */
	.dialog-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 16px 20px 12px;
		border-bottom: 1px solid var(--border);
	}

	.dialog-title {
		font-size: 16px;
		font-weight: 600;
		color: var(--text-primary);
		margin: 0;
	}

	.close-btn {
		width: 28px;
		height: 28px;
		display: flex;
		align-items: center;
		justify-content: center;
		font-size: 18px;
		color: var(--text-secondary);
		border-radius: 4px;
		transition: background 0.1s, color 0.1s;
	}

	.close-btn:hover {
		background: var(--bg-hover);
		color: var(--text-primary);
	}

	/* ── Body ── */
	.dialog-body {
		padding: 16px 20px;
		overflow-y: auto;
		display: flex;
		flex-direction: column;
		gap: 16px;
	}

	/* ── Fields ── */
	.field {
		display: flex;
		flex-direction: column;
		gap: 5px;
	}

	.field-label {
		font-size: 11px;
		font-weight: 600;
		color: var(--text-secondary);
		text-transform: uppercase;
		letter-spacing: 0.5px;
	}

	.field-hint {
		font-weight: 400;
		text-transform: none;
		letter-spacing: 0;
		color: var(--text-dim);
	}

	.field-input {
		padding: 8px 10px;
		font-size: 13px;
		background: var(--bg-tertiary);
		border: 1px solid var(--border);
		border-radius: 6px;
		color: var(--text-primary);
	}

	.field-input:focus {
		outline: none;
		border-color: var(--accent);
	}

	.field-input::placeholder {
		color: var(--text-dim);
	}

	.field-subtext {
		font-size: 10px;
		color: var(--text-dim);
	}

	.field-error {
		font-size: 10px;
		color: var(--accent-coral);
	}

	/* ── Row layout ── */
	.field-row {
		display: flex;
		gap: 12px;
	}

	.field-half {
		flex: 1;
		min-width: 0;
	}

	/* ── Slider ── */
	.field-slider {
		width: 100%;
		accent-color: var(--accent);
		cursor: pointer;
		height: 6px;
		margin-top: 2px;
	}

	.slider-range {
		display: flex;
		justify-content: space-between;
		font-size: 9px;
		color: var(--text-dim);
		margin-top: -2px;
	}

	/* ── Genre selector ── */
	.genre-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
	}

	.genre-clear-btn {
		font-size: 10px;
		color: var(--text-dim);
		padding: 1px 6px;
		border-radius: 3px;
		transition: color 0.1s;
	}

	.genre-clear-btn:hover {
		color: var(--accent-coral);
	}

	.genre-families {
		display: flex;
		flex-direction: column;
		gap: 6px;
		max-height: 180px;
		overflow-y: auto;
		padding: 8px;
		background: var(--bg-tertiary);
		border: 1px solid var(--border);
		border-radius: 6px;
	}

	.genre-family {
		display: flex;
		align-items: flex-start;
		gap: 6px;
	}

	.genre-family-label {
		font-size: 10px;
		font-weight: 600;
		color: var(--text-dim);
		text-transform: uppercase;
		letter-spacing: 0.3px;
		padding: 3px 6px;
		border-radius: 3px;
		white-space: nowrap;
		flex-shrink: 0;
		min-width: 64px;
		text-align: left;
		transition: all 0.1s;
	}

	.genre-family-label:hover {
		color: var(--text-secondary);
		background: var(--bg-hover);
	}

	.genre-family-active {
		color: var(--accent);
	}

	.genre-chips {
		display: flex;
		flex-wrap: wrap;
		gap: 3px;
	}

	.genre-chip {
		font-size: 11px;
		padding: 2px 8px;
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

	/* ── BPM inputs ── */
	.bpm-row {
		display: flex;
		align-items: center;
		gap: 8px;
	}

	.bpm-input {
		flex: 1;
		min-width: 0;
	}

	.bpm-separator {
		color: var(--text-dim);
		font-size: 14px;
		flex-shrink: 0;
	}

	/* ── Seed track ── */
	.seed-track {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 8px;
		padding: 8px 10px;
		background: var(--bg-tertiary);
		border: 1px solid var(--border);
		border-radius: 6px;
	}

	.seed-track-info {
		font-size: 12px;
		color: var(--text-primary);
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
		min-width: 0;
	}

	.seed-clear-btn {
		flex-shrink: 0;
		width: 20px;
		height: 20px;
		display: flex;
		align-items: center;
		justify-content: center;
		font-size: 14px;
		color: var(--text-dim);
		border-radius: 3px;
		transition: all 0.1s;
	}

	.seed-clear-btn:hover {
		color: var(--accent-coral);
		background: rgba(255, 107, 107, 0.1);
	}

	.seed-empty {
		display: flex;
		align-items: center;
		gap: 8px;
		padding: 8px 10px;
		background: var(--bg-tertiary);
		border: 1px solid var(--border);
		border-radius: 6px;
	}

	.seed-empty-text {
		font-size: 12px;
		color: var(--text-dim);
		flex: 1;
	}

	.seed-restore-btn {
		font-size: 11px;
		color: var(--accent);
		padding: 2px 8px;
		border: 1px solid var(--accent);
		border-radius: 3px;
		flex-shrink: 0;
		transition: all 0.1s;
	}

	.seed-restore-btn:hover {
		background: var(--accent);
		color: #000;
	}

	/* ── Footer ── */
	.dialog-footer {
		display: flex;
		justify-content: flex-end;
		gap: 8px;
		padding: 12px 20px 16px;
		border-top: 1px solid var(--border);
	}

	.btn-cancel {
		padding: 8px 16px;
		font-size: 13px;
		color: var(--text-secondary);
		background: var(--bg-tertiary);
		border: 1px solid var(--border);
		border-radius: 6px;
		transition: all 0.1s;
	}

	.btn-cancel:hover {
		background: var(--bg-hover);
		color: var(--text-primary);
	}

	.btn-build {
		padding: 8px 20px;
		font-size: 13px;
		font-weight: 600;
		color: #000;
		background: var(--accent);
		border: 1px solid var(--accent);
		border-radius: 6px;
		transition: all 0.1s;
	}

	.btn-build:hover:not(:disabled) {
		background: var(--accent-dim);
		border-color: var(--accent-dim);
	}

	.btn-build:disabled {
		opacity: 0.4;
		cursor: default;
	}
</style>
