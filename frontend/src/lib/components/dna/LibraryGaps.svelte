<script lang="ts">
	import { getLibraryGaps } from '$lib/api/stats';
	import type { LibraryGapsResponse, CamelotGap, BpmGap, EnergyGap } from '$lib/types';

	let data = $state<LibraryGapsResponse | null>(null);
	let loading = $state(true);
	let error = $state<string | null>(null);

	function severityColor(count: number): string {
		if (count < 3) return '#ef5350';
		if (count <= 7) return '#FFA726';
		return '#FFEE58';
	}

	$effect(() => {
		let cancelled = false;
		getLibraryGaps()
			.then((result) => {
				if (!cancelled) {
					data = result;
					loading = false;
				}
			})
			.catch((err) => {
				if (!cancelled) {
					error = err instanceof Error ? err.message : "Couldn't load gap analysis — try refreshing";
					loading = false;
				}
			});
		return () => { cancelled = true; };
	});
</script>

<div class="library-gaps">
	<h3 class="chart-title">Library Gaps</h3>
	<p class="teaching-note">Weak spots in your collection — filling these gives you more mix options</p>
	{#if loading}
		<div class="loading">
			<div class="loading-pulse"></div>
		</div>
	{:else if error}
		<div class="error-state">{error}</div>
	{:else if data}
		{#if data.camelot_gaps.length > 0}
			<div class="gap-section">
				<h4 class="section-label">Camelot Keys</h4>
				{#each data.camelot_gaps.slice(0, 5) as gap}
					<div class="gap-row">
						<span class="gap-label">{gap.position}</span>
						<span class="gap-badge" style="background: {severityColor(gap.count)}">{gap.count}</span>
						<div class="impact-bar-bg">
							<div class="impact-bar" style="width: {gap.impact}%; background: {severityColor(gap.count)}"></div>
						</div>
						<p class="gap-explanation">{gap.explanation}</p>
					</div>
				{/each}
			</div>
		{/if}

		{#if data.bpm_gaps.length > 0}
			<div class="gap-section">
				<h4 class="section-label">BPM Ranges</h4>
				{#each data.bpm_gaps.slice(0, 5) as gap}
					<div class="gap-row">
						<span class="gap-label">{gap.range}</span>
						<span class="gap-badge" style="background: {severityColor(gap.count)}">{gap.count}</span>
						<div class="impact-bar-bg">
							<div class="impact-bar" style="width: {Math.min(gap.count * 10, 100)}%; background: {severityColor(gap.count)}"></div>
						</div>
					</div>
				{/each}
			</div>
		{/if}

		{#if data.energy_gaps.length > 0}
			<div class="gap-section">
				<h4 class="section-label">Energy Levels</h4>
				{#each data.energy_gaps as gap}
					<div class="gap-row">
						<span class="gap-label">{gap.level}</span>
						<span class="gap-badge" style="background: {severityColor(gap.count)}">{gap.count}</span>
						<div class="impact-bar-bg">
							<div class="impact-bar" style="width: {Math.min(gap.count * 5, 100)}%; background: {severityColor(gap.count)}"></div>
						</div>
					</div>
				{/each}
			</div>
		{/if}

		{#if data.camelot_gaps.length === 0 && data.bpm_gaps.length === 0 && data.energy_gaps.length === 0}
			<div class="empty-state">Your collection is well-rounded — no major gaps found</div>
		{/if}
	{/if}
</div>

<style>
	.library-gaps {
		background: var(--bg-secondary);
		border-radius: 8px;
		padding: 16px;
		min-height: 300px;
	}

	.chart-title {
		font-size: 14px;
		font-weight: 600;
		color: var(--text-primary);
		margin-bottom: 2px;
	}

	.teaching-note {
		font-size: 11px;
		color: var(--text-dim);
		margin-bottom: 12px;
	}

	.loading {
		display: flex;
		align-items: center;
		justify-content: center;
		height: 200px;
	}

	.loading-pulse {
		width: 40px;
		height: 40px;
		border-radius: 50%;
		background: var(--accent);
		opacity: 0.3;
		animation: pulse 1.2s ease-in-out infinite;
	}

	@keyframes pulse {
		0%, 100% { opacity: 0.15; transform: scale(0.8); }
		50% { opacity: 0.4; transform: scale(1); }
	}

	.error-state,
	.empty-state {
		display: flex;
		align-items: center;
		justify-content: center;
		height: 200px;
		color: var(--text-dim);
		font-size: 13px;
	}

	.error-state {
		color: var(--energy-high);
	}

	.gap-section {
		margin-bottom: 16px;
	}

	.gap-section:last-child {
		margin-bottom: 0;
	}

	.section-label {
		font-size: 11px;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.5px;
		color: var(--text-secondary);
		margin-bottom: 8px;
	}

	.gap-row {
		display: grid;
		grid-template-columns: 80px 36px 1fr;
		gap: 8px;
		align-items: center;
		margin-bottom: 6px;
	}

	.gap-label {
		font-size: 12px;
		color: var(--text-primary);
		font-weight: 500;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.gap-badge {
		font-size: 10px;
		font-weight: 700;
		color: #0D0D0D;
		text-align: center;
		border-radius: 10px;
		padding: 2px 6px;
		line-height: 1.2;
	}

	.impact-bar-bg {
		height: 6px;
		background: rgba(63, 65, 74, 0.4);
		border-radius: 3px;
		overflow: hidden;
	}

	.impact-bar {
		height: 100%;
		border-radius: 3px;
		transition: width 0.3s ease;
	}

	.gap-explanation {
		grid-column: 1 / -1;
		font-size: 11px;
		color: var(--text-dim);
		margin-bottom: 4px;
		line-height: 1.3;
	}
</style>
