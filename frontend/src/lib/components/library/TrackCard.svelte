<script lang="ts" module>
	/** First-letter capitalization for library text (title / artist / genre / zone).
	 *
	 *  USER DECISION (spec 023): the Track card forces a capital first letter on
	 *  the track title and artist, overriding the previous "preserve source casing"
	 *  default. This is purely presentational — it only upper-cases the FIRST
	 *  visible character and leaves the rest of the string byte-for-byte intact, so
	 *  stylized casing the DJ relies on (`deadmau5`, `LOUDER`, `MEDUZA`) is
	 *  preserved past the first glyph and no value is ever lost. Safe because it
	 *  never mutates the underlying data — the full original is still exposed via
	 *  the `title` attribute on hover. */
	export function capFirst(value: string | null | undefined): string {
		if (!value) return '';
		return value.charAt(0).toUpperCase() + value.slice(1);
	}

	/** Map a match score (0–1) onto a qualitative strength label + a 0–3 bar
	 *  level. Keeps the affinity row from showing a second raw number next to
	 *  the headline `NN/100` (content-conventions §3) while still pairing the
	 *  color with a word (§4). Thresholds:
	 *    ≥ 0.80 → Strong  (3 bars) — confidently mixes
	 *    ≥ 0.55 → Likely  (2 bars) — workable with intent
	 *    <  0.55 → Weak    (1 bar)  — a stretch */
	export function scoreStrength(score: number): {
		label: 'Strong' | 'Likely' | 'Weak';
		level: 1 | 2 | 3;
		tone: 'success' | 'warn' | 'danger';
	} {
		if (score >= 0.8) return { label: 'Strong', level: 3, tone: 'success' };
		if (score >= 0.55) return { label: 'Likely', level: 2, tone: 'warn' };
		return { label: 'Weak', level: 1, tone: 'danger' };
	}

	import type { SuggestNextItem, Track } from '$lib/types';

	/** The card runs in two modes, expressed as a discriminated union so the
	 *  compiler narrows the mode-specific payload — NO casts, NO `!`. Each mode
	 *  carries exactly the data that mode needs and nothing it doesn't, which is
	 *  why a standalone card structurally CANNOT render a match score or a
	 *  harmony move: those fields only exist on the `related` arm.
	 *
	 *  - `related`    — comparative: this track *relative to a reference track*.
	 *                   Tier 2 shows the harmony move + BPM delta; Tier 3 shows
	 *                   the match score + affinity strength. This is the original
	 *                   SimilarTrackCard behavior, preserved pixel-for-pixel.
	 *  - `standalone` — the track on its own terms. Tier 2 shows ABSOLUTE
	 *                   attributes (key / BPM / energy zone, no delta); Tier 3
	 *                   shows the track's OWN quality read (rating · plays · how
	 *                   settled its energy is). No reference track exists, so no
	 *                   phantom score is ever shown. */
	export type TrackCardMode =
		| {
				kind: 'related';
				/** The comparative suggestion (carries `score` + `breakdown`). */
				item: SuggestNextItem;
				/** Reference track this suggestion is measured against. */
				parentTrackId: number;
				parentBpm?: number | null;
				parentKey?: string | null;
				/** The DJ's stored opinion of this pairing, if any. */
				affinity?: string | null;
				onaffinitychange?: (trackId: number, newAffinity: string | null) => void;
		  }
		| {
				kind: 'standalone';
				/** The track on its own — no reference, no score. */
				track: Track;
		  };
</script>

