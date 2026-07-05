<script lang="ts">
	import type { TransitionScoreBreakdown } from '$lib/types';
	import { harmonicRelationship } from '$lib/utils/camelot';

	let {
		breakdown,
		analysisBreakdown = null,
		keyA = null,
		keyB = null,
	}: {
		breakdown: TransitionScoreBreakdown;
		/** Context-aware (arc) scores. When present, each dimension shows both
		 * values on one row ("on their own" vs "in your arc"). */
		analysisBreakdown?: TransitionScoreBreakdown | null;
		keyA?: string | null;
		keyB?: string | null;
	} = $props();

	let hasDual = $derived(analysisBreakdown !== null);

	/** A dimension counts as diverging when the two lenses disagree enough to
	 * be worth calling out. Grounded in the 0.5/0.8 verdict bands. */
	const DIVERGE = 0.15;
	const WEAK = 0.5;

	const TEACHING: Record<string, [string, string, string]> = {
		harmonic:        ["Keys align naturally", "Some harmonic tension", "Clashing keys — bold move"],
		energy_fit:      ["Right on the energy curve", "Drifting from your target", "Sharp energy jump"],
		bpm_compat:      ["Seamless tempo", "Slight tempo shift", "Big tempo change"],
		genre_coherence: ["Same sonic world", "Crossing genre boundaries", "Genre clash — make it count"],
		track_quality:   ["Well-curated pick", "Decent selection", "Under-played — give it a chance"],
	};

	function getTeachingNote(key: string, value: number): string {
		// For harmonic, use the richer relationship description if keys are available
		if (key === 'harmonic' && (keyA || keyB)) {
			return harmonicRelationship(keyA, keyB).description;
		}
		const [high, mid, low] = TEACHING[key] ?? ["", "", ""];
		if (value >= 0.8) return high;
		if (value >= 0.5) return mid;
		return low;
	}

	function lcFirst(s: string): string {
		return s ? s.charAt(0).toLowerCase() + s.slice(1) : s;
	}

	/** A note for a non-diverging dimension: shown only when it's weak enough
	 * to be a real teaching moment; otherwise it lives in the label tooltip. */
	function weakNote(key: string, arc: number): string | null {
		return arc < WEAK ? getTeachingNote(key, arc) : null;
	}

	const dimensions = [
		{ key: 'harmonic' as const, label: 'Harmonic', weight: 0.25, color: 'var(--zone-close)' },
		{ key: 'energy_fit' as const, label: 'Energy Fit', weight: 0.20, color: 'var(--energy-high)' },
		{ key: 'bpm_compat' as const, label: 'BPM', weight: 0.20, color: 'var(--accent-text)' },
		{ key: 'genre_coherence' as const, label: 'Genre', weight: 0.15, color: 'var(--score-excellent)' },
		{ key: 'track_quality' as const, label: 'Quality', weight: 0.20, color: 'var(--score-good)' },
	];

	let delta = $derived(analysisBreakdown ? analysisBreakdown.total - breakdown.total : 0);
	function fmtDelta(d: number): string {
		return `${d >= 0 ? '+' : '−'}${Math.abs(d).toFixed(3)}`;
	}
</script>

