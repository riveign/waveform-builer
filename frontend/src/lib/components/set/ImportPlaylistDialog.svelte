<script lang="ts">
	import type { ImportResult } from '$lib/types';
	import { importPlaylist } from '$lib/api/sets';

	let {
		open = $bindable(false),
		onimport,
	}: {
		open: boolean;
		onimport?: (result: ImportResult) => void;
	} = $props();

	let dialogEl: HTMLDialogElement | undefined = $state();
	let file = $state<File | null>(null);
	let nameOverride = $state('');
	let force = $state(false);
	let loading = $state(false);
	let error = $state('');
	let result = $state<ImportResult | null>(null);
	let dragOver = $state(false);

	$effect(() => {
		if (open && dialogEl) {
			dialogEl.showModal();
			reset();
		} else if (!open && dialogEl?.open) {
			dialogEl.close();
		}
	});

	function reset() {
		file = null;
		nameOverride = '';
		force = false;
		loading = false;
		error = '';
		result = null;
	}

	function handleClose() {
		open = false;
	}

	function handleDrop(e: DragEvent) {
		e.preventDefault();
		dragOver = false;
		const f = e.dataTransfer?.files[0];
		if (f && (f.name.endsWith('.m3u8') || f.name.endsWith('.m3u'))) {
			file = f;
			if (!nameOverride) {
				nameOverride = f.name.replace(/\.m3u8?$/, '');
			}
		} else {
			error = "Drop an .m3u8 file";
		}
	}

	function handleFileInput(e: Event) {
		const input = e.target as HTMLInputElement;
		const f = input.files?.[0];
		if (f) {
			file = f;
			if (!nameOverride) {
				nameOverride = f.name.replace(/\.m3u8?$/, '');
			}
		}
	}

	async function doImport() {
		if (!file) return;
		loading = true;
		error = '';
		try {
			const res = await importPlaylist(file, nameOverride || undefined, force);
			result = res;
			if (res.duplicate_set_id && !force) {
				error = `Already imported as set ${res.duplicate_set_id}. Toggle "Force re-import" to overwrite.`;
			} else if (res.matched_count > 0) {
				onimport?.(res);
			}
		} catch (err) {
			error = err instanceof Error ? err.message : 'Import failed';
		} finally {
			loading = false;
		}
	}
</script>

