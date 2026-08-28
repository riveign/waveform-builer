const API_BASE = import.meta.env.VITE_API_BASE ?? '';

async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
	const res = await fetch(`${API_BASE}${path}`, init);
	if (!res.ok) {
		const body = await res.text().catch(() => '');
		throw new Error(`API ${res.status}: ${body}`);
	}
	return res.json();
}

/** For 204/empty-body endpoints. Same failure contract as `fetchJson` — a 4xx/5xx
 *  throws — but nothing is parsed, so a bare `fetch` no longer swallows the error. */
async function fetchVoid(path: string, init?: RequestInit): Promise<void> {
	const res = await fetch(`${API_BASE}${path}`, init);
	if (!res.ok) {
		const body = await res.text().catch(() => '');
		throw new Error(`API ${res.status}: ${body}`);
	}
}

export { API_BASE, fetchJson, fetchVoid };
