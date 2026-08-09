<script lang="ts" module>
	export type InputSize = 'sm' | 'md';
</script>

<script lang="ts">
	/**
	 * A labelled text or number field.
	 *
	 * Every dialog had been restyling `padding / border / radius / background` from
	 * scratch, so fields drifted between surfaces. The label is part of the
	 * primitive because a field without one is the most common a11y regression.
	 */

	let {
		value = $bindable(),
		label = undefined,
		type = 'text',
		placeholder = undefined,
		hint = undefined,
		invalid = false,
		disabled = false,
		size = 'md',
		min = undefined,
		max = undefined,
		id = undefined,
		ariaLabel = undefined,
		oninput,
		onkeydown,
	}: {
		value: string | number | undefined;
		/** Visible label. Omit only when `ariaLabel` names the field instead. */
		label?: string;
		type?: 'text' | 'number' | 'search' | 'url';
		placeholder?: string;
		/** Help text below the field. Becomes the error message when `invalid`. */
		hint?: string;
		invalid?: boolean;
		disabled?: boolean;
		size?: InputSize;
		min?: number;
		max?: number;
		id?: string;
		ariaLabel?: string;
		oninput?: (e: Event) => void;
		onkeydown?: (e: KeyboardEvent) => void;
	} = $props();

	// Stable enough for label/hint association within one component instance.
	const uid = `input-${Math.random().toString(36).slice(2, 9)}`;
	const inputId = $derived(id ?? uid);
	const hintId = $derived(hint ? `${inputId}-hint` : undefined);
</script>

<div class="field">
	{#if label}
		<label class="field-label" for={inputId}>{label}</label>
	{/if}
	<input
		id={inputId}
		class="field-input field-input--{size}"
		class:invalid
		{type}
		{placeholder}
		{disabled}
		{min}
		{max}
		aria-label={label ? undefined : ariaLabel}
		aria-invalid={invalid ? 'true' : undefined}
		aria-describedby={hintId}
		bind:value
		{oninput}
		{onkeydown}
	/>
	{#if hint}
		<span class="field-hint" class:invalid id={hintId}>{hint}</span>
	{/if}
</div>

<style>
	.field {
		display: flex;
		flex-direction: column;
		gap: var(--space-xs);
		min-width: 0;
	}

	.field-label {
		font-size: var(--text-xs);
		color: var(--text-3);
	}

	.field-input {
		background: var(--surface-2);
		border: 1px solid var(--border-default);
		border-radius: var(--radius-sm, 6px);
		color: var(--text-1);
		width: 100%;
		min-width: 0;
	}

	.field-input--sm { padding: 4px 8px; font-size: var(--text-xs); }
	.field-input--md { padding: 8px 10px; font-size: var(--text-sm); }

	.field-input:focus-visible {
		outline: 2px solid var(--accent);
		outline-offset: -1px;
		border-color: var(--accent);
	}

	.field-input:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	.field-input.invalid {
		border-color: var(--destructive);
	}

	.field-hint {
		font-size: var(--text-xs);
		color: var(--text-4);
	}

	.field-hint.invalid {
		color: var(--destructive);
	}
</style>
