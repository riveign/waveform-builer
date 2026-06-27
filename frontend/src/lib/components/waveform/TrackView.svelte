<script lang="ts">
	import type { Track, TrackFeatures, WaveformDetailData } from '$lib/types';
	import { getTrackFeatures } from '$lib/api/tracks';
	import { updateTrackRating } from '$lib/api/tracks';
	import { submitDecision } from '$lib/api/tinder';
	import { getWaveformDetail } from '$lib/api/waveforms';
	import { formatKey, getCamelotColor, compatibleKeys } from '$lib/utils/camelot';
	import { formatTime } from '$lib/utils/waveform';
	import WavesurferPlayer from './WavesurferPlayer.svelte';
	import TrackArtwork from './TrackArtwork.svelte';
	import SetAppearances from './SetAppearances.svelte';
	import SimilarTracks from './SimilarTracks.svelte';
	import { getPlayerStore } from '$lib/stores/player.svelte';
	import StarRating from '../library/StarRating.svelte';
	import Spinner from '../Spinner.svelte';
	import EnergyZonePicker from '../library/EnergyZonePicker.svelte';
	import { ZONE_COLORS } from '../library/EnergyZonePicker.svelte';
	import AddToSetPicker from '../set/AddToSetPicker.svelte';
	import Chip from '../primitives/Chip.svelte';
	import Button from '../primitives/Button.svelte';

	let { track }: { track: Track } = $props();

	const player = getPlayerStore();

	let isThisTrackPlaying = $derived(
		player.currentTrack?.id === track.id && player.isPlaying
	);
	let isThisTrackActive = $derived(
		player.currentTrack?.id === track.id && player.status !== 'idle'
	);
	let globalProgress = $derived(
		isThisTrackActive ? player.progress : 0
	);

	/** Harmonically compatible keys to mix into (Camelot neighbours). */
	let compatKeys = $derived(compatibleKeys(track.key));

	function handlePlay() {
		if (isThisTrackActive) {
			player.togglePlay();
		} else {
			player.play(track);
		}
	}

	/** Click on the waveform: jump playback to that point in this track. */
	function handleSeek(fraction: number) {
		const dur = waveformData?.duration_sec ?? track.duration_sec ?? 0;
		if (player.currentTrack?.id === track.id) {
			// Already the active track — just move the playhead.
			player.seek(fraction * dur);
		} else {
			// Not loaded yet — start this track from the clicked point.
			player.play(track, fraction);
		}
	}

	let waveformData = $state<WaveformDetailData | null>(null);
	let features = $state<TrackFeatures | null>(null);
	let loadingWaveform = $state(false);
	let loadingFeatures = $state(false);
	let error = $state<string | null>(null);

	// Editable fields — synced from track prop via $effect below
	let localRating = $state(0);
	let localZone = $state<string | null>(null);
	let showZonePicker = $state(false);
	let teachingMoment = $state<string | null>(null);
	let showAddToSet = $state(false);

	$effect(() => {
		localRating = track.rating ?? 0;
		localZone = track.resolved_energy;
		showZonePicker = false;
		teachingMoment = null;
	});

	$effect(() => {
		if (track.id) {
			loadTrackData(track.id);
		}
	});

	// Auto-clear teaching moment after 8 seconds
	$effect(() => {
		if (!teachingMoment) return;
		const timer = setTimeout(() => { teachingMoment = null; }, 8000);
		return () => clearTimeout(timer);
	});

	// Close zone picker on click outside
	let zoneWrapperEl = $state<HTMLDivElement | null>(null);
	$effect(() => {
		if (!showZonePicker) return;
		function handleClick(e: MouseEvent) {
			if (zoneWrapperEl && !zoneWrapperEl.contains(e.target as Node)) {
				showZonePicker = false;
			}
		}
		const timer = setTimeout(() => document.addEventListener('mousedown', handleClick), 0);
		return () => { clearTimeout(timer); document.removeEventListener('mousedown', handleClick); };
	});

	async function loadTrackData(id: number) {
		error = null;
		waveformData = null;
		features = null;

		if (track.has_waveform) {
			loadingWaveform = true;
			try {
				waveformData = await getWaveformDetail(id);
			} catch (e) {
				error = e instanceof Error ? e.message : String(e);
			} finally {
				loadingWaveform = false;
			}
		}

		if (track.has_features) {
			loadingFeatures = true;
			try {
				features = await getTrackFeatures(id);
			} catch {
				// non-critical
			} finally {
				loadingFeatures = false;
			}
		}
	}

	async function handleZoneSelect(zone: string) {
		const prev = localZone;
		localZone = zone;
		showZonePicker = false;
		try {
			const result = await submitDecision(track.id, 'override', zone);
			if (result.teaching_moment) {
				teachingMoment = result.teaching_moment;
			}
		} catch {
			localZone = prev;
		}
	}

	async function handleRatingChange(rating: number) {
		const prev = localRating;
		localRating = rating;
		// Mutate the shared track object too so the library sidebar reflects the
		// new rating (it's the same object reference selected from the store).
		track.rating = rating;
		try {
			await updateTrackRating(track.id, rating);
		} catch {
			localRating = prev;
			track.rating = prev;
		}
	}

	// Clamp feature values to 0–1 range (some analysers produce >1)
	function pct(v: number | null | undefined): number {
		return Math.min(Math.round((v ?? 0) * 100), 100);
	}

	// Dominant mood label
	let dominantMood = $derived.by(() => {
		if (!features || features.mood_happy == null) return '';
		const moods = [
			{ label: 'Happy', val: features.mood_happy ?? 0 },
			{ label: 'Sad', val: features.mood_sad ?? 0 },
			{ label: 'Aggressive', val: features.mood_aggressive ?? 0 },
			{ label: 'Relaxed', val: features.mood_relaxed ?? 0 },
		];
		moods.sort((a, b) => b.val - a.val);
		return moods[0].label;
	});

	// Metadata grid helper — only show rows with data
	interface MetaRow { label: string; value: string }
	let metaRows = $derived.by(() => {
		const rows: MetaRow[] = [];
		if (track.album) rows.push({ label: 'Album', value: track.album });
		if (track.label) rows.push({ label: 'Label', value: track.label });
		if (track.genre_family) rows.push({ label: 'Genre', value: track.genre_family + (track.genre && track.genre !== track.genre_family ? ` · ${track.genre}` : '') });
		if (track.release_year) rows.push({ label: 'Year', value: String(track.release_year) });

		const plays = (track.play_count ?? 0) + (track.kiku_play_count ?? 0);
		if (plays > 0) {
			const kikuPart = track.kiku_play_count ? ` · ${track.kiku_play_count} in Kiku` : '';
			rows.push({ label: 'Played', value: `${plays}×${kikuPart}` });
		}

		if (track.date_added) {
			const d = track.date_added.slice(0, 7); // YYYY-MM
			rows.push({ label: 'Added', value: d });
		}
		return rows;
	});
