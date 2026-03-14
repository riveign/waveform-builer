const API_BASE = import.meta.env.VITE_API_BASE ?? '';

async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
	const res = await fetch(`${API_BASE}${path}`, init);
	if (!res.ok) {
		const body = await res.text().catch(() => '');
		throw new Error(`API ${res.status}: ${body}`);
	}
	return res.json();
}

export { API_BASE, fetchJson };
