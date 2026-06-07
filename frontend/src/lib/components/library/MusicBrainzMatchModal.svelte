<script lang="ts">
	import type { Track } from '$lib/types';
	import {
		matchAlbumMusicBrainz,
		applyAlbumMusicBrainz,
		type MBCandidate,
		type MBMappingPreviewItem,
	} from '$lib/api/albums';

	let {
		open = $bindable(false),
		albumKey,
		kikuTracks,
		onapply,
	}: {
		open: boolean;
		albumKey: string;
		kikuTracks: Track[];
		onapply: () => void;
	} = $props();

	let dialogEl: HTMLDialogElement | undefined = $state();
	let stage = $state<'loading' | 'pick' | 'review' | 'applying' | 'error'>('loading');
	let error = $state('');
	let candidates = $state<MBCandidate[]>([]);
	let selectedIdx = $state<number | null>(null);
	let overrides = $state<Record<number, number | null>>({});

	$effect(() => {
		if (open && dialogEl) {
			dialogEl.showModal();
			runMatch();
		} else if (!open && dialogEl?.open) {
			dialogEl.close();
		}
	});

	async function runMatch() {
		stage = 'loading';
		error = '';
		candidates = [];
		selectedIdx = null;
		overrides = {};
		try {
			const res = await matchAlbumMusicBrainz(albumKey);
			candidates = res.candidates;
			if (candidates.length === 0) {
				error = "Couldn't find a matching release on MusicBrainz. Try a different album?";
				stage = 'error';
			} else {
				stage = 'pick';
			}
		} catch (e) {
			error = e instanceof Error ? e.message : 'MusicBrainz lookup failed';
			stage = 'error';
		}
	}

	function pickCandidate(idx: number) {
		selectedIdx = idx;
		overrides = {};
		stage = 'review';
	}

	function confidenceClass(c: number): string {
		if (c >= 0.85) return 'green';
		if (c >= 0.7) return 'yellow';
		return 'red';
	}

	function effectivePosition(p: MBMappingPreviewItem): number | null {
		const override = overrides[p.track_id];
		if (override !== undefined) return override;
		return p.mb_position ?? null;
	}

	async function apply() {
		if (selectedIdx === null) return;
		const candidate = candidates[selectedIdx];
		stage = 'applying';
		try {
			const mappings = candidate.mapping_preview.map((p) => {
				const pos = effectivePosition(p);
				const rec = pos != null ? candidate.recordings.find((r) => r.position === pos) : null;
				return {
					track_id: p.track_id,
					mb_position: pos,
					track_number: pos,
					disc_number: rec?.disc ?? p.mb_disc ?? null,
					confidence: p.confidence,
				};
			});
			await applyAlbumMusicBrainz(albumKey, {
				mb_release_id: candidate.mb_release_id,
				mappings,
			});
			onapply();
		} catch (e) {
			error = e instanceof Error ? e.message : 'Apply failed';
			stage = 'error';
		}
	}

	function close() {
		open = false;
		stage = 'loading';
		error = '';
		candidates = [];
		selectedIdx = null;
		overrides = {};
	}

	function handleClose() {
		open = false;
	}
</script>

<dialog
	bind:this={dialogEl}
	onclose={handleClose}
	onkeydown={(e) => e.key === 'Escape' && close()}
