<script lang="ts">
	let {
		placeholder = 'Search...',
		selected = $bindable<string[]>([]),
		fetchSuggestions,
	}: {
		placeholder?: string;
		selected: string[];
		fetchSuggestions: (q: string) => Promise<string[]>;
	} = $props();

	let inputText = $state('');
	let suggestions = $state<string[]>([]);
	let showDropdown = $state(false);
	let activeIndex = $state(-1);
	let timer: ReturnType<typeof setTimeout> | undefined;
	let containerEl = $state<HTMLDivElement | null>(null);

	function onInput() {
		const q = inputText.trim();
		if (q.length < 1) {
			suggestions = [];
			showDropdown = false;
			return;
		}
		clearTimeout(timer);
		timer = setTimeout(async () => {
			try {
				const results = await fetchSuggestions(q);
				// Filter out already-selected items
				suggestions = results.filter((r) => !selected.includes(r));
				showDropdown = suggestions.length > 0;
				activeIndex = -1;
			} catch {
				suggestions = [];
				showDropdown = false;
			}
		}, 200);
	}

	function selectItem(item: string) {
		if (!selected.includes(item)) {
			selected = [...selected, item];
		}
		inputText = '';
		suggestions = [];
		showDropdown = false;
		activeIndex = -1;
	}

	function removeItem(item: string) {
		selected = selected.filter((s) => s !== item);
	}

	function onKeydown(e: KeyboardEvent) {
		if (!showDropdown) return;
		if (e.key === 'ArrowDown') {
			e.preventDefault();
			activeIndex = Math.min(activeIndex + 1, suggestions.length - 1);
		} else if (e.key === 'ArrowUp') {
			e.preventDefault();
			activeIndex = Math.max(activeIndex - 1, 0);
		} else if (e.key === 'Enter' && activeIndex >= 0) {
			e.preventDefault();
			selectItem(suggestions[activeIndex]);
		} else if (e.key === 'Escape') {
			showDropdown = false;
		}
	}

	function onBlur(e: FocusEvent) {
		// Delay to allow click on dropdown item
		setTimeout(() => {
			if (containerEl && !containerEl.contains(document.activeElement)) {
				showDropdown = false;
			}
		}, 150);
	}
</script>

<div class="typeahead" bind:this={containerEl}>
	{#if selected.length > 0}
		<div class="selected-items">
			{#each selected as item}
				<button class="selected-chip" type="button" onclick={() => removeItem(item)}>
					{item} <span class="chip-x">&times;</span>
				</button>
			{/each}
		</div>
	{/if}
	<div class="input-wrap">
		<input
			type="text"
			class="typeahead-input"
			{placeholder}
			bind:value={inputText}
			oninput={onInput}
			onkeydown={onKeydown}
			onblur={onBlur}
			onfocus={onInput}
		/>
		{#if showDropdown}
			<div class="dropdown">
				{#each suggestions as item, i}
					<button
						class="dropdown-item"
						class:dropdown-item-active={i === activeIndex}
						type="button"
						onmousedown={(e: MouseEvent) => { e.preventDefault(); selectItem(item); }}
					>
						{item}
					</button>
				{/each}
			</div>
		{/if}
	</div>
</div>

<style>
	.typeahead {
		display: flex;
		flex-direction: column;
		gap: 4px;
	}

	.selected-items {
		display: flex;
		flex-wrap: wrap;
		gap: 3px;
	}

	.selected-chip {
		display: inline-flex;
		align-items: center;
		gap: 3px;
		font-size: 10px;
		padding: 2px 7px;
		border-radius: 10px;
		background: var(--accent);
		border: 1px solid var(--accent);
		color: #000;
		font-weight: 500;
		cursor: pointer;
		transition: all 0.1s;
	}

	.selected-chip:hover {
		background: var(--accent-dim);
		border-color: var(--accent-dim);
	}

	.chip-x {
		font-size: 12px;
		line-height: 1;
		opacity: 0.7;
	}

	.input-wrap {
		position: relative;
	}

	.typeahead-input {
		width: 100%;
		padding: 5px 8px;
		font-size: 12px;
		background: var(--bg-tertiary);
		border: 1px solid var(--border);
		border-radius: 4px;
		color: var(--text-primary);
		box-sizing: border-box;
	}

	.typeahead-input:focus {
		outline: none;
		border-color: var(--accent);
	}

	.typeahead-input::placeholder {
		color: var(--text-dim);
	}

	.dropdown {
		position: absolute;
		top: 100%;
		left: 0;
		right: 0;
		z-index: 100;
		max-height: 160px;
		overflow-y: auto;
		background: var(--bg-secondary);
		border: 1px solid var(--border);
		border-top: none;
		border-radius: 0 0 4px 4px;
		box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
	}

	.dropdown-item {
		display: block;
		width: 100%;
		text-align: left;
		padding: 6px 8px;
		font-size: 12px;
		color: var(--text-secondary);
		cursor: pointer;
		transition: background 0.05s;
	}

	.dropdown-item:hover,
	.dropdown-item-active {
		background: var(--bg-hover);
		color: var(--text-primary);
	}
</style>
