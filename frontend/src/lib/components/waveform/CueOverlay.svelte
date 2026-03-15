<script lang="ts">
	import { onMount } from 'svelte';
	import type WaveSurfer from 'wavesurfer.js';
	import RegionsPlugin, { type Region } from 'wavesurfer.js/dist/plugins/regions.esm.js';
	import type { Cue } from '$lib/types';
	import { getCues, createCue, deleteCue } from '$lib/api/sets';
	import { decodeFloat32 } from '$lib/utils/waveform';

	let {
		ws,
		setId,
		trackId,
		position,
		beats = null,
		readonly = false,
	}: {
		ws: WaveSurfer;
		setId: number;
		trackId: number;
		position: number;
		beats?: string | null;
		readonly?: boolean;
	} = $props();

	const CUE_COLORS: Record<string, string> = {
		intro: '#00B8A9',
		break: '#F28C28',
		outro: '#E94560',
		drop: '#A855F7',
		marker: '#FFFFFF',
		cue: '#FFFFFF',
	};

	let regions: RegionsPlugin | null = null;
	let cues = $state<Cue[]>([]);
	let editingCue = $state<{ time: number; snapped: number; el: HTMLInputElement | null } | null>(null);

	/** Map region ID → cue ID for deletion */
	const regionCueMap = new Map<string, number>();

	/** Decode beat positions into bar starts (every 4th beat) */
	let barStarts = $derived.by(() => {
		if (!beats) return null;
		const beatTimes = decodeFloat32(beats);
		if (beatTimes.length < 4) return null;
		const bars: number[] = [];
		for (let i = 0; i < beatTimes.length; i += 4) {
			bars.push(beatTimes[i]);
		}
		return bars;
	});

	/** Snap a time to the nearest bar start. Returns original time if no bars available. */
	function snapToBar(time: number): number {
		if (!barStarts || barStarts.length === 0) return time;
		let closest = barStarts[0];
		let minDist = Math.abs(time - closest);
		for (let i = 1; i < barStarts.length; i++) {
			const dist = Math.abs(time - barStarts[i]);
			if (dist < minDist) {
				minDist = dist;
				closest = barStarts[i];
			}
		}
		return closest;
	}

	onMount(() => {
		regions = ws.registerPlugin(RegionsPlugin.create());

		loadCues();

		if (!readonly) {
			// Double-click to create a point cue — snaps to nearest bar start
			regions.on('region-double-clicked', (_region: Region, e: MouseEvent) => {
				e.stopPropagation();
			});

			ws.on('dblclick', (relativeX: number) => {
				const duration = ws.getDuration();
				if (duration <= 0) return;
				const rawTime = relativeX * duration;
				const snapped = snapToBar(rawTime);
				if (snapped >= 0 && snapped <= duration) {
					editingCue = { time: rawTime, snapped, el: null };
				}
			});

		}

		return () => {
			regions?.destroy();
		};
	});

	async function loadCues() {
		try {
			cues = await getCues(setId, trackId);
			renderRegions();
		} catch (err) {
			console.error('Failed to load cues:', err);
		}
	}

	function renderRegions() {
		if (!regions) return;
		regions.clearRegions();
		regionCueMap.clear();

		for (const cue of cues) {
			const color = CUE_COLORS[cue.cue_type] ?? CUE_COLORS.cue;
			const isRange = cue.end_sec != null;

			const region = regions.addRegion({
				start: cue.start_sec,
				end: isRange ? cue.end_sec! : undefined,
				color: isRange ? `${color}33` : color,
				content: cue.name,
				drag: false,
				resize: false,
			});

			regionCueMap.set(region.id, cue.id);
		}
	}

	async function handleCreateCue(name: string, snappedTime: number) {
		editingCue = null;
		if (!name.trim()) return;
		try {
			await createCue(setId, trackId, {
				position,
				name: name.trim(),
				cue_type: 'marker',
				start_sec: Math.round(snappedTime * 1000) / 1000,
			});
			await loadCues();
		} catch (err) {
			console.error('Failed to create cue:', err);
		}
	}

	async function handleDeleteCue(cueId: number) {
		try {
			await deleteCue(cueId);
			cues = cues.filter((c) => c.id !== cueId);
			renderRegions();
		} catch (err) {
			console.error('Failed to delete cue:', err);
		}
	}

	function handleInputKeydown(e: KeyboardEvent) {
		if (e.key === 'Enter' && editingCue) {
			const input = e.target as HTMLInputElement;
			handleCreateCue(input.value, editingCue.snapped);
		} else if (e.key === 'Escape') {
			editingCue = null;
		}
	}
</script>

{#if editingCue}
	<div class="cue-input-bar">
		<span class="cue-input-label">
			Cue at {editingCue.snapped.toFixed(1)}s{barStarts ? ' (bar)' : ''}:
		</span>
		<!-- svelte-ignore a11y_autofocus -->
		<input
			class="cue-input"
			type="text"
			placeholder="Name this cue..."
			autofocus
			onkeydown={handleInputKeydown}
			onblur={() => { editingCue = null; }}
		/>
	</div>
{/if}

{#if cues.length > 0}
	<div class="cue-tags">
		{#each cues as cue (cue.id)}
			<span
				class="cue-tag"
				style="border-color: {CUE_COLORS[cue.cue_type] ?? CUE_COLORS.cue}"
				title="{cue.cue_type} at {cue.start_sec.toFixed(1)}s"
			>
				{cue.name}
				{#if !readonly}
					<button
						class="cue-delete"
						onclick={() => handleDeleteCue(cue.id)}
						title="Remove cue"
						aria-label="Remove {cue.name}"
					>
						<svg width="10" height="10" viewBox="0 0 10 10" fill="none" stroke="currentColor" stroke-width="1.5">
							<line x1="2" y1="2" x2="8" y2="8" /><line x1="8" y1="2" x2="2" y2="8" />
						</svg>
					</button>
				{/if}
			</span>
		{/each}
	</div>
{/if}

<style>
	.cue-input-bar {
		display: flex;
		align-items: center;
		gap: 8px;
		padding: 4px 10px;
		background: var(--bg-tertiary);
		border-radius: 4px;
		margin-top: 4px;
	}

	.cue-input-label {
		font-size: 11px;
		color: var(--text-secondary);
		white-space: nowrap;
	}

	.cue-input {
		flex: 1;
		padding: 3px 6px;
		font-size: 12px;
		background: var(--bg-secondary);
		color: var(--text-primary);
		border: 1px solid var(--border);
		border-radius: 3px;
		outline: none;
	}

	.cue-input:focus {
		border-color: var(--accent);
	}

	.cue-tags {
		display: flex;
		gap: 4px;
		flex-wrap: wrap;
		padding: 4px 0;
	}

	.cue-tag {
		display: inline-flex;
		align-items: center;
		gap: 3px;
		font-size: 10px;
		padding: 1px 6px;
		border: 1px solid;
		border-radius: 3px;
		color: var(--text-secondary);
	}

	.cue-delete {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		width: 14px;
		height: 14px;
		padding: 0;
		border: none;
		background: none;
		color: var(--text-dim);
		cursor: pointer;
		border-radius: 2px;
		opacity: 0.6;
		transition: opacity 0.1s, color 0.1s;
	}

	.cue-delete:hover {
		opacity: 1;
		color: var(--energy-high, #e94560);
	}
</style>
