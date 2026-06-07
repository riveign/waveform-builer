# Human Section
Critical: any text/subsection here cannot be modified by AI.

## High-Level Objective (HLO)
Make the DJ's library *look* like the collection it is. Today most albums show a blank `♪` tile because the only automatic cover source is embedded tags — and Cover Art Archive only fires after a manual per-album MusicBrainz match. Add an on-demand, multi-source artwork resolver (embedded → iTunes → Deezer) with disk caching, so the Albums grid and the Tracks table fill in covers automatically as the DJ browses. Never show a *wrong* cover, and always let the DJ see where a cover came from. This serves "Your Library Is the Lesson" (rediscover what you own as releases) and "Opinions You Can See Through" (the art's source is visible, never silently faked).

## Mid-Level Objectives (MLO)

### Phase A — Unified resolution chain + caching (no more 500s)
- CREATE a single cover resolver that tries sources in order and **never raises to the client**: disk cache → embedded tags → CAA (only if `mb_release_id` already cached) → iTunes → Deezer → `.missing` sentinel.
- MAKE embedded extraction a soft-fail: unreadable/odd files return "no embedded art" and fall through to the next source instead of `500` (current `tracks.py:250` bare `except → 500`).
- CACHE every resolved image on disk keyed by `album_key` (reuse `data/cover_art/`), with a `.missing` sentinel carrying a retry TTL so a transient miss isn't permanent.
- RECORD the winning source on `album_metadata` (`cover_source`, `cover_fetched_at`) so the UI can attribute it and a future backfill can audit coverage.

### Phase B — External art clients (iTunes + Deezer)
- IMPLEMENT `src/kiku/artwork/itunes.py` — Apple Search API (`/search?entity=album&term=<artist album>&limit=5`), no auth, pick the best candidate, upscale the `artworkUrl100` to ≥600px.
- IMPLEMENT `src/kiku/artwork/deezer.py` — Deezer `/search/album?q=<artist album>`, no auth, use `cover_xl`/`cover_big`.
- MATCH candidates with `thefuzz.token_set_ratio` on `(artist, album)` against our values; only accept above a confidence threshold so we never attach a wrong cover. iTunes tried first, Deezer as the next fallback.
- BE polite: per-source timeout, `User-Agent`, response size cap, and a light client-side throttle; aggressive caching + `.missing` keeps request volume near-zero on repeat views.

### Phase C — Track-level inheritance + UI attribution
- UPDATE `GET /api/tracks/{id}/artwork` to fall back to the track's **album cover** (via the resolver) when the file has no embedded art — so the Tracks table and Now Playing bar show covers too.
- SURFACE the cover source in `AlbumDetail.svelte` as a quiet attribution (e.g. "art via iTunes") — *Opinions You Can See Through*.
- KEEP the grid/table graceful: a still-missing cover shows the existing `♪` placeholder, never a broken image or spinner-forever.

## Details (DT)

### Scope & non-goals
- **On-demand only** this round — covers resolve lazily on first request and cache. No bulk `kiku artwork backfill` command yet (explicit follow-up if coverage gaps remain).
- Sources: **iTunes + Deezer** (plus existing embedded + CAA-when-matched). No Last.fm / fanart.tv this round.
- Artwork is *presentation*, not a library write — fetching needs no DJ confirmation (unlike MusicBrainz track-number writes, which stay user-confirmed). The guardrail against bad UX is the **fuzzy-match confidence threshold**, not a confirmation dialog.

### Album identity & cache
- Reuse `album_key` (sha256 of normalized album+artist, 12 chars) and the existing `data/cover_art/{album_key}.{ext}` cache + `is_cover_known_missing()` sentinel (`src/kiku/musicbrainz/cover_art.py`).
- `.missing` gains a TTL: treat as missing only if the sentinel is younger than N days (e.g. 30), so newly-released/late-added art can be re-tried.
- `album_metadata` adds nullable `cover_source` (`embedded|caa|itunes|deezer`), `cover_fetched_at` (DateTime). Additive migration only.

### Resolution order (must never 500)
1. On-disk cache hit → serve.
2. Embedded artwork of the album's cover track (soft-fail, never raises).
3. CAA — only if `album_metadata.mb_release_id` is already set (no new MB lookup here).
4. iTunes Search API → best candidate ≥ threshold.
5. Deezer search → best candidate ≥ threshold.
6. Write `.missing` sentinel, return 404 (frontend hides the `<img>`).

