import type { Track } from '$lib/types';

export type Tab = 'track' | 'set' | 'dna' | 'tinder';
export type TimelineViewMode = 'linear' | 'staircase';

let activeTab = $state<Tab>('track');
let selectedTrack = $state<Track | null>(null);
let selectedSetId = $state<number | null>(null);
let selectedTrackInSet = $state<number | null>(null);
let timelineViewMode = $state<TimelineViewMode>('linear');
let playingTrackId = $state<number | null>(null);

export function getUiStore() {
	return {
		get activeTab() { return activeTab; },
		set activeTab(v: Tab) { activeTab = v; },
		get selectedTrack() { return selectedTrack; },
		set selectedTrack(v: Track | null) { selectedTrack = v; },
		get selectedSetId() { return selectedSetId; },
		set selectedSetId(v: number | null) { selectedSetId = v; },
		get selectedTrackInSet() { return selectedTrackInSet; },
		set selectedTrackInSet(v: number | null) { selectedTrackInSet = v; },
		get timelineViewMode() { return timelineViewMode; },
		set timelineViewMode(v: TimelineViewMode) { timelineViewMode = v; },
		get playingTrackId() { return playingTrackId; },
		set playingTrackId(v: number | null) { playingTrackId = v; },
	};
}