<script lang="ts">
	import { getTrackArtworkUrl, setTrackAffinity, removeTrackAffinity } from '$lib/api/tracks';
	import StarRating from '../primitives/StarRating.svelte';
	import Chip from '../primitives/Chip.svelte';
	import Menu from '../primitives/Menu.svelte';
	import MenuItem from '../primitives/MenuItem.svelte';
	import MenuSeparator from '../primitives/MenuSeparator.svelte';
	import AddToSetPicker from '../set/AddToSetPicker.svelte';
	import { getPlayerStore } from '$lib/stores/player.svelte';
	import { getUiStore } from '$lib/stores/ui.svelte';
	import { getCamelotColor, formatKey, keyMoveLabel } from '$lib/utils/camelot';
	import HarmonyIcon, { toHarmonyRelation, HARMONY_RELATION_LABEL } from '$lib/components/primitives/HarmonyIcon.svelte';
	import MetronomeIcon from '$lib/components/primitives/MetronomeIcon.svelte';

	let { mode }: { mode: TrackCardMode } = $props();

	const player = getPlayerStore();
	const ui = getUiStore();

	let artworkFailed = $state(false);
	let menuOpen = $state(false);
	let menuX = $state(0);
	let menuY = $state(0);
	let showAddPicker = $state(false);

	// The shared track reference — both modes carry a Track, sourced differently.
	const track = $derived(mode.kind === 'related' ? mode.item.track : mode.track);

	// Reset artwork error when the track changes.
	$effect(() => {
		track.id;
		artworkFailed = false;
	});

	const energyZone = $derived(track.resolved_energy ?? null);
	const genreLabel = $derived(track.genre_family ?? track.genre ?? null);

	// First-letter-capped, full value preserved past the first glyph (capFirst).
	const titleText = $derived(track.title ?? 'Unknown');
	const artistText = $derived(track.artist ?? 'Unknown');

	// ── Energy zone color (shared) — from the --zone-* token set (single source). ──
	const ZONES = ['intro', 'warmup', 'build', 'drive', 'peak', 'close'];
	const zoneColor = $derived(
		energyZone && ZONES.includes(energyZone) ? `var(--zone-${energyZone})` : 'var(--text-2)',
	);

	// ── RELATED-only comparative derivations ──
	// All of these read the `related` arm's reference fields. They are guarded by
	// `mode.kind === 'related'`, so the compiler narrows the union and the
	// standalone arm never touches a parent/score/affinity that doesn't exist.
	const scoreDisplay = $derived(mode.kind === 'related' ? Math.round(mode.item.score * 100) : 0);
	const strength = $derived(scoreStrength(mode.kind === 'related' ? mode.item.score : 0));

	// BPM integer + signed colored delta (RELATED). Color follows the Kiku tempo
	// rule by MAGNITUDE (content-conventions §3): within ±6% = seamless (green),
	// ~6–12% = moderate (orange), beyond ±12% = tension (red). Color is always
	// paired with the signed number, so it is never the only cue.
	const bpmDelta = $derived.by(() => {
		if (mode.kind !== 'related') return null;
		if (!track.bpm || !mode.parentBpm) return null;
		return Math.round(track.bpm) - Math.round(mode.parentBpm);
	});
	const bpmDeltaStrength = $derived.by<'seamless' | 'moderate' | 'tension'>(() => {
		if (mode.kind !== 'related' || bpmDelta === null || !mode.parentBpm) return 'seamless';
		const pct = Math.abs(bpmDelta) / mode.parentBpm;
		if (pct <= 0.06) return 'seamless';
		if (pct <= 0.12) return 'moderate';
		return 'tension';
	});
	const bpmDeltaColor = $derived(
		bpmDeltaStrength === 'tension'
			? 'var(--score-poor)'
			: bpmDeltaStrength === 'moderate'
				? 'var(--score-good)'
				: 'var(--score-excellent)',
	);

	// Harmonic move from the reference track (RELATED).
	const harmony = $derived.by(() => {
		if (mode.kind !== 'related') return null;
		if (!track.key || !mode.parentKey) return null;
		return keyMoveLabel(mode.parentKey, track.key);
	});
	const harmonyRelation = $derived(harmony ? toHarmonyRelation(harmony.label) : null);
	// RELATED key chip color comes from the harmony quality (meaning); STANDALONE
	// key chip color is the absolute Camelot color (the wheel position), since
	// there is no move to qualify it.
	const keyColor = $derived.by(() => {
		if (mode.kind !== 'related' || !harmony) return getCamelotColor(track.key);
		if (harmony.score >= 0.8) return 'var(--score-excellent)';
		if (harmony.score >= 0.55) return 'var(--score-good)';
		return 'var(--score-poor)';
	});

	// Full opinion phrasing — kept for the hover title / aria so it reads naturally.
	const affinity = $derived(mode.kind === 'related' ? (mode.affinity ?? null) : null);
	const affinityLabel = $derived(
		affinity === 'good' ? 'Great together' : affinity === 'bad' ? 'Not for me' : null,
	);
	const matchWord = $derived.by(() => {
		if (affinity === 'bad') return 'Not for me';
		if (affinity === 'good') return 'Great';
		return strength.label === 'Strong' ? 'Great' : strength.label;
	});
	const matchTitle = $derived(
		affinityLabel ? `${affinityLabel} · ${strength.label} match` : `${strength.label} match`,
	);

	// ── STANDALONE-only own-quality derivations ──
	const playCount = $derived((track.play_count ?? 0) + (track.kiku_play_count ?? 0));
	// How SETTLED the track's energy read is — its own quality signal, no
	// reference needed. "Approved" = the DJ confirmed the zone; otherwise it is
	// Kiku's inferred read (and `—` when there is no zone at all). This is the
	// honest standalone analogue of the related card's match strength: it reads
	// the track's OWN confidence, not a pair-wise verdict.
	const energyFit = $derived.by<{ word: string; tone: 'success' | 'warn' | 'muted'; title: string }>(() => {
		if (!energyZone) {
			return { word: '—', tone: 'muted', title: 'Energy zone not set yet' };
		}
		if (track.energy_source === 'approved') {
			return { word: 'Settled', tone: 'success', title: `Energy zone ${capFirst(energyZone)} — approved by you` };
		}
		return { word: 'Inferred', tone: 'warn', title: `Energy zone ${capFirst(energyZone)} — Kiku's read, not yet approved` };
	});

	function handleCardClick() {
		ui.selectedTrack = track;
		ui.activeTab = 'track';
	}

	function handleMenuClick(e: MouseEvent) {
		e.stopPropagation();
		e.preventDefault();
		menuX = e.clientX;
		menuY = e.clientY;
		menuOpen = true;
	}

	function handleContextMenu(e: MouseEvent) {
		e.preventDefault();
		e.stopPropagation();
		menuX = e.clientX;
		menuY = e.clientY;
		menuOpen = true;
	}

	function handleDragStart(e: DragEvent) {
		e.dataTransfer?.setData(
			'application/x-kiku-track',
			JSON.stringify({ id: track.id, title: track.title })
		);
		if (e.dataTransfer) e.dataTransfer.effectAllowed = 'copy';
	}

	async function handleAffinity(value: 'good' | 'bad') {
		menuOpen = false;
		if (mode.kind !== 'related') return;
		const { parentTrackId, onaffinitychange } = mode;
		try {
			await setTrackAffinity(parentTrackId, track.id, value);
			onaffinitychange?.(track.id, value);
		} catch {
			// Silently fail — affinity API may not exist yet
		}
	}

	async function handleRemoveAffinity() {
		menuOpen = false;
		if (mode.kind !== 'related') return;
		const { parentTrackId, onaffinitychange } = mode;
		try {
			await removeTrackAffinity(parentTrackId, track.id);
			onaffinitychange?.(track.id, null);
		} catch {
			// Silently fail
		}
	}

	function handlePlay() {
		menuOpen = false;
		player.play(track);
	}

	function handleOpenTrack() {
		menuOpen = false;
		ui.selectedTrack = track;
		ui.activeTab = 'track';
	}

	function handleAddToSet(e: MouseEvent) {
		e.stopPropagation();
		showAddPicker = !showAddPicker;
	}