>
	<div class="dialog-content">
		<header>
			<h2>Match on MusicBrainz</h2>
			<button class="close" onclick={close} aria-label="Close">×</button>
		</header>

		{#if stage === 'loading'}
			<div class="status">Searching MusicBrainz...</div>
		{:else if stage === 'error'}
			<div class="status error">{error}</div>
			<div class="footer">
				<button onclick={close}>Close</button>
				<button class="primary" onclick={runMatch}>Try again</button>
			</div>
		{:else if stage === 'pick'}
			<p class="prompt">Found {candidates.length} possible release{candidates.length === 1 ? '' : 's'}. Does any of these look like your album?</p>
			<div class="candidates">
				{#each candidates as cand, i (cand.mb_release_id)}
					<button class="candidate" onclick={() => pickCandidate(i)}>
						<div class="cand-title">{cand.title}</div>
						<div class="cand-artist">{cand.artist}</div>
						<div class="cand-meta">
							{#if cand.year}{cand.year}{:else}—{/if}
							· {cand.track_count} tracks
							{#if cand.label} · {cand.label}{/if}
							{#if cand.country} · {cand.country}{/if}
						</div>
					</button>
				{/each}
			</div>
		{:else if stage === 'review' && selectedIdx !== null}
			{@const cand = candidates[selectedIdx]}
			<p class="prompt">Does this mapping look right? You can override any position before applying.</p>
			<div class="mapping">
				<div class="map-row map-head">
					<div>Your track</div>
					<div>→ MB position</div>
					<div>MusicBrainz title</div>
					<div>Match</div>
				</div>
				{#each cand.mapping_preview as p (p.track_id)}
					<div class="map-row">
						<div class="map-track" title={p.track_title ?? ''}>{p.track_title ?? '—'}</div>
						<select
							class="map-select"
							value={effectivePosition(p)}
							onchange={(e) => {
								const v = (e.currentTarget as HTMLSelectElement).value;
								overrides = { ...overrides, [p.track_id]: v === '' ? null : Number(v) };
							}}
						>
							<option value="">— skip —</option>
							{#each cand.recordings as r}
								<option value={r.position}>
									{r.disc > 1 ? `${r.disc}.` : ''}{String(r.position).padStart(2, '0')}
								</option>
							{/each}
						</select>
						<div class="map-mb-title">{p.mb_title ?? '—'}</div>
						<div class="map-conf {confidenceClass(p.confidence)}">
							{Math.round(p.confidence * 100)}%
						</div>
					</div>
				{/each}
			</div>
			<div class="footer">
				<button onclick={() => (stage = 'pick')}>Back</button>
				<button class="primary" onclick={apply}>Apply mapping</button>
			</div>
		{:else if stage === 'applying'}
			<div class="status">Writing track numbers...</div>
		{/if}
	</div>
</dialog>

<style>
	dialog {
		border: 1px solid var(--border);
		border-radius: 10px;
		background: var(--bg-primary, #0c0c0e);
		color: var(--text-primary);
		padding: 0;
		max-width: 720px;
		width: 90vw;
		max-height: 80vh;
	}
	dialog::backdrop {
		background: rgba(0, 0, 0, 0.6);
	}

	.dialog-content {
		display: flex;
		flex-direction: column;
		max-height: 80vh;
	}

	header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 14px 18px;
		border-bottom: 1px solid var(--border);
	}
	h2 { margin: 0; font-size: 15px; font-weight: 600; }
	.close {
		appearance: none;
		background: transparent;
		border: none;
		color: var(--text-secondary);
		font-size: 22px;
		cursor: pointer;
		line-height: 1;
		padding: 0 6px;
	}

	.prompt {
		padding: 12px 18px 4px;
		font-size: 13px;
		color: var(--text-secondary);
	}

	.candidates {
		display: flex;
		flex-direction: column;
		gap: 6px;
		padding: 8px 16px 16px;
		overflow-y: auto;
	}
	.candidate {
		appearance: none;
		background: var(--bg-secondary, rgba(255,255,255,0.04));
		border: 1px solid var(--border);
		border-radius: 8px;
		padding: 10px 14px;
		text-align: left;
		cursor: pointer;
		color: var(--text-primary);
		display: flex;
		flex-direction: column;
		gap: 2px;
	}
	.candidate:hover { border-color: var(--accent); }
	.cand-title { font-weight: 600; font-size: 13px; }
	.cand-artist { font-size: 12px; color: var(--text-secondary); }
	.cand-meta { font-size: 11px; color: var(--text-dim); }

	.mapping {
		display: flex;
		flex-direction: column;
		overflow-y: auto;
		padding: 6px 16px 12px;
	}
	.map-row {
		display: grid;
		grid-template-columns: 1.6fr 80px 1.6fr 60px;
		gap: 10px;
		align-items: center;
		padding: 6px 0;
		font-size: 12px;
		border-bottom: 1px solid rgba(255,255,255,0.04);
	}
	.map-head { font-size: 11px; color: var(--text-dim); text-transform: uppercase; }
	.map-track, .map-mb-title {
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	.map-select {
		background: var(--bg-secondary, #1a1a1d);
		color: var(--text-primary);
		border: 1px solid var(--border);
		border-radius: 4px;
		padding: 3px 6px;
		font-size: 11px;
	}
	.map-conf {
		text-align: right;
		font-variant-numeric: tabular-nums;
		font-weight: 600;
	}
	.map-conf.green { color: #4ade80; }
	.map-conf.yellow { color: #facc15; }
	.map-conf.red { color: #f87171; }

	.footer {
		display: flex;
		justify-content: flex-end;
		gap: 8px;
		padding: 12px 18px;
		border-top: 1px solid var(--border);
	}
	.footer button {
		appearance: none;
		background: transparent;
		color: var(--text-secondary);
		border: 1px solid var(--border);
		border-radius: 6px;
		padding: 6px 14px;
		font-size: 12px;
		cursor: pointer;
	}
	.footer button.primary {
		background: var(--accent);
		color: var(--bg-primary, #000);
		border-color: var(--accent);
	}

	.status {
		padding: 30px;
		text-align: center;
		color: var(--text-secondary);
		font-size: 13px;
	}
	.status.error { color: #f87171; }
</style>
