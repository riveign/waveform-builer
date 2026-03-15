<script lang="ts">
	import { getEnergyGenre } from '$lib/api/stats';

	const ENERGY_LEVELS = ['low', 'warmup', 'closing', 'mid', 'dance', 'up', 'high', 'fast', 'peak'] as const;

	const FAMILY_COLORS: Record<string, string> = {
		Techno: '#40E0D0',
		House: '#FF7F50',
		Groove: '#66BB6A',
		Trance: '#9575CD',
		Breaks: '#FFB74D',
		Electronic: '#42A5F5',
		Other: '#95a5a6',
	};

	let data: Record<string, Record<string, number>> | null = $state(null);
	let loading = $state(true);
	let error: string | null = $state(null);
	let tooltip = $state({ visible: false, text: '', x: 0, y: 0 });

	let families = $derived(
		data ? Object.keys(data).sort() : []
	);

	let maxCount = $derived(() => {
		if (!data) return 1;
		let max = 1;
		for (const family of Object.values(data)) {
			for (const count of Object.values(family)) {
				if (count > max) max = count;
			}
		}
		return max;
	});

	function getOpacity(count: number): number {
		if (count === 0) return 0.05;
		const max = maxCount();
		return 0.15 + (count / max) * 0.85;
	}

	function getFamilyColor(family: string): string {
		return FAMILY_COLORS[family] ?? FAMILY_COLORS.Other;
	}

	function showTooltip(e: MouseEvent, family: string, level: string, count: number) {
		tooltip = {
			visible: true,
			text: `${family} / ${level}: ${count} track${count !== 1 ? 's' : ''}`,
			x: e.clientX,
			y: e.clientY,
		};
	}

	function hideTooltip() {
		tooltip = { ...tooltip, visible: false };
	}

	$effect(() => {
		let cancelled = false;
		getEnergyGenre()
			.then((result) => {
				if (!cancelled) {
					data = result;
					loading = false;
				}
			})
			.catch((err) => {
				if (!cancelled) {
					error = err instanceof Error ? err.message : "Couldn't load energy-genre data — try refreshing";
					loading = false;
				}
			});
		return () => { cancelled = true; };
	});
</script>

<div class="heatmap-container">
	<h3 class="chart-title">Energy x Genre</h3>
	<p class="teaching-note">How energy maps across genres — bright cells are your sweet spots</p>
	{#if loading}
		<div class="loading">
			<div class="loading-pulse"></div>
		</div>
	{:else if error}
		<div class="error-state">{error}</div>
	{:else if families.length === 0}
		<div class="empty-state">No energy-genre data yet</div>
	{:else}
		<div class="heatmap-grid" style="grid-template-columns: 100px repeat({ENERGY_LEVELS.length}, 1fr)">
			<!-- Header row -->
			<div class="header-cell corner"></div>
			{#each ENERGY_LEVELS as level}
				<div class="header-cell">{level}</div>
			{/each}

			<!-- Data rows -->
			{#each families as family}
				<div class="row-label" style="color: {getFamilyColor(family)}">{family}</div>
				{#each ENERGY_LEVELS as level}
					{@const count = data?.[family]?.[level] ?? 0}
					<div
						class="cell"
						style="background: {getFamilyColor(family)}; opacity: {getOpacity(count)}"
						role="gridcell"
						tabindex="-1"
						aria-label="{family} {level}: {count} tracks"
						onmouseenter={(e) => showTooltip(e, family, level, count)}
						onmouseleave={hideTooltip}
					>
						{#if count > 0}
							<span class="cell-count">{count}</span>
						{/if}
					</div>
				{/each}
			{/each}
		</div>
	{/if}

	{#if tooltip.visible}
		<div class="tooltip" style="left: {tooltip.x + 12}px; top: {tooltip.y - 8}px">
			{tooltip.text}
		</div>
	{/if}
</div>

<style>
	.heatmap-container {
		background: var(--bg-secondary);
		border-radius: 8px;
		padding: 16px;
		position: relative;
	}

	.chart-title {
		font-size: 13px;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.5px;
		color: var(--text-secondary);
		margin-bottom: 2px;
	}

	.teaching-note {
		font-size: 11px;
		color: var(--text-dim);
		margin-bottom: 8px;
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

	.heatmap-grid {
		display: grid;
		gap: 2px;
		align-items: center;
	}

	.header-cell {
		font-size: 10px;
		text-transform: uppercase;
		letter-spacing: 0.3px;
		color: var(--text-dim);
		text-align: center;
		padding: 4px 2px;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.row-label {
		font-size: 11px;
		font-weight: 600;
		padding-right: 8px;
		text-align: right;
		white-space: nowrap;
	}

	.cell {
		position: relative;
		display: flex;
		align-items: center;
		justify-content: center;
		height: 32px;
		border-radius: 3px;
		cursor: default;
		transition: transform 0.1s;
	}

	.cell:hover {
		transform: scale(1.1);
		z-index: 1;
	}

	.cell-count {
		font-size: 10px;
		font-weight: 700;
		color: #fff;
		text-shadow: 0 1px 2px rgba(0, 0, 0, 0.6);
		/* Override the parent opacity for text readability */
		opacity: 1;
	}

	.tooltip {
		position: fixed;
		z-index: 100;
		background: var(--bg-primary);
		border: 1px solid var(--border);
		border-radius: 4px;
		padding: 6px 10px;
		font-size: 12px;
		color: var(--text-primary);
		pointer-events: none;
		white-space: nowrap;
		box-shadow: 0 2px 8px rgba(0, 0, 0, 0.4);
	}
</style>
