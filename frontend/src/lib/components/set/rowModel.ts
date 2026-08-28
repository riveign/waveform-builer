/**
 * One derivation of "what a set row knows", shared by the three list layouts.
 *
 * Ledger, Spine and Inspector disagree about presentation, not about facts. Each
 * needs the same things per position — the key in both notations, the keys that
 * mix cleanly out of it, the move to the next track, energy as a fraction — so
 * the arithmetic lives here once instead of three times.
 */

import type { SetAnalysis, SetWaveformTrack } from '$lib/types';
import {
	compatibleKeys,
	formatKey,
	getCamelotColor,
	harmonicMove,
	parseCamelot,
	type CompatibleKey,
} from '$lib/utils/camelot';
import { getTrackEnergyNumeric } from '$lib/utils/energy';

/** How the set moves from one track to the next. */
export interface MoveOut {
	/** Wheel classification, shared vocabulary with the strips (spec 025). */
	kind: 'hold' | 'lift' | 'switch' | 'clash';
	/** Verb the DJ reads: what this move does to the set. */
	label: string;
	/** Rounded BPM change; null when either track has no tempo. */
	bpmDelta: number | null;
	/** Scored transition total from the set analysis, when it has been run. */
	score: number | null;
	teaching: string | null;
}

export interface SetRow {
	track: SetWaveformTrack;
	/** 1-based, as displayed. */
	position: number;
	/** Camelot code ("8A"), or null when the key can't be placed on the wheel. */
	camelot: string | null;
	/** Musical name ("Am") — the notation the rows have always shown. */
	keyName: string;
	keyColor: string;
	/** 0–1, or null when the track has no resolved energy. */
	energy: number | null;
	/** The three keys that mix cleanly out of this one, with what each does. */
	nextKeys: CompatibleKey[];
	/** The move to the following track; null on the last row. */
	moveOut: MoveOut | null;
}

/** Plain-language verb per wheel move — the same words the rail and rows use. */
const MOVE_LABEL: Record<MoveOut['kind'], string> = {
	hold: 'HOLD',
	lift: 'LIFT',
	switch: 'SWITCH',
	clash: 'JUMP',
};

/**
 * A `-1` step reads as settling rather than lifting, but `harmonicMove` folds
 * both directions into `lift`. Recover the direction so the row can say which.
 */
function directedLabel(a: string | null | undefined, b: string | null | undefined): string {
	const ka = parseCamelot(a);
	const kb = parseCamelot(b);
	if (!ka || !kb || ka.letter !== kb.letter) return MOVE_LABEL.lift;
	const down = ((ka.number - 2 + 12) % 12) + 1;
	return kb.number === down ? 'SETTLE' : 'LIFT';
}

export function buildRows(
	tracks: SetWaveformTrack[],
	analysis: SetAnalysis | null = null,
): SetRow[] {
	const scored = new Map<number, { score: number; teaching: string }>();
	for (const t of analysis?.transitions ?? []) {
		scored.set(t.position, { score: t.scores.total, teaching: t.teaching_moment });
	}

	return tracks.map((track, i) => {
		const next = tracks[i + 1];
		let moveOut: MoveOut | null = null;

		if (next) {
			const kind = harmonicMove(track.key, next.key);
			const a = scored.get(i);
			moveOut = {
				kind,
				label: kind === 'lift' ? directedLabel(track.key, next.key) : MOVE_LABEL[kind],
				bpmDelta:
					track.bpm != null && next.bpm != null ? Math.round(next.bpm - track.bpm) : null,
				score: a?.score ?? null,
				teaching: a?.teaching ?? null,
			};
		}

		const parsed = parseCamelot(track.key);

		return {
			track,
			position: i + 1,
			camelot: parsed ? `${parsed.number}${parsed.letter}` : null,
			keyName: formatKey(track.key),
			keyColor: getCamelotColor(track.key),
			energy: getTrackEnergyNumeric(track.energy_value, track.energy),
			nextKeys: compatibleKeys(track.key),
			moveOut,
		};
	});
}

/** Signed BPM for display: "+2", "−2", "0". Uses a real minus sign. */
export function formatBpmDelta(delta: number | null): string {
	if (delta == null) return '';
	if (delta === 0) return '0';
	return delta > 0 ? `+${delta}` : `−${Math.abs(delta)}`;
}

/** Score → the semantic quality token the app already uses for verdicts. */
export function scoreColor(score: number | null): string {
	if (score == null) return 'var(--text-4)';
	if (score >= 0.8) return 'var(--score-excellent)';
	if (score >= 0.6) return 'var(--score-good)';
	if (score >= 0.4) return 'var(--score-fair)';
	return 'var(--score-poor)';
}
