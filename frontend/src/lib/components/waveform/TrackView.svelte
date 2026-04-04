<script lang="ts">
	import type { Track, TrackFeatures, WaveformDetailData } from '$lib/types';
	import { getTrackFeatures } from '$lib/api/tracks';
	import { updateTrackRating } from '$lib/api/tracks';
	import { submitDecision } from '$lib/api/tinder';
	import { getWaveformDetail } from '$lib/api/waveforms';
	import { getCamelotColor } from '$lib/utils/camelot';
	import { formatTime } from '$lib/utils/waveform';
	import WavesurferPlayer from './WavesurferPlayer.svelte';
	import TrackArtwork from './TrackArtwork.svelte';
	import SetAppearances from './SetAppearances.svelte';
	import SimilarTracks from './SimilarTracks.svelte';
	import { getPlayerStore } from '$lib/stores/player.svelte';
	import StarRating from '../library/StarRating.svelte';
	import EnergyZonePicker from '../library/EnergyZonePicker.svelte';
	import { ZONE_COLORS } from '../library/EnergyZonePicker.svelte';

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

	function handlePlay() {
		if (isThisTrackActive) {
			player.togglePlay();
		} else {
			player.play(track);
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
		try {
			await updateTrackRating(track.id, rating);
		} catch {
			localRating = prev;
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
	<!-- Header: artwork + title/artist + play button — full width -->
	<div class="track-header">
		<TrackArtwork trackId={track.id} />
		<div class="header-text">
			<div class="title-row">
				<button class="play-btn" onclick={handlePlay} title={isThisTrackPlaying ? 'Pause' : 'Play'}>
					{isThisTrackPlaying ? '⏸' : '▶'}
				</button>
				<div>
					<h2 class="track-title">{track.title ?? 'Unknown'}</h2>
					<span class="track-artist">{track.artist ?? 'Unknown'}</span>
				</div>
			</div>
			<div class="track-meta">
				<span class="meta-badge" style="color: {getCamelotColor(track.key)}">
					{track.key ?? '?'}
				</span>
				<span class="meta-badge">{track.bpm ? Math.round(track.bpm) : '?'} BPM</span>
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
					<span class="meta-badge dim">{formatTime(track.duration_sec)}</span>
				{/if}
			</div>
		</div>
	</div>

	<!-- Star rating — full width -->
	<div class="track-rating-row">
		<StarRating
			rating={localRating}
			size="lg"
			showScore={true}
			onchange={handleRatingChange}
		/>
		<span class="sync-note">Ratings sync from Rekordbox — changes here last until your next sync</span>
	</div>

	{#if teachingMoment}
		<p class="teaching-moment" aria-live="polite">{teachingMoment}</p>
	{/if}

	<!-- Two-column body -->
	<div class="two-col">
		<!-- Left column: metadata, tags, comment, sets, similar -->
		<div class="col-left">
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
						<span class="chip">{tag}</span>
					{/each}
				</div>
			{/if}

			{#if track.comment}
				<p class="track-comment">{track.comment}</p>
			{/if}

			<SetAppearances trackId={track.id} />
			<SimilarTracks trackId={track.id} trackKey={track.key} />
		</div>

		<!-- Right column: waveform, features -->
		<div class="col-right">
			{#if error}
				<div class="error-msg">{error}</div>
			{/if}

			{#if loadingWaveform}
				<div class="loading">Drawing the waveform...</div>
			{:else if waveformData}
				<WavesurferPlayer
					trackId={track.id}
					peaks={waveformData.envelope}
					duration={waveformData.duration_sec}
					beats={waveformData.beats}
					spectral={false}
					visualOnly={true}
					externalProgress={globalProgress}
				/>
			{:else if !track.has_waveform}
				<div class="no-data">
					No waveform yet — run <code>kiku analyze</code> to unlock it
				</div>
			{/if}

			{#if features}
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
									<span class="mood-item" title="Happy"><span class="mood-dot" style="background: #2ecc71"></span>{pct(features.mood_happy)}</span>
									<span class="mood-item" title="Sad"><span class="mood-dot" style="background: #3498db"></span>{pct(features.mood_sad)}</span>
									<span class="mood-item" title="Aggressive"><span class="mood-dot" style="background: #e74c3c"></span>{pct(features.mood_aggressive)}</span>
									<span class="mood-item" title="Relaxed"><span class="mood-dot" style="background: #9b59b6"></span>{pct(features.mood_relaxed)}</span>
								</div>
							</div>
						</div>
					{/if}
				</div>
			{/if}
		</div>
	</div>
</div>

<style>
	.track-view {
		padding: 20px 24px;
		display: flex;
		flex-direction: column;
		gap: 16px;
	}

	/* ── Header (full width) ── */

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
		gap: 8px;
	}

	.title-row {
		display: flex;
		align-items: center;
		gap: 10px;
	}

	.play-btn {
		width: 36px;
		height: 36px;
		border-radius: 50%;
		background: var(--accent);
		color: #000;
		font-size: 15px;
		display: flex;
		align-items: center;
		justify-content: center;
		flex-shrink: 0;
		cursor: pointer;
		border: none;
	}

	.play-btn:hover {
		background: var(--accent-dim);
	}

	.track-title {
		font-size: 18px;
		font-weight: 600;
	}

	.track-artist {
		font-size: 14px;
		color: var(--text-secondary);
	}

	.track-meta {
		display: flex;
		gap: 8px;
		align-items: center;
		flex-wrap: wrap;
		position: relative;
	}

	.meta-badge {
		font-size: 12px;
		font-weight: 600;
		padding: 2px 8px;
		background: var(--bg-tertiary);
		border-radius: 4px;
		border: none;
		color: var(--text-primary);
	}

	.meta-badge.dim {
		color: var(--text-dim);
	}

	.meta-badge-interactive {
		cursor: pointer;
		display: flex;
		align-items: center;
		gap: 4px;
		transition: background 0.1s;
	}

	.meta-badge-interactive:hover {
		background: var(--bg-secondary);
	}

	.zone-dot-sm {
		width: 8px;
		height: 8px;
		border-radius: 50%;
		background: var(--zone-color);
	}

	.source-check {
		font-size: 10px;
		color: var(--accent);
	}

	.zone-badge-wrapper {
		position: relative;
	}

	.zone-dropdown {
		position: absolute;
		top: 100%;
		right: 0;
		margin-top: 4px;
		background: var(--bg-primary);
		border: 1px solid var(--border);
		border-radius: 8px;
		padding: 4px;
		min-width: 150px;
		box-shadow: 0 4px 16px rgba(0, 0, 0, 0.4);
		z-index: 50;
		animation: menu-appear 0.1s ease-out;
	}

	@keyframes menu-appear {
		from { opacity: 0; transform: scale(0.97) translateY(-2px); }
		to   { opacity: 1; transform: scale(1) translateY(0); }
	}

	/* ── Rating row (full width) ── */

	.track-rating-row {
		display: flex;
		align-items: center;
		gap: 12px;
	}

	.sync-note {
		font-size: 11px;
		color: var(--text-dim);
	}

	.teaching-moment {
		font-size: 13px;
		color: var(--accent);
		background: rgba(0, 206, 209, 0.08);
		padding: 8px 12px;
		border-radius: 6px;
		border-left: 3px solid var(--accent);
		animation: fade-in 0.3s ease-out;
	}

	@keyframes fade-in {
		from { opacity: 0; }
		to   { opacity: 1; }
	}

	/* ── Two-column layout ── */

	.two-col {
		display: grid;
		grid-template-columns: 300px 1fr;
		gap: 24px;
		align-items: start;
	}

	/* Stack on narrow panels (< 600px content area) */
	@container (max-width: 600px) {
		.two-col {
			grid-template-columns: 1fr;
		}
	}

	/* Fallback for browsers without container queries */
	@media (max-width: 800px) {
		.two-col {
			grid-template-columns: 1fr;
		}
	}

	.col-left {
		display: flex;
		flex-direction: column;
		gap: 12px;
	}

	.col-right {
		display: flex;
		flex-direction: column;
		gap: 16px;
		min-width: 0;
	}

	/* ── Metadata grid ── */

	.meta-grid {
		display: grid;
		grid-template-columns: auto 1fr;
		gap: 6px 16px;
		font-size: 13px;
		padding: 12px 14px;
		background: var(--bg-secondary);
		border-radius: 8px;
		border: 1px solid var(--border);
	}

	.meta-label {
		color: var(--text-dim);
	}

	.meta-value {
		color: var(--text-primary);
	}

	/* ── Playlist tag chips ── */

	.tag-chips {
		display: flex;
		flex-wrap: wrap;
		gap: 6px;
	}

	.chip {
		font-size: 11px;
		padding: 2px 8px;
		background: var(--bg-tertiary);
		border-radius: 10px;
		color: var(--text-secondary);
	}

	/* ── Comment ── */

	.track-comment {
		font-size: 13px;
		font-style: italic;
		color: var(--text-secondary);
		margin: 0;
		padding: 6px 10px;
		border-left: 2px solid var(--border);
	}

	/* ── Waveform / features (right column) ── */

	.loading, .no-data, .error-msg {
		padding: 20px;
		text-align: center;
		font-size: 13px;
		color: var(--text-secondary);
	}

	.error-msg {
		color: var(--energy-high);
	}

	.no-data code {
		background: var(--bg-tertiary);
		padding: 2px 6px;
		border-radius: 3px;
		font-size: 12px;
	}

	.section-title {
		font-size: 12px;
		text-transform: uppercase;
		letter-spacing: 0.5px;
		color: var(--text-secondary);
		margin-bottom: 4px;
	}

	/* ── Feature cards ── */

	.feature-cards {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
		gap: 12px;
	}

	.feature-card {
		display: flex;
		gap: 14px;
		padding: 16px 18px;
		background: var(--bg-secondary);
		border-radius: 10px;
		border: 1px solid var(--border);
		transition: border-color 0.15s;
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
		padding-top: 2px;
	}

	.card-icon svg {
		width: 28px;
		height: 28px;
	}

	.dance-icon { color: var(--energy-mid, #f39c12); }
	.mood-icon { color: #9b59b6; }

	.card-body {
		flex: 1;
		min-width: 0;
		display: flex;
		flex-direction: column;
		gap: 6px;
	}

	.card-label {
		font-size: 11px;
		text-transform: uppercase;
		letter-spacing: 0.5px;
		color: var(--text-dim);
		font-weight: 500;
	}

	.card-value {
		font-size: 22px;
		font-weight: 700;
		font-variant-numeric: tabular-nums;
		color: var(--text-primary);
		line-height: 1;
	}

	.card-unit {
		font-size: 13px;
		font-weight: 400;
		color: var(--text-dim);
		margin-left: 1px;
	}

	.card-bar {
		height: 5px;
		background: var(--bg-tertiary);
		border-radius: 3px;
		overflow: hidden;
		margin-top: 4px;
	}

	.bar-fill {
		height: 100%;
		border-radius: 2px;
		transition: width 0.3s;
	}

	.bar-fill.energy { background: var(--accent); }
	.bar-fill.dance { background: var(--energy-mid, #f39c12); }

	.card-detail {
		display: flex;
		gap: 10px;
		font-size: 11px;
		color: var(--text-dim);
		font-variant-numeric: tabular-nums;
		margin-top: 4px;
	}

	.mood-grid {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 4px 12px;
		font-size: 11px;
		color: var(--text-secondary);
		font-variant-numeric: tabular-nums;
		margin-top: 4px;
	}

	.mood-item {
		display: flex;
		align-items: center;
		gap: 4px;
	}

	.mood-dot {
		width: 6px;
		height: 6px;
		border-radius: 50%;
		flex-shrink: 0;
	}
</style>
