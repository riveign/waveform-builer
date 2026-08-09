---
id: OBS-005
title: Frontend data layer — transport is clean, orchestration is hand-rolled per component
type: OBS
date: 2026-08-09
depends-on: []
superseded-by: null
---

## C — Context

How data gets from the 86 backend endpoints into 92 components, and what each component
has to do for itself along the way.

> **Re-check 2026-08-09 — [[PLN-001]]/P5 part 1.** `createResource` exists and the 8 DNA
> components are on it; 18 remain, so K1 and K2 still stand. **K3 needs amending:** (a) and
> (c) are now structurally preventable, but **(b) is not** — de-duplication merges only
> concurrent requests, and the common case is sequential. See `PLN-001`/P5.

## D — Definitions

- **D1 · Transport.** Turning a call into an HTTP request and a typed result.
- **D2 · Orchestration.** Everything around the transport: when to fire, loading state,
  error state, cancellation on unmount, deduplication, caching, invalidation after writes.

## E — Evidence

- **E1 · Transport is fully centralised and clean.** All network access goes through
  `lib/api/{albums,client,config,hunt,sets,soundcloud,stats,tinder,tracks,waveforms}.ts`.
  **Zero** raw `fetch(` calls exist in any `.svelte` file
  (`grep -rn 'fetch(' src/lib/components --include='*.svelte'` → 0).
- **E2 · `client.ts` is 12 lines.** One `fetchJson<T>` helper: prefix the base URL, throw
  `API ${status}: ${body}` on non-2xx, `res.json()` otherwise.
- **E3 · Orchestration is per-component.** 44 of 92 components import `$lib/api` directly.
  26 components declare their own load-state variables — 23 a `let loading = $state(…)`,
  18 a `let error = $state(…)`, i.e. **only 15 declare both**, so the handling is not just
  duplicated but inconsistent. 37 components drive fetches from a `$effect`.
- **E4 · Types are shared and substantial.** `lib/types/index.ts` is 699 LOC of hand-written
  interfaces mirroring the backend's 976-LOC `api/schemas.py`. They are maintained by hand;
  nothing generates one from the other.
- **E5 · Caching exists in exactly one place.** `lib/api/waveforms.ts:6` holds a
  module-level `Map<number, WaveformData>` peaks cache with a hover prefetch. No other
  endpoint is cached.
- **E6 · No cancellation anywhere.** `AbortController` appears zero times in `lib/api` and
  `lib/stores`. An in-flight search whose component unmounts still resolves and writes.
- **E7 · Stores are thin and inconsistent in role.** Seven `*.svelte.ts` stores. Two are
  substantial state machines (`playback` 465 LOC, `player` 371 LOC). `tracks.svelte.ts` is
  40 LOC and is the *only* store that owns the load/error/data triple for a resource. The
  other 43 API-calling components do that work inline.
- **E8 · No list virtualization.** No virtual-list implementation and no
  `IntersectionObserver` anywhere in `src/lib`. Long lists render every row.
- **E9 · Server-side pagination does exist.** `searchTracks` sends `limit`/`offset` and the
  API returns `PaginatedTracks { items, total }`, so the wire is paged even though the DOM
  is not virtualized.

## K — Conclusions

- **K1 · The layering is correct; the abstraction stops one level too early.** E1/E2 are
  genuinely good — cleaner than most apps this size. But `lib/api` solves D1 only. D2 is
  re-implemented, slightly differently, 44 times.
- **K2 · The cost is concentrated in the largest files.** `TrackView.svelte` (1,246 LOC)
  imports four API modules; `TrackCard.svelte` is 1,119 LOC. `OBS-001/K3`'s ten oversized
  files are large *substantially because* each one carries its own copy of D2.
- **K3 · Three classes of bug are currently unpreventable, not merely unfixed.**
  (a) stale-response races — E6 means the slower of two searches wins;
  (b) redundant refetches — E5 means the same track is re-fetched on every remount;
  (c) stale reads after writes — with no invalidation, a mutation in one component leaves
  another component's copy wrong until something happens to re-render it.
- **K4 · E4 is a silent-drift surface.** 699 LOC of client types mirroring 976 LOC of
  server schemas, with no generator and no CI check (`OBS-002/K1`), means a backend field
  rename is caught only when a human notices wrong data in the browser. FastAPI already
  serves an OpenAPI schema, so the generator input exists and is unused.
- **K5 · E8 is latent, not yet acute.** Against a ~4,300-track library, paged server-side
  (E9), full-DOM rendering is survivable. It becomes acute the moment any view drops
  paging or the library grows several-fold.

## Q — Open

- **Q1.** Is a full query-cache library warranted, or does a ~100-LOC first-party
  `createResource` rune covering load/error/abort/invalidate cover E3/E5/E6 at a fraction
  of the dependency cost? See [[PLN-001]] item 3.
