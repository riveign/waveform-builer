/**
 * The single source of truth for every canvas color in the app.
 *
 * Canvas surfaces (Chart.js charts, the WaveSurfer waveform, the CSS heatmap)
 * can't consume CSS custom properties directly, so we read the live token
 * values off the document root at runtime via getComputedStyle. This keeps
 * every canvas following the theme: when the cerceta tokens re-point, the
 * canvases recolor with the rest of the app — the next recolor is a one-file
 * change.
 *
 * Each lookup falls back to a cerceta-ramp HEX constant that mirrors the token
 * it reads (sourced from tokens.primitives.css). The fallbacks only apply if a
 * token is missing or a value is needed before the document is styled (e.g. a
 * test/SSR context) — in the running app the token wins.
 *
 * The 7-family categorical palette is mapped onto maximally-separated cerceta
 * hues (teal / hot-magenta / sky-navy / pale-lilac / deep-magenta / deep-navy /
 * neutral gray) so the families stay visually distinct and AA-legible against
 * the dark app surface (--gray-950 #0D0D0D) — the reason this palette was
 * originally left categorical.
 *
 * Two formerly-inline holdouts now live here too:
 *   - deviationColors() — the energy-arc fit ramp (good/acceptable/poor),
 *     mapped onto the in-book --score-* tokens so it follows the theme.
 *   - spectrumBands() — the 4-band frequency palette for the spectral waveform,
 *     a documented DOMAIN exception (see its own comment).
 */

/** Read a CSS custom property off :root, falling back to a cerceta-ramp hex. */
export function token(name: string, fallback: string): string {
	if (typeof document === 'undefined') return fallback;
	const value = getComputedStyle(document.documentElement)
		.getPropertyValue(name)
		.trim();
	return value || fallback;
}

/**
 * Categorical palette for the 7 genre families. Token-driven, with cerceta-hex
 * fallbacks mirroring each token. Hues are chosen for separation + legibility.
 */
export function familyColors(): Record<string, string> {
	return {
		Techno: token('--teal-400', '#00B1B8'), // bright teal — the primary
		House: token('--magenta-400', '#F969A3'), // hot magenta
		Groove: token('--navy-400', '#5FABE2'), // sky blue
		Trance: token('--lilac-300', '#D5B2D5'), // pale lilac
		Breaks: token('--magenta-600', '#AF125A'), // deep magenta
		Electronic: token('--navy-700', '#166595'), // deep navy
		Other: token('--gray-400', '#666666'), // neutral
	};
}

/** Resolve one family to its cerceta color (falls back to Other). */
export function familyColor(
	family: string,
	colors: Record<string, string> = familyColors(),
): string {
	return colors[family] ?? colors.Other;
}

/**
 * Shared chart "chrome" colors (axis text, grid lines, labels, tooltip surface)
 * sourced from the cerceta semantic/primitive tokens. Used by every Chart.js
 * chart so the chrome agrees with the rest of the app.
 */
export function chartChrome() {
	return {
		text: token('--gray-50', '#F5F5F0'), // legend / strong label text
		label: token('--gray-200', '#A0A1A7'), // axis titles / point labels
		tick: token('--gray-400', '#666666'), // axis tick text
		grid: gridColor(), // grid / angle lines (translucent border)
		surface: token('--gray-950', '#0D0D0D'), // tooltip / canvas surface
		border: token('--gray-600', '#3F414A'), // tooltip / axis border
		muted: token('--gray-500', '#555555'), // crosshair / faint chrome
	};
}

/** Translucent grid line color derived from the cerceta border token. */
function gridColor(): string {
	const border = token('--gray-600', '#3F414A');
	return rgba(border, 0.5);
}

/** Convert a #rrggbb hex (or pass-through rgb) to an rgba() string. */
export function rgba(hex: string, alpha: number): string {
	const m = /^#?([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})$/i.exec(hex.trim());
	if (!m) return hex;
	const r = parseInt(m[1], 16);
	const g = parseInt(m[2], 16);
	const b = parseInt(m[3], 16);
	return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

/** The teal accent used for single-series charts (e.g. the Taste radar). */
export function accentColor(): string {
	return token('--teal-400', '#00B1B8');
}

/**
 * Energy-arc fit ramp for EnergyFlowChart point/segment colors.
 *
 * Each verdict reads an in-book --score-* token (cerceta semantic ramp) so the
 * fit colors follow the theme instead of the old off-book traffic-light hexes.
 * The "no target" case has no verdict to score, so it falls to the brand accent.
 * Fallbacks mirror the tokens in tokens.semantic.css (--score-* → cerceta hues).
 */
export function deviationColors() {
	return {
		good: token('--score-good', '#BA94BA'), // dev <= 0.15 — fits the arc
		acceptable: token('--score-fair', '#F969A3'), // dev <= 0.30 — drifting
		poor: token('--score-poor', '#FF8DBA'), // dev  > 0.30 — off the arc
		noTarget: accentColor(), // no profile to score against
	};
}

/**
 * 4-band frequency palette for the spectral waveform (WavesurferPlayer).
 *
 * DOMAIN EXCEPTION: unlike the rest of this module, these are intentional
 * domain hues (bass/low-mid/high-mid/high), the same convention an audio
 * spectrum analyzer uses. They are NOT part of the cerceta semantic ramp and
 * deliberately stay constant across theme flips. They live here — in ONE
 * exported function — so a future retint is still a single-file edit, and so
 * the waveform and its on-screen legend read the SAME source of truth.
 *
 * `played` is the darker variant painted over the elapsed portion.
 * Note: the CSS swatches inside WavesurferPlayer's spectral-toggle icon
 * (.band-low/.band-midlow/.band-midhigh/.band-high) mirror these hexes; keep
 * the two in sync if these change.
 */
export interface SpectrumBand {
	/** Human-readable band name, surfaced in the legend / accessible description. */
	name: string;
	/** Color for the unplayed (upcoming) portion of the waveform. */
	unplayed: string;
	/** Darker color for the played (elapsed) portion. */
	played: string;
}

export function spectrumBands(): SpectrumBand[] {
	return [
		{ name: 'Bass', unplayed: '#e74c3c', played: '#c0392b' }, // red
		{ name: 'Low-mid', unplayed: '#e67e22', played: '#d35400' }, // orange
		{ name: 'High-mid', unplayed: '#2ecc71', played: '#27ae60' }, // green
		{ name: 'High', unplayed: '#3498db', played: '#2980b9' }, // blue
	];
}
