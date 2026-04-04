/**
 * Shared energy utilities — single source of truth for zone-to-numeric mapping.
 *
 * Replaces duplicate normalizeEnergy/parseEnergy functions across
 * EnergyFlowChart, SetTimeline, and SetTrackCard.
 */

/** Zone/tag to numeric energy value (0-1). Matches backend ENERGY_TAG_VALUES. */
export const ENERGY_VALUES: Record<string, number> = {
	low: 0.2,
	warmup: 0.25,
	closing: 0.35,
	close: 0.35,
	mid: 0.5,
	build: 0.55,
	dance: 0.6,
	up: 0.7,
	drive: 0.72,
	high: 0.75,
	fast: 0.85,
	peak: 0.9,
};

/**
 * Normalize an energy string (zone label, tag, or numeric) to a 0-1 value.
 * Returns null if the input is unrecognized.
 */
export function normalizeEnergy(energy: string | null | undefined): number | null {
	if (!energy) return null;

	// Try integer parsing (old Rekordbox 1-9 scale)
	const n = parseInt(energy, 10);
	if (!isNaN(n) && n >= 1 && n <= 9) return (n - 1) / 8;

	return ENERGY_VALUES[energy.toLowerCase()] ?? null;
}

/**
 * Get the best numeric energy value for a track, preferring the backend-computed
 * energy_value (from audio_features.energy) over zone-derived values.
 */
export function getTrackEnergyNumeric(
	energyValue: number | null | undefined,
	energy: string | null | undefined,
): number | null {
	if (energyValue != null) return energyValue;
	return normalizeEnergy(energy);
}

/** Energy bar color based on numeric value. */
export function energyColor(value: number | null): string {
	if (value === null) return 'var(--text-dim)';
	if (value < 0.4) return 'var(--energy-low)';
	if (value < 0.65) return 'var(--energy-mid)';
	return 'var(--energy-high)';
}
