import { redirect } from '@sveltejs/kit';

/** `/` has no content of its own — Track view is where a session starts. */
export function load() {
	redirect(307, '/track');
}
