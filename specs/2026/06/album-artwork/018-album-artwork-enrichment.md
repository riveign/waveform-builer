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

### External API shapes (verified live, 2026-06-07)
- **iTunes Search** — `GET https://itunes.apple.com/search?term=<artist+album>&entity=album&limit=5` (no auth). Response: `{ "resultCount", "results": [ { "artistName", "collectionName", "artworkUrl100", "collectionType":"Album", "trackCount", ... } ] }`.
  - Upscale: replace the trailing `100x100bb.jpg` in `artworkUrl100` with `600x600bb.jpg` — verified `200 image/jpeg` for a real URL. Higher sizes (`1000x1000bb`) also resolve; 600 is a safe default.
  - Filter `collectionType == "Album"` to skip non-album entities.
- **Deezer Search** — `GET https://api.deezer.com/search/album?q=<artist album>&limit=5` (no auth). Response: `{ "data": [ { "title", "artist": { "name", ... }, "cover", "cover_big" (500px), "cover_xl" (1000px), "nb_tracks" } ] }`.
  - `cover_xl` / `cover_big` are direct CDN image URLs — **no upscale step needed**. Note `artist` is a nested object → match on `artist.name`.

### Reusable codebase patterns
- **HTTP client template**: `src/kiku/musicbrainz/client.py` — `MusicBrainzClient` is the exact shape to mirror: `__init__(*, user_agent, transport: httpx.BaseTransport | None, timeout)`, an `httpx.Client(base_url=..., headers={"User-Agent": ...})`, context-manager (`__enter__/__exit__/close`), and a **process-wide throttle** via class vars `_last_request_at: float` + `threading.Lock` in `_throttle()`. iTunes/Deezer clients copy this (throttle gentler: ~3 req/s is fine, both are no-auth public).
- **Query normalizer**: `src/kiku/musicbrainz/match.py:normalize_title()` strips `(Original Mix)`/`feat.`/remix parens, lowercases, collapses whitespace. Reuse for building the search term and for scoring. Scoring helper `_score()` wraps `thefuzz.fuzz.token_set_ratio / 100.0` (graceful when `thefuzz` import missing). `thefuzz[speedup]` is already a core dep.
- **CAA fetcher**: `src/kiku/musicbrainz/cover_art.py` already implements the disk-cache + `.missing` sentinel contract used by the resolver: `cover_art_dir()`, `cached_cover_path(album_key)` (checks `jpg/png/jpeg`), `is_cover_known_missing()`, `mark_cover_missing()`, `fetch_front_cover(mb_release_id, album_key, *, transport=None)`. The new resolver generalizes this: write `data/cover_art/{album_key}.{ext}` for ANY source, not just CAA. **Gap found**: `.missing` is a bare `touch()` with no timestamp check → needs a TTL (compare `mtime` vs now) so late-added art can be retried.

### Endpoints to modify
- `src/kiku/api/routes/albums.py` `album_cover()` (~line 302) — currently inlines the cache→CAA→embedded-redirect→404 chain. Refactor to call `artwork.resolver.resolve_album_cover(db, album_key)` and record the winning source on `AlbumMetadata`.
- `src/kiku/api/routes/tracks.py` `track_artwork()` (lines 188–250) — the `500` source is the bare `except Exception: raise HTTPException(500)` at line 249–250 (covers mutagen parse errors / OS errors on present-but-odd files; missing files already 404 at line 204). Phase A makes embedded extraction a helper that **returns `bytes | None`** (never raises); Phase C adds: if no embedded art, resolve the track's album cover (look up `Track.album` → album_key → resolver) and serve/redirect that.

### Data model & migration
- `src/kiku/db/models.py:260` `AlbumMetadata` — add `cover_source = Column(String)` (`embedded|caa|itunes|deezer`) and `cover_fetched_at = Column(DateTime)`. Both nullable.
- Alembic head is `e5f6a7b8c9d0` (verified `alembic heads`). New revision sets `down_revision = "e5f6a7b8c9d0"`, `op.add_column("album_metadata", ...)` ×2 in `upgrade`, drops in `downgrade`. Additive only.

### Test patterns
- `tests/test_musicbrainz_client.py` is the template: `httpx.MockTransport(handler)` injected via the client's `transport=` kwarg; an **autouse fixture resets the throttle class var** between tests; handlers assert request URL/headers and return `httpx.Response(200, json=...)`. New tests: `tests/artwork/test_itunes.py`, `test_deezer.py`, `test_resolver.py`.
- `tests/api/test_albums_api.py` + `tests/api/conftest.py` (in-memory SQLite, `get_db` override, seeded albums) — extend with cover-endpoint cases (resolver order, soft-fail on a crafted bad file, track inheritance). The resolver must accept an injected transport / source set so API tests stay offline.

### Strategy