</script>

<div class="track-view">
	<!-- ── Header: artwork + title/artist + badges ── -->
	<div class="track-header">
		<TrackArtwork trackId={track.id} />
		<div class="header-text">
			<div class="title-row">
				<Button
					iconOnly
					shape="round"
					onclick={handlePlay}
					ariaLabel={isThisTrackPlaying ? 'Pause' : 'Play'}
					title={isThisTrackPlaying ? 'Pause' : 'Play'}
				>
					{#snippet icon()}{isThisTrackPlaying ? '⏸' : '▶'}{/snippet}
				</Button>
				<div>
					<h2 class="track-title">{track.title ?? 'Unknown'}</h2>
					<span class="track-artist">{track.artist ?? 'Unknown'}</span>
				</div>
			</div>
			<div class="track-meta">
				<Chip
					variant="key"
					color={getCamelotColor(track.key)}
					value={formatKey(track.key) || '?'}
					title="Camelot key {formatKey(track.key) || 'unknown'}"
				/>
				<Chip variant="bpm" value={track.bpm ? Math.round(track.bpm) : '?'} title="Tempo {track.bpm ? Math.round(track.bpm) + ' BPM' : 'unknown'}" />
				<div class="zone-badge-wrapper" bind:this={zoneWrapperEl}>
					<button
						class="meta-badge meta-badge-interactive zone-badge"
						style="--zone-color: {ZONE_COLORS[localZone ?? ''] ?? 'var(--text-dim)'}"
						onclick={() => showZonePicker = !showZonePicker}
						title="Change energy zone"
						aria-label="Energy zone: {localZone ?? 'not set'}. Click to change."
					>
						<span class="zone-dot-sm"></span>
						{localZone ?? track.energy ?? '?'}
						{#if track.energy_source === 'approved'}
							<span class="source-check" title="You approved this zone">✓</span>
						{/if}
					</button>
					{#if showZonePicker}
						<div class="zone-dropdown">
							<EnergyZonePicker
								current={localZone}
								onselect={handleZoneSelect}
							/>
						</div>
					{/if}
				</div>
				{#if track.duration_sec}
					<Chip variant="neutral" size="sm" value={formatTime(track.duration_sec)} title="Track length" />
				{/if}
				{#if compatKeys.length}
					<span class="mixes-label" title="Harmonically compatible keys (Camelot wheel)">Mixes with</span>
					{#each compatKeys as ck (ck.camelot)}
						<Chip
							variant="key"
							size="sm"
							color={getCamelotColor(ck.camelot)}
							value={ck.name}
							title="{ck.name} — {ck.relation}"
						/>
					{/each}
				{/if}
				<Button
					variant="secondary"
					size="sm"
					onclick={() => showAddToSet = !showAddToSet}
					title="Add to a set"
				>+ Add to set</Button>
			</div>
			<!-- Rating inline with header -->
			<div class="track-rating-row">
				<StarRating
					rating={localRating}
					size="lg"
					showScore={true}
					onchange={handleRatingChange}
				/>
				<span class="sync-note">Ratings sync from Rekordbox — changes here last until your next sync</span>
			</div>
		</div>
	</div>

	{#if showAddToSet}
		<div class="add-to-set-popover">
			<AddToSetPicker
				trackId={track.id}
				trackTitle={track.title ?? 'track'}
				onclose={() => showAddToSet = false}
			/>
		</div>
	{/if}

	{#if teachingMoment}
		<p class="teaching-moment" aria-live="polite">{teachingMoment}</p>
	{/if}

	<!-- ── Metadata (compact row) ── -->
	{#if metaRows.length > 0 || track.playlist_tags.length > 0 || track.comment}
		<div class="meta-section">
			{#if metaRows.length > 0}
				<div class="meta-grid">
					{#each metaRows as row}
						<span class="meta-label">{row.label}</span>
						<span class="meta-value">{row.value}</span>
					{/each}
				</div>
			{/if}

			{#if track.playlist_tags.length > 0}
				<div class="tag-chips">
					{#each track.playlist_tags as tag}
						<Chip variant="neutral" size="sm" value={tag} title={tag} />
					{/each}
				</div>
			{/if}

			{#if track.comment}
				<p class="track-comment">{track.comment}</p>
			{/if}
		</div>
	{/if}

	<!-- ── Waveform Player ── -->
	<div class="player-section">
		{#if error}
			<div class="error-msg">{error}</div>
		{:else if loadingWaveform}
			<Spinner label="Drawing the waveform..." />
		{:else if waveformData}
			<WavesurferPlayer
				trackId={track.id}
				peaks={waveformData.envelope}
				duration={waveformData.duration_sec}
				beats={waveformData.beats}
				spectral={false}
				visualOnly={true}
				externalProgress={globalProgress}
				onseek={handleSeek}
			/>
		{:else if !track.has_waveform}
			<div class="no-data">
				No waveform yet — run <code>kiku analyze</code> to unlock it
			</div>
		{/if}
	</div>

	<!-- ── What Kiku Hears (always visible) ── -->
	{#if features}
		<div class="kiku-hears">
			<h3 class="section-title">What Kiku hears</h3>
			<div class="feature-cards">
				<!-- Energy card -->
				<div class="feature-card">
					<div class="card-icon">
						<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
							<path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
						</svg>
					</div>
					<div class="card-body">
						<span class="card-label">Energy</span>
						<span class="card-value">{pct(features.energy)}<span class="card-unit">%</span></span>
						<div class="card-bar">
							<div class="bar-fill energy" style="width: {pct(features.energy)}%"></div>
						</div>
						{#if features.energy_intro != null}
							<div class="card-detail">
								<span>In {features.energy_intro.toFixed(2)}</span>
								<span>Body {features.energy_body?.toFixed(2)}</span>
								<span>Out {features.energy_outro?.toFixed(2)}</span>
							</div>
						{/if}
					</div>
				</div>

				<!-- Danceability card -->
				<div class="feature-card">
					<div class="card-icon dance-icon">
						<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
							<circle cx="12" cy="4" r="2" stroke="currentColor" stroke-width="1.5"/>
							<path d="M8 22l1-7M16 22l-1-7M8.5 8L7 12h4l-1.5 3M15.5 8L17 12h-4l1.5 3" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
							<path d="M10 8h4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
						</svg>
					</div>
					<div class="card-body">
						<span class="card-label">Danceability</span>
						<span class="card-value">{pct(features.danceability)}<span class="card-unit">%</span></span>
						<div class="card-bar">
							<div class="bar-fill dance" style="width: {pct(features.danceability)}%"></div>
						</div>
					</div>
				</div>

				<!-- Mood card -->
				{#if features.mood_happy != null}
					<div class="feature-card">
						<div class="card-icon mood-icon">
							<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
								<circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="1.5"/>
								<path d="M8 14s1.5 2 4 2 4-2 4-2" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
								<circle cx="9" cy="10" r="1" fill="currentColor"/>
								<circle cx="15" cy="10" r="1" fill="currentColor"/>
							</svg>
						</div>
						<div class="card-body">
							<span class="card-label">Mood</span>
							<span class="card-value">{dominantMood}</span>
							<div class="mood-grid">
								<span class="mood-item" title="Happy"><span class="mood-dot mood-dot--happy"></span>{pct(features.mood_happy)}</span>
								<span class="mood-item" title="Sad"><span class="mood-dot mood-dot--sad"></span>{pct(features.mood_sad)}</span>
								<span class="mood-item" title="Aggressive"><span class="mood-dot mood-dot--aggressive"></span>{pct(features.mood_aggressive)}</span>
								<span class="mood-item" title="Relaxed"><span class="mood-dot mood-dot--relaxed"></span>{pct(features.mood_relaxed)}</span>
							</div>
						</div>
					</div>
				{/if}
			</div>
		</div>
	{/if}

	<!-- ── Sounds Like (always visible, auto-loads) ── -->
	<SimilarTracks trackId={track.id} trackKey={track.key} parentBpm={track.bpm} />

	<!-- ── Sets (at the bottom) ── -->
	<SetAppearances trackId={track.id} />
</div>

<style>
	.track-view {
		padding: var(--space-2xl) var(--space-3xl);
		display: flex;
		flex-direction: column;
		gap: var(--space-2xl);
	}

	/* ── Header ── */

	.track-header {
		display: flex;
		gap: 14px;
		align-items: flex-start;
	}

	.header-text {
		flex: 1;
		min-width: 0;
		display: flex;
		flex-direction: column;
		gap: var(--space-md);
	}

	.title-row {
		display: flex;
		align-items: center;
		gap: 10px;
	}

	.track-title {
		font-size: var(--text-lg);
		font-weight: var(--font-weight-semibold);
	}

	.track-artist {
		font-size: var(--text-md);
		color: var(--text-secondary);
	}

	.track-meta {
		display: flex;
		gap: var(--space-md);
		align-items: center;
		flex-wrap: wrap;
		position: relative;
	}

	.meta-badge {
		font-size: var(--text-sm);
		font-weight: var(--font-weight-semibold);
		padding: var(--space-2xs) var(--space-md);
		background: var(--bg-tertiary);
		border-radius: var(--radius-sm);
		border: none;
		color: var(--text-primary);
	}

	.mixes-label {
		font-size: var(--text-xs);
		color: var(--text-dim);
		margin-left: var(--space-xs);
		align-self: center;
	}

	.meta-badge-interactive {
		cursor: pointer;
		display: flex;
		align-items: center;
		gap: var(--space-xs);
		transition: background var(--dur-fast) var(--ease-standard);
	}

	.meta-badge-interactive:hover {
		background: var(--bg-secondary);
	}

	.zone-dot-sm {
		width: var(--space-md);
		height: var(--space-md);
		border-radius: var(--radius-full);
		background: var(--zone-color);
	}

	.source-check {
		font-size: var(--text-2xs);
		color: var(--accent);
	}

	.zone-badge-wrapper {
		position: relative;
	}

	.zone-dropdown {
		position: absolute;
		top: 100%;
		right: 0;
		margin-top: var(--space-xs);
		background: var(--bg-primary);
		border: 1px solid var(--border);
		border-radius: var(--radius-lg);
		padding: var(--space-xs);
		min-width: 150px;
		box-shadow: 0 4px 16px rgba(0, 0, 0, 0.4);
		z-index: 50;
		animation: menu-appear var(--dur-fast) var(--ease-standard);
	}

	@keyframes menu-appear {
		from { opacity: 0; transform: scale(0.97) translateY(-2px); }
		to   { opacity: 1; transform: scale(1) translateY(0); }
	}

	/* ── Rating row ── */

	.track-rating-row {
		display: flex;
		align-items: center;
		gap: var(--space-lg);
	}

	.sync-note {
		font-size: var(--text-xs);
		color: var(--text-dim);
	}

	.teaching-moment {
		font-size: var(--text-base);
		color: var(--accent);
		background: color-mix(in srgb, var(--accent) 8%, transparent);
		padding: var(--space-md) var(--space-lg);
		border-radius: var(--radius-md);
		border-left: 3px solid var(--accent);
		animation: fade-in var(--dur-base) var(--ease-standard);
	}

	@keyframes fade-in {
		from { opacity: 0; }
		to   { opacity: 1; }
	}

	/* ── Metadata section ── */

	.meta-section {
		display: flex;
		flex-direction: column;
		gap: 10px;
	}

	.meta-grid {
		display: grid;
		grid-template-columns: auto 1fr;
		gap: var(--space-sm) var(--space-xl);
		font-size: var(--text-base);
		padding: var(--space-lg) 14px;
		background: var(--bg-secondary);
		border-radius: var(--radius-lg);
		border: 1px solid var(--border);
	}

	.meta-label {
		color: var(--text-dim);
	}

	.meta-value {
		color: var(--text-primary);
	}

	.tag-chips {
		display: flex;
		flex-wrap: wrap;
		gap: var(--space-sm);
	}

	.track-comment {
		font-size: var(--text-base);
		font-style: italic;
		color: var(--text-secondary);
		margin: 0;
		padding: var(--space-sm) 10px;
		border-left: 2px solid var(--border);
	}

	/* ── Player section ── */

	.player-section {
		min-height: 80px;
	}

	.no-data, .error-msg {
		padding: var(--space-2xl);
		text-align: center;
		font-size: var(--text-base);
		color: var(--text-secondary);
	}

	.error-msg {
		color: var(--energy-high);
	}

	.no-data code {
		background: var(--bg-tertiary);
		padding: var(--space-2xs) var(--space-sm);
		border-radius: var(--radius-xs);
		font-size: var(--text-sm);
	}

	/* ── What Kiku Hears ── */

	.kiku-hears {
		display: flex;
		flex-direction: column;
		gap: var(--space-lg);
	}

	.section-title {
		font-size: var(--text-sm);
		text-transform: uppercase;
		letter-spacing: 0.5px;
		color: var(--text-secondary);
		margin: 0;
	}

	.feature-cards {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
		gap: var(--space-lg);
	}

	.feature-card {
		display: flex;
		gap: 14px;
		padding: var(--space-xl) 18px;
		background: var(--bg-secondary);
		border-radius: 10px;
		border: 1px solid var(--border);
		transition: border-color var(--dur-fast) var(--ease-standard);
	}

	.feature-card:hover {
		border-color: var(--text-dim);
	}

	.card-icon {
		width: 36px;
		height: 36px;
		flex-shrink: 0;
		color: var(--accent);
		display: flex;
		align-items: flex-start;
		justify-content: center;
		padding-top: var(--space-2xs);
	}

	.card-icon svg {
		width: 28px;
		height: 28px;
	}

	.dance-icon { color: var(--energy-mid); }
	.mood-icon { color: var(--lilac-400); }

	.card-body {
		flex: 1;
		min-width: 0;
		display: flex;
		flex-direction: column;
		gap: var(--space-sm);
	}

	.card-label {
		font-size: var(--text-xs);
		text-transform: uppercase;
		letter-spacing: 0.5px;
		color: var(--text-dim);
		font-weight: var(--font-weight-medium);
	}

	.card-value {
		font-size: 22px;
		font-weight: 700;
		font-variant-numeric: tabular-nums;
		color: var(--text-primary);
		line-height: 1;
	}

	.card-unit {
		font-size: var(--text-base);
		font-weight: 400;
		color: var(--text-dim);
		margin-left: 1px;
	}

	.card-bar {
		height: 5px;
		background: var(--bg-tertiary);
		border-radius: var(--radius-xs);
		overflow: hidden;
		margin-top: var(--space-xs);
	}

	.bar-fill {
		height: 100%;
		border-radius: var(--radius-xs);
		transition: width var(--dur-slow) var(--ease-standard);
	}

	.bar-fill.energy { background: var(--accent); }
	.bar-fill.dance { background: var(--energy-mid); }

	.card-detail {
		display: flex;
		gap: 10px;
		font-size: var(--text-xs);
		color: var(--text-dim);
		font-variant-numeric: tabular-nums;
		margin-top: var(--space-xs);
	}

	.mood-grid {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: var(--space-xs) var(--space-lg);
		font-size: var(--text-xs);
		color: var(--text-secondary);
		font-variant-numeric: tabular-nums;
		margin-top: var(--space-xs);
	}

	.mood-item {
		display: flex;
		align-items: center;
		gap: var(--space-xs);
	}

	.mood-dot {
		width: var(--space-sm);
		height: var(--space-sm);
		border-radius: var(--radius-full);
		flex-shrink: 0;
	}
	/* Mood family colors map to the nearest palette primitives (happy→green,
	   sad→cyan, aggressive→red, relaxed→lilac) so the swatches stay tokenized.
	   Each dot is paired with its word label + title, so color is never the
	   only cue (content-conventions §4). */
	.mood-dot--happy      { background: var(--green-500); }
	.mood-dot--sad        { background: var(--cyan-500); }
	.mood-dot--aggressive { background: var(--red-500); }
	.mood-dot--relaxed    { background: var(--lilac-400); }

	.add-to-set-popover {
		position: relative;
		background: var(--bg-primary);
		border: 1px solid var(--border);
		border-radius: var(--radius-lg);
		box-shadow: 0 4px 16px rgba(0, 0, 0, 0.4);
		z-index: 100;
		max-width: 300px;
	}
</style>
