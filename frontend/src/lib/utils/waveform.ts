/**
 * Decode a base64-encoded Float32Array from the API.
 */
export function decodeFloat32(b64: string): Float32Array {
	const binary = atob(b64);
	const bytes = new Uint8Array(binary.length);
	for (let i = 0; i < binary.length; i++) {
		bytes[i] = binary.charCodeAt(i);
	}
	return new Float32Array(bytes.buffer);
}

/**
 * Format seconds as mm:ss.
 */
export function formatTime(sec: number): string {
	const m = Math.floor(sec / 60);
	const s = Math.floor(sec % 60);
	return `${m}:${s.toString().padStart(2, '0')}`;
}
