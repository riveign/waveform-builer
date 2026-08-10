import '@testing-library/jest-dom/vitest';

// jsdom has no layout engine, so <dialog> is inert there: showModal() and close()
// are missing entirely. Modal is built on the native element, so without these the
// component under test can never open. This is a jsdom gap, not a Kiku one.
if (typeof HTMLDialogElement !== 'undefined') {
	if (!HTMLDialogElement.prototype.showModal) {
		HTMLDialogElement.prototype.showModal = function (this: HTMLDialogElement) {
			this.open = true;
		};
	}
	if (!HTMLDialogElement.prototype.close) {
		HTMLDialogElement.prototype.close = function (this: HTMLDialogElement) {
			this.open = false;
			this.dispatchEvent(new Event('close'));
		};
	}
}

// This jsdom build exposes `window` but not `localStorage`. The playback store
// persists builder-mode keeps there, so without it the store cannot be tested at
// all. Another jsdom gap rather than a Kiku one.
if (typeof localStorage === 'undefined') {
	const store = new Map<string, string>();
	const shim: Storage = {
		get length() {
			return store.size;
		},
		clear: () => store.clear(),
		getItem: (k) => store.get(k) ?? null,
		key: (i) => [...store.keys()][i] ?? null,
		removeItem: (k) => void store.delete(k),
		setItem: (k, v) => void store.set(k, String(v)),
	};
	Object.defineProperty(globalThis, 'localStorage', { value: shim, configurable: true });
	Object.defineProperty(window, 'localStorage', { value: shim, configurable: true });
}
