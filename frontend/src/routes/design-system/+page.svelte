<script lang="ts">
	import Button from '$lib/components/primitives/Button.svelte';
	import Stack from '$lib/components/primitives/Stack.svelte';
	import Grid from '$lib/components/primitives/Grid.svelte';
	import SimilarTrackCard from '$lib/components/library/SimilarTrackCard.svelte';
	import StarRating from '$lib/components/library/StarRating.svelte';
	import Chip from '$lib/components/primitives/Chip.svelte';
	import HarmonyIcon, {
		HARMONY_RELATION_LABEL,
		type HarmonyRelation,
	} from '$lib/components/primitives/HarmonyIcon.svelte';
	import Menu from '$lib/components/primitives/Menu.svelte';
	import MenuItem from '$lib/components/primitives/MenuItem.svelte';
	import MenuSeparator from '$lib/components/primitives/MenuSeparator.svelte';
	import { getCamelotColor } from '$lib/utils/camelot';

	// The five harmonic-move relations, in teaching order, for the Icons section.
	const harmonyRelations: { relation: HarmonyRelation; color: string }[] = [
		{ relation: 'same', color: 'var(--score-excellent)' },
		{ relation: 'up', color: 'var(--score-excellent)' },
		{ relation: 'down', color: 'var(--score-good)' },
		{ relation: 'swap', color: 'var(--score-good)' },
		{ relation: 'clash', color: 'var(--score-poor)' },
	];
	import type { SuggestNextItem, Track } from '$lib/types';

	// Interactive rating demo — clicking a star updates this local value live.
	let demoRating = $state(3);

	// Removable-filter demo for the chip section — the × actually drops the chip.
	let filterChips = $state(['Techno', 'deadmau5', 'Anjunadeep']);
	function dropChip(label: string) {
		filterChips = filterChips.filter((c) => c !== label);
	}

	// Menu demos — each trigger opens an anchored, keyboard-driven panel.
	let basicMenuOpen = $state(false);
	let richMenuOpen = $state(false);
	let pickerMenuOpen = $state(false);
	// Picker-style menu: the selected zone is the one with the trailing check.
	const sortZones = ['Warmup', 'Build', 'Drive', 'Peak'];
	let selectedZone = $state('Build');
	// Last action picked, so the inert demos still show they fired.
	let lastMenuAction = $state<string | null>(null);

	// Cerceta palette: five source colors mapped to UI roles. Each ratio is the
	// WCAG 2.1 contrast figure measured against the app background (#0D0D0D).
	// Fill and text-safe steps are listed separately per color.
	type Verdict = 'text' | 'large' | 'nontext';
	// Compact uppercase role chip for the ramp cards, mirroring the palette card's
	// role chip. Short label + the WCAG threshold that step clears.
	const verdictChip: Record<Verdict, string> = {
		text: 'Body text · AA',
		large: 'Large · UI',
		nontext: 'Non-text',
	};
	const verdictTitle: Record<Verdict, string> = {
		text: 'Passes WCAG AA body text (≥4.5:1)',
		large: 'Passes large text / UI only (≥3:1)',
		nontext: 'Non-text only (fails 3:1)',
	};

	// The five source colors with their role, fill step, and text-safe step.
	const palette: {
		name: string; role: string; family: string;
		fillVar: string; fillHex: string; fillRatio: string;
		textVar: string; textHex: string; textRatio: string;
		verdict: Verdict; note: string;
	}[] = [
		{ name: 'Cerceta', role: 'Primary action', family: 'teal',
			fillVar: '--teal-500', fillHex: '#44AAA2', fillRatio: '6.96:1',
			textVar: '--teal-500', textHex: '#44AAA2', textRatio: '6.96:1',
			verdict: 'text', note: 'the dominant. Soft enough to fill large, light enough to read.' },
		{ name: 'Teal (bright)', role: 'Hover / focus lift', family: 'teal',
			fillVar: '--teal-400', fillHex: '#00B1B8', fillRatio: '7.39:1',
			textVar: '--teal-400', textHex: '#00B1B8', textRatio: '7.39:1',
			verdict: 'text', note: 'rare lift only — too saturated to rest on a dark fill.' },
		{ name: 'Navy', role: 'Surface tint / secondary', family: 'navy',
			fillVar: '--navy-800', fillHex: '#005380', fillRatio: '2.36:1',
			textVar: '--navy-400', textHex: '#5FABE2', textRatio: '7.78:1',
			verdict: 'large', note: 'fill is structure (panels, borders). Text needs the 400 step.' },
		{ name: 'Magenta', role: 'Accent / highlight', family: 'magenta',
			fillVar: '--magenta-600', fillHex: '#AF125A', fillRatio: '2.83:1',
			textVar: '--magenta-400', textHex: '#F969A3', textRatio: '7.01:1',
			verdict: 'large', note: 'sparing pop — now-playing, peak, alerts. Text needs the 400 step.' },
		{ name: 'Lilac', role: 'Soft / secondary text', family: 'lilac',
			fillVar: '--lilac-300', fillHex: '#D5B2D5', fillRatio: '10.33:1',
			textVar: '--lilac-300', textHex: '#D5B2D5', textRatio: '10.33:1',
			verdict: 'text', note: 'the soft echo — safe as body text, muted headings, chips.' },
	];

	// Primary teal ramp 50→950 with real contrast and the role each step earns.
	const tealRamp: { step: string; hex: string; ratio: string; verdict: Verdict; note: string }[] = [
		{ step: '50',  hex: '#E1F9F7', ratio: '17.67:1', verdict: 'text',    note: 'lightest tint' },
		{ step: '100', hex: '#C8F2EE', ratio: '16.10:1', verdict: 'text',    note: '' },
		{ step: '200', hex: '#9EE0DB', ratio: '13.09:1', verdict: 'text',    note: '' },
		{ step: '300', hex: '#70CDC7', ratio: '10.41:1', verdict: 'text',    note: '' },
		{ step: '400', hex: '#00B1B8', ratio: '7.39:1',  verdict: 'text',    note: 'bright lift — hover / focus only' },
		{ step: '500', hex: '#44AAA2', ratio: '6.96:1',  verdict: 'text',    note: 'PRIMARY action — also safe as text on dark' },
		{ step: '600', hex: '#008A84', ratio: '4.60:1',  verdict: 'text',    note: 'solid hover fill — still clears AA text' },
		{ step: '700', hex: '#00706C', ratio: '3.27:1',  verdict: 'large',   note: 'pressed — large UI only' },
		{ step: '800', hex: '#005652', ratio: '2.27:1',  verdict: 'nontext', note: '' },
		{ step: '900', hex: '#003B38', ratio: '1.56:1',  verdict: 'nontext', note: '' },
		{ step: '950', hex: '#002321', ratio: '1.17:1',  verdict: 'nontext', note: '' },
	];

	const spacing = [
		{ name: '2xs', val: '2px' }, { name: 'xs', val: '4px' }, { name: 'sm', val: '6px' },
		{ name: 'md', val: '8px' }, { name: 'lg', val: '12px' }, { name: 'xl', val: '16px' },
		{ name: '2xl', val: '20px' }, { name: '3xl', val: '24px' }, { name: '4xl', val: '32px' },
		{ name: '5xl', val: '48px' }, { name: '6xl', val: '64px' },
	];

	const typeScale = [
		{ name: '2xs', px: '10px' }, { name: 'xs', px: '11px' }, { name: 'sm', px: '12px' },
		{ name: 'base', px: '13px' }, { name: 'md', px: '14px' }, { name: 'lg', px: '16px' },
		{ name: 'xl', px: '20px' }, { name: '2xl', px: '24px' },
	];

	const radii = ['xs', 'sm', 'md', 'lg', 'xl', 'full'];
	const elevations = ['0', '1', '2', '3'];
	const variants = ['primary', 'secondary', 'ghost', 'danger'] as const;
	const sizes = ['sm', 'md', 'lg'] as const;

	// Related tracks card — showcase mock data. The card consumes only module-level
	// singleton stores (player, ui) and pure helpers, so it renders safely on this
	// route with no provider. Artwork URLs intentionally 404 here, exercising the
	// music-note fallback; one state below also forces the no-artwork variant.
	// Callbacks are no-ops so the card is inert in the showcase.
	function mockTrack(overrides: Partial<Track>): Track {
		return {
			id: 0, title: null, artist: null, album: null, label: null,
			bpm: null, key: null, rating: null, genre: null, energy: null,
			duration_sec: null, play_count: null, kiku_play_count: null,
			has_waveform: false, has_features: false, resolved_energy: null,
			energy_source: null, energy_confidence: null, energy_value: null,
			energy_label: null, energy_conflict: null, date_added: null,
			release_year: null, track_number: null, disc_number: null,
			comment: null, playlist_tags: [], genre_family: null,
			...overrides,
		};
	}

	function mockItem(track: Track, score: number): SuggestNextItem {
		return {
			track,
			score,
			breakdown: {
				harmonic: score, energy_fit: score, bpm_compat: score,
				genre_coherence: score, track_quality: score, total: score,
			},
		};
	}

	// The parent track context every card scores against (128 BPM, 8A).
	const parentBpm = 128;
	const parentKey = '8A';

	// Four meaningful states shown side by side.
	const relatedStates: {
		label: string;
		item: SuggestNextItem;
		affinity: string | null;
	}[] = [
		{
			label: 'Strong match',
			affinity: 'good',
			item: mockItem(
				mockTrack({
					id: 9001, title: 'Midnight Drive', artist: 'Lena Vox',
					bpm: 128, key: '8A', rating: 5, genre_family: 'Techno',
					resolved_energy: 'peak',
				}),
				0.94,
			),
		},
		{
			label: 'Key / BPM clash',
			affinity: null,
			item: mockItem(
				mockTrack({
					id: 9002, title: 'Off Axis', artist: 'Corner Theory',
					bpm: 138, key: '3B', rating: 3, genre_family: 'House',
					resolved_energy: 'build',
				}),
				0.41,
			),
		},
		{
			label: 'No artwork (fallback)',
			affinity: null,
			item: mockItem(
				mockTrack({
					id: 9003, title: 'Untagged Bootleg With A Very Long Title That Clamps',
					artist: 'Unknown Pressing', bpm: 150, key: '9A', rating: 0,
					genre_family: 'Groove', resolved_energy: 'drive',
				}),
				0.78,
			),
		},
		{
			label: 'Marked: not for me',
			affinity: 'bad',
			item: mockItem(
				mockTrack({
					id: 9004, title: 'Warm Up Tool', artist: 'Slow Hands',
					bpm: 124, key: '7A', rating: 4, genre_family: 'Trance',
					resolved_energy: 'warmup',
				}),
				0.66,
			),
		},
	];

	const noop = () => {};
