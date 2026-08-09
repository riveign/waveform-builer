import { error } from '@sveltejs/kit';
import { getTrack } from '$lib/api/tracks';
import type { Track } from '$lib/types';

/**
 * The track is resolved from the URL, not handed over in memory, so a pasted
 * link opens the same view a click does.
 */
export async function load({ params }): Promise<{ track: Track | null }> {
	if (!params.id) return { track: null };

	const id = Number(params.id);
	if (!Number.isFinite(id)) error(404, 'That track id doesn’t look right.');

	try {
		return { track: await getTrack(id) };
	} catch {
		error(404, 'Couldn’t find that track in your library.');
	}
}
