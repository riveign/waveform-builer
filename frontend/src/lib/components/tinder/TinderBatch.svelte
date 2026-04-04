<script lang="ts">
	import type { TinderQueueItem, TinderDecision, TinderBatchDecision } from '$lib/types';
	import { ZONES, ZONE_COLORS as zoneColors } from '../library/EnergyZonePicker.svelte';
	import { getPlayerStore } from '$lib/stores/player.svelte';

	const player = getPlayerStore();

	let {
		items,
		onsubmit,
	}: {
		items: TinderQueueItem[];
		onsubmit: (decisions: TinderBatchDecision[]) => void;
	} = $props();

	// Per-row decision state
	let decisions = $state<Record<number, { decision: TinderDecision; override_zone?: string }>>({});

	function setDecision(trackId: number, decision: TinderDecision, zone?: string) {
		decisions[trackId] = { decision, override_zone: zone };
	}

	function getDecision(trackId: number): TinderDecision | null {
		return decisions[trackId]?.decision ?? null;
	}

	function getOverrideZone(trackId: number): string | undefined {
		return decisions[trackId]?.override_zone;
	}

	let pendingCount = $derived(items.filter(i => !decisions[i.track.id]).length);
	let decidedCount = $derived(items.length - pendingCount);

	function confirmAll() {
		for (const item of items) {
			if (!decisions[item.track.id]) {
				decisions[item.track.id] = { decision: 'confirm' };
			}
		}
	}

	function submitBatch() {
		const batch: TinderBatchDecision[] = [];
		for (const item of items) {
			const d = decisions[item.track.id];
			// Default undecided items to skip
			const decision = d?.decision ?? 'skip';
			batch.push({
				track_id: item.track.id,
				decision,
				override_zone: d?.override_zone,
			});
		}
		onsubmit(batch);
		decisions = {};
	}
</script>

<div class="batch-review">
	<div class="batch-header">
		<span class="batch-count">{decidedCount}/{items.length} decided</span>
		<button class="confirm-all-btn" onclick={confirmAll}>Confirm All Remaining</button>
		<button class="submit-btn" onclick={submitBatch} disabled={decidedCount === 0}>
			Submit {decidedCount}
		</button>
	</div>

	<div class="batch-list">
		{#each items as item (item.track.id)}
			{@const decided = getDecision(item.track.id)}
			{@const overrideZone = getOverrideZone(item.track.id)}
			<div class="batch-row" class:decided={decided !== null}>
				<button
					class="play-btn"
					class:playing={player.currentTrack?.id === item.track.id && player.isPlaying}
					onclick={() => {
						if (player.currentTrack?.id === item.track.id && player.isPlaying) {
							player.pause();
						} else {
							player.play(item.track);
						}
					}}
					title="Listen"
				>{player.currentTrack?.id === item.track.id && player.isPlaying ? '⏸' : '▶'}</button>
				<div class="row-info">
					<div class="row-title">{item.track.title ?? 'Unknown'}</div>
					<div class="row-meta">
						<span class="row-artist">{item.track.artist ?? 'Unknown'}</span>
						<span>{item.track.bpm ? `${Math.round(item.track.bpm)} BPM` : ''}</span>
						<span>{item.track.key ?? ''}</span>
					</div>
				</div>

				<div class="row-prediction">
					<span class="zone-chip" style="color: {zoneColors[item.energy_predicted ?? ''] ?? 'var(--text-primary)'}">
						{item.energy_predicted ?? '?'}
					</span>
					<span class="conf">{((item.energy_confidence ?? 0) * 100).toFixed(0)}%</span>
				</div>

				<div class="row-actions">
					<button
						class="row-btn"
						class:active={decided === 'confirm'}
						onclick={() => setDecision(item.track.id, 'confirm')}
						title="Confirm"
					>&#10003;</button>
					<button
						class="row-btn skip-btn"
						class:active={decided === 'skip'}
						onclick={() => setDecision(item.track.id, 'skip')}
						title="Skip"
					>&#8212;</button>
					<div class="override-group">
						{#each ZONES as zone}
							<button
								class="zone-mini"
								class:active={decided === 'override' && overrideZone === zone}
								style="color: {zoneColors[zone]}"
								onclick={() => setDecision(item.track.id, 'override', zone)}
								title="Override to {zone}"
							>{zone[0].toUpperCase()}</button>
						{/each}
					</div>
				</div>
			</div>
		{/each}
	</div>
</div>

<style>
	.batch-review { display: flex; flex-direction: column; gap: 8px; }
	.batch-header { display: flex; align-items: center; gap: 8px; padding: 8px 0; }
	.batch-count { font-size: 13px; color: var(--text-secondary); flex: 1; }
	.confirm-all-btn { padding: 4px 10px; font-size: 12px; background: var(--bg-secondary); color: var(--text-secondary); border: 1px solid var(--border); border-radius: 4px; cursor: pointer; }
	.confirm-all-btn:hover { background: var(--bg-hover); }
	.submit-btn { padding: 6px 16px; font-size: 13px; font-weight: 600; background: #2ecc71; color: #000; border-radius: 6px; cursor: pointer; }
	.submit-btn:disabled { opacity: 0.4; cursor: not-allowed; }
	.submit-btn:hover:not(:disabled) { background: #27ae60; }

	.batch-list { display: flex; flex-direction: column; gap: 2px; }
	.batch-row { display: flex; align-items: center; gap: 10px; padding: 8px 10px; border-radius: 6px; background: var(--bg-secondary); transition: opacity 0.15s; }
	.batch-row.decided { opacity: 0.7; }
	.play-btn { width: 28px; height: 28px; border-radius: 50%; font-size: 12px; background: none; color: var(--text-dim); cursor: pointer; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
	.play-btn:hover { background: var(--bg-hover); color: var(--text-primary); }
	.play-btn.playing { color: var(--accent); }
	.row-info { flex: 1; min-width: 0; }
	.row-title { font-size: 13px; font-weight: 500; color: var(--text-primary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
	.row-meta { display: flex; gap: 8px; font-size: 11px; color: var(--text-dim); }
	.row-artist { max-width: 120px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
	.row-prediction { display: flex; align-items: center; gap: 6px; min-width: 80px; }
	.zone-chip { font-size: 12px; font-weight: 700; text-transform: uppercase; }
	.conf { font-size: 10px; color: var(--text-dim); }

	.row-actions { display: flex; align-items: center; gap: 4px; }
	.row-btn { width: 28px; height: 28px; border-radius: 4px; font-size: 14px; background: none; color: var(--text-dim); cursor: pointer; display: flex; align-items: center; justify-content: center; }
	.row-btn:hover { background: var(--bg-hover); color: var(--text-primary); }
	.row-btn.active { background: #2ecc71; color: #000; }
	.skip-btn.active { background: var(--bg-hover); color: var(--text-secondary); }

	.override-group { display: flex; gap: 1px; }
	.zone-mini { width: 22px; height: 22px; border-radius: 3px; font-size: 10px; font-weight: 700; background: none; cursor: pointer; display: flex; align-items: center; justify-content: center; opacity: 0.5; }
	.zone-mini:hover { opacity: 1; background: var(--bg-hover); }
	.zone-mini.active { opacity: 1; background: var(--bg-hover); outline: 1px solid currentColor; }
</style>
