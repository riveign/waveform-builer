<script lang="ts">
	import Button from '$lib/components/primitives/Button.svelte';
	import Stack from '$lib/components/primitives/Stack.svelte';
	import Grid from '$lib/components/primitives/Grid.svelte';

	// CERCETA book palette — Sara Caldas's 5 source colors, mapped to roles.
	// Every ratio is the honest WCAG 2.x figure vs the page bg (#0D0D0D) — the
	// showcase never lies. text-safe vs fill steps are called out per color.
	type Verdict = 'text' | 'large' | 'nontext';
	const verdictLabel: Record<Verdict, string> = {
		text: 'Body text AA (≥4.5:1)',
		large: 'Large / UI only (≥3:1)',
		nontext: 'Non-text only',
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
</script>

<div class="ds" data-theme="cerceta">
	<header class="ds__head">
		<p class="ds__kicker">Kiku 聴く — the visual language</p>
		<h1>How Kiku looks when it listens</h1>
		<p class="ds__lede">
			The shared vocabulary every screen is built from — the tokens, the rhythm, the primitives.
			Read it the way you'd read a track before you mix it: notice the spacing, the contrast, the
			restraint. The cerceta palette renders here in isolation, so you can learn the system before
			the rest of the app speaks it. Tab through anything to hear its focus ring.
		</p>
	</header>

	<!-- 1. COLOR & PALETTE -->
	<section class="ds__section">
		<h2>The cerceta palette</h2>
		<p class="ds__note">
			Five colors from Sara Caldas's book, each with a job. Cerceta leads; lilac echoes; navy holds
			structure; magenta is the rare pop. The ratio decides the role — fill steps fill, text steps
			read. Every figure is real contrast against the page (#0D0D0D).
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
			The primary teal, stepped. The ratio against the page decides what each step is allowed to do.
		</p>
		<div class="swatch-grid">
			{#each tealRamp as s (s.step)}
				<div class="swatch">
					<div class="swatch__chip" style="background: var(--teal-{s.step});"></div>
					<div class="swatch__meta">
						<code>--teal-{s.step}</code>
						<span class="swatch__hex">{s.hex}</span>
						<span class="swatch__ratio">{s.ratio}</span>
						<span class="swatch__verdict swatch__verdict--{s.verdict}">{verdictLabel[s.verdict]}</span>
						{#if s.note}<span class="swatch__hint">{s.note}</span>{/if}
					</div>
				</div>
			{/each}
		</div>

		<div class="on-accent-proof">
			<div class="on-accent-proof__chip">Aa label</div>
			<p>
				Button labels are <strong>white on teal-600</strong> = <strong>4.23:1</strong> (passes AA
				large / 3:1). So <code>--on-accent</code> stays white on the cerceta fill.
			</p>
		</div>
	</section>

	<!-- 2. SPACING -->
	<section class="ds__section">
		<h2>Spacing scale</h2>
		<p class="ds__note">A 4px rhythm with a 2px mini-unit for dense rows. Every bar is its real width.</p>
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
		<p class="ds__note">Anchored at a 12px body — the size most of your library reads at. Each line is set at its own token size and line-height.</p>
		<Stack gap="var(--space-md)">
			{#each typeScale as t (t.name)}
				<div class="type-row">
					<code class="type-row__name">--text-{t.name}</code>
					<span class="type-row__sample" style="font-size: var(--text-{t.name}); line-height: var(--lh-{t.name});">
						The set breathes through energy — {t.px}
					</span>
				</div>
			{/each}
		</Stack>
	</section>

	<!-- 4. RADIUS -->
	<section class="ds__section">
		<h2>Radius</h2>
		<p class="ds__note">Five steps plus full. Replaces the old 2/3/4/6/8/10/12 sprawl.</p>
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
		<p class="ds__note">Border-first on dark — shadows read poorly on #0D0D0D, so they're reserved for floating layers.</p>
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
		<p class="ds__note">Opt-in for content. The app shell and the fixed two-pane layout stay flex.</p>
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
		<p class="ds__note">One primitive, every variant × size, plus disabled and loading. Cerceta fill, white label.</p>
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
		<p class="ds__note">Tab through these to see the ring. It only shows for keyboard, never the mouse.</p>
		<div class="cluster cluster--md">
			<Button variant="primary">First</Button>
			<Button variant="secondary">Second</Button>
			<input type="text" placeholder="and a field" />
			<Button variant="ghost">Last</Button>
		</div>
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
	}

	.ds {
		max-width: 960px;
		margin: 0 auto;
		padding: var(--space-5xl) var(--space-4xl) var(--space-6xl);
		height: 100%;
		overflow-y: auto;
		color: var(--text-1);
	}

	.ds__head { margin-bottom: var(--space-6xl); }
	.ds__kicker {
		font-size: var(--text-xs);
		font-weight: var(--font-weight-semibold);
		line-height: var(--lh-xs);
		letter-spacing: 0.08em;
		text-transform: uppercase;
		color: var(--accent-text);
		margin-bottom: var(--space-lg);
	}
	.ds h1 {
		font-size: var(--text-2xl);
		line-height: var(--lh-2xl);
		font-weight: var(--font-weight-semibold);
		color: var(--text-1);
		margin-bottom: var(--space-lg);
	}
	.ds__lede {
		font-size: var(--text-lg);
		line-height: var(--lh-lg);
		color: var(--text-2);
		max-width: 60ch;
	}

	.ds__section {
		padding: var(--space-5xl) 0;
		border-top: 1px solid var(--border-subtle);
	}
	.ds h2 {
		font-size: var(--text-xl);
		line-height: var(--lh-xl);
		font-weight: var(--font-weight-semibold);
		margin-bottom: var(--space-md);
	}
	.ds__note {
		font-size: var(--text-sm);
		line-height: var(--lh-sm);
		color: var(--text-3);
		margin-bottom: var(--space-2xl);
		max-width: 60ch;
	}

	/* color */
	.swatch-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
		gap: var(--space-lg);
	}
	.swatch {
		display: flex;
		gap: var(--space-md);
		background: var(--surface-2);
		border: 1px solid var(--border-subtle);
		border-radius: var(--radius-md);
		padding: var(--space-md);
	}
	.swatch__chip { width: 48px; height: 48px; border-radius: var(--radius-sm); flex-shrink: 0; }
	.swatch__meta { display: flex; flex-direction: column; gap: var(--space-2xs); min-width: 0; }
	.swatch__meta code { font-size: var(--text-xs); color: var(--text-1); }
	.swatch__hex { font-size: var(--text-2xs); color: var(--text-3); text-transform: uppercase; }
	.swatch__ratio { font-size: var(--text-sm); font-weight: var(--font-weight-semibold); }
	.swatch__verdict { font-size: var(--text-2xs); }
	.swatch__verdict--text { color: var(--energy-low); }
	.swatch__verdict--large { color: var(--energy-mid); }
	.swatch__verdict--nontext { color: var(--text-4); }
	.swatch__hint { font-size: var(--text-2xs); color: var(--text-3); }

	/* palette role cards (the five source colors) */
	.ds__subhead {
		font-size: var(--text-lg);
		line-height: var(--lh-lg);
		font-weight: var(--font-weight-semibold);
		margin-top: var(--space-4xl);
		margin-bottom: var(--space-md);
	}
	.palette-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
		gap: var(--space-lg);
		margin-bottom: var(--space-2xl);
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
		margin-top: var(--space-xl);
		padding: var(--space-lg);
		background: var(--surface-2);
		border: 1px solid var(--border-subtle);
		border-radius: var(--radius-md);
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
</style>