### Candidate matching
- Query term: `"{artist} {album}"`, stripped of `(Original Mix)` / `feat.` noise (reuse the normalizer from `src/kiku/musicbrainz/match.py`).
- Score = `thefuzz.token_set_ratio` on artist AND album; require both ≥ threshold (start at 80, tune against real misses). Compilations (`Various Artists`) match on album title only.
- Pick highest-scoring candidate; on tie prefer the larger image.

### External API constraints
- **iTunes**: `https://itunes.apple.com/search` — no key; unofficial ~20 req/min. Upscale `artworkUrl100` → replace `100x100` with `600x600`.
- **Deezer**: `https://api.deezer.com/search/album` — no key; ~50 req/5s. Use `cover_xl` (1000px) / `cover_big`.
- Shared: 10–20s timeout, `User-Agent: Kiku/<version> ( riveign@gmail.com )`, 8 MB size cap, follow redirects. Inject `httpx` transport for tests.

### Files (likely touched)
- Backend:
  - `src/kiku/artwork/__init__.py` — new package
  - `src/kiku/artwork/resolver.py` — ordered resolution chain + cache/sentinel logic
  - `src/kiku/artwork/itunes.py`, `src/kiku/artwork/deezer.py` — new clients
  - `src/kiku/musicbrainz/cover_art.py` — keep CAA fetch; resolver calls it (or move under `artwork/`)
  - `src/kiku/api/routes/albums.py` — `album_cover` delegates to resolver, records source
  - `src/kiku/api/routes/tracks.py` — `track_artwork` soft-fail + album-cover inheritance
  - `src/kiku/db/models.py` — `AlbumMetadata.cover_source`, `.cover_fetched_at`
  - `alembic/versions/<new>_add_album_cover_source.py`
- Frontend:
  - `frontend/src/lib/components/library/AlbumDetail.svelte` — cover-source attribution
  - `frontend/src/lib/api/albums.ts` — expose `cover_source` if returned in detail DTO
  - (Tracks table / Now Playing already use `getTrackArtworkUrl` — inheritance is server-side, no client change expected)
- Tests:
  - `tests/artwork/test_resolver.py` — chain order, soft-fail embedded, cache hit, `.missing` TTL
  - `tests/artwork/test_itunes.py`, `tests/artwork/test_deezer.py` — `httpx.MockTransport`, candidate ranking, upscaling, threshold rejection
  - `tests/api/test_albums_api.py` — extend: cover endpoint serves resolver result; never 500s on bad file

### Testing
- **Unit**: candidate scoring buckets (accept ≥80 / reject below); iTunes URL upscaling; Deezer cover-size selection; `.missing` TTL boundary; embedded soft-fail returns None not raise.
- **Integration**: `GET /api/albums/{key}/cover` serves cache → embedded → iTunes (mocked) → Deezer (mocked) → 404 in order; a deliberately-corrupt embedded file falls through instead of 500; `GET /api/tracks/{id}/artwork` inherits album cover when no embedded art.
- **Manual E2E**: open Albums grid on the real library, confirm previously-blank tiles fill in; confirm a wrong-artist album does NOT get a mismatched cover; confirm source attribution shows in AlbumDetail.

### Constraints
- Cover resolution must NEVER return 500 — every failure path falls through to the next source or a clean 404.
- Additive migration only; no destructive column changes.
- No bulk network sweeps — strictly on-demand + cached; `.missing` prevents repeat hits.
- Never attach a cover below the confidence threshold (no wrong art).
- Honor branding voice: attribution reads "art via iTunes/Deezer"; no "smart"/"powerful"; a missing cover message (if any) follows the error format (what/why/what-to-try) and never blames the DJ.

## Behavior
Implement Phase A → B → C, each independently shippable. Phase A alone kills the 500s and centralizes resolution; B adds the high-coverage sources; C spreads covers to track rows and surfaces provenance. Artwork is presentation, so external fetches are silent-by-design — but the confidence threshold is non-negotiable (a wrong cover is worse than none), and the source is always visible in detail view so the DJ can see and distrust it (*Opinions You Can See Through*). Caching + `.missing` sentinels keep the experience fast and the APIs unbothered.

# AI Section
Critical: AI can ONLY modify this section.

## Research
<!-- Filled by /spec RESEARCH -->

## Plan
<!-- Filled by /spec PLAN -->

## Test Evidence & Outputs
<!-- Filled by /spec IMPLEMENT -->

## Updated Doc
<!-- Filled by explicit documentation updates after /spec IMPLEMENT -->

## Post-Implement Review
<!-- Filled by /spec REVIEW -->
