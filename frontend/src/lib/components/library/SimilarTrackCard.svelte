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
			<span class="track-artist" title={artistText}>{capFirst(artistText)}</span>
		</div>

		<div class="menu-area">
			<button
				class="menu-btn"
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

	<!-- Tier 2: Attribute chips — priority key → BPM → energy → genre.
	     No-wrap; lowest-priority chips drop first when space is tight. -->
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
			<Chip variant="bpm" tone={bpmDeltaTone} title="Tempo {Math.round(track.bpm)} BPM">
				<span class="bpm-num">{Math.round(track.bpm)}</span>
				<span class="bpm-unit">BPM</span>
				{#if bpmDelta !== null && bpmDelta !== 0}
					<span
						class="bpm-delta"
						title="{Math.abs(bpmDelta)} BPM {bpmDelta > 0 ? 'faster' : 'slower'} than this track"
					>{bpmDelta > 0 ? '+' : '−'}{Math.abs(bpmDelta)}</span>
				{/if}
			</Chip>
		{/if}
		{#if energyZone}
			<Chip variant="energy" color={zoneColor} value={capFirst(energyZone)} title="Energy zone: {capFirst(energyZone)}" />
		{/if}
		{#if genreLabel}
			<Chip variant="genre" value={capFirst(genreLabel)} title={genreLabel} />
		{/if}
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
	.similar-card {
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

	.track-artist {
		font-size: var(--text-xs);
		color: var(--text-2);
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
	.zone-chips {
		display: flex;
		align-items: center;
		flex-wrap: nowrap;
		gap: var(--space-xs);
		padding: var(--space-sm) var(--space-md);
		overflow: hidden;
	}
	/* BPM chip internals — number leads, unit + signed delta follow. */
	.bpm-num {
		font-weight: var(--font-weight-semibold);
		font-variant-numeric: tabular-nums;
		color: var(--text-1);
	}
	.bpm-unit {
		font-size: var(--text-2xs);
		color: var(--text-4);
	}
	.bpm-delta {
		font-variant-numeric: tabular-nums;
		font-weight: var(--font-weight-medium);
	}
	/* the harmony glyph rides inside the key chip at the shared icon size. */
	.zone-chips :global(.harmony-icon--sm) {
		width: var(--icon-size-sm);
		height: var(--icon-size-sm);
	}

	/* ── Tier 3: Track signals — score · rating · affinity strength ── */
	.zone-signals {
		display: flex;
		align-items: center;
		gap: var(--space-md);
		padding: var(--space-sm) var(--space-md) var(--space-md);
	}

	/* Score is the headline verdict — visually heaviest, sits left. */
	.signal-score {
		display: flex;
		align-items: baseline;
		flex-shrink: 0;
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
</style>
