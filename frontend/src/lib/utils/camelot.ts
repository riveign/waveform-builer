/**
 * Camelot wheel color mapping for key display.
 */
const CAMELOT_COLORS: Record<string, string> = {
	'1A': '#f44336', '1B': '#ff7043',
	'2A': '#ff5722', '2B': '#ff9800',
	'3A': '#ff9800', '3B': '#ffc107',
	'4A': '#ffc107', '4B': '#ffeb3b',
	'5A': '#cddc39', '5B': '#8bc34a',
	'6A': '#4caf50', '6B': '#66bb6a',
	'7A': '#009688', '7B': '#26a69a',
	'8A': '#00bcd4', '8B': '#29b6f6',
	'9A': '#2196f3', '9B': '#42a5f5',
	'10A': '#3f51b5', '10B': '#5c6bc0',
	'11A': '#673ab7', '11B': '#7e57c2',
	'12A': '#9c27b0', '12B': '#e91e63',
};

export function getCamelotColor(key: string | null): string {
	if (!key) return '#666';
	const upper = key.toUpperCase();
	if (CAMELOT_COLORS[upper]) return CAMELOT_COLORS[upper];
	// Try converting standard key name to Camelot
	const camelot = toCamelot(key);
	if (camelot) return CAMELOT_COLORS[camelot] ?? '#888';
	return '#888';
}

export interface CamelotKey {
	number: number;
	letter: 'A' | 'B';
}

/** Standard key names → Camelot notation. Minor = A, Major = B. */
const KEY_TO_CAMELOT: Record<string, string> = {
	// Minor keys (A)
	'ABM': '1A', 'G#M': '1A',
	'EBM': '2A', 'D#M': '2A',
	'BBM': '3A', 'A#M': '3A',
	'FM': '4A',
	'CM': '5A',
	'GM': '6A',
	'DM': '7A',
	'AM': '8A',
	'EM': '9A',
	'BM': '10A',
	'F#M': '11A', 'GBM': '11A',
	'C#M': '12A', 'DBM': '12A',
	// Major keys (B)
	'B': '1B',
	'F#': '2B', 'GB': '2B',
	'C#': '3B', 'DB': '3B',
	'AB': '4B', 'G#': '4B',
	'EB': '5B', 'D#': '5B',
	'BB': '6B', 'A#': '6B',
	'F': '7B',
	'C': '8B',
	'G': '9B',
	'D': '10B',
	'A': '11B',
	'E': '12B',
};

/**
 * Normalize a key string to Camelot notation.
 * Accepts: "8A", "F#m", "Cm", "Ab", "Ebm", "D#min", "C Major", etc.
 */
function toCamelot(key: string): string | null {
	const k = key.trim();
	// Already Camelot notation?
	if (/^\d{1,2}[AB]$/i.test(k)) return k.toUpperCase();

	// Normalize: strip "min/minor/maj/major", detect minor via trailing "m"
	const normalized = k
		.replace(/\s*(minor|min)\s*$/i, 'm')
		.replace(/\s*(major|maj)\s*$/i, '')
		.trim();

	const isMinor = /m$/i.test(normalized) && !/^[A-G]$/i.test(normalized);
	const root = normalized.replace(/m$/i, '').replace(/♯/g, '#').replace(/♭/g, 'b').toUpperCase();

	const lookup = isMinor ? root + 'M' : root;
	return KEY_TO_CAMELOT[lookup] ?? null;
}

/**
 * Parse a key string into Camelot number + letter.
 * Accepts Camelot ("8A") and standard notation ("F#m", "Ab", "C").
 */
export function parseCamelot(key: string | null | undefined): CamelotKey | null {
	if (!key) return null;
	const camelot = toCamelot(key);
	if (!camelot) return null;
	const match = camelot.match(/^(\d{1,2})([AB])$/);
	if (!match) return null;
	const num = parseInt(match[1], 10);
	if (num < 1 || num > 12) return null;
	return { number: num, letter: match[2] as 'A' | 'B' };
}

export interface HarmonicRelationship {
	type: 'same' | 'adjacent' | 'modeSwitch' | 'adjacentMode' | 'twoAway' | 'clash' | 'unknown';
	score: number;
	label: string;
	description: string;
}

/**
 * Determine the harmonic relationship between two Camelot keys.
 */
export function harmonicRelationship(keyA: string | null | undefined, keyB: string | null | undefined): HarmonicRelationship {
	const a = parseCamelot(keyA);
	const b = parseCamelot(keyB);

	if (!a || !b) {
		return { type: 'unknown', score: 0.5, label: 'Unknown', description: "Key data missing — trust your ears" };
	}

	const numDist = Math.min(
		Math.abs(a.number - b.number),
		12 - Math.abs(a.number - b.number)
	);
	const sameLetter = a.letter === b.letter;

	if (numDist === 0 && sameLetter) {
		return { type: 'same', score: 1.0, label: 'Same key', description: "Same key — perfect harmonic match" };
	}
	if (numDist === 1 && sameLetter) {
		return { type: 'adjacent', score: 0.85, label: 'Adjacent', description: "Adjacent on the Camelot wheel — smooth, natural transition" };
	}
	if (numDist === 0 && !sameLetter) {
		return { type: 'modeSwitch', score: 0.8, label: 'Mode switch', description: "Major/minor switch — same energy, different colour" };
	}
	if (numDist === 1 && !sameLetter) {
		return { type: 'adjacentMode', score: 0.6, label: 'Adjacent + mode', description: "Adjacent + mode switch — subtle harmonic shift" };
	}
	if (numDist === 2 && sameLetter) {
		return { type: 'twoAway', score: 0.5, label: 'Two steps', description: "Two steps apart — noticeable change, use with intention" };
	}

	return { type: 'clash', score: 0.2, label: 'Distant keys', description: "Distant keys — this will sound rough without careful phrasing" };
}