</script>

<div
	class="similar-card"
	class:standalone={mode.kind === 'standalone'}
	role="button"
	tabindex="0"
	draggable="true"
	onclick={handleCardClick}
	oncontextmenu={handleContextMenu}
	ondragstart={handleDragStart}
	onkeydown={(e) => { if (e.key === 'Enter') handleCardClick(); }}
>
	<!-- Tier 1: Identity — artwork + title/artist + actions (IDENTICAL both modes) -->
	<div class="zone-header">
		<div class="artwork-wrap">
			{#if artworkFailed}
				<div class="artwork-fallback">
					<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
						<path d="M9 18V5l12-2v13" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
						<circle cx="6" cy="18" r="3" stroke="currentColor" stroke-width="1.5"/>
						<circle cx="18" cy="16" r="3" stroke="currentColor" stroke-width="1.5"/>
					</svg>
				</div>
			{:else}
				<img
					src={getTrackArtworkUrl(track.id)}
					alt=""
					class="artwork-img"
					onerror={() => { artworkFailed = true; }}
				/>
			{/if}
		</div>

		<div class="text-col">
			<span class="track-title" title={titleText}>{capFirst(titleText)}</span>
			<!-- Identity subtitle: artist (plain muted text, ellipsizes FIRST under
			     width pressure) · genre as genre-family-COLORED TEXT (no box/border).
			     Genre is lightweight colored text — the color carries the signal, so it
			     reads without the visual weight of a chip on the dense identity line.
			     Artist `flex-shrink:1` yields space first so the artist ellipsizes BEFORE
			     the genre word. Genre shows at the regular + intermediate tiers and is
			     hidden ONLY at the compact tier (Row 2 is essentials-only there). -->
			<span class="track-meta">
				<span class="track-artist" title={artistText}>{capFirst(artistText)}</span>
				{#if genreLabel}
					<span class="meta-dot" aria-hidden="true">·</span>
					<span class="track-genre" title="Genre: {genreLabel}">{capFirst(genreLabel)}</span>
				{/if}
			</span>
		</div>

		<div class="menu-area">
			<button
				class="menu-btn add-btn"
				onclick={handleAddToSet}
				aria-label="Add to set"
				title="Add to set"
			>+</button>
			<button
				class="menu-btn"
				onclick={handleMenuClick}
				aria-label="Track options"
				title="Track options"
			>&#8942;</button>
			{#if showAddPicker}
				<div class="add-picker-popover">
					<AddToSetPicker
						trackId={track.id}
						trackTitle={track.title ?? 'track'}
						onclose={() => showAddPicker = false}
					/>
				</div>
			{/if}
		</div>
	</div>

	<!-- Divider -->
	<div class="zone-divider"></div>

	{#if mode.kind === 'related'}
		<!-- ── RELATED Tier 2: COMPARATIVE attribute chips — key + harmony move,
		     BPM + signed delta, energy zone. The harmony glyph, the key
		     color-by-harmony, and the BPM delta are all relative to the reference
		     track. Whole-chip priority hiding via the card's container query. ── -->
		<div class="zone-chips">
			{#if track.key}
				<Chip
					variant="key"
					color={keyColor}
					value={formatKey(track.key)}
					title={harmony ? `${formatKey(track.key)} — ${harmony.label} from this track` : `Key ${formatKey(track.key)}`}
				>
					{#snippet icon()}
						{#if harmonyRelation}
							<HarmonyIcon
								relation={harmonyRelation}
								size="sm"
								label={HARMONY_RELATION_LABEL[harmonyRelation]}
							/>
						{/if}
					{/snippet}
				</Chip>
			{/if}
			{#if track.bpm}
				<!-- bpm chip leads with the metronome glyph (auto-rendered by the bpm
				     variant) instead of a literal "BPM" text label — saves width; the
				     glyph + the chip's a11y title carry the meaning. -->
				<Chip variant="bpm" title="Tempo {Math.round(track.bpm)} BPM">
					<span class="bpm-num">{Math.round(track.bpm)}</span>
					{#if bpmDelta !== null && bpmDelta !== 0}
						<!-- Signed delta colored green/orange/red by magnitude (seamless /
						     moderate / tension). Color is tokenized and always paired with
						     the number, so it is never the only cue. -->
						<span
							class="bpm-delta"
							style:color={bpmDeltaColor}
							title="{Math.abs(bpmDelta)} BPM {bpmDelta > 0 ? 'faster' : 'slower'} than this track — {bpmDeltaStrength === 'seamless' ? 'seamless' : bpmDeltaStrength === 'moderate' ? 'moderate shift' : 'big jump'}"
						>{bpmDelta > 0 ? '+' : '−'}{Math.abs(bpmDelta)}</span>
					{/if}
				</Chip>
			{/if}
			{#if energyZone}
				<!-- Energy chip: stays at the regular AND intermediate tiers (key + BPM +
				     energy all fit now the bpm chip uses the compact metronome glyph). It
				     only drops at the compact tier, where the whole chip row is replaced
				     by the color-coded icon row. -->
				<div class="energy-chip" title="Energy zone: {capFirst(energyZone)}">
					<Chip variant="energy" color={zoneColor} value={capFirst(energyZone)} title="Energy zone: {capFirst(energyZone)}" />
				</div>
			{/if}
		</div>

		<!-- Compact-tier ONLY: a single row of COLOR-CODED ICONS (no text, no numbers,
		     no chips). At <200px the card becomes a dense pill; the chip row + signals
		     row are hidden and the signal is carried purely by icon SHAPE + COLOR + the
		     star count. Every icon keeps its real value in aria-label/title so nothing
		     is lost (a11y), and the distinct shapes mean color is never the only cue. -->
		<div class="compact-icons">
			{#if track.key && harmonyRelation}
				<span
					class="cicon"
					style="color: {keyColor}"
					title={harmony ? `${formatKey(track.key)} — ${harmony.label} from this track` : `Key ${formatKey(track.key)}`}
				>
					<HarmonyIcon
						relation={harmonyRelation}
						size="sm"
						label={harmony ? `${formatKey(track.key)}, ${harmony.label}` : `Key ${formatKey(track.key)}`}
						title={harmony ? `${formatKey(track.key)} — ${harmony.label} from this track` : `Key ${formatKey(track.key)}`}
					/>
				</span>
			{/if}
			{#if track.bpm}
				<span
					class="cicon"
					style:color={bpmDelta !== null && bpmDelta !== 0 ? bpmDeltaColor : 'var(--text-2)'}
					title="{Math.round(track.bpm)} BPM{bpmDelta !== null && bpmDelta !== 0 ? ` (${bpmDelta > 0 ? '+' : '−'}${Math.abs(bpmDelta)} vs this track)` : ''}"
				>
					<MetronomeIcon
						size="sm"
						label="{Math.round(track.bpm)} BPM"
						title="{Math.round(track.bpm)} BPM{bpmDelta !== null && bpmDelta !== 0 ? ` (${bpmDelta > 0 ? '+' : '−'}${Math.abs(bpmDelta)} vs this track)` : ''}"
					/>
				</span>
			{/if}
			<span
				class="cicon affinity-{strength.tone}"
				role="img"
				aria-label={matchTitle}
				title={matchTitle}
			>
				<span class="affinity-bars" aria-hidden="true">
					<span class="bar" class:on={strength.level >= 1}></span>
					<span class="bar" class:on={strength.level >= 2}></span>
					<span class="bar" class:on={strength.level >= 3}></span>
				</span>
			</span>
			{#if track.rating && track.rating > 0}
				<span class="cicon cicon-stars" title="Your rating: {track.rating} of 5">
					<StarRating rating={track.rating} display="compact" size="md" />
				</span>
			{/if}
		</div>

		<!-- Divider -->
		<div class="zone-divider"></div>

		<!-- RELATED Tier 3: Track signals — score (lead) · rating · affinity strength -->
		<div class="zone-signals">
			<div class="signal-score" title="Match score {scoreDisplay} out of 100">
				<span class="score-number">{scoreDisplay}</span><span class="score-suffix">/100</span>
			</div>
			<div class="signal-rating" title={track.rating && track.rating > 0 ? `Your rating: ${track.rating} of 5` : 'Unrated'}>
				{#if track.rating && track.rating > 0}
					<StarRating rating={track.rating} display="compact" size="sm" />
				{:else}
					<span class="signal-empty">—</span>
				{/if}
			</div>
			<div
				class="signal-affinity affinity-{strength.tone}"
				title={matchTitle}
			>
				<span class="affinity-bars" aria-hidden="true">
					<span class="bar" class:on={strength.level >= 1}></span>
					<span class="bar" class:on={strength.level >= 2}></span>
					<span class="bar" class:on={strength.level >= 3}></span>
				</span>
				<span class="affinity-text">{matchWord}</span>
			</div>
		</div>
	{:else}
		<!-- ── STANDALONE Tier 2: ABSOLUTE attribute chips — key / BPM / energy zone.
		     No reference track, so NO harmony-move glyph and NO BPM delta. Uses the
		     `plain` Chip mode (bare colored text, no box) for a lighter read since
		     these are descriptive facts, not transition deltas. ── -->
		<div class="zone-chips">
			{#if track.key}
				<Chip
					variant="key"
					mode="plain"
					color={getCamelotColor(track.key)}
					value={formatKey(track.key)}
					title="Camelot key {formatKey(track.key)}"
				/>
			{/if}
			{#if track.bpm}
				<Chip variant="bpm" mode="plain" value={Math.round(track.bpm)} title="Tempo {Math.round(track.bpm)} BPM" />
			{/if}
			{#if energyZone}
				<div class="energy-chip" title="Energy zone: {capFirst(energyZone)}">
					<Chip variant="energy" mode="plain" color={zoneColor} value={capFirst(energyZone)} title="Energy zone: {capFirst(energyZone)}" />
				</div>
			{/if}
		</div>

		<!-- Compact-tier ONLY: absolute color-coded icons (no comparison). key dot ·
		     metronome · N★. No harmony move, no match-strength bars — there is no
		     reference track, so those signals must NOT render. -->
		<div class="compact-icons compact-icons--standalone">
			{#if track.key}
				<span class="cicon" style="color: {getCamelotColor(track.key)}" title="Camelot key {formatKey(track.key)}">
					<span class="key-dot" aria-hidden="true"></span>
					<span class="sr-only">Key {formatKey(track.key)}</span>
				</span>
			{/if}
			{#if track.bpm}
				<span class="cicon" style:color={'var(--text-2)'} title="{Math.round(track.bpm)} BPM">
					<MetronomeIcon size="sm" label="{Math.round(track.bpm)} BPM" title="{Math.round(track.bpm)} BPM" />
				</span>
			{/if}
			{#if track.rating && track.rating > 0}
				<span class="cicon cicon-stars" title="Your rating: {track.rating} of 5">
					<StarRating rating={track.rating} display="compact" size="md" />
				</span>
			{/if}
		</div>

		<!-- Divider -->
		<div class="zone-divider"></div>

		<!-- ── STANDALONE Tier 3: the track's OWN quality read — rating · plays ·
		     energy settledness. NO match score (no reference), NO affinity bars,
		     NO harmony move. Three balanced columns, same layout as related so a
		     mixed grid still aligns. ── -->
		<div class="zone-signals">
			<div class="signal-rating signal-rating--lead" title={track.rating && track.rating > 0 ? `Your rating: ${track.rating} of 5` : 'Unrated — neutral weight in transitions'}>
				{#if track.rating && track.rating > 0}
					<StarRating rating={track.rating} display="compact" size="sm" />
				{:else}
					<span class="signal-empty">—</span>
				{/if}
			</div>
			<div class="signal-plays" title={playCount > 0 ? `Played ${playCount}× (Rekordbox + Kiku)` : 'Never played'}>
				{#if playCount > 0}
					<span class="plays-number">{playCount}</span><span class="plays-suffix">×</span>
				{:else}
					<span class="signal-empty">—</span>
				{/if}
			</div>
			<div class="signal-fit fit-{energyFit.tone}" title={energyFit.title}>
				<span class="fit-text">{energyFit.word}</span>
			</div>
		</div>
	{/if}
</div>

<!-- Context menu — affinity rows only apply in RELATED mode. -->
<Menu bind:open={menuOpen} x={menuX} y={menuY} label={mode.kind === 'related' ? 'Related track actions' : 'Track actions'}>
	{#if mode.kind === 'related'}
		<MenuItem onselect={() => handleAffinity('good')}>
			{#snippet icon()}<span style="color: var(--accent)">&#9679;</span>{/snippet}
			Great together
		</MenuItem>
		<MenuItem onselect={() => handleAffinity('bad')}>
			{#snippet icon()}<span style="color: var(--destructive)">&#9679;</span>{/snippet}
			Not for me
		</MenuItem>
		{#if affinity}
			<MenuItem onselect={handleRemoveAffinity}>
				{#snippet icon()}&#10005;{/snippet}
				Remove opinion
			</MenuItem>
		{/if}
		<MenuSeparator />
	{/if}
	<MenuItem onselect={handlePlay}>
		{#snippet icon()}&#9654;{/snippet}
		Play
	</MenuItem>
	<MenuItem onselect={handleOpenTrack}>
		{#snippet icon()}&#8599;{/snippet}
		Open track
	</MenuItem>
</Menu>

<style>
	/* ── Card Container ── */
	/* The card is a size container, so its inner tiers can adapt to the card's
	 * real laid-out width (whatever grid density it lands in) rather than the
	 * viewport. The Tier-2 chip priority and Tier-3 signal compaction both key
	 * off @container width below — no JS measurement needed. */
	.similar-card {
		container-type: inline-size;
		container-name: relcard;
		background: var(--surface-2);
		border: var(--space-px) solid var(--border-subtle);
		border-radius: var(--radius-xl);
		cursor: pointer;
		transition: border-color var(--dur-fast) var(--ease-standard);
		display: flex;
		flex-direction: column;
		flex: 1; /* fill the equal-height grid cell */
		min-width: 0;
		overflow: hidden;
	}

	/* Push the signals row to the bottom so it lines up across all cards. The
	 * divider sits between the (hidden-at-regular) compact-icons row and the signals
	 * row, so the margin goes on the divider that precedes the signals. */
	.compact-icons + .zone-divider {
		margin-top: auto;
	}

	.similar-card:hover {
		border-color: var(--border-strong);
	}

	/* ── Zone Divider ── */
	.zone-divider {
		height: var(--space-px);
		background: currentColor;
		opacity: 0.08;
	}

	/* ── Tier 1: Identity ── */
	.zone-header {
		display: flex;
		gap: var(--space-md);
		align-items: flex-start;
		padding: var(--space-md) var(--space-md) var(--space-sm);
	}

	.artwork-wrap {
		width: 38px;
		height: 38px;
		flex-shrink: 0;
		border-radius: var(--radius-md);
		overflow: hidden;
		background: var(--surface-1);
	}

	.artwork-img {
		width: 100%;
		height: 100%;
		object-fit: cover;
		display: block;
	}

	.artwork-fallback {
		width: 100%;
		height: 100%;
		display: flex;
		align-items: center;
		justify-content: center;
		color: var(--text-4);
	}

	.artwork-fallback svg {
		width: var(--space-3xl);
		height: var(--space-3xl);
	}

	.text-col {
		flex: 1;
		min-width: 0;
		display: flex;
		flex-direction: column;
		gap: var(--space-2xs);
	}

	/* Title + artist: one line each, ellipsis on overflow, full value on hover
	 * (content-conventions §2). No -webkit-line-clamp wrap. */
	.track-title {
		font-size: var(--text-sm);
		font-weight: var(--font-weight-medium);
		line-height: var(--lh-sm);
		color: var(--text-1);
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	/* Artist + genre on one identity subtitle line. Genre is descriptive identity
	 * metadata (not a transition signal), so it lives here in Tier 1 — not in the
	 * chip row. The artist is plain muted text and ellipsizes FIRST under width
	 * pressure; the genre is genre-family-COLORED TEXT (no box) — the color is the
	 * signal, so it stays legible while staying lightweight. Full artist/genre value
	 * on hover via title (§2). */
	.track-meta {
		display: flex;
		align-items: baseline;
		gap: var(--space-xs);
		min-width: 0;
		font-size: var(--text-xs);
		line-height: var(--lh-sm);
	}

	.track-artist {
		color: var(--text-2);
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
		min-width: 0;
		/* Artist yields space first so the genre word stays visible. */
		flex-shrink: 1;
	}

	/* Separator between artist and genre — muted, never shrinks. */
	.meta-dot {
		flex-shrink: 0;
		color: var(--text-4);
	}

	/* Genre as genre-family-COLORED TEXT (NO background/border): the color is the
	 * only signal. Uses the tokenized genre color (--chip-genre-fg, cerceta-aware)
	 * so it never hardcodes hex and re-themes automatically. Holds its intrinsic
	 * width (does not shrink) so the artist ellipsizes first, then 1-line ellipsis +
	 * `title` hover if the genre itself overflows. */
	.track-genre {
		flex-shrink: 0;
		min-width: 0;
		color: var(--chip-genre-fg);
		font-weight: var(--font-weight-medium);
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.menu-area {
		flex-shrink: 0;
		display: flex;
		align-items: center;
		gap: var(--space-xs);
		position: relative;
	}

	.menu-btn {
		background: none;
		border: none;
		color: var(--text-4);
		cursor: pointer;
		font-size: var(--text-lg);
		/* padding keeps the hit target ≈32px even with a small glyph (§5). */
		padding: var(--space-xs) var(--space-sm);
		border-radius: var(--radius-sm);
		line-height: 1;
		transition: background var(--dur-fast) var(--ease-standard), color var(--dur-fast) var(--ease-standard);
	}

	.menu-btn:hover {
		background: var(--surface-3);
		color: var(--text-1);
	}

	/* ── Tier 2: Attribute chips ── */
	/* Whole-chip priority: chips never shrink, so they are never clipped mid-word.
	 * The energy chip is hidden as a whole unit (container query, below) when it
	 * would not fit; key + BPM always show. overflow:hidden is a final safety net. */
	.zone-chips {
		display: flex;
		align-items: center;
		flex-wrap: nowrap;
		gap: var(--space-xs);
		padding: var(--space-sm) var(--space-md);
		overflow: hidden;
	}
	/* Chips never shrink, so a chip is never clipped mid-word; a whole chip is
	 * hidden instead (energy, below). */
	.zone-chips :global(.chip) {
		flex-shrink: 0;
	}

	.energy-chip {
		display: inline-flex;
		flex-shrink: 0;
		min-width: 0;
	}

	/* ── Compact-tier icon row ── color-coded ICONS ONLY (no text/numbers/chips).
	 * Hidden at regular + intermediate; revealed at the compact tier (below) where
	 * the card becomes a dense pill. Each icon's color carries the signal; the
	 * distinct SHAPES (harmony glyph, metronome, strength bars, stars) keep color
	 * from being the only cue, and per-icon title/aria-label preserve the real
	 * value. */
	/* Compact icon row — icons are EVENLY DISTRIBUTED across the full width
	 * (space-between), not bunched-left with the star flung to the far edge. Each
	 * icon owns an equal slot so harmony · metronome · match-bars · stars read as
	 * a balanced row. */
	.compact-icons {
		display: none;
		align-items: center;
		justify-content: space-between;
		gap: var(--space-sm);
		padding: 0 var(--space-md) var(--space-md);
		margin-top: auto;
	}
	.cicon {
		display: inline-flex;
		align-items: center;
		flex-shrink: 0;
		line-height: 0;
		position: relative;
	}
	/* the match-bars icon colors by affinity strength via the shared mapping. */
	.cicon.affinity-success { --strength-color: var(--score-excellent); }
	.cicon.affinity-warn { --strength-color: var(--score-good); }
	.cicon.affinity-danger { --strength-color: var(--score-poor); }
	.cicon.affinity-success,
	.cicon.affinity-warn,
	.cicon.affinity-danger { color: var(--strength-color); }
	.compact-icons :global(.harmony-icon--sm),
	.compact-icons :global(.metronome-icon--sm) {
		width: var(--icon-size-sm);
		height: var(--icon-size-sm);
	}

	/* Standalone compact key swatch — a small colored dot standing in for the
	 * absolute Camelot key (no harmony move to draw). Color paired with the
	 * sr-only key text, so it is never color-only. */
	.key-dot {
		width: var(--icon-size-sm);
		height: var(--icon-size-sm);
		border-radius: var(--radius-full);
		background: currentColor;
		display: inline-block;
	}
	.sr-only {
		position: absolute;
		width: 1px;
		height: 1px;
		padding: 0;
		margin: -1px;
		overflow: hidden;
		clip: rect(0, 0, 0, 0);
		white-space: nowrap;
		border: 0;
	}

	/* Bold the compact N★ COUNT wherever it appears in the card (the compact-pill
	 * icon row and the regular-tier rating column), matching the semibold weight
	 * the score/rating numbers use elsewhere. Card-scoped :global() so StarRating
	 * stays untouched and other compact-star sites are unaffected. The star glyph
	 * itself keeps its normal weight. */
	.cicon-stars :global(.star-compact__count),
	.signal-rating :global(.star-compact__count) {
		font-weight: var(--font-weight-semibold);
		color: var(--text-1);
	}

	/* BPM chip internals — the metronome glyph (auto-rendered by the bpm variant)
	 * leads, then the number, then the signed delta. No literal "BPM" text. */
	.bpm-num {
		font-weight: var(--font-weight-semibold);
		font-variant-numeric: tabular-nums;
		color: var(--text-1);
	}
	.bpm-delta {
		font-variant-numeric: tabular-nums;
		font-weight: var(--font-weight-medium);
	}
	/* the harmony + metronome glyphs ride inside their chips at the shared icon size. */
	.zone-chips :global(.harmony-icon--sm),
	.zone-chips :global(.metronome-icon--sm) {
		width: var(--icon-size-sm);
		height: var(--icon-size-sm);
	}

	/* ── Tier 3: Track signals — THREE BALANCED columns: score · rating · match ──
	 * `repeat(3, minmax(0,1fr))` gives each signal an equal third, so they read as
	 * aligned columns down a row of cards (no bunch-left + dead-gap-right). Column
	 * content alignment reads like a table:
	 *   1) score NN/100 — START (left), the lead/anchor,
	 *   2) rating N★ / — — CENTER, balances the row's middle third,
	 *   3) match — END (right), so the verdict sits at the card's trailing edge.
	 * min-width:0 (via minmax) lets the match column ellipsize within its third
	 * instead of forcing the row wider than the narrow card. */
	.zone-signals {
		display: grid;
		grid-template-columns: repeat(3, minmax(0, 1fr));
		align-items: center;
		gap: var(--space-sm);
		padding: var(--space-sm) var(--space-md) var(--space-md);
	}

	/* Score is the headline verdict — visually heaviest, sits in column 1. */
	.signal-score {
		display: flex;
		align-items: baseline;
		min-width: 0;
	}
	.score-number {
		font-size: var(--text-lg);
		font-weight: var(--font-weight-semibold);
		color: var(--text-1);
		font-variant-numeric: tabular-nums;
		line-height: 1;
	}
	.score-suffix {
		font-size: var(--text-xs);
		color: var(--text-3);
		margin-left: var(--space-2xs);
	}

	/* Rating sits in the CENTER of its middle third (L/C/R balance across the
	 * three signal columns). */
	.signal-rating {
		display: flex;
		align-items: center;
		justify-content: center;
		min-width: 0;
	}
	/* In standalone mode the rating IS the lead signal (column 1, no score), so it
	 * aligns START to read as the headline of the row. */
	.signal-rating--lead {
		justify-content: flex-start;
	}
	.signal-empty {
		color: var(--text-4);
		font-size: var(--text-sm);
	}

	/* Standalone play count (column 2, centered) — the DJ's own usage signal. */
	.signal-plays {
		display: flex;
		align-items: baseline;
		justify-content: center;
		min-width: 0;
	}
	.plays-number {
		font-size: var(--text-md);
		font-weight: var(--font-weight-semibold);
		color: var(--text-1);
		font-variant-numeric: tabular-nums;
		line-height: 1;
	}
	.plays-suffix {
		font-size: var(--text-xs);
		color: var(--text-3);
		margin-left: var(--space-2xs);
	}

	/* Standalone energy settledness (column 3, trailing edge) — the track's OWN
	 * energy-read confidence, NOT a pair-wise match. Word + tokenized color,
	 * never color alone (§4). */
	.signal-fit {
		display: flex;
		align-items: center;
		justify-content: flex-end;
		min-width: 0;
		--fit-color: var(--text-3);
	}
	.fit-success { --fit-color: var(--score-excellent); }
	.fit-warn { --fit-color: var(--score-good); }
	.fit-muted { --fit-color: var(--text-3); }
	.fit-text {
		font-size: var(--text-xs);
		font-weight: var(--font-weight-medium);
		color: var(--fit-color);
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	/* Affinity as a labelled qualitative strength — bar + word, never a raw
	 * number and never color alone (content-conventions §3, §4). Sits at the END of
	 * its 1fr column (trailing edge), so it reads as the right-most aligned column
	 * across a row of cards. */
	.signal-affinity {
		display: flex;
		align-items: center;
		justify-content: flex-end;
		gap: var(--space-xs);
		min-width: 0;
		--strength-color: var(--text-3);
	}
	.affinity-success { --strength-color: var(--score-excellent); }
	.affinity-warn { --strength-color: var(--score-good); }
	.affinity-danger { --strength-color: var(--score-poor); }

	.affinity-bars {
		display: inline-flex;
		align-items: flex-end;
		gap: var(--space-px);
		flex-shrink: 0;
	}
	.affinity-bars .bar {
		width: var(--space-2xs);
		height: var(--space-sm);
		border-radius: var(--radius-xs);
		background: var(--surface-3);
	}
	.affinity-bars .bar.on {
		background: var(--strength-color);
	}

	.affinity-text {
		font-size: var(--text-xs);
		font-weight: var(--font-weight-medium);
		color: var(--strength-color);
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	/* Context-menu rows come from the <Menu>/<MenuItem> primitives. */

	/* ── Add to Set Popover ── */
	.add-picker-popover {
		position: absolute;
		top: 100%;
		right: 0;
		margin-top: var(--space-xs);
		background: var(--surface-1);
		border: var(--space-px) solid var(--border-subtle);
		border-radius: var(--radius-lg);
		box-shadow: var(--elev-3);
		z-index: 10;
		min-width: 220px;
	}

	/* ── Responsive tiers (container queries on the card's inline size) ──
	 * Placed LAST so they win over the base rules above by source order (container
	 * queries add no specificity). The card adapts to its real laid-out column
	 * width, not the viewport, so it works at any grid density. Three tiers:
	 *
	 *   • Regular   (≥ 240px) — the full card (the base rules above): identity with
	 *                 artist + genre colored text · chips key→BPM→energy · 3-col
	 *                 signals (score L · rating C · match R).
	 *   • Intermediate (200–240px) — tighten only: smaller artwork, reduced
	 *                 padding/gaps. Genre colored text STAYS; all THREE chips
	 *                 (key + BPM + energy) STAY (no "+1"); signals stay 3-col.
	 *   • Compact   (< 200px) — RESTRUCTURED into a dense PILL: Row 1 small artwork +
	 *                 title + ⋮; Row 2 a single row of evenly-distributed COLOR-CODED
	 *                 ICONS (harmony · metronome · match bars · N★). Numbers, key/BPM
	 *                 text, genre, energy and the + action are hidden. */

	/* ── Intermediate (≤ 240px) ── */
	@container relcard (max-width: 240px) {
		.zone-header {
			gap: var(--space-sm);
			padding: var(--space-sm) var(--space-sm) var(--space-2xs);
		}
		.artwork-wrap {
			width: 30px;
			height: 30px;
		}
		/* Genre STAYS at the intermediate tier — it is now lightweight colored text,
		 * not a chip, so it costs almost no width. Only the compact tier hides it. */
		/* All THREE chips (key + BPM + energy) STAY at the intermediate tier: with
		 * the metronome glyph replacing the literal "BPM" text the bpm chip is short
		 * enough that key + BPM + energy fit, so the energy chip no longer drops and
		 * the "+1" overflow affordance is not needed here. (The +1 only surfaces if
		 * chips genuinely overflow — they don't at this width.) */
		.zone-chips {
			gap: var(--space-2xs);
			padding: var(--space-xs) var(--space-sm);
		}
		.zone-signals {
			gap: var(--space-sm);
			padding: var(--space-2xs) var(--space-sm) var(--space-sm);
		}
	}

	/* ── Compact (< 200px) — DENSE PILL, color-coded icons only ──
	 * The card is space-starved here, so it becomes a minimal, badge-like PILL:
	 * rounder corners, no chips, no numbers, no text values. Top: small artwork +
	 * 1-line title (+ ⋮ only if it fits). Below: a single row of COLOR-CODED ICONS —
	 * harmony glyph · metronome · match-strength bars · N★ — where icon SHAPE + COLOR
	 * + the star count carry the whole signal. Everything else is hidden: the numeric
	 * score, key text, BPM number, genre, energy, the + action, both dividers and the
	 * whole chip + signals rows. Per-icon title/aria-label keep the real values, so
	 * nothing is lost and color is never the only cue. Legible/no-overlap to ~180px. */
	@container relcard (max-width: 200px) {
		/* pill treatment — rounder so the dense variant reads as distinct. */
		.similar-card {
			border-radius: var(--radius-full);
		}
		/* Top: artwork + title (+ ⋮). The + action, both dividers, the full chip row
		 * and the signals row are all hidden; the icon row replaces them. */
		.zone-divider,
		.zone-signals,
		.zone-chips,
		.add-btn {
			display: none;
		}
		/* Genre and the artist·genre dot drop — the icon row carries the signal
		 * instead. (The energy chip drops here too, as part of the whole .zone-chips
		 * row being hidden above.) */
		.track-genre,
		.meta-dot {
			display: none;
		}
		.zone-header {
			padding: var(--space-sm) var(--space-md) var(--space-2xs) var(--space-sm);
		}
		.artwork-wrap {
			width: 28px;
			height: 28px;
		}
		/* the icon row becomes the bottom row, pushed down so cards align. Icons
		 * stay EVENLY DISTRIBUTED (space-between from the base rule) across the
		 * pill's width — not bunched left. */
		.compact-icons {
			display: flex;
			padding: var(--space-2xs) var(--space-md) var(--space-sm) var(--space-md);
		}
	}
</style>
