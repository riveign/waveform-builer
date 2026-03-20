<script lang="ts">
	import type { ReplacementCandidate, ReplacementContext, SetTrack } from '$lib/types';
	import { getReplacements, replaceTrackInSet } from '$lib/api/sets';
	import { getCamelotColor } from '$lib/utils/camelot';
	import { API_BASE } from '$lib/api/client';

	let {
		setId,
		position,
		currentTrack,
		onclose,
		onreplaced,
	}: {
		setId: number;
		position: number;
		currentTrack: SetTrack;
		onclose: () => void;
		onreplaced: () => void;
	} = $props();

	let loading = $state(true);
	let replacing = $state<number | null>(null);
	let context = $state<ReplacementContext | null>(null);
	let candidates = $state<ReplacementCandidate[]>([]);
	let error = $state<string | null>(null);
	let previewTrackId = $state<number | null>(null);
	let audioEl = $state<HTMLAudioElement | null>(null);

	$effect(() => {
		loadReplacements();
	});

	async function loadReplacements() {
		loading = true;
		error = null;
		try {
			const res = await getReplacements(setId, position);
			context = res.context;
			candidates = res.candidates;
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to load suggestions';
		} finally {
			loading = false;
		}
	}

	async function handleReplace(trackId: number) {
		if (replacing !== null) return;
		replacing = trackId;
		try {
			await replaceTrackInSet(setId, position, trackId);
			stopPreview();
			onreplaced();
			onclose();
		} catch (err) {
			console.error('Failed to replace track:', err);
		} finally {
			replacing = null;
		}
	}

	function togglePreview(trackId: number) {
		if (previewTrackId === trackId) {
			stopPreview();
			return;
		}
		stopPreview();
		previewTrackId = trackId;
		const audio = new Audio(`${API_BASE}/api/audio/${trackId}/stream`);
		audio.currentTime = 30; // start ~30s in for a representative snippet
		audio.play().catch(() => {});
		audioEl = audio;
		// Auto-stop after 30s
		setTimeout(() => {
			if (previewTrackId === trackId) stopPreview();
		}, 30000);
	}

	function stopPreview() {
		if (audioEl) {
			audioEl.pause();
			audioEl = null;
		}
		previewTrackId = null;
	}

	function scoreColor(score: number): string {
		if (score >= 0.7) return 'var(--energy-low, #2ecc71)';
		if (score >= 0.5) return 'var(--energy-mid, #f39c12)';
		return 'var(--energy-high, #e94560)';
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Escape') {
			stopPreview();
			onclose();
		}
	}

	function handleBackdropClick(e: MouseEvent) {
		if ((e.target as HTMLElement).classList.contains('modal-backdrop')) {
			stopPreview();
			onclose();
		}
	}
</script>

<svelte:window onkeydown={handleKeydown} />