{#if hasDual && analysisBreakdown}
	<!-- ── Dual mode: one table, two lenses ── -->
	<div class="score-breakdown dual">
		<div class="score-head">
			<div class="score-tot own" title="the two tracks as a pair">
				<span class="tot-lab">On their own</span>
				<span class="tot-val">{breakdown.total.toFixed(3)}</span>
			</div>
			<div class="score-tot arc" title="weighed against the set's journey">
				<span class="tot-lab">In your arc</span>
				<span class="tot-val">{analysisBreakdown.total.toFixed(3)}</span>
				<span class="tot-delta" class:up={delta >= 0} class:down={delta < 0}>{fmtDelta(delta)}</span>
			</div>
		</div>

		<div class="dimensions">
			{#each dimensions as dim}
				{@const own = breakdown[dim.key]}
				{@const arc = analysisBreakdown[dim.key]}
				{@const diverges = Math.abs(own - arc) >= DIVERGE}
				{@const wNote = weakNote(dim.key, arc)}
				{@const hasNote = diverges || wNote !== null}
				<div class="dim-group" class:diverge={diverges}>
					<div class="dim-row">
						<span class="dim-label" title={hasNote ? null : getTeachingNote(dim.key, arc)}>
							{dim.label}<span class="dim-weight">×{dim.weight}</span>
						</span>
						<div class="dim-bar">
							{#if !diverges}
								<div class="dim-fill" style="width: {arc * 100}%; background: {dim.color}"></div>
							{:else if arc > own}
								<div class="dim-fill dim-own" style="width: {own * 100}%; background: {dim.color}"></div>
								<div class="dim-fill dim-lift" style="left: {own * 100}%; width: {(arc - own) * 100}%"></div>
							{:else}
								<div class="dim-fill dim-own" style="width: {own * 100}%; background: {dim.color}"></div>
								<div class="dim-fill dim-drop" style="left: {arc * 100}%; width: {(own - arc) * 100}%"></div>
							{/if}
						</div>
						<span class="dim-vals">
							{#if diverges}
								<span class="own-v">{own.toFixed(2)}</span>
								<span class="arr">→</span>
								<span class="arc-v">{arc.toFixed(2)}</span>
							{:else}
								<span class="same-v">{arc.toFixed(2)}</span>
							{/if}
						</span>
					</div>
					{#if diverges}
						<div class="dim-note split">On their own <b>{lcFirst(getTeachingNote(dim.key, own))}</b> — in your arc, <b>{lcFirst(getTeachingNote(dim.key, arc))}</b>.</div>
					{:else if wNote}
						<div class="dim-note">{wNote}</div>
					{/if}
				</div>
			{/each}
		</div>

		{#if breakdown.discovery_label}
			<div class="discovery-badge">
				<span class="discovery-icon">&#9679;</span>
				<span class="discovery-text">{breakdown.discovery_label}</span>
				{#if breakdown.set_appearances != null && breakdown.set_appearances > 0}
					<span class="discovery-detail">&middot; in {breakdown.set_appearances} set{breakdown.set_appearances > 1 ? 's' : ''}</span>
				{/if}
			</div>
		{/if}
	</div>
{:else}
	<!-- ── Single mode (fallback) ── -->
	<div class="score-breakdown">
		<div class="total-score">
			<span class="total-label">Score</span>
			<span class="total-value">{breakdown.total.toFixed(3)}</span>
		</div>
		<div class="dimensions">
			{#each dimensions as dim}
				{@const value = breakdown[dim.key]}
				<div class="dim-group">
					<div class="dim-row">
						<span class="dim-label">{dim.label}</span>
						<div class="dim-bar">
							<div
								class="dim-fill"
								style="width: {value * 100}%; background: {dim.color}"
							></div>
						</div>
						<span class="dim-value">{value.toFixed(2)}</span>
						<span class="dim-weight">x{dim.weight}</span>
					</div>
					<div class="dim-note">{getTeachingNote(dim.key, value)}</div>
				</div>
			{/each}
		</div>
		{#if breakdown.discovery_label}
			<div class="discovery-badge">
				<span class="discovery-icon">&#9679;</span>
				<span class="discovery-text">{breakdown.discovery_label}</span>
				{#if breakdown.set_appearances != null && breakdown.set_appearances > 0}
					<span class="discovery-detail">&middot; in {breakdown.set_appearances} set{breakdown.set_appearances > 1 ? 's' : ''}</span>
				{/if}
			</div>
		{/if}
	</div>
{/if}

<style>
	.score-breakdown {
		background: var(--bg-secondary);
		border-radius: 6px;
		padding: 12px;
	}

	/* dual mode fills its column so its bottom aligns with the players column */
	.score-breakdown.dual {
		display: flex;
		flex-direction: column;
		flex: 1;
		min-height: 0;
	}

	/* ── Totals (dual) ── */

	.score-head {
		display: flex;
		align-items: stretch;
		gap: 8px;
		margin-bottom: 8px;
	}

	.score-tot {
		flex: 1;
		display: flex;
		align-items: baseline;
		gap: 8px;
		border: 1px solid var(--border);
		border-radius: var(--radius-md);
		padding: 8px 11px;
	}

	.score-tot.arc {
		background: linear-gradient(180deg, color-mix(in srgb, var(--accent) 10%, transparent), transparent);
		border-color: color-mix(in srgb, var(--accent) 40%, transparent);
	}

	.tot-lab {
		font-size: 10px;
		text-transform: uppercase;
		letter-spacing: 0.5px;
		color: var(--text-dim);
		white-space: nowrap;
	}

	.tot-val {
		font-size: 19px;
		font-weight: 700;
		line-height: 1;
		font-variant-numeric: tabular-nums;
		color: var(--text-secondary);
	}

	.score-tot.arc .tot-val {
		color: var(--accent-text);
	}

	.tot-delta {
		margin-left: auto;
		align-self: center;
		font-size: 11px;
		font-weight: 600;
		font-variant-numeric: tabular-nums;
	}

	.tot-delta.up {
		color: var(--score-excellent);
	}

	.tot-delta.down {
		color: var(--score-fair);
	}

	/* ── Dimensions ── */

	.dimensions {
		display: flex;
		flex-direction: column;
		gap: 10px;
	}

	.dual .dimensions {
		flex: 1;
		justify-content: space-between;
		gap: 6px;
	}

	.dim-group {
		display: flex;
		flex-direction: column;
		gap: 2px;
	}

	.dual .dim-group.diverge {
		background: linear-gradient(90deg, color-mix(in srgb, var(--accent-hover) 8%, transparent), transparent 70%);
		margin: 0 -8px;
		padding: 4px 8px;
		border-radius: var(--radius-sm);
	}

	.dim-row {
		display: flex;
		align-items: center;
		gap: 8px;
	}

	.dim-label {
		width: 70px;
		font-size: 11px;
		color: var(--text-secondary);
		flex-shrink: 0;
	}

	.dim-label[title] {
		cursor: help;
	}

	.dual .dim-weight {
		display: block;
		font-size: 9px;
		color: var(--text-dim);
		font-variant-numeric: tabular-nums;
		margin-top: 1px;
	}

	.dim-bar {
		position: relative;
		flex: 1;
		height: 6px;
		background: var(--bg-tertiary);
		border-radius: 3px;
		overflow: hidden;
	}

	.dim-fill {
		height: 100%;
		border-radius: 3px;
		transition: width 0.3s;
	}

	.dual .dim-fill {
		position: absolute;
		top: 0;
		bottom: 0;
		left: 0;
	}

	.dual .dim-own {
		opacity: 0.55;
	}

	.dual .dim-lift {
		background: var(--accent-hover);
	}

	.dual .dim-drop {
		background: var(--score-fair);
		opacity: 0.9;
	}

	/* single-mode value + weight */
	.dim-value {
		width: 32px;
		text-align: right;
		font-size: 11px;
		font-variant-numeric: tabular-nums;
		color: var(--text-primary);
	}

	.score-breakdown:not(.dual) .dim-weight {
		width: 28px;
		text-align: right;
		font-size: 10px;
		color: var(--text-dim);
	}

	/* dual value cluster */
	.dim-vals {
		display: flex;
		align-items: center;
		gap: 6px;
		justify-content: flex-end;
		min-width: 96px;
		font-size: 12px;
		font-variant-numeric: tabular-nums;
	}

	.dim-vals .own-v {
		color: var(--text-dim);
	}

	.dim-vals .arr {
		color: var(--accent-hover);
		font-size: 11px;
	}

	.dim-vals .arc-v {
		color: var(--accent-text);
		font-weight: 700;
	}

	.dim-vals .same-v {
		color: var(--text-primary);
		font-weight: 600;
	}

	.dim-note {
		font-size: 10px;
		color: var(--text-dim);
		padding-left: 78px;
		font-style: italic;
	}

	.dual .dim-note {
		padding-left: 0;
	}

	.dual .dim-note.split {
		color: var(--text-secondary);
	}

	.dual .dim-note.split b {
		color: var(--accent-text);
		font-style: normal;
		font-weight: 600;
	}

	/* ── Total (single) ── */

	.total-score {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 10px;
		padding-bottom: 8px;
		border-bottom: 1px solid var(--border);
	}

	.total-label {
		font-size: 12px;
		text-transform: uppercase;
		letter-spacing: 0.5px;
		color: var(--text-secondary);
	}

	.total-value {
		font-size: 20px;
		font-weight: 700;
		color: var(--accent);
		font-variant-numeric: tabular-nums;
	}

	/* ── Discovery ── */

	.discovery-badge {
		display: flex;
		align-items: center;
		gap: 5px;
		margin-top: 8px;
		padding: 6px 10px;
		background: var(--bg-tertiary);
		border-radius: 4px;
		font-size: 11px;
	}

	.discovery-icon {
		color: var(--accent);
		font-size: 8px;
	}

	.discovery-text {
		color: var(--accent);
		font-weight: 500;
		text-transform: capitalize;
	}

	.discovery-detail {
		color: var(--text-dim);
	}
</style>
