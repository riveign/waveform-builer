<script lang="ts">
	/* ── RelatedTrackCard — the TALLER, horizontal related-track card ──
	 *
	 * The related-tracks grid on the Track view used to run 6-up, which crushed the
	 * comparative card (TrackCard's `related` mode) down into its dense compact-pill
	 * tier: 38px artwork, no room to breathe. This card is the redesign — a roomier
	 * HORIZONTAL layout (prominent 72px artwork on the left; identity, chips and
	 * signals stacked on the right) meant to run ~3-up so every candidate reads
	 * clearly.
	 *
	 * It is comparative-only (there is always a reference/parent track), so unlike
	 * TrackCard it carries no discriminated union — every field here measures THIS
	 * track relative to the parent. Shared math is reused, not duplicated:
	 * `capFirst`/`scoreStrength` come from TrackCard; the harmony move, key color and
	 * BPM formatting come from the same camelot utils + primitives TrackCard uses. */
	import type { SuggestNextItem } from '$lib/types';
	import { getTrackArtworkUrl, setTrackAffinity, removeTrackAffinity } from '$lib/api/tracks';
	import { capFirst, scoreStrength } from './TrackCard.svelte';
	import StarRating from '../primitives/StarRating.svelte';
	import Chip from '../primitives/Chip.svelte';
	import Menu from '../primitives/Menu.svelte';
	import MenuItem from '../primitives/MenuItem.svelte';
	import MenuSeparator from '../primitives/MenuSeparator.svelte';
	import AddToSetPicker from '../set/AddToSetPicker.svelte';
	import { getPlayerStore } from '$lib/stores/player.svelte';
	import { getUiStore } from '$lib/stores/ui.svelte';
	import { getCamelotColor, formatKey, keyMoveLabel } from '$lib/utils/camelot';
	import HarmonyIcon, { toHarmonyRelation, HARMONY_RELATION_LABEL } from '../primitives/HarmonyIcon.svelte';
	import MetronomeIcon from '../primitives/MetronomeIcon.svelte';

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

	const track = $derived(item.track);

	let artworkFailed = $state(false);
	let menuOpen = $state(false);
	let menuX = $state(0);
	let menuY = $state(0);
	let showAddPicker = $state(false);

	// Reset artwork error when the track changes.
	$effect(() => {
		track.id;
		artworkFailed = false;
	});

	const energyZone = $derived(track.resolved_energy ?? null);
	const genreLabel = $derived(track.genre_family ?? track.genre ?? null);
	const titleText = $derived(track.title ?? 'Unknown');
	const artistText = $derived(track.artist ?? 'Unknown');

	const ZONES = ['intro', 'warmup', 'build', 'drive', 'peak', 'close'];
	const zoneColor = $derived(
		energyZone && ZONES.includes(energyZone) ? `var(--zone-${energyZone})` : 'var(--text-2)',
	);

	const scoreDisplay = $derived(Math.round(item.score * 100));
	const strength = $derived(scoreStrength(item.score));

	// BPM integer + signed colored delta — color by MAGNITUDE (content-conventions
	// §3): within ±6% = seamless (green), ~6–12% = moderate (orange), beyond ±12% =
	// tension (red). Always paired with the signed number, so color is never alone.
	const bpmDelta = $derived.by(() => {
		if (!track.bpm || !parentBpm) return null;
		return Math.round(track.bpm) - Math.round(parentBpm);
	});
	const bpmDeltaStrength = $derived.by<'seamless' | 'moderate' | 'tension'>(() => {
		if (bpmDelta === null || !parentBpm) return 'seamless';
		const pct = Math.abs(bpmDelta) / parentBpm;
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

	// Harmonic move from the reference track.
	const harmony = $derived.by(() => {
		if (!track.key || !parentKey) return null;
		return keyMoveLabel(parentKey, track.key);
	});
	const harmonyRelation = $derived(harmony ? toHarmonyRelation(harmony.label) : null);
	// Key chip color comes from the harmony quality (meaning); falls back to the
	// absolute Camelot color when there is no move to qualify it.
	const keyColor = $derived.by(() => {
		if (!harmony) return getCamelotColor(track.key);
		if (harmony.score >= 0.8) return 'var(--score-excellent)';
		if (harmony.score >= 0.55) return 'var(--score-good)';
		return 'var(--score-poor)';
	});

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
			JSON.stringify({ id: track.id, title: track.title }),
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
	class="related-card"
	role="button"
	tabindex="0"
	draggable="true"
	onclick={handleCardClick}
	oncontextmenu={handleContextMenu}
	ondragstart={handleDragStart}
	onkeydown={(e) => {
		// Only the card itself activates on Enter/Space — nested controls (the +/⋮
		// buttons, StarRating stars) keep their own native activation.
		if (e.target !== e.currentTarget) return;
		if (e.key === 'Enter' || e.key === ' ') {
			e.preventDefault();
			handleCardClick();
		}
	}}
>
	<!-- Prominent artwork — the roomy left column the redesign is about. -->
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

	<div class="body">
		<!-- Row 1: identity — title / artist · genre — plus the +/⋮ actions. -->
		<div class="head">
			<div class="text-col">
				<span class="track-title" title={titleText}>{capFirst(titleText)}</span>
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
							onclose={() => (showAddPicker = false)}
						/>
					</div>
				{/if}
			</div>
		</div>

		<!-- Row 2: comparative attribute chips — key + harmony move, BPM + signed
		     delta, energy zone. All measured against the reference track. -->
		<div class="chips">
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
				<Chip variant="bpm" title="Tempo {Math.round(track.bpm)} BPM">
					<span class="bpm-num">{Math.round(track.bpm)}</span>
					{#if bpmDelta !== null && bpmDelta !== 0}
						<span
							class="bpm-delta"
							style:color={bpmDeltaColor}
							title="{Math.abs(bpmDelta)} BPM {bpmDelta > 0 ? 'faster' : 'slower'} than this track — {bpmDeltaStrength === 'seamless' ? 'seamless' : bpmDeltaStrength === 'moderate' ? 'moderate shift' : 'big jump'}"
						>{bpmDelta > 0 ? '+' : '−'}{Math.abs(bpmDelta)}</span>
					{/if}
				</Chip>
			{/if}
			{#if energyZone}
				<div class="energy-chip" title="Energy zone: {capFirst(energyZone)}">
					<Chip variant="energy" color={zoneColor} value={capFirst(energyZone)} title="Energy zone: {capFirst(energyZone)}" />
				</div>
			{/if}
		</div>

		<!-- Row 3: signals — score (lead) · rating · match strength (trailing). -->
		<div class="signals">
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
			<div class="signal-affinity affinity-{strength.tone}" title={matchTitle}>
				<span class="affinity-bars" aria-hidden="true">
					<span class="bar" class:on={strength.level >= 1}></span>
					<span class="bar" class:on={strength.level >= 2}></span>
					<span class="bar" class:on={strength.level >= 3}></span>
				</span>
				<span class="affinity-text">{matchWord}</span>
			</div>
		</div>
	</div>
</div>

<!-- Context menu — opinion rows + play / open. -->
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
	/* ── Card container — horizontal: prominent artwork + stacked body. ──
	 * A size container so the inner layout can relax to a single column if it ever
	 * lands narrow, but the grid keeps it ≳300px in practice (3-up). */
	.related-card {
		container-type: inline-size;
		container-name: relcard;
		display: flex;
		gap: var(--space-lg);
		align-items: stretch;
		background: var(--surface-2);
		border: var(--space-px) solid var(--border-subtle);
		border-radius: var(--radius-xl);
		padding: var(--space-lg);
		cursor: pointer;
		transition: border-color var(--dur-fast) var(--ease-standard);
		flex: 1; /* fill the equal-height grid cell */
		min-width: 0;
		overflow: hidden;
	}

	.related-card:hover {
		border-color: var(--border-strong);
	}

	/* ── Prominent artwork — the roomy left column. ── */
	.artwork-wrap {
		width: 72px;
		height: 72px;
		flex-shrink: 0;
		border-radius: var(--radius-lg);
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
		width: var(--space-4xl);
		height: var(--space-4xl);
	}

	/* ── Body — three stacked rows (identity · chips · signals). ── */
	.body {
		flex: 1;
		min-width: 0;
		display: flex;
		flex-direction: column;
		gap: var(--space-md);
	}

	/* Row 1: identity + actions. */
	.head {
		display: flex;
		gap: var(--space-sm);
		align-items: flex-start;
	}
	.text-col {
		flex: 1;
		min-width: 0;
		display: flex;
		flex-direction: column;
		gap: var(--space-2xs);
	}
	.track-title {
		font-size: var(--text-sm);
		font-weight: var(--font-weight-medium);
		line-height: var(--lh-sm);
		color: var(--text-1);
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}
	/* Artist (plain muted, ellipsizes first) · genre (family-colored text, no box).
	 * Same identity-subtitle recipe as TrackCard (content-conventions §2, §4). */
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
		flex-shrink: 1;
	}
	.meta-dot {
		flex-shrink: 0;
		color: var(--text-4);
	}
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
		padding: var(--space-xs) var(--space-sm);
		border-radius: var(--radius-sm);
		line-height: 1;
		transition: background var(--dur-fast) var(--ease-standard), color var(--dur-fast) var(--ease-standard);
	}
	.menu-btn:hover {
		background: var(--surface-3);
		color: var(--text-1);
	}

	/* Row 2: comparative chips. Whole-chip priority (never clipped mid-word). */
	.chips {
		display: flex;
		align-items: center;
		flex-wrap: wrap;
		gap: var(--space-xs);
	}
	.chips :global(.chip) {
		flex-shrink: 0;
	}
	.energy-chip {
		display: inline-flex;
		flex-shrink: 0;
		min-width: 0;
	}
	.bpm-num {
		font-weight: var(--font-weight-semibold);
		font-variant-numeric: tabular-nums;
		color: var(--text-1);
	}
	.bpm-delta {
		font-variant-numeric: tabular-nums;
		font-weight: var(--font-weight-medium);
	}
	.chips :global(.harmony-icon--sm),
	.chips :global(.metronome-icon--sm) {
		width: var(--icon-size-sm);
		height: var(--icon-size-sm);
	}

	/* Row 3: signals — score lead (left) · rating · match (trailing). Pushed to the
	 * bottom so a row of cards aligns their verdicts along one line. */
	.signals {
		display: flex;
		align-items: center;
		gap: var(--space-md);
		margin-top: auto;
	}
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
		display: flex;
		align-items: center;
		min-width: 0;
	}
	.signal-rating :global(.star-compact__count) {
		font-weight: var(--font-weight-semibold);
		color: var(--text-1);
	}
	.signal-empty {
		color: var(--text-4);
		font-size: var(--text-sm);
	}

	/* Match strength — bar + word, sits at the trailing edge. Never a raw number,
	 * never color alone (content-conventions §3, §4). */
	.signal-affinity {
		display: flex;
		align-items: center;
		justify-content: flex-end;
		gap: var(--space-xs);
		min-width: 0;
		margin-left: auto;
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

	/* Add-to-set popover. */
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

	/* ── Narrow fallback — if the card ever lands < 260px (e.g. 1-up on a very
	 * narrow pane collapses fine, but a squeezed column would), drop the artwork to
	 * a smaller box and let the body keep its rows. Keeps the card graceful without
	 * the dense-pill restructuring the 6-up grid used to force. ── */
	@container relcard (max-width: 260px) {
		.related-card {
			gap: var(--space-md);
			padding: var(--space-md);
		}
		.artwork-wrap {
			width: 52px;
			height: 52px;
		}
		.signals {
			gap: var(--space-sm);
		}
	}
</style>
