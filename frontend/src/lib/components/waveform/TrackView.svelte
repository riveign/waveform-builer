<script lang="ts">
	import type { Track, TrackFeatures, WaveformDetailData } from '$lib/types';
	import { getTrackFeatures } from '$lib/api/tracks';
	import { createResource } from '$lib/data/resource.svelte';
	import { updateTrackRating, updateTrackSetRoles } from '$lib/api/tracks';
	import { submitDecision } from '$lib/api/tinder';
	import { getWaveformDetail } from '$lib/api/waveforms';
	import { formatKey, getCamelotColor, compatibleKeys } from '$lib/utils/camelot';
	import { formatTime } from '$lib/utils/waveform';
	import WavesurferPlayer from './WavesurferPlayer.svelte';
	import TrackArtwork from './TrackArtwork.svelte';
	import SetAppearances from './SetAppearances.svelte';
	import SimilarTracks from './SimilarTracks.svelte';
	import { getPlayerStore } from '$lib/stores/player.svelte';
	import StarRating from '../primitives/StarRating.svelte';
	import { capFirst } from '../library/TrackCard.svelte';
	import Spinner from '../Spinner.svelte';
	import EnergyZonePicker from '../library/EnergyZonePicker.svelte';
	import { ZONE_COLORS } from '../library/EnergyZonePicker.svelte';
	import SetRolePicker from '../library/SetRolePicker.svelte';
	import SetRoleBadge from '../library/SetRoleBadge.svelte';
	import { ROLE_LABEL } from '../library/SetRoleIcon.svelte';
	import AddToSetPicker from '../set/AddToSetPicker.svelte';
	import Chip from '../primitives/Chip.svelte';
	import Button from '../primitives/Button.svelte';
	import HarmonyIcon from '../primitives/HarmonyIcon.svelte';

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

	// Waveform and features are separate requests with separate failure modes: a
	// missing feature row should not blank the waveform.
	const waveformRes = createResource(
		() => (track.has_waveform ? track.id : null),
		(id, signal) => getWaveformDetail(id, signal),
		{ key: (id) => `track:${id}:waveform-detail` },
	);
	const featuresRes = createResource(
		() => (track.has_features ? track.id : null),
		(id, signal) => getTrackFeatures(id, signal),
		{ key: (id) => `track:${id}:features` },
	);
	const features = $derived<TrackFeatures | null>(featuresRes.data ?? null);
	const loadingWaveform = $derived(waveformRes.loading);
	const loadingFeatures = $derived(featuresRes.loading);
	// Features are non-critical — only a missing waveform is worth reporting.
	const error = $derived(waveformRes.error);
	const waveformData = $derived<WaveformDetailData | null>(waveformRes.data ?? null);

	// Editable fields — synced from track prop via $effect below
	let localRating = $state(0);
	let localZone = $state<string | null>(null);
	let showZonePicker = $state(false);
	let localRoles = $state<string[]>([]);
	let showRolePicker = $state(false);
	let teachingMoment = $state<string | null>(null);
	let showAddToSet = $state(false);

	$effect(() => {
		localRating = track.rating ?? 0;
		localZone = track.resolved_energy ?? null;
		localRoles = track.set_roles ?? [];
		showZonePicker = false;
		showRolePicker = false;
		teachingMoment = null;
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

	// Close role picker on click outside
	let roleWrapperEl = $state<HTMLDivElement | null>(null);
	$effect(() => {
		if (!showRolePicker) return;
		function handleClick(e: MouseEvent) {
			if (roleWrapperEl && !roleWrapperEl.contains(e.target as Node)) {
				showRolePicker = false;
			}
		}
		const timer = setTimeout(() => document.addEventListener('mousedown', handleClick), 0);
		return () => { clearTimeout(timer); document.removeEventListener('mousedown', handleClick); };
	});

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

	async function handleRoleToggle(role: string) {
		const prev = localRoles;
		const next = prev.includes(role) ? prev.filter((r) => r !== role) : [...prev, role];
		// Keep the picker open — the DJ may mark several roles at once. Mutate the
		// shared track object too so the library sidebar/cards reflect the change.
		localRoles = next;
		track.set_roles = next;
		try {
			await updateTrackSetRoles(track.id, next);
		} catch {
			localRoles = prev;
			track.set_roles = prev;
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

	// Persistent curation caption beside the rating stars. Mirrors StarRating's
	// curation-score read (rating → % of curation weight) but always visible — not
	// hover-only, so the info is keyboard/AT-reachable (content-conventions §5) —
	// and folds in the Rekordbox sync note. Sentence case throughout.
	let ratingCaption = $derived.by(() => {
		const sync = 'Ratings sync from Rekordbox — changes here last until your next sync';
		if (localRating === 0) return `Unrated — neutral weight in transitions. ${sync}`;
		const curationPct = Math.round((localRating / 5) * 40);
		return `${localRating}★ — ${curationPct}% of curation score. ${sync}`;
	});

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

	// The aside (tags + comment) is what justifies the boxed two-column layout.
	// Without it, a few facts in a full-width box leaves a wasted empty right
	// half — so we collapse to a compact inline row instead. "Rich" keeps the
	// 2-col box; "sparse" (facts only, no aside) renders one tidy line.
	let hasAside = $derived(track.playlist_tags.length > 0 || Boolean(track.comment));
</script>

<div class="track-view">
	<!-- ── Toolbar band: persistent identity strip (play + title/artist) ──
	     Pinned sticky to the scroller top so the track you're exploring stays
	     anchored while the attributes, waveform and related cards scroll beneath
	     it. Same band rhythm as the Set tab (height var(--band-toolbar-h),
	     sticky top:0 z:5, opaque bg + bottom divider) so every tab reads with the
	     same vertical rhythm. -->
	<div class="track-band">
		<Button
			iconOnly
			shape="round"
			onclick={handlePlay}
			ariaLabel={isThisTrackPlaying ? 'Pause' : 'Play'}
			title={isThisTrackPlaying ? 'Pause' : 'Play'}
		>
			{#snippet icon()}{isThisTrackPlaying ? '⏸' : '▶'}{/snippet}
		</Button>
		<div class="title-text">
			<h2 class="track-title" title={track.title ?? 'Unknown'}>{capFirst(track.title ?? 'Unknown')}</h2>
			<span class="track-subline">
				<span class="track-artist" title={track.artist ?? 'Unknown'}>{capFirst(track.artist ?? 'Unknown')}</span>
				{#if track.duration_sec}
					<span class="track-duration" title="Track length">{formatTime(track.duration_sec)}</span>
				{/if}
			</span>
		</div>
	</div>

	<!-- ── Body: scrolls beneath the band ── -->
	<div class="track-body">
	<!-- ── Header: artwork + absolute attributes + your rating ──
	     This is the standalone-track read open-coded as an interactive editor —
	     absolute key / BPM / energy (no mix-from comparison, so no match score),
	     plus an editable rating and zone picker. It mirrors StandaloneTrackCard's
	     "track on its own terms" model (StandaloneTrackCard itself is the static,
	     grid-sized version; this header stays interactive). -->
	<div class="track-header">
		<TrackArtwork trackId={track.id} />
		<div class="header-text">
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
						class="zone-chip-btn"
						class:approved={track.energy_source === 'approved'}
						style="--zone-color: {ZONE_COLORS[localZone ?? ''] ?? 'var(--text-dim)'}"
						onclick={() => showZonePicker = !showZonePicker}
						title={track.energy_source === 'approved' ? 'Energy zone (you approved this) — change it' : 'Energy zone — change it'}
						aria-label="Energy zone: {localZone ?? 'not set'}{track.energy_source === 'approved' ? ', approved by you' : ''}. Click to change."
					>
						<span class="zone-dot-sm"></span>
						{capFirst(localZone ?? track.energy ?? '?')}
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
				<div class="role-badge-wrapper" bind:this={roleWrapperEl}>
					<button
						class="role-chip-btn"
						onclick={() => showRolePicker = !showRolePicker}
						title="Set role — mark this a great opener, closer or break"
						aria-label="Set role: {localRoles.length ? localRoles.map((r) => ROLE_LABEL[r] ?? r).join(', ') : 'not set'}. Click to change."
					>
						{#if localRoles.length}
							<SetRoleBadge roles={localRoles} variant="full" />
						{:else}
							<span class="role-add">+ Set role</span>
						{/if}
					</button>
					{#if showRolePicker}
						<div class="role-dropdown">
							<SetRolePicker current={localRoles} ontoggle={handleRoleToggle} />
						</div>
					{/if}
				</div>
				{#if compatKeys.length}
					<span
						class="mixes-with"
						aria-label="Mixes with: {compatKeys.map((ck) => ck.name).join(', ')}"
						title="Mixes with: {compatKeys.map((ck) => ck.name).join(', ')}"
					>
						<span class="mixes-icon" aria-hidden="true">
							<HarmonyIcon relation="swap" size="sm" label="Mixes with" />
						</span>
						{#each compatKeys as ck (ck.camelot)}
							<Chip
								variant="key"
								size="sm"
								color={getCamelotColor(ck.camelot)}
								value={ck.name}
								title="{ck.name} — {ck.relation}"
							/>
						{/each}
					</span>
				{/if}
				<Button
					variant="secondary"
					size="sm"
					onclick={() => showAddToSet = !showAddToSet}
					title="Add to a set"
				>+ Add to set</Button>
			</div>
			<!-- Track signals row — the DJ's rating + what it contributes to curation.
			     A standalone track has no match-score (NN/100 is a pair-wise verdict),
			     so this header renders the rating half of the Related-tracks "Track
			     signals" pattern: editable stars, a compact read of the curation
			     contribution, and the sync caption. -->
			<div class="track-rating-row">
				<StarRating
					rating={localRating}
					size="lg"
					onchange={handleRatingChange}
				/>
				<span class="curation-note">{ratingCaption}</span>
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

	<!-- ── Metadata ──
	     Rich (facts + tags/comment): two columns in one row — facts left (8),
	     tags + note right (4) — reflowing to a stacked column on narrow widths.
	     Sparse (facts only, no aside): a compact inline row instead of a boxed
	     2-col grid with an empty right half. Nothing renders when there's
	     genuinely no extra info. ── -->
	{#if hasAside}
		<div class="meta-section grid-12 grid-12--content">
			{#if metaRows.length > 0}
				<div class="meta-grid meta-col-facts">
					{#each metaRows as row}
						<span class="meta-label">{row.label}</span>
						<span class="meta-value">{row.value}</span>
					{/each}
				</div>
			{/if}

			<div class="meta-col-aside">
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
		</div>
	{:else if metaRows.length > 0}
		<dl class="meta-inline">
			{#each metaRows as row}
				<div class="meta-inline-pair">
					<dt class="meta-label">{row.label}</dt>
					<dd class="meta-value">{row.value}</dd>
				</div>
			{/each}
		</dl>
	{/if}

	<!-- ── Waveform + What Kiku Hears + Sets featuring: one row — waveform keeps
	     priority (~2.2fr), then two analysis columns (What Kiku Hears · Sets
	     featuring). Container queries reflow to waveform-full + two columns, then a
	     single stacked column, so the waveform keeps a usable width and the panels
	     don't get crushed. ── -->
	<div class="sound-row" class:sound-row--with-cards={features}>
		<!-- ── Waveform column ── -->
		<div class="sr-col sr-col--wave">
			<p class="sr-eyebrow">Waveform</p>
			<div class="player-section">
			{#if error}
				<div class="error-msg" role="alert">
					<p class="error-headline">Couldn't draw this waveform.</p>
					<p class="error-detail">The track's analysis may still be running, or its file moved since the last scan — try again in a moment, or pick another track.</p>
				</div>
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
		</div>

		<!-- ── What Kiku Hears column (always visible) ── -->
		{#if features}
			<div class="sr-col sr-col--hears">
				<p class="sr-eyebrow">What Kiku hears</p>
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

		<!-- ── Sets column — third column of the sound row (top-aligned, natural
		     height: it's collapsed by default, so it must not stretch). ── -->
		<div class="sr-col sr-col--sets">
			<p class="sr-eyebrow">In your sets</p>
			<SetAppearances trackId={track.id} trackTitle={track.title ?? 'track'} />
		</div>
	</div>

	<!-- ── Related tracks (always visible, auto-loads) — full width below ── -->
	<SimilarTracks trackId={track.id} trackKey={track.key} parentBpm={track.bpm} />
	</div>
</div>

<style>
	.track-view {
		display: flex;
		flex-direction: column;
		/* No padding here: the toolbar band must span the full scroller width and
		   pin to top:0 (the body carries the page padding instead). */
	}

	/* ── Toolbar band ──
	   Replicates the Set tab's reference band recipe (set/SetPicker.svelte):
	   height var(--band-toolbar-h), sticky top:0 z:5, opaque background and a
	   bottom divider, so the Track tab reads with the same vertical rhythm as
	   every other tab. Holds the persistent play + title/artist identity. */
	.track-band {
		display: flex;
		align-items: center;
		gap: 10px;
		padding: 0 var(--space-xl);
		height: var(--band-toolbar-h);
		border-bottom: 1px solid var(--border);
		position: sticky;
		top: 0;
		z-index: 5;
		background: var(--bg-primary);
	}

	/* ── Body: the scrolling document beneath the band ── */
	.track-body {
		display: flex;
		flex-direction: column;
		gap: var(--space-2xl);
		padding: var(--space-2xl) var(--space-3xl);
		/* Container context for the sound-row's 9/3 split. The query must live on an
		   ANCESTOR of .sound-row — a `container-type` element cannot be styled by its
		   OWN container query, so .sound-row can't both establish the context and be
		   the queried target. .track-body spans the full content pane (~917px on a
		   1440px screen, content pane minus page padding), well past the 720px
		   split threshold. */
		container-type: inline-size;
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

	/* The text column must be able to shrink so the title/artist ellipsize
	 * (content-conventions §2) rather than push the row wider than the band.
	 * It grows to fill the band beside the play button. */
	.title-text {
		flex: 1;
		min-width: 0;
		display: flex;
		flex-direction: column;
		justify-content: center;
	}

	/* Title + artist: one line each, ellipsis on overflow, full value on hover
	 * via title (content-conventions §2). First-letter-capped via capFirst (§1).
	 * Sized + line-height tightened so title + subline both fit the 48px band. */
	.track-title {
		font-size: var(--text-md);
		font-weight: var(--font-weight-semibold);
		line-height: 1.2;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	/* Artist + a quiet duration on one subline. The duration is demoted from a
	 * chip to muted metadata text so the chip row below carries only the musical
	 * signals (key / BPM / energy). */
	.track-subline {
		display: flex;
		align-items: baseline;
		gap: var(--space-sm);
		min-width: 0;
		line-height: 1.2;
	}

	.track-artist {
		font-size: var(--text-sm);
		color: var(--text-secondary);
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
		min-width: 0;
	}

	.track-duration {
		flex-shrink: 0;
		font-size: var(--text-xs);
		color: var(--text-dim);
		font-variant-numeric: tabular-nums;
	}

	.track-meta {
		display: flex;
		gap: var(--space-md);
		align-items: center;
		flex-wrap: wrap;
		position: relative;
	}

	/* "Mixes with" cluster: a small ⇄ glyph (the harmonic-swap shape) stands in
	 * for the words, followed by the lighter compatible-key chips. The literal
	 * meaning is preserved for AT via aria-label/title on the wrapper. */
	.mixes-with {
		display: inline-flex;
		align-items: center;
		gap: var(--space-xs);
		margin-left: var(--space-xs);
	}

	.mixes-icon {
		display: inline-flex;
		color: var(--text-dim);
	}

	/* Interactive energy-zone chip. Mirrors the SimilarTrackCard energy chip's
	 * treatment — zone-colored label + dot (color paired with the zone word, never
	 * color alone, §4) — but stays a real <button> because it opens the zone
	 * picker. Surface/hover/focus follow the chip + states conventions (§5). The
	 * "approved" affordance is a tokenized left border, not a one-off ✓ glyph. */
	.zone-chip-btn {
		display: inline-flex;
		align-items: center;
		gap: var(--space-xs);
		height: var(--chip-height-md);
		padding: 0 var(--chip-pad-x-md);
		border: 1px solid transparent;
		border-radius: var(--chip-radius);
		background: var(--chip-bg);
		color: var(--zone-color);
		font-size: var(--chip-font-md);
		font-weight: var(--font-weight-medium);
		line-height: 1;
		white-space: nowrap;
		cursor: pointer;
		transition:
			background var(--dur-fast) var(--ease-standard),
			border-color var(--dur-fast) var(--ease-standard);
	}

	.zone-chip-btn:hover {
		background: var(--surface-hover);
	}

	/* Approved-by-you: a tokenized accent left edge (consistent affordance), paired
	 * with the title/aria-label text so it's never color-only (§4). */
	.zone-chip-btn.approved {
		border-left: var(--space-2xs) solid var(--accent);
	}

	.zone-dot-sm {
		width: var(--space-md);
		height: var(--space-md);
		border-radius: var(--radius-full);
		background: var(--zone-color);
		flex-shrink: 0;
	}

	.zone-badge-wrapper {
		position: relative;
	}

	/* Set-role control — mirrors the zone control: a chip-button that opens the
	   multi-toggle picker. Shows the gold role badge when set, else a "+ Set role"
	   affordance in the role hue. */
	.role-badge-wrapper {
		position: relative;
	}
	/* Bare wrapper — the tile (empty) or the SetRoleBadge (set) owns its own box. */
	.role-chip-btn {
		display: inline-flex;
		align-items: center;
		padding: 0;
		border: none;
		background: none;
		border-radius: var(--chip-radius);
		font: inherit;
		cursor: pointer;
	}
	/* EMPTY state — a quiet dashed gold ghost tile: an invitation, not a value.
	   Dashed + transparent + muted gold reads as "add", and stays quieter than the
	   solid gold set badge so a tagged track still pops. */
	.role-add {
		display: inline-flex;
		align-items: center;
		gap: var(--space-xs);
		height: var(--chip-height-md);
		padding: 0 var(--chip-pad-x-md);
		border: 1px dashed color-mix(in srgb, var(--role) 45%, transparent);
		border-radius: var(--chip-radius);
		background: transparent;
		color: color-mix(in srgb, var(--role) 78%, var(--text-2));
		font-size: var(--chip-font-md);
		font-weight: var(--font-weight-medium);
		line-height: 1;
		transition:
			background var(--dur-fast) var(--ease-standard),
			border-color var(--dur-fast) var(--ease-standard),
			color var(--dur-fast) var(--ease-standard);
	}
	/* Hover / keyboard-focus — the invitation "arms" to full gold with a faint fill. */
	.role-chip-btn:hover .role-add,
	.role-chip-btn:focus-visible .role-add {
		background: color-mix(in srgb, var(--role) 12%, transparent);
		border-color: var(--role);
		color: var(--role);
	}
	.role-chip-btn:active .role-add {
		background: color-mix(in srgb, var(--role) 18%, transparent);
	}
	/* SET state — brighten the badge's soft border on hover to signal it's editable. */
	.role-chip-btn:hover :global(.set-role-badge),
	.role-chip-btn:focus-visible :global(.set-role-badge) {
		border-color: var(--role);
	}
	.role-dropdown {
		position: absolute;
		top: 100%;
		right: 0;
		margin-top: var(--space-xs);
		background: var(--bg-primary);
		border: 1px solid var(--border);
		border-radius: var(--radius-lg);
		padding: var(--space-xs);
		min-width: 220px;
		box-shadow: 0 4px 16px rgba(0, 0, 0, 0.4);
		z-index: 50;
		animation: menu-appear var(--dur-fast) var(--ease-standard);
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

	.curation-note {
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

	/* ── Metadata section: two columns in one row (.grid-12 from the markup) ──
	 * Facts span 8, the tags + note aside span 4 so the previously-wasted right
	 * half is used. A container query collapses both to full width when the
	 * content pane is narrow. */
	.meta-section {
		container-type: inline-size;
		align-items: start;
		row-gap: var(--space-md);
	}

	.meta-col-facts {
		grid-column: span 8;
	}

	.meta-col-aside {
		grid-column: span 4;
		display: flex;
		flex-direction: column;
		gap: var(--space-md);
		min-width: 0;
	}

	@container (max-width: 520px) {
		.meta-col-facts,
		.meta-col-aside {
			grid-column: span 12;
		}
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

	/* Sparse state: a single tidy inline row of the present facts, wrapping
	   gracefully — no boxed grid, no empty half. Pairs are separated by a quiet
	   middot via the gap; each pair keeps label + value together. */
	.meta-inline {
		display: flex;
		flex-wrap: wrap;
		align-items: baseline;
		gap: var(--space-sm) var(--space-lg);
		margin: 0;
		font-size: var(--text-base);
	}

	.meta-inline-pair {
		display: inline-flex;
		align-items: baseline;
		gap: var(--space-xs);
	}

	.meta-inline dt {
		margin: 0;
	}

	.meta-inline dd {
		margin: 0;
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

	/* ── Sound row: waveform + What Kiku Hears + Sets featuring ──
	 * Container-query driven (context lives on the ancestor .track-view). Three
	 * tiers: stacked (narrow) → waveform full-width + two panels below (mid) →
	 * three side-by-side columns (wide). NOTE: .sound-row must NOT carry
	 * `container-type` itself — it is the element the queries style, and a container
	 * can't be the target of its own query. */
	.sound-row {
		display: flex;
		flex-direction: column;
		gap: var(--space-lg);
	}

	/* Each column is [eyebrow][body]. A shared eyebrow treatment + equal height
	   means the three bodies below all begin on one baseline. */
	.sr-col {
		display: flex;
		flex-direction: column;
		min-width: 0;
	}

	/* Shared section eyebrow — one uppercase label across all three columns,
	   matching the page's other section labels (the old .section-title and the
	   "Related tracks" eyebrow: uppercase, ~12px, muted, medium weight). The
	   margin-bottom sets the single baseline the three bodies share. */
	.sr-eyebrow {
		margin: 0 0 var(--space-md);
		font-size: var(--text-sm);
		line-height: var(--lh-sm);
		text-transform: uppercase;
		letter-spacing: 0.5px;
		font-weight: var(--font-weight-medium);
		color: var(--text-3);
	}

	.player-section {
		min-height: 80px;
		min-width: 0;
	}

	/* ── Mid tier (≥720px): waveform full-width on top, then What Kiku Hears · Sets
	 * featuring as two columns below. Each panel keeps its natural height. ── */
	@container (min-width: 720px) {
		.sound-row--with-cards {
			display: grid;
			grid-template-columns: 1fr 1fr;
			grid-template-areas:
				"wave wave"
				"hears sets";
			gap: var(--space-xl);
			align-items: start;
		}
		.sound-row--with-cards .sr-col--wave { grid-area: wave; }
		.sound-row--with-cards .sr-col--hears { grid-area: hears; }
		.sound-row--with-cards .sr-col--sets { grid-area: sets; }
	}

	/* ── Wide tier (≥900px): three side-by-side columns. The waveform keeps
	 * priority (~2.2fr); its intrinsic block height (--waveform-block-h: canvas 128
	 * + bottom-pad 10 + controls ≈ 28 ≈ 166px) is pinned and lent to What Kiku
	 * Hears so its stacked feature cards split it evenly. Sets featuring stays
	 * top-aligned at its natural collapsed height (no forced stretch, no empty
	 * pinned box). ── */
	@container (min-width: 900px) {
		.sound-row--with-cards {
			grid-template-columns: minmax(0, 2.2fr) minmax(0, 1fr) minmax(0, 1fr);
			grid-template-areas: "wave hears sets";
			--waveform-block-h: 166px;
		}

		.sound-row--with-cards .sr-col--wave .player-section {
			height: var(--waveform-block-h);
		}

		/* The feature-cards body is pinned to the SAME definite height as the
		   waveform body, so the two bodies bottom-align and the stacked cards split
		   the height evenly rather than out-growing the waveform. */
		.sound-row--with-cards .sr-col--hears .feature-cards {
			height: var(--waveform-block-h);
			min-height: 0;
			/* Switch from the default responsive grid to a single flex column so the
			   two cards can `flex: 1 1 0` and split the column height evenly. */
			display: flex;
			flex-direction: column;
			gap: var(--space-md);
		}

		.sound-row--with-cards .sr-col--hears .feature-card {
			/* Each card shares the column height equally and shrinks to fit; content
			   vertically centred. Vertical padding trimmed so the compressed cards
			   read clean, not cramped. */
			flex: 1 1 0;
			min-height: 0;
			overflow: hidden;
			align-items: center;
			padding: var(--space-xs) var(--space-xl);
		}

		/* Tighten the card-body stack so the tallest card (Energy: label + value +
		   bar + In/Body/Out detail) fits the split without clipping. */
		.sound-row--with-cards .sr-col--hears .feature-card .card-body {
			gap: var(--space-2xs);
		}

		.sound-row--with-cards .sr-col--hears .feature-card .card-value {
			font-size: var(--text-lg);
		}

		.sound-row--with-cards .sr-col--hears .feature-card .card-bar {
			height: var(--space-xs);
			margin-top: 0;
		}

		.sound-row--with-cards .sr-col--hears .feature-card .card-detail {
			margin-top: var(--space-2xs);
		}

		/* Sets panel fills to the SAME block height as the waveform + stat cards, so
		   the row reads as three balanced, equal-height panels (rather than a short
		   card marooned at the top with dead space below). It still grows past this
		   if the track is in many sets. */
		.sound-row--with-cards .sr-col--sets :global(.sets-card) {
			min-height: var(--waveform-block-h);
		}
	}

	.no-data, .error-msg {
		padding: var(--space-2xl);
		text-align: center;
		font-size: var(--text-base);
		color: var(--text-2);
	}

	/* Error state (content-conventions §5): a calm "what happened" headline plus a
	   "why + what to try" detail line — never an alarming raw dump, never blame the
	   DJ. The headline carries the warm warn color; the detail stays muted. */
	.error-msg {
		display: flex;
		flex-direction: column;
		gap: var(--space-xs);
	}

	.error-headline {
		margin: 0;
		font-weight: var(--font-weight-medium);
		color: var(--energy-high);
	}

	.error-detail {
		margin: 0;
		font-size: var(--text-sm);
		color: var(--text-4);
	}

	.no-data code {
		background: var(--surface-3);
		padding: var(--space-2xs) var(--space-sm);
		border-radius: var(--radius-xs);
		font-size: var(--text-sm);
	}

	/* ── What Kiku Hears — the stat cards (the eyebrow now lives in the .sr-col). ── */

	.feature-cards {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
		gap: var(--space-lg);
	}

	.feature-card {
		display: flex;
		gap: var(--space-lg);
		padding: var(--space-xl);
		background: var(--surface-2);
		border-radius: var(--radius-lg);
		border: var(--space-px) solid var(--border-subtle);
		transition: border-color var(--dur-fast) var(--ease-standard);
	}

	.feature-card:hover {
		border-color: var(--text-4);
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
		gap: var(--space-xs);
	}

	.card-label {
		font-size: var(--text-xs);
		text-transform: uppercase;
		letter-spacing: 0.5px;
		color: var(--text-4);
		font-weight: var(--font-weight-medium);
	}

	/* The big % is the focal point: large, tabular, primary-text. */
	.card-value {
		font-size: var(--text-2xl);
		font-weight: var(--font-weight-semibold);
		font-variant-numeric: tabular-nums;
		color: var(--text-1);
		line-height: 1;
	}

	.card-unit {
		font-size: var(--text-base);
		font-weight: var(--font-weight-regular);
		color: var(--text-4);
		margin-left: var(--space-px);
	}

	/* Thin full-width meter — subordinate to the value. */
	.card-bar {
		height: var(--space-xs);
		background: var(--surface-3);
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
		gap: var(--space-md);
		font-size: var(--text-xs);
		color: var(--text-4);
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
