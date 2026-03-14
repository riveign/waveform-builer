import type { Track } from '$lib/types';

type Tab = 'track' | 'set' | 'dna';

let activeTab = $state<Tab>('track');
let selectedTrack = $state<Track | null>(null);
let selectedSetId = $state<number | null>(null);

export function getUiStore() {
	return {
		get activeTab() { return activeTab; },
		set activeTab(v: Tab) { activeTab = v; },
		get selectedTrack() { return selectedTrack; },
		set selectedTrack(v: Track | null) { selectedTrack = v; },
		get selectedSetId() { return selectedSetId; },
		set selectedSetId(v: number | null) { selectedSetId = v; },
	};
}
