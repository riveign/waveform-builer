<script lang="ts">
	import Button from '$lib/components/primitives/Button.svelte';
	import Stack from '$lib/components/primitives/Stack.svelte';
	import Grid from '$lib/components/primitives/Grid.svelte';

	// Pine ramp swatches with their REAL computed contrast vs the page bg (#0D0D0D).
	// Ratios are the honest WCAG 2.x figures from Research §4 — the showcase never lies.
	type Verdict = 'text' | 'large' | 'nontext';
	const pineRamp: { step: string; hex: string; ratio: string; verdict: Verdict; note: string }[] = [
		{ step: '50',  hex: '#E8F8F0', ratio: '18.9:1', verdict: 'text',    note: 'lightest tint' },
		{ step: '100', hex: '#D3F0E2', ratio: '16.6:1', verdict: 'text',    note: '' },
		{ step: '200', hex: '#B5E2CD', ratio: '13.4:1', verdict: 'text',    note: '' },
		{ step: '300', hex: '#8ACDAF', ratio: '9.9:1',  verdict: 'text',    note: '' },
		{ step: '400', hex: '#3FB489', ratio: '7.50:1', verdict: 'text',    note: 'the only decided hex safe as body text on dark' },
		{ step: '500', hex: '#25855E', ratio: '4.25:1', verdict: 'large',   note: 'hover fill, large text / UI only' },
		{ step: '600', hex: '#1F6F54', ratio: '3.20:1', verdict: 'large',   note: 'PRIMARY fill — UI / large text only, never body' },
		{ step: '700', hex: '#185C45', ratio: '2.46:1', verdict: 'nontext', note: 'press / dim — non-text only' },
		{ step: '800', hex: '#164735', ratio: '1.9:1',  verdict: 'nontext', note: '' },
		{ step: '900', hex: '#123226', ratio: '1.5:1',  verdict: 'nontext', note: '' },
		{ step: '950', hex: '#0C2018', ratio: '1.2:1',  verdict: 'nontext', note: '' },
	];

	const verdictLabel: Record<Verdict, string> = {
		text: 'Body text AA (≥4.5:1)',
		large: 'Large / UI only (≥3:1)',
		nontext: 'Non-text only',
	};

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

<div class="ds" data-theme="pine">
	<header class="ds__head">
		<h1>Kiku design system</h1>
		<p class="ds__lede">
			One source of visual truth — the tokens, layout helpers, and primitives your sets are
			built on. Pine renders here, in isolation, so you can read the system before the rest of
			the app adopts it. Tab through anything to see its focus ring.
		</p>
	</header>

	<!-- 1. COLOR & CONTRAST -->
	<section class="ds__section">
		<h2>Color &amp; contrast</h2>
		<p class="ds__note">
			Every pine step with its real contrast against the page (#0D0D0D) and what it's allowed to
			do. The ratio decides the role — not the other way around.
		</p>
		<div class="swatch-grid">
			{#each pineRamp as s (s.step)}
				<div class="swatch">
					<div class="swatch__chip" style="background: var(--pine-{s.step});"></div>
					<div class="swatch__meta">
						<code>--pine-{s.step}</code>
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
				Button labels are <strong>white on pine-600</strong> = <strong>6.07:1</strong> (passes AA).
				Black would be 3.20:1 — it wouldn't. So <code>--on-accent</code> is white.
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
		<p class="ds__note">Anchored at 12px body. Each line is set at its own token size and line-height.</p>
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
		<p class="ds__note">One primitive, every variant × size, plus disabled and loading. Pine fill, white label.</p>
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
	/* Pine resolves ONLY inside this subtree. :global() is required because data-theme
	 * sits on the page root and the override must cascade to <Button> children. */
	:global([data-theme='pine']) {
		--accent-9:  var(--pine-600);  /* #1F6F54 fill */
		--accent-10: var(--pine-500);  /* #25855E hover */
		--accent-11: var(--pine-400);  /* #3FB489 text-on-dark, 7.50:1 */
		--accent-contrast: #FFFFFF;    /* on-fill label, 6.07:1 — NOT black, NOT #3FB489 */
		--accent-pressed: var(--pine-700);
	}

	.ds {
		max-width: 960px;
		margin: 0 auto;
		padding: var(--space-5xl) var(--space-4xl) var(--space-6xl);
		height: 100%;
		overflow-y: auto;
		color: var(--text-1);
	}

	.ds__head { margin-bottom: var(--space-5xl); }
	.ds h1 {
		font-size: var(--text-2xl);
		font-weight: var(--font-weight-semibold);
		color: var(--accent-text);
		margin-bottom: var(--space-md);
	}
	.ds__lede { font-size: var(--text-md); line-height: var(--lh-md); color: var(--text-2); max-width: 60ch; }

	.ds__section {
		padding: var(--space-4xl) 0;
		border-top: 1px solid var(--border-subtle);
	}
	.ds h2 {
		font-size: var(--text-xl);
		font-weight: var(--font-weight-semibold);
		margin-bottom: var(--space-sm);
	}
	.ds__note { font-size: var(--text-sm); color: var(--text-3); margin-bottom: var(--space-xl); max-width: 60ch; }

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

	.on-accent-proof {
		display: flex; align-items: center; gap: var(--space-lg);
		margin-top: var(--space-xl);
		padding: var(--space-lg);
		background: var(--surface-2);
		border: 1px solid var(--border-subtle);
		border-radius: var(--radius-md);
	}
	.on-accent-proof__chip {
		background: var(--pine-600); color: #FFFFFF;
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