<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
<dialog bind:this={dialogEl} onclose={handleClose} onkeydown={(e) => e.key === 'Escape' && handleClose()}>
	<div class="dialog-content">
		<h2>Import Playlist</h2>
		<p class="subtitle">Drop a Rekordbox M3U8 export to create a set from it</p>

		{#if !result || error}
			<!-- Drop zone -->
			<!-- svelte-ignore a11y_no_static_element_interactions -->
			<div
				class="drop-zone"
				class:drag-over={dragOver}
				class:has-file={!!file}
				ondragover={(e) => { e.preventDefault(); dragOver = true; }}
				ondragleave={() => dragOver = false}
				ondrop={handleDrop}
			>
				{#if file}
					<span class="file-name">{file.name}</span>
					<button class="clear-btn" onclick={() => { file = null; }}>change</button>
				{:else}
					<span class="drop-text">Drop .m3u8 file here</span>
					<span class="or">or</span>
					<label class="browse-btn">
						Browse
						<input type="file" accept=".m3u8,.m3u" onchange={handleFileInput} hidden />
					</label>
				{/if}
			</div>

			<!-- Name override -->
			<label class="field">
				<span>Set name</span>
				<input type="text" bind:value={nameOverride} placeholder="Uses filename if empty" />
			</label>

			<!-- Force checkbox -->
			<label class="checkbox-field">
				<input type="checkbox" bind:checked={force} />
				<span>Force re-import (overwrite if already imported)</span>
			</label>

			{#if error}
				<p class="error">{error}</p>
			{/if}

			<div class="actions">
				<button class="secondary" onclick={handleClose}>Cancel</button>
				<button class="primary" onclick={doImport} disabled={!file || loading}>
					{loading ? 'Importing...' : 'Import'}
				</button>
			</div>
		{:else}
			<!-- Result -->
			<div class="result">
				<div class="result-header">
					<span class="result-icon">&#10003;</span>
					<strong>{result.name}</strong>
				</div>
				<div class="stats">
					<span>Matched: <strong>{result.matched_count}</strong> / {result.total_tracks}</span>
					{#if result.unmatched_count > 0}
						<span class="warn">Unmatched: {result.unmatched_count}</span>
					{/if}
				</div>

				{#if Object.keys(result.match_methods).length > 0}
					<div class="methods">
						{#each Object.entries(result.match_methods) as [method, count]}
							<span class="method-chip">{method}: {count}</span>
						{/each}
					</div>
				{/if}

				{#if result.unmatched_paths.length > 0}
					<details class="unmatched">
						<summary>{result.unmatched_count} unmatched tracks</summary>
						<ul>
							{#each result.unmatched_paths.slice(0, 20) as u}
								<li>{u.title || u.path}</li>
							{/each}
							{#if result.unmatched_paths.length > 20}
								<li class="more">... and {result.unmatched_paths.length - 20} more</li>
							{/if}
						</ul>
					</details>
				{/if}

				{#if result.warnings.length > 0}
					<div class="warnings">
						{#each result.warnings as w}
							<p class="warning">{w}</p>
						{/each}
					</div>
				{/if}

				<div class="actions">
					<button class="primary" onclick={handleClose}>Done</button>
				</div>
			</div>
		{/if}
	</div>
</dialog>

<style>
	dialog {
		border: 1px solid var(--border);
		border-radius: 12px;
		padding: 0;
		max-width: 480px;
		width: 90vw;
		background: var(--bg-primary);
		color: var(--text-primary);
	}

	dialog::backdrop {
		background: rgba(0, 0, 0, 0.6);
	}

	.dialog-content {
		padding: 24px;
	}

	h2 {
		margin: 0 0 4px;
		font-size: 18px;
	}

	.subtitle {
		margin: 0 0 20px;
		color: var(--text-dim);
		font-size: 13px;
	}

	.drop-zone {
		border: 2px dashed var(--border);
		border-radius: 8px;
		padding: 32px;
		text-align: center;
		margin-bottom: 16px;
		transition: border-color 0.15s, background 0.15s;
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 8px;
	}

	.drop-zone.drag-over {
		border-color: var(--accent);
		background: var(--bg-secondary);
	}

	.drop-zone.has-file {
		border-style: solid;
		border-color: var(--accent);
	}

	.drop-text {
		color: var(--text-dim);
		font-size: 14px;
	}

	.or {
		color: var(--text-dim);
		font-size: 12px;
	}

	.browse-btn {
		cursor: pointer;
		color: var(--accent);
		font-size: 13px;
		text-decoration: underline;
	}

	.file-name {
		font-weight: 600;
		font-size: 14px;
	}

	.clear-btn {
		background: none;
		border: none;
		color: var(--accent);
		cursor: pointer;
		font-size: 12px;
		text-decoration: underline;
		padding: 0;
	}

	.field {
		display: flex;
		flex-direction: column;
		gap: 4px;
		margin-bottom: 12px;
		font-size: 13px;
	}

	.field input {
		padding: 8px 10px;
		font-size: 13px;
		border: 1px solid var(--border);
		border-radius: 6px;
		background: var(--bg-secondary);
		color: var(--text-primary);
	}

	.checkbox-field {
		display: flex;
		align-items: center;
		gap: 8px;
		font-size: 13px;
		margin-bottom: 16px;
		color: var(--text-dim);
	}

	.error {
		color: var(--color-red, #e74c3c);
		font-size: 13px;
		margin: 8px 0;
	}

	.actions {
		display: flex;
		justify-content: flex-end;
		gap: 8px;
		margin-top: 16px;
	}

	button {
		padding: 8px 16px;
		border-radius: 6px;
		font-size: 13px;
		cursor: pointer;
		border: 1px solid var(--border);
	}

	button.primary {
		background: var(--accent);
		color: white;
		border-color: var(--accent);
	}

	button.primary:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	button.secondary {
		background: var(--bg-secondary);
		color: var(--text-primary);
	}

	.result-header {
		display: flex;
		align-items: center;
		gap: 8px;
		margin-bottom: 12px;
	}

	.result-icon {
		color: var(--color-green, #2ecc71);
		font-size: 20px;
	}

	.stats {
		display: flex;
		gap: 16px;
		font-size: 13px;
		margin-bottom: 12px;
	}

	.warn {
		color: var(--color-yellow, #f39c12);
	}

	.methods {
		display: flex;
		gap: 6px;
		flex-wrap: wrap;
		margin-bottom: 12px;
	}

	.method-chip {
		font-size: 11px;
		padding: 2px 8px;
		border-radius: 10px;
		background: var(--bg-tertiary);
		color: var(--text-dim);
	}

	.unmatched {
		font-size: 13px;
		margin-bottom: 12px;
	}

	.unmatched summary {
		cursor: pointer;
		color: var(--text-dim);
	}

	.unmatched ul {
		margin: 8px 0 0;
		padding-left: 20px;
	}

	.unmatched li {
		margin-bottom: 2px;
		color: var(--text-dim);
		font-size: 12px;
	}

	.more {
		font-style: italic;
	}

	.warnings {
		margin-bottom: 8px;
	}

	.warning {
		color: var(--color-yellow, #f39c12);
		font-size: 12px;
		margin: 4px 0;
	}
</style>
