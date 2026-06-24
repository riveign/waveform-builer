<script lang="ts" module>
	/** First-letter capitalization for library text (title / artist).
	 *
	 *  USER DECISION (spec 023): the Related tracks card forces a capital first
	 *  letter on the track title and artist, overriding the previous
	 *  "preserve source casing" default. This is purely presentational — it
	 *  only upper-cases the FIRST visible character and leaves the rest of the
	 *  string byte-for-byte intact, so stylized casing the DJ relies on
	 *  (`deadmau5`, `LOUDER`, `MEDUZA`) is preserved past the first glyph and no
	 *  value is ever lost. Safe because it never mutates the underlying data —
	 *  the full original is still exposed via the `title` attribute on hover. */
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
</script>

<script lang="ts">
	import type { SuggestNextItem } from '$lib/types';
	import { getTrackArtworkUrl, setTrackAffinity, removeTrackAffinity } from '$lib/api/tracks';
	import StarRating from './StarRating.svelte';
	import Chip from '../primitives/Chip.svelte';
	import Stack from '../primitives/Stack.svelte';
	import Menu from '../primitives/Menu.svelte';
	import MenuItem from '../primitives/MenuItem.svelte';
	import MenuSeparator from '../primitives/MenuSeparator.svelte';
	import AddToSetPicker from '../set/AddToSetPicker.svelte';
	import { getPlayerStore } from '$lib/stores/player.svelte';
	import { getUiStore } from '$lib/stores/ui.svelte';
	import { getCamelotColor, formatKey, keyMoveLabel } from '$lib/utils/camelot';
	import HarmonyIcon, { toHarmonyRelation, HARMONY_RELATION_LABEL } from '$lib/components/primitives/HarmonyIcon.svelte';

	let {
		item,
		parentTrackId,
		parentBpm = null,
		parentKey = null,
		affinity = null,
		onaffinitychange,
	}: {
		item: SuggestNextItem;
		parentTrackId: number;
		parentBpm?: number | null;
		parentKey?: string | null;
		affinity?: string | null;
		onaffinitychange?: (trackId: number, newAffinity: string | null) => void;
	} = $props();

	const player = getPlayerStore();
	const ui = getUiStore();

	let artworkFailed = $state(false);
	let menuOpen = $state(false);
	let menuX = $state(0);
	let menuY = $state(0);
	let isSelected = $state(false);
	let showAddPicker = $state(false);

	// Reset artwork error when item changes
	$effect(() => {
		item.track.id;
		artworkFailed = false;
	});

	const track = $derived(item.track);
	const energyZone = $derived(track.resolved_energy ?? null);
	const genreLabel = $derived(track.genre_family ?? track.genre ?? null);
	const scoreDisplay = $derived(Math.round(item.score * 100));
	const strength = $derived(scoreStrength(item.score));

	// First-letter-capped, full value preserved past the first glyph (capFirst).
	const titleText = $derived(track.title ?? 'Unknown');
	const artistText = $derived(track.artist ?? 'Unknown');

	// BPM integer + signed colored delta. Tone follows the ±6% tension rule
	// (content-conventions §3): within 6% reads neutral, beyond reads warn.
	const bpmDelta = $derived.by(() => {
		if (!track.bpm || !parentBpm) return null;
		return Math.round(track.bpm) - Math.round(parentBpm);
	});
	const bpmDeltaTone = $derived.by<'default' | 'warn'>(() => {
		if (bpmDelta === null || !parentBpm) return 'default';
		return Math.abs(bpmDelta) / parentBpm > 0.06 ? 'warn' : 'default';
	});

	// Harmonic move from the current track — same vocabulary as the Harmonic
	// mixing card (energy up/down, mood switch, same key, distant keys).
	const harmony = $derived.by(() => {
		if (!track.key || !parentKey) return null;
		return keyMoveLabel(parentKey, track.key);
	});
	// Compact icon per harmonic move — the standardized HarmonyIcon glyph.
	const harmonyRelation = $derived(harmony ? toHarmonyRelation(harmony.label) : null);
	// Key chip color comes from the harmony quality (meaning), pairing the
	// Camelot text with the move glyph so color is never the only cue (§4).
	const keyColor = $derived.by(() => {
		if (!harmony) return getCamelotColor(track.key);
		if (harmony.score >= 0.8) return 'var(--score-excellent)';
		if (harmony.score >= 0.55) return 'var(--score-good)';
		return 'var(--score-poor)';
	});

	// Energy zone color from the shared --zone-* token set (single source).
	const ZONES = ['intro', 'warmup', 'build', 'drive', 'peak', 'close'];
	const zoneColor = $derived(
		energyZone && ZONES.includes(energyZone) ? `var(--zone-${energyZone})` : 'var(--text-2)',
	);

	const affinityLabel = $derived(
		affinity === 'good' ? 'Great together' : affinity === 'bad' ? 'Not for me' : null,
	);

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
		try {
			await setTrackAffinity(parentTrackId, track.id, value);
			onaffinitychange?.(track.id, value);
		} catch {
			// Silently fail — affinity API may not exist yet
		}
	}

	async function handleRemoveAffinity() {
		menuOpen = false;
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
	class:selected={isSelected}
	role="button"
	tabindex="0"
	draggable="true"
	onclick={handleCardClick}
	oncontextmenu={handleContextMenu}
	ondragstart={handleDragStart}
	onkeydown={(e) => { if (e.key === 'Enter') handleCardClick(); }}
>
	<!-- Tier 1: Identity — artwork + title/artist + actions -->
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
			     width pressure) + a visible genre CHIP. Genre is a small genre-colored
			     Chip rather than muted text so it reads as clearly as the key/energy
			     chips. The genre chip is HIDDEN at the compact tier (space too tight).
			     Genre stays OUT of the Tier-2 chip row (that caused the prior overflow). -->
			<span class="track-meta">
				<span class="track-artist" title={artistText}>{capFirst(artistText)}</span>
				{#if genreLabel}
					<span class="track-genre" title="Genre: {genreLabel}">
						<Chip variant="genre" size="sm" value={capFirst(genreLabel)} title="Genre: {genreLabel}" />
					</span>
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

	<!-- Tier 2: Attribute chips — priority key → BPM → energy.
	     Whole-chip priority hiding via a CSS container query on the card: key +
	     BPM are transition-critical and ALWAYS show; the energy chip drops as a
	     WHOLE unit when the card is too narrow (never clipped mid-word). This
	     responds to the card's real laid-out width, so it adapts to whatever grid
	     density (4-up ~250px, 6-up ~210px, expanded) the card lands in. Genre
	     lives in Tier 1 (identity), not here. overflow:hidden is a final safety
	     net only. -->
	<div class="zone-chips">
		<!-- Compact-tier score: at <200px the signals row is dropped and the score
		     moves up onto this line (NN/100 · key · BPM · match). Hidden at the
		     regular + intermediate tiers, where the score lives in the signals row. -->
		<span class="chips-score" title="Match score {scoreDisplay} out of 100">
			<span class="score-number">{scoreDisplay}</span><span class="score-suffix">/100</span>
		</span>
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
			<Chip variant="bpm" tone={bpmDeltaTone} title="Tempo {Math.round(track.bpm)} BPM">
				<span class="bpm-num">{Math.round(track.bpm)}</span>
				{#if bpmDelta !== null && bpmDelta !== 0}
					<span
						class="bpm-delta"
						title="{Math.abs(bpmDelta)} BPM {bpmDelta > 0 ? 'faster' : 'slower'} than this track"
					>{bpmDelta > 0 ? '+' : '−'}{Math.abs(bpmDelta)}</span>
				{/if}
			</Chip>
		{/if}
		{#if energyZone}
			<!-- Energy chip: stays in the DOM so its hover title always resolves;
			     a container query hides the whole chip when the card is narrow. -->
			<div class="energy-chip" title="Energy zone: {capFirst(energyZone)}">
				<Chip variant="energy" color={zoneColor} value={capFirst(energyZone)} title="Energy zone: {capFirst(energyZone)}" />
			</div>
			<!-- Discoverability for the dropped chip: a subtle "+1" that only shows
			     (via the same container query) when energy is hidden, revealing the
			     full value on hover. Never clips a chip. -->
			<span class="chips-more" title="Energy zone: {capFirst(energyZone)}">+1</span>
		{/if}
		<!-- Compact-tier match: bar + word, pushed right onto Row 2. Hidden at the
		     regular + intermediate tiers (match lives in the signals row there). -->
		<span
			class="chips-match affinity-{strength.tone}"
			title={affinityLabel ? `${affinityLabel} · ${strength.label} match` : `${strength.label} match`}
		>
			<span class="affinity-bars" aria-hidden="true">
				<span class="bar" class:on={strength.level >= 1}></span>
				<span class="bar" class:on={strength.level >= 2}></span>
				<span class="bar" class:on={strength.level >= 3}></span>
			</span>
			<span class="affinity-text">{affinityLabel ?? `${strength.label} match`}</span>
		</span>
	</div>

	<!-- Divider -->
	<div class="zone-divider"></div>

	<!-- Tier 3: Track signals — score (lead) · rating · affinity strength -->
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
			title={affinityLabel ? `${affinityLabel} · ${strength.label} match` : `${strength.label} match`}
		>
			<span class="affinity-bars" aria-hidden="true">
				<span class="bar" class:on={strength.level >= 1}></span>
				<span class="bar" class:on={strength.level >= 2}></span>
				<span class="bar" class:on={strength.level >= 3}></span>
			</span>
			<span class="affinity-text">{affinityLabel ?? `${strength.label} match`}</span>
		</div>
	</div>
</div>

<!-- Context menu -->
<Menu bind:open={menuOpen} x={menuX} y={menuY} label="Related track actions">
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

	/* Push the signals row to the bottom so it lines up across all cards. */
	.zone-chips + .zone-divider {
		margin-top: auto;
	}

	.similar-card:hover {
		border-color: var(--border-strong);
	}

	.similar-card.selected {
		border: var(--space-2xs) solid var(--accent);
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
	 * pressure; the genre CHIP stays fixed and visible so genre reads as clearly as
	 * the key/energy chips. Full artist value on hover via title (§2). */
	.track-meta {
		display: flex;
		align-items: center;
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
		/* Artist yields space first so the genre chip stays visible. */
		flex-shrink: 1;
	}

	/* The genre chip wrapper holds its intrinsic width — it does not shrink, so the
	 * genre stays legible while the artist text ellipsizes around it. */
	.track-genre {
		flex-shrink: 0;
		min-width: 0;
		display: inline-flex;
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

	/* "+1" affordance for the dropped energy chip — hidden by default (energy is
	 * visible at wide widths); revealed by the intermediate/compact tiers below.
	 * Tiny, muted, full value on hover, never clips. */
	.chips-more {
		display: none;
		flex-shrink: 0;
		font-size: var(--text-2xs);
		font-weight: var(--font-weight-medium);
		color: var(--text-4);
		padding: 0 var(--space-2xs);
		cursor: default;
	}

	/* Compact-tier-only elements — hidden at the regular + intermediate tiers,
	 * where the score + match live in the dedicated signals row. At the compact
	 * tier the signals row is dropped and these move onto the chip line. */
	.chips-score {
		display: none;
		flex-shrink: 0;
		align-items: baseline;
	}
	.chips-match {
		display: none;
		flex-shrink: 0;
		align-items: center;
		gap: var(--space-xs);
		margin-left: auto;
		--strength-color: var(--text-3);
	}
	.chips-match.affinity-success { --strength-color: var(--score-excellent); }
	.chips-match.affinity-warn { --strength-color: var(--score-good); }
	.chips-match.affinity-danger { --strength-color: var(--score-poor); }
	.chips-match .affinity-text {
		font-size: var(--text-2xs);
		font-weight: var(--font-weight-medium);
		color: var(--strength-color);
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
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

	/* ── Tier 3: Track signals — 3-column grid: score · rating · match ──
	 * Three explicit columns so cards in a row read as aligned columns:
	 *   1) score NN/100 — sized to its content (the lead/anchor),
	 *   2) rating N★ / — — sized to its content,
	 *   3) match — takes the remaining space (1fr), right-aligned.
	 * min-width:0 on the cells lets the match column ellipsize instead of
	 * forcing the row wider than the narrow card. */
	.zone-signals {
		display: grid;
		grid-template-columns: auto auto minmax(0, 1fr);
		align-items: center;
		gap: var(--space-md);
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

	.signal-rating {
		flex-shrink: 0;
	}
	.signal-empty {
		color: var(--text-4);
		font-size: var(--text-sm);
	}

	/* Affinity as a labelled qualitative strength — bar + word, never a raw
	 * number and never color alone (content-conventions §3, §4). Pushed right. */
	.signal-affinity {
		display: flex;
		align-items: center;
		gap: var(--space-xs);
		margin-left: auto;
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
	 *                 artist + genre chip · chips key→BPM→energy · 3-col signals.
	 *   • Intermediate (200–240px) — tighten: smaller artwork, reduced padding/gaps;
	 *                 genre chip drops (artist only); energy chip drops (→ "+1");
	 *                 chips = key(+harmony) + BPM; signals stay the 3-col grid.
	 *   • Compact   (< 200px) — RESTRUCTURED into a dense 2-line layout: Row 1 small
	 *                 artwork + title + ⋮; Row 2 NN/100 · key · BPM · match. Stars,
	 *                 energy, genre and the + action are hidden. */

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
		/* genre chip drops — artist alone on the subtitle line. */
		.track-genre {
			display: none;
		}
		/* energy chip drops as a whole unit; "+1" surfaces in its place. */
		.energy-chip {
			display: none;
		}
		.chips-more {
			display: inline-flex;
			align-items: center;
		}
		.zone-chips {
			gap: var(--space-2xs);
			padding: var(--space-xs) var(--space-sm);
		}
		.zone-signals {
			gap: var(--space-sm);
			padding: var(--space-2xs) var(--space-sm) var(--space-sm);
		}
	}

	/* ── Compact (≤ 200px) — restructured 2-line layout ── */
	@container relcard (max-width: 200px) {
		/* Row 1: artwork + title + ⋮ only. The + action and the dividers go away;
		 * the signals row is dropped entirely and its data moves onto Row 2. */
		.zone-divider,
		.zone-signals,
		.add-btn {
			display: none;
		}
		.zone-header {
			padding: var(--space-sm) var(--space-sm) var(--space-2xs);
		}
		.artwork-wrap {
			width: 28px;
			height: 28px;
		}
		/* Row 2: NN/100 · key(+harmony) · BPM · match. Score + match move up here;
		 * stars, energy and genre stay hidden (inherited from intermediate). */
		.chips-score {
			display: inline-flex;
		}
		.chips-match {
			display: inline-flex;
		}
		/* "+1" is redundant in the compact row (energy is intentionally dropped). */
		.chips-more {
			display: none;
		}
		.zone-chips {
			gap: var(--space-2xs);
			padding: 0 var(--space-sm) var(--space-sm);
			/* let the chip line use the full width; match is pushed right. */
			margin-top: auto;
		}
		.chips-score .score-number {
			font-size: var(--text-base);
		}
	}
</style>
