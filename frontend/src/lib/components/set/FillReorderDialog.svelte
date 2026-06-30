<script lang="ts">
	import { fillSet, optimizeOrder, reorderSetTracks, addTrackToSet, type OptimizeOrderResponse } from '$lib/api/sets';
	import Button from '$lib/components/primitives/Button.svelte';
	import SegmentedControl, { type SegmentOption } from '$lib/components/primitives/SegmentedControl.svelte';
	import { focusTrap } from '$lib/actions/focusTrap';

	const tabOptions: SegmentOption<'fill' | 'reorder'>[] = [
		{ value: 'fill', label: 'Fill gaps' },
		{ value: 'reorder', label: 'Reorder' },
	];

	let {
		setId,
		setName = 'set',
		trackCount = 0,
		durationMin = 0,
		energyProfile = null,
		onclose,
		onapplied,
	}: {
		setId: number;
		setName?: string;
		trackCount?: number;
		durationMin?: number;
		energyProfile?: string | null;
		onclose: () => void;
		onapplied?: () => void;
	} = $props();

	let activeTab = $state<'fill' | 'reorder'>('fill');

	// Fill state
	let fillRunning = $state(false);
	let fillTargetMin = $state(60);
	let fillMaxTracks = $state(10);
	let proposals = $state<Array<{ position: number; track_id: number; track_title: string | null; track_artist: string | null; score: number; explanation: string; accepted: boolean }>>([]);
	let fillComplete = $state(false);
	let applying = $state(false);

	// Reorder state
	let strategy = $state<'gentle' | 'full'>('gentle');
	let reorderResult = $state<OptimizeOrderResponse | null>(null);
	let optimizing = $state(false);
	let applyingReorder = $state(false);

	async function startFill() {
		fillRunning = true;
		proposals = [];
		fillComplete = false;
		try {
			await fillSet(setId, {
				energy_profile: energyProfile,
				target_duration_min: fillTargetMin,
				max_fill_tracks: fillMaxTracks,
			}, (event, data: any) => {
				if (event === 'fill_proposed') {
					proposals = [...proposals, {
						position: data.position,
						track_id: data.track_id,
						track_title: data.track_title,
						track_artist: data.track_artist,
						score: data.score,
						explanation: data.explanation,
						accepted: true,
					}];
				} else if (event === 'fill_complete') {
					fillComplete = true;
				}
			});
		} catch {
			// Handled via events
		} finally {
			fillRunning = false;
			fillComplete = true;
		}
	}

	async function applyFill() {
		applying = true;
		try {
			const accepted = proposals.filter((p) => p.accepted);
			for (const p of accepted) {
				await addTrackToSet(setId, p.track_id, p.position);
			}
			onapplied?.();
			onclose();
		} catch {
			// Silently fail
		} finally {
			applying = false;
		}
	}

	async function startOptimize() {
		optimizing = true;
		reorderResult = null;
		try {
			reorderResult = await optimizeOrder(setId, {
				strategy,
				energy_profile: energyProfile,
			});
		} catch {
			// Handled
		} finally {
			optimizing = false;
		}
	}

	async function applyReorder() {
		if (!reorderResult) return;
		applyingReorder = true;
		try {
			await reorderSetTracks(setId, reorderResult.proposed_order);
			onapplied?.();
			onclose();
		} catch {
			// Handled
		} finally {
			applyingReorder = false;
		}
	}

	function scoreColor(score: number): string {
		if (score >= 0.8) return 'var(--score-excellent)';
		if (score >= 0.6) return 'var(--score-fair)';
		return 'var(--score-poor)';
	}
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<div class="dialog-overlay" onclick={onclose} onkeydown={(e) => { if (e.key === 'Escape') onclose(); }}>
	<!-- Inner panel stops backdrop-dismiss clicks; the overlay above owns Escape. -->
	<!-- svelte-ignore a11y_click_events_have_key_events -->
	<div
		class="dialog"
		role="dialog"
		aria-modal="true"
		aria-label="Fill or reorder set"
		tabindex="-1"
		use:focusTrap
		onclick={(e) => e.stopPropagation()}
	>
		<div class="dialog-header">
			<SegmentedControl options={tabOptions} value={activeTab} onchange={(v) => activeTab = v} ariaLabel="Fill or reorder" />
			<Button variant="ghost" size="sm" iconOnly ariaLabel="Close" onclick={onclose}>
				{#snippet icon()}×{/snippet}
			</Button>
		</div>

		{#if activeTab === 'fill'}
			<div class="tab-content">
				<div class="set-info">Your set: "{setName}" ({trackCount} tracks, {durationMin} min)</div>

				{#if !fillComplete && !fillRunning}
					<div class="fill-form">
						<label class="form-label">
							Target length (minutes)
							<input type="number" bind:value={fillTargetMin} min={1} max={300} class="form-input" />
						</label>
						<label class="form-label">
							Max tracks to add
							<input type="number" bind:value={fillMaxTracks} min={1} max={30} class="form-input" />
						</label>
						<div class="form-actions">
							<Button variant="secondary" size="sm" onclick={onclose}>Cancel</Button>
							<Button variant="primary" size="sm" onclick={startFill}>Find tracks</Button>
						</div>
					</div>
				{:else if fillRunning}
					<div class="fill-status">Listening to your set and finding candidates...</div>
				{/if}

				{#if proposals.length > 0}
					<div class="proposals">
						{#each proposals as proposal, i}
							<div class="proposal-row" class:skipped={!proposal.accepted}>
								<div class="proposal-info">
									<span class="proposal-score" style="color: {scoreColor(proposal.score)}">
										{proposal.score.toFixed(2)}
									</span>
									<span class="proposal-title">
										Insert at pos {proposal.position}: {proposal.track_title ?? '?'}
										{#if proposal.track_artist}
											<span class="dim"> - {proposal.track_artist}</span>
										{/if}
									</span>
								</div>
								<p class="proposal-explanation">{proposal.explanation}</p>
								<div class="proposal-actions">
									<Button
										variant="ghost"
										size="sm"
										pressed={proposal.accepted}
										onclick={() => { proposals[i].accepted = true; proposals = proposals; }}
									>Keep</Button>
									<Button
										variant="ghost"
										size="sm"
										pressed={!proposal.accepted}
										onclick={() => { proposals[i].accepted = false; proposals = proposals; }}
									>Skip</Button>
								</div>
							</div>
						{/each}
					</div>
				{/if}

				{#if fillComplete && proposals.length > 0}
					<div class="form-actions">
						<Button variant="secondary" size="sm" onclick={onclose}>Cancel</Button>
						<Button variant="primary" size="sm" onclick={applyFill} loading={applying} disabled={proposals.filter(p => p.accepted).length === 0}>
							{applying ? 'Applying...' : `Apply ${proposals.filter(p => p.accepted).length} tracks`}
						</Button>
					</div>
				{/if}
			</div>
		{:else}
			<div class="tab-content">
				{#if !reorderResult && !optimizing}
					<div class="reorder-form">
						<div class="strategy-options">
							<label class="strategy-option">
								<input type="radio" bind:group={strategy} value="gentle" />
								<div>
									<strong>Gentle</strong>
									<span class="dim"> - minimal changes, keeps your intent</span>
								</div>
							</label>
							<label class="strategy-option">
								<input type="radio" bind:group={strategy} value="full" />
								<div>
									<strong>Full Rethink</strong>
									<span class="dim"> - best possible flow</span>
								</div>
							</label>
						</div>
						<div class="form-actions">
							<Button variant="secondary" size="sm" onclick={onclose}>Cancel</Button>
							<Button variant="primary" size="sm" onclick={startOptimize}>Optimize</Button>
						</div>
					</div>
				{:else if optimizing}
					<div class="fill-status">Finding the best flow...</div>
				{:else if reorderResult}
					<div class="reorder-result">
						<div class="score-comparison">
							<span style="color: {scoreColor(reorderResult.current_score)}">
								{reorderResult.current_score.toFixed(3)}
							</span>
							<span class="arrow">→</span>
							<span style="color: {scoreColor(reorderResult.proposed_score)}">
								{reorderResult.proposed_score.toFixed(3)}
							</span>
							{#if reorderResult.proposed_score - reorderResult.current_score > 0}
								<span class="delta positive">(+{((reorderResult.proposed_score - reorderResult.current_score) * 100 / reorderResult.current_score).toFixed(0)}%)</span>
							{:else}
								<span class="delta">({((reorderResult.proposed_score - reorderResult.current_score) * 100 / reorderResult.current_score).toFixed(0)}%)</span>
							{/if}
						</div>

						{#if reorderResult.changes.length === 0}
							<div class="no-changes">Your set is already in good shape — no changes suggested.</div>
						{:else}
							<div class="changes-list">
								<div class="changes-header">{reorderResult.changes.length} tracks moved:</div>
								{#each reorderResult.changes as change}
									<div class="change-row">
										<span class="change-title">{change.track_title ?? 'Track'}</span>
										<span class="change-positions">{change.from_position + 1} → {change.to_position + 1}</span>
										<span class="change-explanation">{change.explanation}</span>
									</div>
								{/each}
							</div>
						{/if}

						<div class="form-actions">
							<Button variant="secondary" size="sm" onclick={onclose}>Cancel</Button>
							<Button variant="primary" size="sm" onclick={applyReorder} loading={applyingReorder} disabled={reorderResult.changes.length === 0}>
								{applyingReorder ? 'Applying...' : 'Apply new order'}
							</Button>
						</div>
					</div>
				{/if}
			</div>
		{/if}
	</div>
</div>

<style>
	.dialog-overlay {
		position: fixed;
		inset: 0;
		background: rgba(0, 0, 0, 0.6);
		display: flex;
		align-items: center;
		justify-content: center;
		z-index: 200;
	}

	.dialog {
		background: var(--bg-primary);
		border: 1px solid var(--border);
		border-radius: 12px;
		width: 560px;
		max-height: 80vh;
		overflow-y: auto;
		box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5);
	}

	.dialog-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 12px 16px;
		border-bottom: 1px solid var(--border);
	}

	.tab-content {
		padding: 16px;
	}

	.set-info {
		font-size: 13px;
		color: var(--text-secondary);
		margin-bottom: 16px;
	}

	.fill-form, .reorder-form {
		display: flex;
		flex-direction: column;
		gap: 12px;
	}

	.form-label {
		display: flex;
		flex-direction: column;
		gap: 4px;
		font-size: 13px;
		color: var(--text-secondary);
	}

	.form-input {
		padding: 8px 10px;
		font-size: 13px;
		background: var(--bg-secondary);
		border: 1px solid var(--border);
		border-radius: 6px;
		color: var(--text-primary);
		width: 100px;
	}

	.form-actions {
		display: flex;
		gap: 8px;
		justify-content: flex-end;
		margin-top: 12px;
	}

	.fill-status {
		padding: 20px 0;
		text-align: center;
		color: var(--text-dim);
		font-size: 13px;
	}

	.proposals {
		display: flex;
		flex-direction: column;
		gap: 8px;
		margin-top: 12px;
	}

	.proposal-row {
		padding: 10px 12px;
		border: 1px solid var(--border);
		border-radius: 6px;
	}

	.proposal-row.skipped {
		opacity: 0.4;
	}

	.proposal-info {
		display: flex;
		align-items: center;
		gap: 8px;
	}

	.proposal-score {
		font-weight: 700;
		font-size: 13px;
	}

	.proposal-title {
		font-size: 13px;
	}

	.proposal-explanation {
		font-size: 12px;
		color: var(--text-dim);
		margin: 4px 0 6px;
	}

	.proposal-actions {
		display: flex;
		gap: 6px;
	}

	.strategy-options {
		display: flex;
		flex-direction: column;
		gap: 8px;
	}

	.strategy-option {
		display: flex;
		align-items: flex-start;
		gap: 8px;
		padding: 8px 10px;
		border: 1px solid var(--border);
		border-radius: 6px;
		cursor: pointer;
		font-size: 13px;
	}

	.score-comparison {
		display: flex;
		align-items: center;
		gap: 8px;
		font-size: 18px;
		font-weight: 700;
		margin-bottom: 16px;
	}

	.arrow {
		color: var(--text-dim);
	}

	.delta {
		font-size: 14px;
		font-weight: 400;
	}

	.delta.positive {
		color: var(--score-excellent);
	}

	.no-changes {
		padding: 16px 0;
		color: var(--text-dim);
		font-size: 13px;
	}

	.changes-list {
		display: flex;
		flex-direction: column;
		gap: 6px;
	}

	.changes-header {
		font-size: 12px;
		font-weight: 600;
		color: var(--text-secondary);
		text-transform: uppercase;
		letter-spacing: 0.05em;
	}

	.change-row {
		display: flex;
		align-items: baseline;
		gap: 8px;
		font-size: 13px;
		padding: 4px 0;
	}

	.change-title {
		font-weight: 600;
	}

	.change-positions {
		color: var(--accent);
		font-size: 12px;
	}

	.change-explanation {
		color: var(--text-dim);
		font-size: 12px;
	}

	.dim {
		color: var(--text-dim);
	}
</style>