<!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
<div class="modal-backdrop" onclick={handleBackdropClick}>
	<div class="modal" role="dialog" aria-label="Replace track">
		<header class="modal-header">
			<h3>Replace track</h3>
			<div class="current-track">
				<span class="pos">#{position + 1}</span>
				<span class="title">{currentTrack.title ?? 'Untitled'}</span>
				<span class="artist">{currentTrack.artist ?? ''}</span>
			</div>
			<button class="close-btn" onclick={onclose} aria-label="Close">
				<svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="1.5">
					<line x1="3" y1="3" x2="11" y2="11" /><line x1="11" y1="3" x2="3" y2="11" />
				</svg>
			</button>
		</header>

		{#if context}
			<div class="context-bar">
				<div class="neighbor" class:empty={!context.prev_track}>
					{#if context.prev_track}
						<span class="neighbor-key" style="color: {getCamelotColor(context.prev_track.key ?? null)}">{context.prev_track.key ?? '?'}</span>
						<span class="neighbor-bpm">{context.prev_track.bpm ? Math.round(context.prev_track.bpm) : '?'}</span>
						<span class="neighbor-title">{context.prev_track.title ?? ''}</span>
					{:else}
						<span class="neighbor-label">start</span>
					{/if}
				</div>
				<div class="slot-indicator">
					<span class="arrow">&rarr;</span>
					<span class="slot-label">slot</span>
					<span class="energy-target">E: {(context.energy_target * 100).toFixed(0)}%</span>
					<span class="arrow">&rarr;</span>
				</div>
				<div class="neighbor" class:empty={!context.next_track}>
					{#if context.next_track}
						<span class="neighbor-key" style="color: {getCamelotColor(context.next_track.key ?? null)}">{context.next_track.key ?? '?'}</span>
						<span class="neighbor-bpm">{context.next_track.bpm ? Math.round(context.next_track.bpm) : '?'}</span>
						<span class="neighbor-title">{context.next_track.title ?? ''}</span>
					{:else}
						<span class="neighbor-label">end</span>
					{/if}
				</div>
			</div>
		{/if}

		<div class="candidates-list">
			{#if loading}
				<div class="loading">Scoring candidates...</div>
			{:else if error}
				<div class="error">{error}</div>
			{:else if candidates.length === 0}
				<div class="empty-msg">No compatible tracks found for this slot</div>
			{:else}
				{#each candidates as cand (cand.track.id)}
					{@const isPreviewing = previewTrackId === cand.track.id}
					<div class="candidate" class:previewing={isPreviewing}>
						<div class="score-col">
							<span class="score" style="color: {scoreColor(cand.combined_score)}">
								{(cand.combined_score * 100).toFixed(0)}
							</span>
							{#if cand.incoming_breakdown && cand.outgoing_breakdown}
								<div class="dual-bar">
									<div class="bar-segment" title="Incoming: {(cand.incoming_breakdown.total * 100).toFixed(0)}%">
										<div class="bar-fill" style="width: {cand.incoming_breakdown.total * 100}%; background: {scoreColor(cand.incoming_breakdown.total)}"></div>
									</div>
									<div class="bar-segment" title="Outgoing: {(cand.outgoing_breakdown.total * 100).toFixed(0)}%">
										<div class="bar-fill" style="width: {cand.outgoing_breakdown.total * 100}%; background: {scoreColor(cand.outgoing_breakdown.total)}"></div>
									</div>
								</div>
							{/if}
						</div>

						<div class="track-info">
							<div class="title-row">
								<span class="track-title">{cand.track.title ?? 'Untitled'}</span>
								{#if cand.track.genre}
									<span class="genre-badge">{cand.track.genre}</span>
								{/if}
							</div>
							<span class="track-artist">{cand.track.artist ?? 'Unknown'}</span>
						</div>

						<div class="meta">
							<span class="key-badge" style="color: {getCamelotColor(cand.track.key ?? null)}">
								{cand.track.key ?? '?'}
							</span>
							<span class="bpm">{cand.track.bpm ? Math.round(cand.track.bpm) : '?'}</span>
							{#if cand.track.energy}
								<span class="energy-badge">{cand.track.energy}</span>
							{/if}
						</div>

						<div class="actions">
							<button
								class="preview-btn"
								class:active={isPreviewing}
								onclick={() => togglePreview(cand.track.id)}
								title={isPreviewing ? 'Stop preview' : 'Preview snippet'}
								aria-label={isPreviewing ? 'Stop preview' : 'Preview'}
							>
								{#if isPreviewing}
									<svg width="14" height="14" viewBox="0 0 14 14" fill="currentColor">
										<rect x="3" y="3" width="3" height="8" rx="1" />
										<rect x="8" y="3" width="3" height="8" rx="1" />
									</svg>
								{:else}
									<svg width="14" height="14" viewBox="0 0 14 14" fill="currentColor">
										<path d="M3 2v10l9-5L3 2z" />
									</svg>
								{/if}
							</button>
							<button
								class="replace-btn"
								onclick={() => handleReplace(cand.track.id)}
								disabled={replacing !== null}
								title="Replace with this track"
							>
								{#if replacing === cand.track.id}
									<span class="spinner"></span>
								{:else}
									Replace
								{/if}
							</button>
						</div>
					</div>
				{/each}
			{/if}
		</div>
	</div>
</div>

<style>
	.modal-backdrop {
		position: fixed;
		inset: 0;
		background: rgba(0, 0, 0, 0.6);
		display: flex;
		align-items: center;
		justify-content: center;
		z-index: 100;
	}

	.modal {
		background: var(--bg-primary);
		border: 1px solid var(--border);
		border-radius: 8px;
		width: 620px;
		max-width: 95vw;
		max-height: 80vh;
		display: flex;
		flex-direction: column;
		overflow: hidden;
	}

	.modal-header {
		display: flex;
		align-items: center;
		gap: 12px;
		padding: 12px 16px;
		border-bottom: 1px solid var(--border);
	}

	.modal-header h3 {
		margin: 0;
		font-size: 14px;
		font-weight: 600;
		color: var(--text-primary);
		white-space: nowrap;
	}

	.current-track {
		flex: 1;
		display: flex;
		align-items: center;
		gap: 6px;
		min-width: 0;
		font-size: 12px;
		color: var(--text-secondary);
	}

	.current-track .pos {
		color: var(--text-dim);
		font-weight: 600;
	}

	.current-track .title {
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.current-track .artist {
		color: var(--text-dim);
	}

	.close-btn {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 24px;
		height: 24px;
		border: none;
		background: none;
		color: var(--text-dim);
		cursor: pointer;
		border-radius: 4px;
		padding: 0;
	}

	.close-btn:hover {
		background: var(--bg-tertiary);
		color: var(--text-primary);
	}

	/* ── Context bar ── */

	.context-bar {
		display: flex;
		align-items: center;
		gap: 8px;
		padding: 8px 16px;
		background: var(--bg-secondary);
		border-bottom: 1px solid var(--border);
		font-size: 11px;
	}

	.neighbor {
		flex: 1;
		display: flex;
		align-items: center;
		gap: 4px;
		min-width: 0;
	}

	.neighbor.empty {
		justify-content: center;
	}

	.neighbor-label {
		color: var(--text-dim);
		font-style: italic;
	}

	.neighbor-key {
		font-weight: 600;
		flex-shrink: 0;
	}

	.neighbor-bpm {
		color: var(--text-secondary);
		flex-shrink: 0;
		font-variant-numeric: tabular-nums;
	}

	.neighbor-title {
		color: var(--text-secondary);
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.slot-indicator {
		display: flex;
		align-items: center;
		gap: 4px;
		flex-shrink: 0;
		padding: 3px 8px;
		background: var(--bg-tertiary);
		border-radius: 4px;
	}

	.arrow {
		color: var(--text-dim);
	}

	.slot-label {
		font-weight: 600;
		color: var(--accent);
		text-transform: uppercase;
		letter-spacing: 0.5px;
	}

	.energy-target {
		color: var(--text-dim);
		font-variant-numeric: tabular-nums;
	}

	/* ── Candidates list ── */

	.candidates-list {
		flex: 1;
		overflow-y: auto;
		padding: 4px 0;
	}

	.loading,
	.error,
	.empty-msg {
		display: flex;
		align-items: center;
		justify-content: center;
		padding: 32px 16px;
		color: var(--text-dim);
		font-size: 13px;
	}

	.error {
		color: var(--energy-high, #e94560);
	}

	.candidate {
		display: flex;
		align-items: center;
		gap: 10px;
		padding: 6px 16px;
		transition: background 0.1s;
	}

	.candidate:hover {
		background: var(--bg-hover);
	}

	.candidate.previewing {
		background: var(--bg-active);
	}

	/* ── Score column ── */

	.score-col {
		width: 36px;
		flex-shrink: 0;
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 3px;
	}

	.score {
		font-size: 14px;
		font-weight: 700;
		font-variant-numeric: tabular-nums;
	}

	.dual-bar {
		width: 100%;
		display: flex;
		flex-direction: column;
		gap: 2px;
	}

	.bar-segment {
		height: 3px;
		background: var(--bg-tertiary);
		border-radius: 1.5px;
		overflow: hidden;
	}

	.bar-fill {
		height: 100%;
		border-radius: 1.5px;
		transition: width 0.2s;
	}

	/* ── Track info ── */

	.track-info {
		flex: 1;
		min-width: 0;
		display: flex;
		flex-direction: column;
		gap: 1px;
	}

	.title-row {
		display: flex;
		align-items: center;
		gap: 6px;
		min-width: 0;
	}

	.track-title {
		font-size: 12px;
		font-weight: 500;
		color: var(--text-primary);
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.track-artist {
		font-size: 11px;
		color: var(--text-secondary);
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.genre-badge {
		flex-shrink: 0;
		font-size: 9px;
		text-transform: uppercase;
		letter-spacing: 0.5px;
		padding: 1px 5px;
		border-radius: 3px;
		background: var(--bg-tertiary);
		color: var(--text-secondary);
	}

	/* ── Meta ── */

	.meta {
		display: flex;
		align-items: center;
		gap: 6px;
		flex-shrink: 0;
	}

	.key-badge {
		font-weight: 600;
		font-size: 11px;
		width: 28px;
		text-align: center;
	}

	.bpm {
		font-size: 11px;
		color: var(--text-secondary);
		font-variant-numeric: tabular-nums;
	}

	.energy-badge {
		font-size: 9px;
		text-transform: uppercase;
		padding: 1px 4px;
		border-radius: 3px;
		background: var(--bg-tertiary);
		color: var(--text-dim);
	}

	/* ── Actions ── */

	.actions {
		display: flex;
		align-items: center;
		gap: 4px;
		flex-shrink: 0;
	}

	.preview-btn {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 28px;
		height: 28px;
		border: none;
		background: none;
		color: var(--text-dim);
		cursor: pointer;
		border-radius: 4px;
		padding: 0;
		transition: background 0.1s, color 0.1s;
	}

	.preview-btn:hover,
	.preview-btn.active {
		background: var(--bg-tertiary);
		color: var(--accent);
	}

	.replace-btn {
		font-size: 11px;
		font-weight: 500;
		padding: 4px 10px;
		border: 1px solid var(--accent);
		background: none;
		color: var(--accent);
		cursor: pointer;
		border-radius: 4px;
		transition: background 0.1s, color 0.1s;
		white-space: nowrap;
	}

	.replace-btn:hover {
		background: var(--accent);
		color: var(--bg-primary);
	}

	.replace-btn:disabled {
		opacity: 0.4;
		cursor: default;
	}

	/* ── Spinner ── */

	.spinner {
		display: inline-block;
		width: 12px;
		height: 12px;
		border: 1.5px solid currentColor;
		border-top-color: transparent;
		border-radius: 50%;
		animation: spin 0.6s linear infinite;
	}

	@keyframes spin {
		to { transform: rotate(360deg); }
	}
</style>
