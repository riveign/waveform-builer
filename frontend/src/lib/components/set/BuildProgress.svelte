<script lang="ts">
	type BuildEvent = {
		type: 'started' | 'track_added' | 'complete' | 'analyzed' | 'error';
		data: any;
	};

	type BuildState = 'idle' | 'building' | 'complete' | 'error';

	let {
		buildState = 'idle' as BuildState,
		events = [] as BuildEvent[],
		error = '' as string,
		onretry,
		onclose,
	}: {
		buildState: BuildState;
		events: BuildEvent[];
		error?: string;
		onretry?: () => void;
		onclose?: () => void;
	} = $props();

	let trackEvents = $derived(
		events.filter((e) => e.type === 'track_added')
	);

	let completeEvent = $derived(
		events.find((e) => e.type === 'complete')
	);

	let listEl = $state<HTMLDivElement | undefined>();

	// Auto-scroll to bottom when new tracks arrive
	$effect(() => {
		if (trackEvents.length && listEl) {
			listEl.scrollTop = listEl.scrollHeight;
		}
	});

	// Auto-close after 1.5s on complete
	$effect(() => {
		if (buildState === 'complete' && onclose) {
			const timer = setTimeout(onclose, 1500);
			return () => clearTimeout(timer);
		}
	});
</script>

{#if buildState === 'building'}
	<div class="build-progress" role="status" aria-live="polite">
		<div class="progress-header">
			<span class="pulse-dot"></span>
			<h3>Building your set...</h3>
		</div>

		<div class="track-list" bind:this={listEl}>
			{#each trackEvents as event, i (i)}
				<div class="track-row" style="animation-delay: {Math.min(i * 0.04, 0.5)}s">
					<span class="track-pos">{(event.data?.position ?? i + 1)}</span>
					<div class="track-info">
						<span class="track-title">{event.data?.title ?? 'Untitled'}</span>
						<span class="track-artist">{event.data?.artist ?? 'Unknown'}</span>
					</div>
					<div class="track-meta">
						{#if event.data?.bpm}
							<span class="track-bpm">{Math.round(event.data.bpm)}</span>
						{/if}
						{#if event.data?.key}
							<span class="track-key">{event.data.key}</span>
						{/if}
					</div>
				</div>
			{/each}
		</div>

		<div class="progress-footer">
			<span class="track-count">{trackEvents.length} track{trackEvents.length !== 1 ? 's' : ''} so far</span>
		</div>
	</div>

{:else if buildState === 'complete'}
	<div class="build-progress">
		<div class="complete-header">
			<h3>Set ready!</h3>
			{#if completeEvent?.data}
				<p class="complete-summary">
					{completeEvent.data.track_count} tracks, {completeEvent.data.duration_min} minutes
				</p>
			{/if}
		</div>
		{#if onclose}
			<button class="btn-accent" onclick={onclose} type="button">View Set</button>
		{/if}
	</div>

{:else if buildState === 'error'}
	<div class="build-progress" role="alert">
		<div class="error-header">
			<h3>Something went wrong</h3>
			{#if error}
				<p class="error-message">{error}</p>
			{/if}
		</div>
		<div class="error-actions">
			{#if onretry}
				<button class="btn-accent" onclick={onretry} type="button">Try Again</button>
			{/if}
			{#if onclose}
				<button class="btn-secondary" onclick={onclose} type="button">Close</button>
			{/if}
		</div>
	</div>
{/if}

<style>
	.build-progress {
		display: flex;
		flex-direction: column;
		gap: 12px;
		padding: 16px;
		background: var(--bg-secondary);
		border-radius: 6px;
	}

	/* --- Building state --- */

	.progress-header {
		display: flex;
		align-items: center;
		gap: 10px;
	}

	.progress-header h3 {
		font-size: 14px;
		font-weight: 600;
		color: var(--text-primary);
	}

	.pulse-dot {
		width: 8px;
		height: 8px;
		border-radius: 50%;
		background: var(--accent);
		flex-shrink: 0;
		animation: pulse 1.4s ease-in-out infinite;
	}

	@keyframes pulse {
		0%, 100% { opacity: 0.4; transform: scale(0.85); }
		50% { opacity: 1; transform: scale(1); }
	}

	.track-list {
		display: flex;
		flex-direction: column;
		gap: 2px;
		max-height: 280px;
		overflow-y: auto;
		scrollbar-width: thin;
	}

	.track-row {
		display: flex;
		align-items: center;
		gap: 8px;
		padding: 4px 8px;
		border-radius: 3px;
		animation: slide-in 0.25s ease-out both;
	}

	.track-row:hover {
		background: var(--bg-hover);
	}

	@keyframes slide-in {
		from {
			opacity: 0;
			transform: translateY(6px);
		}
		to {
			opacity: 1;
			transform: translateY(0);
		}
	}

	.track-pos {
		width: 20px;
		flex-shrink: 0;
		font-size: 11px;
		font-weight: 600;
		color: var(--text-dim);
		text-align: center;
		font-variant-numeric: tabular-nums;
	}

	.track-info {
		flex: 1;
		min-width: 0;
		display: flex;
		align-items: baseline;
		gap: 6px;
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
		flex-shrink: 1;
	}

	.track-meta {
		display: flex;
		align-items: center;
		gap: 6px;
		flex-shrink: 0;
	}

	.track-bpm {
		font-size: 11px;
		color: var(--text-secondary);
		font-variant-numeric: tabular-nums;
	}

	.track-key {
		font-size: 11px;
		font-weight: 600;
		color: var(--accent);
	}

	.progress-footer {
		padding-top: 8px;
		border-top: 1px solid var(--border);
	}

	.track-count {
		font-size: 12px;
		color: var(--text-secondary);
	}

	/* --- Complete state --- */

	.complete-header {
		text-align: center;
	}

	.complete-header h3 {
		font-size: 16px;
		font-weight: 600;
		color: var(--accent);
	}

	.complete-summary {
		margin-top: 4px;
		font-size: 13px;
		color: var(--text-secondary);
	}

	/* --- Error state --- */

	.error-header {
		text-align: center;
	}

	.error-header h3 {
		font-size: 14px;
		font-weight: 600;
		color: var(--energy-high);
	}

	.error-message {
		margin-top: 6px;
		font-size: 12px;
		color: var(--text-secondary);
		line-height: 1.4;
	}

	.error-actions {
		display: flex;
		justify-content: center;
		gap: 8px;
	}

	/* --- Buttons --- */

	.btn-accent {
		padding: 6px 16px;
		border-radius: 4px;
		font-size: 13px;
		font-weight: 500;
		background: var(--accent);
		color: #000;
		transition: background 0.15s;
	}

	.btn-accent:hover {
		background: var(--accent-dim);
	}

	.btn-secondary {
		padding: 6px 16px;
		border-radius: 4px;
		font-size: 13px;
		font-weight: 500;
		background: var(--bg-tertiary);
		color: var(--text-secondary);
		transition: background 0.15s;
	}

	.btn-secondary:hover {
		background: var(--bg-hover);
	}

	@media (prefers-reduced-motion: reduce) {
		.pulse-dot {
			animation: none;
			opacity: 1;
		}
		.track-row {
			animation: none;
			opacity: 1;
		}
	}
</style>