</script>

<div class="ds" data-theme="cerceta">
	<header class="ds__head">
		<p class="ds__kicker">KIKU 聴く · DESIGN SYSTEM</p>
		<h1>Design System</h1>
		<p class="ds__lede">
			The shared foundation behind every Kiku screen — design tokens, color, typography, spacing,
			and the core component primitives. Use this page as the reference when building or reviewing
			the interface.
		</p>
	</header>

	<!-- 1. COLOR & PALETTE -->
	<section class="ds__section">
		<h2>Color palette</h2>
		<p class="ds__note">
			Five core colors, each with a defined role. Every swatch shows its fill token, its text-safe
			token, the source hex, and the WCAG contrast ratio against the app background (#0D0D0D).
		</p>
		<div class="palette-grid">
			{#each palette as c (c.name)}
				<div class="palette-card">
					<div class="palette-card__head">
						<div class="palette-card__chip" style="background: var({c.fillVar});"></div>
						<div class="palette-card__id">
							<strong>{c.name}</strong>
							<span class="palette-card__role">{c.role}</span>
						</div>
					</div>
					<div class="palette-card__steps">
						<div class="palette-step">
							<span class="palette-step__label">Fill</span>
							<code>{c.fillVar}</code>
							<span class="swatch__hex">{c.fillHex}</span>
							<span class="swatch__ratio swatch__verdict--{c.verdict}">{c.fillRatio}</span>
						</div>
						<div class="palette-step">
							<span class="palette-step__label">Text-safe</span>
							<code>{c.textVar}</code>
							<span class="swatch__hex">{c.textHex}</span>
							<span class="swatch__ratio swatch__verdict--text">{c.textRatio}</span>
						</div>
					</div>
					<span class="swatch__hint">{c.note}</span>
				</div>
			{/each}
		</div>

		<h3 class="ds__subhead">Cerceta ramp · 50 → 950</h3>
		<p class="ds__note">
			The cerceta ramp from 50 to 950. Lighter steps carry text on dark; mid steps are solid fills;
			darker steps are borders and subtle backgrounds.
		</p>
		<div class="swatch-grid">
			{#each tealRamp as s (s.step)}
				<div class="swatch">
					<div class="swatch__head">
						<div class="swatch__chip" style="background: var(--teal-{s.step});"></div>
						<div class="swatch__id">
							<code>--teal-{s.step}</code>
							<span
								class="swatch__chiplabel swatch__verdict--{s.verdict}"
								title={verdictTitle[s.verdict]}
							>{verdictChip[s.verdict]}</span>
						</div>
					</div>
					<div class="swatch__rows">
						<div class="swatch__row">
							<span class="swatch__label">Hex</span>
							<span class="swatch__hex">{s.hex}</span>
						</div>
						<div class="swatch__row">
							<span class="swatch__label">On #0D0D0D</span>
							<span class="swatch__ratio swatch__verdict--{s.verdict}">{s.ratio}</span>
						</div>
					</div>
					{#if s.note}<span class="swatch__hint">{s.note}</span>{/if}
				</div>
			{/each}
		</div>

		<div class="on-accent-proof">
			<div class="on-accent-proof__chip">Aa label</div>
			<p>
				Button labels are <strong>white on teal-600</strong> at <strong>4.23:1</strong>, which
				passes WCAG AA for large text and UI (≥3:1). <code>--on-accent</code> is therefore white on
				the cerceta fill.
			</p>
		</div>
	</section>

	<!-- 2. SPACING -->
	<section class="ds__section">
		<h2>Spacing scale</h2>
		<p class="ds__note">A 4px base rhythm with a 2px mini-unit for dense rows. Each bar is rendered at its token width.</p>
		<Stack gap="var(--space-sm)">
			{#each spacing as sp (sp.name)}
				<div class="scale-row">
					<code class="scale-row__name">--space-{sp.name}</code>
					<div class="scale-row__bar" style="width: var(--space-{sp.name});"></div>
					<span class="scale-row__val">{sp.val}</span>
				</div>
			{/each}
		</Stack>
	</section>

	<!-- 3. TYPE -->
	<section class="ds__section">
		<h2>Type scale</h2>
		<p class="ds__note">Anchored at a 12px body size. Each row is set at its own token size and line-height.</p>
		<Stack gap="var(--space-md)">
			{#each typeScale as t (t.name)}
				<div class="type-row">
					<code class="type-row__name">--text-{t.name}</code>
					<span class="type-row__sample" style="font-size: var(--text-{t.name}); line-height: var(--lh-{t.name});">
						The quick brown fox jumps over the lazy dog — {t.px}
					</span>
				</div>
			{/each}
		</Stack>
	</section>

	<!-- 4. RADIUS -->
	<section class="ds__section">
		<h2>Radius</h2>
		<p class="ds__note">Five corner-radius steps plus a full pill. These tokens replace the previous ad-hoc radius values.</p>
		<div class="cluster cluster--lg">
			{#each radii as r (r)}
				<div class="radius-demo">
					<div class="radius-demo__box" style="border-radius: var(--radius-{r});"></div>
					<code>--radius-{r}</code>
				</div>
			{/each}
		</div>
	</section>

	<!-- 5. ELEVATION -->
	<section class="ds__section">
		<h2>Elevation</h2>
		<p class="ds__note">Borders define depth on the dark background. Shadows read poorly on #0D0D0D, so they are reserved for floating layers.</p>
		<div class="cluster cluster--lg">
			{#each elevations as e (e)}
				<div class="elev-demo" style="box-shadow: var(--elev-{e});">
					<code>--elev-{e}</code>
				</div>
			{/each}
		</div>
	</section>

	<!-- 6. 12-COL GRID -->
	<section class="ds__section">
		<h2>12-column grid</h2>
		<p class="ds__note">An opt-in grid for content areas. The app shell and the fixed two-pane layout remain flex-based.</p>
		<Stack gap="var(--space-lg)">
			<Grid>
				<div class="grid-cell col-span-6">6</div>
				<div class="grid-cell col-span-6">6</div>
			</Grid>
			<Grid>
				<div class="grid-cell col-span-4">4</div>
				<div class="grid-cell col-span-4">4</div>
				<div class="grid-cell col-span-4">4</div>
			</Grid>
			<Grid condensed>
				<div class="grid-cell col-span-3">3</div>
				<div class="grid-cell col-span-3">3</div>
				<div class="grid-cell col-span-3">3</div>
				<div class="grid-cell col-span-3">3</div>
			</Grid>
		</Stack>
	</section>

	<!-- 7. BUTTON MATRIX -->
	<section class="ds__section">
		<h2>Buttons</h2>
		<p class="ds__note">The Button primitive across every variant and size, including disabled and loading states. Primary uses the cerceta fill with a white label.</p>
		<Stack gap="var(--space-lg)">
			{#each variants as v (v)}
				<div class="btn-row">
					<span class="btn-row__label">{v}</span>
					<div class="cluster cluster--md">
						{#each sizes as sz (sz)}
							<Button variant={v} size={sz}>{sz}</Button>
						{/each}
						<Button variant={v} disabled>disabled</Button>
						<Button variant={v} loading>loading</Button>
					</div>
				</div>
			{/each}
		</Stack>
	</section>

	<!-- 8. FOCUS RING -->
	<section class="ds__section">
		<h2>Focus ring</h2>
		<p class="ds__note">The focus ring appears on keyboard navigation only, not on mouse interaction. It is shown here on buttons and an input field.</p>
		<div class="cluster cluster--md">
			<Button variant="primary">First</Button>
			<Button variant="secondary">Second</Button>
			<input type="text" placeholder="and a field" />
			<Button variant="ghost">Last</Button>
		</div>
	</section>

	<!-- 9. RATING -->
	<section class="ds__section">
		<h2>Rating</h2>
		<p class="ds__note">
			The five-star rating carries your curation signal — it feeds the track-quality dimension when
			Kiku scores a transition. The filled color comes from the <code>--star-fill</code> token. Each
			star is a keyboard-reachable control with its own focus ring; clicking a filled star again
			clears the rating. Read-only ratings drop the cursor and interaction. For tight inline spots
			like the related-tracks card, the <code>display="compact"</code> mode collapses the rating to a
			count plus a single glyph (3★).
		</p>
		<div class="rating-grid">
			<div class="rating-cell rating-cell--center">
				<span class="rating-cell__label">Empty</span>
				<StarRating rating={0} readonly />
			</div>
			<div class="rating-cell rating-cell--center">
				<span class="rating-cell__label">Partial</span>
				<StarRating rating={3} readonly />
			</div>
			<div class="rating-cell rating-cell--center">
				<span class="rating-cell__label">Full</span>
				<StarRating rating={5} readonly />
			</div>
			<div class="rating-cell">
				<span class="rating-cell__label">Interactive</span>
				<Stack gap="var(--space-sm)">
					<StarRating rating={demoRating} onchange={(r) => (demoRating = r)} />
					<span class="rating-cell__caption" aria-live="polite">
						{#if demoRating === 0}
							Unrated — neutral weight in transitions
						{:else}
							{demoRating}★ — {Math.round((demoRating / 5) * 40)}% of curation score
						{/if}
					</span>
				</Stack>
			</div>
			<div class="rating-cell">
				<span class="rating-cell__label">Compact</span>
				<div class="cluster cluster--md">
					<StarRating rating={0} display="compact" />
					<StarRating rating={3} display="compact" />
					<StarRating rating={5} display="compact" />
				</div>
			</div>
			<div class="rating-cell rating-cell--center">
				<span class="rating-cell__label">Small / large</span>
				<div class="cluster cluster--md">
					<StarRating rating={4} readonly size="sm" />
					<StarRating rating={4} readonly size="lg" />
				</div>
			</div>
		</div>
	</section>

	<!-- 10. CHIP -->
	<section class="ds__section">
		<h2>Chip</h2>
		<p class="ds__note">
			One primitive for every labelled value — genre, Camelot key, BPM delta, energy zone, harmony
			move, vibe and level. Color always derives from a token by meaning and is paired with a word or
			glyph, so it's never the only signal. Dynamic colors (key, zone, vibe) flow in through a
			<code>color</code> prop, keeping the chip presentational. Sentence case throughout, keys in
			Camelot notation, and a muted <code>—</code> for missing values. The <code>bpm</code> variant
			leads with a <strong>metronome icon</strong> instead of a literal "BPM" text label (saving width
			in dense rows); the integer tempo and a <strong>signed delta colored green / orange / red by
			magnitude</strong> (seamless ≤6% · moderate ~6–12% · tension &gt;12%) follow, and the chip's
			<code>title</code> carries "Beats per minute" for screen readers. The <code>genre</code> variant gets its own
			visible tinted treatment so genre reads as clearly as the colored key and energy chips.
		</p>

		<div class="chip-grid">
			<div class="chip-cell">
				<span class="chip-cell__label">Genre</span>
				<div class="cluster cluster--sm">
					<Chip variant="genre" value="Techno" />
					<Chip variant="genre" value="Tech house" />
					<Chip variant="genre" value="Melodic house" />
				</div>
			</div>

			<div class="chip-cell">
				<span class="chip-cell__label">Camelot key</span>
				<div class="cluster cluster--sm">
					<Chip variant="key" value="8A" color={getCamelotColor('8A')} />
					<Chip variant="key" value="12B" color={getCamelotColor('12B')} />
					<Chip variant="key" value="5A" color={getCamelotColor('5A')} />
				</div>
			</div>

			<div class="chip-cell">
				<span class="chip-cell__label">BPM delta — green / orange / red by magnitude</span>
				<div class="cluster cluster--sm">
					<!-- seamless (≈ within ±6%) → green -->
					<Chip variant="bpm" title="128 BPM — +1, seamless (within ±6%)">
						<span class="bpm-num">128</span><span class="bpm-delta" style="color: var(--score-excellent)">+1</span>
					</Chip>
					<!-- moderate (~6–12%) → orange -->
					<Chip variant="bpm" title="138 BPM — +10, moderate shift (~6–12%)">
						<span class="bpm-num">138</span><span class="bpm-delta" style="color: var(--score-good)">+10</span>
					</Chip>
					<!-- tension (> ~12%) → red -->
					<Chip variant="bpm" title="146 BPM — +18, big jump (> ±12%)">
						<span class="bpm-num">146</span><span class="bpm-delta" style="color: var(--score-poor)">+18</span>
					</Chip>
				</div>
				<span class="chip-cell__note">
					Within ±6% reads <span style="color: var(--score-excellent)">seamless</span>,
					~6–12% <span style="color: var(--score-good)">moderate</span>,
					beyond ±12% <span style="color: var(--score-poor)">tension</span> — the color is
					always paired with the signed number, never the only cue.
				</span>
			</div>

			<div class="chip-cell">
				<span class="chip-cell__label">Energy zone</span>
				<div class="cluster cluster--sm">
					<Chip variant="energy" value="Warmup" color="var(--zone-warmup)" />
					<Chip variant="energy" value="Drive" color="var(--zone-drive)" />
					<Chip variant="energy" value="Peak" color="var(--zone-peak)" />
				</div>
			</div>

			<div class="chip-cell">
				<span class="chip-cell__label">Harmony move</span>
				<div class="cluster cluster--sm">
					<Chip variant="harmony" value="Energy up" color="var(--score-excellent)" title="Energy up — one step on the Camelot wheel">
						{#snippet icon()}<HarmonyIcon relation="up" size="sm" />{/snippet}
					</Chip>
					<Chip variant="harmony" value="Mood switch" color="var(--score-good)" title="Mood switch — relative major/minor">
						{#snippet icon()}<HarmonyIcon relation="swap" size="sm" />{/snippet}
					</Chip>
					<Chip variant="harmony" value="Clash" color="var(--score-poor)" title="Distant keys — clashing">
						{#snippet icon()}<HarmonyIcon relation="clash" size="sm" />{/snippet}
					</Chip>
				</div>
			</div>

			<div class="chip-cell">
				<span class="chip-cell__label">Vibe</span>
				<div class="cluster cluster--sm">
					<Chip variant="vibe" value="Bright &amp; dense" color="hsl(48 90% 60%)">
						{#snippet icon()}<span class="vibe-dot" style:background="hsl(48 90% 60%)"></span>{/snippet}
					</Chip>
					<Chip variant="vibe" value="Dark &amp; sparse" color="hsl(265 50% 55%)">
						{#snippet icon()}<span class="vibe-dot" style:background="hsl(265 50% 55%)"></span>{/snippet}
					</Chip>
				</div>
			</div>

			<div class="chip-cell">
				<span class="chip-cell__label">Level (belt)</span>
				<div class="cluster cluster--sm">
					<Chip variant="level" value="Green belt" tone="success" />
					<Chip variant="level" value="Brown belt" tone="warn" />
				</div>
			</div>

			<div class="chip-cell">
				<span class="chip-cell__label">Neutral &amp; tones</span>
				<div class="cluster cluster--sm">
					<Chip variant="neutral" value="Tag" />
					<Chip variant="neutral" value="Owned" tone="success" />
					<Chip variant="neutral" value="Gap" tone="warn" />
				</div>
			</div>

			<div class="chip-cell">
				<span class="chip-cell__label">Sizes</span>
				<div class="cluster cluster--sm">
					<Chip variant="genre" value="Small" size="sm" />
					<Chip variant="genre" value="Medium" size="md" />
				</div>
			</div>

			<div class="chip-cell">
				<span class="chip-cell__label">Missing value</span>
				<div class="cluster cluster--sm">
					<Chip variant="genre" />
					<Chip variant="key" />
				</div>
			</div>

			<div class="chip-cell">
				<span class="chip-cell__label">Removable filters</span>
				<div class="cluster cluster--sm">
					{#each filterChips as label (label)}
						<Chip
							variant="neutral"
							value={label}
							removable
							removeLabel={`Remove ${label} filter`}
							onremove={() => dropChip(label)}
						/>
					{/each}
					{#if filterChips.length === 0}
						<span class="chip-cell__empty">All filters cleared — click reset to bring them back.</span>
						<Button size="sm" variant="ghost" onclick={() => (filterChips = ['Techno', 'deadmau5', 'Anjunadeep'])}>
							Reset
						</Button>
					{/if}
				</div>
			</div>
		</div>
	</section>

	<!-- 11. ICONS -->
	<section class="ds__section">
		<h2>Icons</h2>
		<p class="ds__note">
			Meaning-bearing icons are inline SVG drawn with <code>currentColor</code>, so they inherit the
			chip or theme color rather than hardcoding hex. The harmony-move set is the first standardized
			family: each of the five relations has a distinct <em>shape</em>, so the signal survives
			colorblindness — color is never the only cue. Every icon carries a sentence-case accessible
			label (used as its <code>aria-label</code> and tooltip) and means the same thing everywhere.
			Icons size off one shared scale (<code>--icon-size-sm / -md / -lg</code>) with one stroke weight.
		</p>

		<h3 class="ds__subhead">Harmony moves</h3>
		<div class="icon-grid">
			{#each harmonyRelations as { relation, color } (relation)}
				<div class="icon-cell">
					<span class="icon-cell__glyph" style:color>
						<HarmonyIcon {relation} size="lg" />
					</span>
					<span class="icon-cell__label">{HARMONY_RELATION_LABEL[relation]}</span>
				</div>
			{/each}
		</div>

		<h3 class="ds__subhead">Size scale</h3>
		<div class="icon-sizes">
			<div class="icon-cell">
				<span class="icon-cell__glyph"><HarmonyIcon relation="swap" size="sm" /></span>
				<span class="icon-cell__label">Small — 16px</span>
			</div>
			<div class="icon-cell">
				<span class="icon-cell__glyph"><HarmonyIcon relation="swap" size="md" /></span>
				<span class="icon-cell__label">Medium — 20px</span>
			</div>
			<div class="icon-cell">
				<span class="icon-cell__glyph"><HarmonyIcon relation="swap" size="lg" /></span>
				<span class="icon-cell__label">Large — 24px</span>
			</div>
		</div>
	</section>

	<!-- 12. MENU -->
	<section class="ds__section">
		<h2>Menu</h2>
		<p class="ds__note">
			One floating menu mechanism for the right-click track actions and anchored pickers. The panel
			is fully keyboard-driven: <kbd>Enter</kbd> or <kbd>Space</kbd> opens it and lands focus on the
			first item, <kbd>↑</kbd>/<kbd>↓</kbd> move between items, <kbd>Home</kbd>/<kbd>End</kbd> jump to
			the ends, <kbd>Enter</kbd>/<kbd>Space</kbd> activate, and <kbd>Esc</kbd> closes it and returns
			focus to the trigger. Focus is trapped while open and a click outside dismisses it. The trigger
			carries <code>aria-haspopup</code> + <code>aria-expanded</code>; rows are real
			<code>menuitem</code>s. The surface and rows are fully tokenized, so the cerceta theme recolors
			them like everything else.
		</p>

		<div class="menu-grid">
			<div class="menu-cell">
				<span class="menu-cell__label">Basic menu</span>
				<Menu bind:open={basicMenuOpen} label="Set actions">
					{#snippet trigger({ open, props })}
						<span {...props}><Button variant="secondary" size="sm" onclick={open}>Set actions</Button></span>
					{/snippet}
					<MenuItem onselect={() => (lastMenuAction = 'Rename set')}>Rename set</MenuItem>
					<MenuItem onselect={() => (lastMenuAction = 'Duplicate set')}>Duplicate set</MenuItem>
					<MenuItem onselect={() => (lastMenuAction = 'Export set')}>Export set</MenuItem>
				</Menu>
			</div>

			<div class="menu-cell">
				<span class="menu-cell__label">Icons, separator, destructive</span>
				<Menu bind:open={richMenuOpen} label="Track actions">
					{#snippet trigger({ open, props })}
						<span {...props}><Button variant="secondary" size="sm" onclick={open}>Track actions</Button></span>
					{/snippet}
					<MenuItem onselect={() => (lastMenuAction = 'Play')}>
						{#snippet icon()}&#9654;{/snippet}
						Play
					</MenuItem>
					<MenuItem onselect={() => (lastMenuAction = 'Add to set')}>
						{#snippet icon()}+{/snippet}
						Add to set
					</MenuItem>
					<MenuItem disabled>
						{#snippet icon()}<HarmonyIcon relation="swap" size="sm" />{/snippet}
						Find a transition
					</MenuItem>
					<MenuSeparator />
					<MenuItem danger onselect={() => (lastMenuAction = 'Remove from set')}>
						{#snippet icon()}&#10005;{/snippet}
						Remove from set
					</MenuItem>
				</Menu>
			</div>

			<div class="menu-cell">
				<span class="menu-cell__label">Picker (selected item)</span>
				<Menu bind:open={pickerMenuOpen} label="Sort by energy zone">
					{#snippet trigger({ open, props })}
						<span {...props}><Button variant="secondary" size="sm" onclick={open}>Sort: {selectedZone}</Button></span>
					{/snippet}
					{#each sortZones as zone (zone)}
						<MenuItem selected={selectedZone === zone} onselect={() => (selectedZone = zone)}>
							{zone}
						</MenuItem>
					{/each}
				</Menu>
			</div>
		</div>

		<p class="ds__note ds__note--quiet" aria-live="polite">
			{#if lastMenuAction}Last action: {lastMenuAction}.{:else}Pick an item to see it register here.{/if}
		</p>
	</section>

	<!-- 13. RELATED TRACKS CARD -->
	<section class="ds__section">
		<h2>Related tracks card</h2>
		<p class="ds__note">
			The card shown under the "Related tracks" header on the track view — each entry is a candidate
			to mix into next, built entirely from the design-system primitives (<code>Chip</code>,
			<code>StarRating</code>, <code>HarmonyIcon</code>, <code>Menu</code>). It stacks three tiers:
			<strong>identity</strong> (first-letter-capped title, with artist · genre on a subtitle line —
			the genre is rendered as <strong>genre-family-colored text</strong> (no box), the color carrying
			the signal, while the artist stays muted plain text and ellipsizes first); the
			<strong>attribute chips</strong> in priority order key → BPM → energy, the key chip carrying its
			harmony-move icon and the BPM chip carrying its metronome glyph + a <strong>signed delta colored
			green / orange / red by magnitude</strong> (seamless / moderate / tension); and the
			<strong>Track signals</strong> block — <strong>three balanced columns</strong> (each an equal third)
			reading left → center → right: the match score <code>NN/100</code> (lead, <strong>left</strong>),
			the DJ's rating as a compact <code>N★</code> (<strong>center</strong>), and affinity rendered as a
			labelled qualitative strength bar (Great / Likely / Weak, <strong>right</strong>) rather than a
			second raw number.
		</p>
		<p class="ds__note">
			The card is a <strong>size container</strong>: it renders across grid densities (4-up, 6-up, the
			expanded "Show more" grid) and adapts to its real column width through three container-query
			tiers rather than one shrinking design. <strong>Regular (≥240px)</strong> shows everything:
			identity with artist + genre-colored text, chips key → BPM → energy, and the three-balanced-column
			signals grid (NN/100 left · N★ center · match right). <strong>Intermediate (200–240px)</strong>
			tightens only — smaller artwork and reduced padding — but <strong>all three chips (key + BPM +
			energy) stay</strong> (the compact metronome glyph makes the BPM chip short enough that no chip
			drops and no <code>+1</code> overflow is needed), and the genre text and three-column signals both
			stay too. <strong>Compact (&lt;200px)</strong> becomes a dense <strong>pill</strong> (rounder,
			badge-like): artwork + title (+ ⋮), then a single row of <strong>color-coded icons only</strong>,
			<strong>evenly distributed</strong> across the pill — harmony glyph · metronome · match-strength
			bars · a <strong>larger, bold</strong> N★ — where icon shape + color + the star count carry the signal. The numeric score, key
			text, BPM number, genre and energy all drop there; every icon keeps its real value in its
			<code>title</code>/aria-label. Chips never clip mid-word at any width. The visible match verdict is
			a single terse word (<strong>Great / Likely / Weak / Not for me</strong>), with the fuller phrasing
			on hover.
		</p>

		<p class="related-density-label">Regular — ~250px columns (everything visible; genre as colored text)</p>
		<div class="related-grid related-grid--regular">
			{#each relatedStates as s (s.item.track.id)}
				<div class="related-cell">
					<span class="related-cell__label">{s.label}</span>
					<SimilarTrackCard
						item={s.item}
						parentTrackId={1}
						parentBpm={parentBpm}
						parentKey={parentKey}
						affinity={s.affinity}
						onaffinitychange={noop}
					/>
				</div>
			{/each}
		</div>

		<p class="related-density-label">Intermediate — ~220px columns (tighter, but all three chips key + BPM + energy stay; no +1)</p>
		<div class="related-grid related-grid--intermediate">
			{#each relatedStates as s (s.item.track.id)}
				<div class="related-cell">
					<SimilarTrackCard
						item={s.item}
						parentTrackId={1}
						parentBpm={parentBpm}
						parentKey={parentKey}
						affinity={s.affinity}
						onaffinitychange={noop}
					/>
				</div>
			{/each}
		</div>

		<p class="related-density-label">Compact — ~190px columns (dense pill: artwork + title / evenly-distributed color-coded icons only — harmony · metronome · match bars · larger bold N★)</p>
		<div class="related-grid related-grid--compact">
			{#each relatedStates as s (s.item.track.id)}
				<div class="related-cell">
					<SimilarTrackCard
						item={s.item}
						parentTrackId={1}
						parentBpm={parentBpm}
						parentKey={parentKey}
						affinity={s.affinity}
						onaffinitychange={noop}
					/>
				</div>
			{/each}
		</div>
	</section>

	<!-- 14. REFERENCES -->
	<section class="ds__section">
		<h2>References</h2>
		<p class="ds__note">
			Color palette inspired by Sara Caldas — La paleta perfecta para diseño gráfico e ilustración
			(Hoaki, ISBN 978-84-17412-93-7).
		</p>
		<p class="ds__note">Contrast ratios follow WCAG 2.1 AA.</p>
	</section>
</div>

<style>
	/* Cerceta (teal book palette) resolves ONLY inside this subtree. :global() is
	 * required because data-theme sits on the page root and the override must
	 * cascade to <Button> children. The live app :root stays cyan — untouched. */
	:global([data-theme='cerceta']) {
		--accent-9:  var(--teal-600);  /* #008A84 fill */
		--accent-10: var(--teal-400);  /* #00B1B8 bright hover lift */
		--accent-11: var(--teal-500);  /* #44AAA2 text-on-dark, 6.96:1 */
		--accent-contrast: #FFFFFF;    /* on-fill label, 4.23:1 on teal-600 — passes large/UI */
		--accent-pressed: var(--teal-700);
		/* Rating star re-points to the magenta highlight step under cerceta — the
		 * palette's "accent / highlight" role. Amber stays the live-app default. */
		--star-fill: var(--magenta-400);

		/* Chip ramps under cerceta — the energy journey and the score-quality
		 * ramp re-point onto the teal-book palette steps (all text-safe). The
		 * live app keeps the original ZONE_COLORS / score hexes. */
		--zone-intro:  var(--navy-400);   /* cool blue — doors-open lull */
		--zone-warmup: var(--teal-400);   /* teal — easing in */
		--zone-build:  var(--lilac-400);  /* soft lilac — lifting */
		--zone-drive:  var(--magenta-400);/* magenta — floor moving */
		--zone-peak:   var(--magenta-300);/* bright highlight — the apex */
		--zone-close:  var(--lilac-500);  /* dusk violet — comedown */

		--score-excellent: var(--teal-400);
		--score-good:      var(--lilac-400);
		--score-fair:      var(--magenta-400);
		--score-poor:      var(--magenta-300);
	}

	/* One centered document. Every section — header, titles, descriptions and the
	 * card grids — shares this container's left + right edges. The lede and section
	 * notes run the full container width, reaching the same right edge as the grids
	 * below them. --ds-measure caps only the boxed on-accent proof. */
	/* The page is ONE flex column. A single gap token (--space-4xl = 32px) sets the
	 * vertical break between EVERY adjacent block — header→first section and every
	 * section→section pair alike. No block carries its own top/bottom margin, so
	 * nothing compounds (never 32 + 32 = 64). The rhythm is uniform by construction. */
	.ds {
		--ds-measure: 70ch;
		max-width: 1120px;
		margin: 0 auto;
		padding: var(--space-5xl) var(--space-5xl) var(--space-6xl);
		height: 100%;
		overflow-y: auto;
		color: var(--text-1);
		display: flex;
		flex-direction: column;
		gap: var(--space-4xl);
	}

	.ds__head {
		display: flex;
		flex-direction: column;
		gap: var(--space-lg);
	}
	.ds__kicker {
		font-size: var(--text-xs);
		font-weight: var(--font-weight-semibold);
		line-height: var(--lh-xs);
		letter-spacing: 0.08em;
		text-transform: uppercase;
		color: var(--accent-text);
	}
	.ds h1 {
		font-size: var(--text-2xl);
		line-height: var(--lh-2xl);
		font-weight: var(--font-weight-semibold);
		color: var(--text-1);
	}
	.ds__lede {
		font-size: var(--text-lg);
		line-height: var(--lh-lg);
		color: var(--text-2);
	}

	/* Each section is a stack: title → description → content. gap handles the
	 * internal title→description→content spacing; the inter-section 32px break is
	 * owned solely by the parent .ds flex gap, so sections carry no vertical
	 * padding or margin of their own. The border-top is a flush divider only —
	 * it adds no spacing, so the rhythm above every section stays an even 32px. */
	.ds__section {
		display: flex;
		flex-direction: column;
		gap: var(--space-lg);
		border-top: 1px solid var(--border-subtle);
		padding-top: var(--space-lg);
	}
	.ds h2 {
		font-size: var(--text-xl);
		line-height: var(--lh-xl);
		font-weight: var(--font-weight-semibold);
	}
	.ds__note {
		font-size: var(--text-sm);
		line-height: var(--lh-sm);
		color: var(--text-3);
	}

	/* color — ramp cards mirror the palette card's labeled mini-table. Three
	 * columns give each card room for its label column without awkward wraps;
	 * it drops to two on narrower widths. */
	.swatch-grid {
		display: grid;
		grid-template-columns: repeat(3, 1fr);
		gap: var(--space-lg);
	}
	.swatch {
		display: flex;
		flex-direction: column;
		gap: var(--space-md);
		background: var(--surface-2);
		border: 1px solid var(--border-subtle);
		border-radius: var(--radius-md);
		padding: var(--space-lg);
	}
	.swatch__head { display: flex; align-items: center; gap: var(--space-md); }
	.swatch__chip { width: 40px; height: 40px; border-radius: var(--radius-sm); flex-shrink: 0; }
	.swatch__id { display: flex; flex-direction: column; gap: var(--space-2xs); min-width: 0; }
	.swatch__id code { font-size: var(--text-md); color: var(--text-1); }
	.swatch__chiplabel {
		font-size: var(--text-2xs);
		text-transform: uppercase;
		letter-spacing: 0.06em;
		font-weight: var(--font-weight-semibold);
	}
	.swatch__rows { display: flex; flex-direction: column; gap: var(--space-sm); }
	.swatch__row {
		display: grid;
		grid-template-columns: 88px 1fr;
		align-items: center;
		gap: var(--space-sm);
	}
	.swatch__label {
		font-size: var(--text-2xs);
		color: var(--text-3);
		text-transform: uppercase;
		letter-spacing: 0.04em;
	}
	.swatch__hex { font-size: var(--text-xs); color: var(--text-1); text-transform: uppercase; }
	.swatch__ratio { font-size: var(--text-sm); font-weight: var(--font-weight-semibold); }
	.swatch__verdict--text { color: var(--energy-low); }
	.swatch__verdict--large { color: var(--energy-mid); }
	.swatch__verdict--nontext { color: var(--text-4); }
	.swatch__hint { font-size: var(--text-2xs); color: var(--text-3); }

	@media (max-width: 720px) {
		.swatch-grid { grid-template-columns: repeat(2, 1fr); }
	}

	/* palette role cards (the five source colors) */
	.ds__subhead {
		font-size: var(--text-lg);
		line-height: var(--lh-lg);
		font-weight: var(--font-weight-semibold);
		margin-top: var(--space-3xl); /* extra break above a sub-block within a section */
	}
	.palette-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
		gap: var(--space-lg);
	}
	.palette-card {
		display: flex;
		flex-direction: column;
		gap: var(--space-md);
		background: var(--surface-2);
		border: 1px solid var(--border-subtle);
		border-radius: var(--radius-md);
		padding: var(--space-lg);
	}
	.palette-card__head { display: flex; align-items: center; gap: var(--space-md); }
	.palette-card__chip {
		width: 40px; height: 40px;
		border-radius: var(--radius-sm);
		flex-shrink: 0;
	}
	.palette-card__id { display: flex; flex-direction: column; gap: var(--space-2xs); }
	.palette-card__id strong { font-size: var(--text-md); color: var(--text-1); }
	.palette-card__role {
		font-size: var(--text-2xs);
		color: var(--accent-text);
		text-transform: uppercase;
		letter-spacing: 0.06em;
	}
	.palette-card__steps { display: flex; flex-direction: column; gap: var(--space-sm); }
	.palette-step {
		display: grid;
		grid-template-columns: 64px 1fr auto auto;
		align-items: center;
		gap: var(--space-sm);
	}
	.palette-step__label {
		font-size: var(--text-2xs);
		color: var(--text-3);
		text-transform: uppercase;
		letter-spacing: 0.04em;
	}
	.palette-step code { font-size: var(--text-xs); color: var(--text-1); }

	.on-accent-proof {
		display: flex; align-items: center; gap: var(--space-lg);
		margin-top: var(--space-md); /* small lift above the proof block */
		padding: var(--space-lg);
		background: var(--surface-2);
		border: 1px solid var(--border-subtle);
		border-radius: var(--radius-md);
		max-width: var(--ds-measure);
	}
	.on-accent-proof__chip {
		background: var(--teal-600); color: #FFFFFF;
		padding: var(--space-md) var(--space-xl);
		border-radius: var(--radius-sm);
		font-weight: var(--font-weight-semibold);
		flex-shrink: 0;
	}
	.on-accent-proof p { font-size: var(--text-sm); color: var(--text-2); line-height: var(--lh-sm); }

	/* spacing */
	.scale-row { display: flex; align-items: center; gap: var(--space-lg); }
	.scale-row__name { font-size: var(--text-xs); color: var(--text-3); width: 120px; flex-shrink: 0; }
	.scale-row__bar { height: 16px; background: var(--accent); border-radius: var(--radius-xs); flex-shrink: 0; }
	.scale-row__val { font-size: var(--text-xs); color: var(--text-4); }

	/* type */
	.type-row { display: flex; align-items: baseline; gap: var(--space-lg); }
	.type-row__name { font-size: var(--text-xs); color: var(--text-3); width: 120px; flex-shrink: 0; }
	.type-row__sample { color: var(--text-1); }

	/* radius */
	.radius-demo { display: flex; flex-direction: column; align-items: center; gap: var(--space-sm); }
	.radius-demo__box { width: 64px; height: 64px; background: var(--accent); }
	.radius-demo code, .elev-demo code { font-size: var(--text-2xs); color: var(--text-3); }

	/* elevation */
	.elev-demo {
		width: 120px; height: 80px;
		display: flex; align-items: flex-end; justify-content: center;
		padding: var(--space-sm);
		background: var(--surface-2);
		border: 1px solid var(--border-subtle);
		border-radius: var(--radius-md);
	}

	/* grid */
	.grid-cell {
		background: var(--surface-3);
		border: 1px solid var(--border-default);
		border-radius: var(--radius-sm);
		padding: var(--space-lg);
		text-align: center;
		font-size: var(--text-sm);
		color: var(--text-2);
	}

	/* buttons */
	.btn-row { display: flex; align-items: center; gap: var(--space-xl); }
	.btn-row__label {
		font-size: var(--text-xs); color: var(--text-3);
		width: 80px; flex-shrink: 0; text-transform: capitalize;
	}

	/* rating — each state sits in a captioned cell, mirroring the related-tracks
	 * grid. Cells wrap responsively rather than locking to a fixed column count. */
	.rating-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
		gap: var(--space-lg);
	}
	.rating-cell {
		display: flex;
		flex-direction: column;
		gap: var(--space-sm);
		min-width: 0;
	}
	.rating-cell__label {
		font-size: var(--text-2xs);
		color: var(--text-3);
		text-transform: uppercase;
		letter-spacing: 0.06em;
	}
	/* Static star-display cells (Empty / Partial / Full / Small-large) center the
	 * stars within the card so a row of cards reads balanced — the label stays at
	 * the top-left, only the star row centers. The Interactive cell is untouched. */
	.rating-cell--center {
		align-items: center;
	}
	.rating-cell--center .rating-cell__label {
		align-self: flex-start;
	}
	/* the interactive cell's resolved value/explanation sits on its own row
	 * beneath the stars (via Stack), not crammed onto the control's line. */
	.rating-cell__caption {
		font-size: var(--text-xs);
		color: var(--text-3);
	}

	/* chip — each variant sits in a captioned cell, mirroring the rating grid.
	 * Cells wrap responsively; the chips inside cluster with the shared utility. */
	.chip-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
		gap: var(--space-lg);
	}
	.chip-cell {
		display: flex;
		flex-direction: column;
		gap: var(--space-sm);
		min-width: 0;
	}
	.chip-cell__label {
		font-size: var(--text-2xs);
		color: var(--text-3);
		text-transform: uppercase;
		letter-spacing: 0.06em;
	}
	.chip-cell__empty {
		font-size: var(--text-xs);
		color: var(--text-3);
	}
	.chip-cell__note {
		font-size: var(--text-xs);
		line-height: var(--lh-sm);
		color: var(--text-3);
	}
	.vibe-dot {
		display: inline-block;
		width: var(--space-md);
		height: var(--space-md);
		border-radius: var(--radius-full);
	}
	/* bpm chip internals in the showcase — number leads (after the metronome glyph),
	 * signed delta follows. No literal "BPM" text. */
	.bpm-num {
		font-weight: var(--font-weight-semibold);
		font-variant-numeric: tabular-nums;
		color: var(--text-1);
	}
	.bpm-delta {
		font-variant-numeric: tabular-nums;
		font-weight: var(--font-weight-medium);
		margin-left: var(--space-2xs);
	}

	/* icons — labeled cards on the same uniform spacing as the chip grid. */
	.icon-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
		gap: var(--space-lg);
	}
	.icon-sizes {
		display: flex;
		flex-wrap: wrap;
		gap: var(--space-2xl);
		margin-top: var(--space-lg);
	}
	.icon-cell {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: var(--space-sm);
		padding: var(--space-lg);
		border: 1px solid var(--border-subtle);
		border-radius: var(--radius-md);
		background: var(--surface-2);
		min-width: 0;
	}
	.icon-sizes .icon-cell {
		min-width: 100px;
	}
	.icon-cell__glyph {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		color: var(--text-1);
	}
	.icon-cell__label {
		font-size: var(--text-2xs);
		color: var(--text-3);
		text-align: center;
	}

	/* menu — labeled trigger cards on the same uniform spacing as the icon grid.
	 * The panels float above on open; the cards just host the triggers. */
	.menu-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
		gap: var(--space-lg);
	}
	.menu-cell {
		display: flex;
		flex-direction: column;
		align-items: flex-start;
		gap: var(--space-sm);
		padding: var(--space-lg);
		border: 1px solid var(--border-subtle);
		border-radius: var(--radius-md);
		background: var(--surface-2);
		min-width: 0;
	}
	.menu-cell__label {
		font-size: var(--text-2xs);
		color: var(--text-3);
		text-transform: uppercase;
		letter-spacing: 0.06em;
	}
	.ds__note--quiet {
		color: var(--text-3);
	}
	kbd {
		font-family: inherit;
		font-size: var(--text-2xs);
		padding: var(--space-2xs) var(--space-xs);
		border: 1px solid var(--border-default);
		border-radius: var(--radius-sm);
		background: var(--surface-3);
		color: var(--text-2);
	}

	/* related tracks card — four states on the same equal-height grid the live
	 * track view uses, so the showcase matches reality. Each cell carries a small
	 * caption above the real card. */
	.related-grid {
		display: grid;
		grid-auto-rows: 1fr;
		gap: var(--space-lg);
	}
	/* Each demo grid uses FIXED-width columns so each row reliably lands in its
	 * intended container-query tier regardless of the viewport — the card adapts
	 * to its real column width, which is what we want to demonstrate. */
	/* Regular — 250px columns (≥240px tier): the full card, everything visible. */
	.related-grid--regular {
		grid-template-columns: repeat(auto-fill, 250px);
	}
	/* Intermediate — 220px columns (200–240px tier): genre + energy chips drop,
	 * energy folds to "+1"; signals stay the 3-col grid. */
	.related-grid--intermediate {
		grid-template-columns: repeat(auto-fill, 220px);
		gap: var(--space-md);
		margin-bottom: var(--space-lg);
	}
	/* Compact — 190px columns (<200px tier): the restructured 2-line layout. */
	.related-grid--compact {
		grid-template-columns: repeat(auto-fill, 190px);
		gap: var(--space-md);
		margin-bottom: var(--space-lg);
	}
	.related-density-label {
		font-size: var(--text-xs);
		color: var(--text-3);
		margin: var(--space-md) 0 var(--space-sm);
	}
	.related-cell {
		display: flex;
		flex-direction: column;
		gap: var(--space-sm);
		min-width: 0;
	}
	.related-cell__label {
		font-size: var(--text-2xs);
		color: var(--text-3);
		text-transform: uppercase;
		letter-spacing: 0.06em;
	}

	@media (max-width: 720px) {
		.related-grid--regular { grid-template-columns: repeat(2, minmax(0, 1fr)); }
		.related-grid--intermediate { grid-template-columns: repeat(2, minmax(0, 1fr)); }
		.related-grid--compact { grid-template-columns: repeat(3, minmax(0, 1fr)); }
	}
</style>