**Sequencing — one IMPLEMENT, three internal phases (mirror spec 015's bundling):**

**Phase A — Resolver + cache + de-500.**
1. New `src/kiku/artwork/__init__.py`, `src/kiku/artwork/resolver.py`. Resolver owns the ordered chain and the disk cache. Define a small `CoverSource` protocol: `name: str`, `fetch(artist, album, album_key) -> bytes | None`.
2. Extract embedded-art reading from `tracks.py` into `resolver.embedded_cover_bytes(track) -> bytes | None` (swallows mutagen/OS errors → `None`, the de-500 fix). `album_cover` and `track_artwork` both call the resolver.
3. Add `.missing` TTL: `is_cover_known_missing(album_key, ttl_days=30)` checks sentinel `mtime`. Keep signature back-compatible (default TTL).
4. `AlbumMetadata.cover_source/cover_fetched_at` + migration `<rev>_add_album_cover_source` (down_revision `e5f6a7b8c9d0`). Run `alembic upgrade head` against `data/dj_library.db`.

**Phase B — iTunes + Deezer clients.**
5. `src/kiku/artwork/itunes.py` (`ItunesClient`) and `deezer.py` (`DeezerClient`) — mirror `MusicBrainzClient` (injectable transport, throttle, UA). Each exposes `search_cover(artist, album) -> bytes | None`: query → pick best candidate by `token_set_ratio(normalize(artist|album), candidate) ≥ THRESHOLD` (start 80; album-only match for `Various Artists`) → download (`artworkUrl100`→`600x600bb` for iTunes; `cover_xl` for Deezer) with size cap → return bytes.
6. Wire into resolver chain after CAA: iTunes then Deezer. On success, cache to disk + set `cover_source`.

**Phase C — Track inheritance + attribution.**
7. `track_artwork`: no embedded art → resolve album cover via `Track.album`→album_key→resolver; serve bytes or 302 to `/api/albums/{key}/cover`.
8. Frontend: add `cover_source` to the album-detail DTO; `AlbumDetail.svelte` shows a quiet "art via iTunes/Deezer" line. Grid/table need no change (already use `getAlbumCoverUrl`/`getTrackArtworkUrl`).

**Testing strategy**
- **Unit** (`tests/artwork/`): URL upscaling (iTunes 100→600), Deezer cover-size pick, candidate threshold accept/reject (correct album vs wrong-artist decoy), `.missing` TTL boundary (fresh sentinel = missing, stale = retry), embedded soft-fail returns `None` on a crafted unreadable file.
- **API** (`tests/api/test_albums_api.py`): resolver order with `MockTransport` (cache miss → iTunes hit; iTunes miss → Deezer hit; both miss → 404 + sentinel written); `GET /api/tracks/{id}/artwork` inherits album cover; cover endpoint **never 500s** on a bad embedded file. Inject transports/sources so no real network in CI.
- **Coverage target**: resolver chain branches + both clients' happy/threshold-reject/network-error paths; ≥1 API test per resolution tier. Reuse the throttle-reset autouse fixture pattern.
- **Manual E2E**: real library Albums grid — blank tiles fill in; a deliberately mistitled album does NOT get a wrong cover; AlbumDetail shows source.

## Plan

> Renumbered 016 → **018** on implementation: 016 is the metadata-correction track, 017 is vibe-aware-sets. RESEARCH above is preserved verbatim (verified API facts). Built as one IMPLEMENT over the three internal phases, reusing the spec-016 `src/kiku/metadata/album_key` + `src/kiku/musicbrainz/cover_art` cache rather than duplicating.

**Architecture** — cover art is orthogonal to the textual `ReleaseCandidate`, so it lives in a parallel package `src/kiku/artwork/`, NOT inside the source `.search()` path:
- `artwork/util.py` — `download_image(url, *, transport) -> (bytes, content_type) | None` (soft-fail, UA, 8 MB cap, follow redirects).
- `artwork/match.py` — `score_candidate()` / `accept()` using `token_sort_ratio ≥ 0.85` on artist+album (album-only for Various Artists), reusing `musicbrainz.match.normalize_title`.
- `artwork/itunes.py` `ItunesClient`, `artwork/deezer.py` `DeezerClient` — mirror `MusicBrainzClient` (injectable transport + process-wide throttle); each exposes `search_cover(artist, album) -> (bytes, ct) | None`.
- `artwork/resolver.py` — `embedded_cover_bytes(path)` (the de-500 helper) + `resolve_album_cover(db, album_key, *, transport)` running the chain and recording `cover_source`.
- `cover_art.py` — added `.missing` TTL (`is_cover_known_missing(key, ttl_days=30)`, stale sentinel removed) + generic `store_cover()`.
- `albums.py` `album_cover` delegates to the resolver; `tracks.py` `track_artwork` = embedded soft-fail → album-cover inheritance, never 500.
- DB: `AlbumMetadata.cover_source` + `.cover_fetched_at`; migration `b8c9d0e1f2a3` (down_revision `a7b8c9d0e1f2`, the current head — stacks on the vibe migration which stacked on spec-016's `f6a7b8c9d0e1`).

## Test Evidence & Outputs

Implemented all three phases. Backend: **294 passed** (5 pre-existing `test_energy.py::TestNumericToZone` calibration-drift failures unrelated to artwork). Frontend `svelte-check`: 0 errors.

New tests (all offline via `httpx.MockTransport` + autouse throttle-reset, mirroring `test_musicbrainz_client.py`):
- `tests/artwork/test_itunes.py` — match/upscale (100→600), wrong-artist reject, VA album-only match, empty/network soft-fail.
- `tests/artwork/test_deezer.py` — `cover_xl`>`cover_big`>`cover` preference, nested `artist.name` match, threshold reject, network soft-fail.
- `tests/artwork/test_resolver.py` — chain order (iTunes hit → records source; iTunes miss → Deezer; CAA-before-external when mb known; all-miss → `.missing` sentinel; cache-hit short-circuits network), embedded soft-fail on a corrupt/absent file, `.missing` TTL boundary (fresh=missing, 31d-old=retry+cleared).
- `tests/api/test_album_cover_api.py` — track inherits album cover via mocked iTunes; **`track_artwork` returns 404 (never 500) on a corrupt file**; album cover records `cover_source` and the album-tracks DTO surfaces it.
- Updated `tests/api/test_albums_api.py`: the old 302-redirect and CAA-monkeypatch cover tests rewritten for the resolver contract (serves bytes directly; patch `kiku.artwork.resolver.fetch_front_cover`).

## Updated Doc
- Memory topic `album-cover-art` added; MEMORY.md index updated.

## Post-Implement Review
<!-- Filled by /spec REVIEW -->
