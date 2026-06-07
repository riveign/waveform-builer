# Human Section
Critical: any text/subsection here cannot be modified by AI.

## High-Level Objective (HLO)
Give the DJ a repeatable way to **check and correct library metadata against external sources** — the exact thing we did by hand for the Hadone *"Bite The Hand That Feeds You"* album, where master-file names had leaked the vinyl side-position into the `artist` field (`A1 hadone`) and a mastering tag into the `title` (`..._MASTER_24_CharlesAccarisi`), with `album`/`label`/`year`/`track_number` all empty.

The DJ should be able to point the tool at a release — by pasting a Bandcamp URL, by an album already grouped in the browser, or by a free query — pick the source, **see a clear before→after diff**, and apply only what they confirm. This serves **"Opinions You Can See Through"** (every proposed change is visible and arguable before it's written) and **"Your Library Is the Lesson"** (the DJ's own collection, corrected, stays the reference).

## Mid-Level Objectives (MLO)
- Support **four sources**: Bandcamp (pasted album URL), MusicBrainz (existing), Discogs (API, optional token), and embedded file tags (on-disk WAV/AIFF/MP3).
- Correct the **full identity**: `title`, `artist`, `album`, `label`, `release_year`, `track_number`, `disc_number` — never a blind overwrite, always preview + confirm.
- Surface in **two places**: a `kiku fix-album` CLI command (fast / scriptable / batch) and the existing **album browser UI** (source picker + full-field diff in the match modal).
- Handle the **ungrouped case**: when `album` is empty/garbled (like Hadone), a pasted Bandcamp URL discovers the member tracks by fuzzy-matching titles across the library, not by relying on an existing album grouping.

## Constraints
- Never write a field unless the new value differs and is non-empty; preview shows old→new per field per track.
- Reuse the existing `match_tracklist` fuzzy aligner and `album_key` identity; do not duplicate them.
- Discogs requires a user token in `~/.kiku/config.toml`; degrade gracefully (source hidden / clear CLI error) when absent.
- Respect source etiquette: MusicBrainz 1 req/s (existing client), Bandcamp/Discogs reasonable timeouts + User-Agent.
- Tests must cover each source parser against a captured fixture (no live network in tests).

---

# AI Section

## RESEARCH

### Existing foundation (reusable)
- `src/kiku/musicbrainz/client.py` — throttled MB HTTP client (`search_releases`, `get_release`). Keep, wrap as one source.
- `src/kiku/musicbrainz/match.py` — `normalize_title()` + `match_tracklist()` greedy bipartite title aligner. **Already source-agnostic** — takes `[{"id","title"}]` + `[{"position","disc","title",...}]`. Reuse verbatim.
- `src/kiku/api/routes/albums.py` — `_album_key()`, `_find_album_by_key()`, `match_musicbrainz`, `apply_mb_mapping`. The apply endpoint writes **only** `track_number`/`disc_number` — this is the core gap.
- `src/kiku/db/models.py::AlbumMetadata` — per-album cache (`mb_release_id`, `match_status`). Extend with `source` + `source_ref` (generic, not MB-specific).
- `src/kiku/config.py` — TOML config pattern (`_get`, `save_config_value`). Add `[discogs] token`.
- Deps already installed: `mutagen` (tags), `thefuzz` (match), `httpx` (http), `bs4` (bandcamp scrape).
- CLI: Click group in `src/kiku/cli.py`; commands use `rich` Console/Table, `get_session()`, `--dry-run`/`--yes` convention.

### Source lookup modes (differ per source)
- **Bandcamp**: URL only. The album JSON is embedded in the page as `data-tralbum` (current/trackinfo) and `application/ld+json`. Yields album, artist, tracklist (title + duration), and `og:` fields. No track positions on Bandcamp digital → derive position from listing order.
- **MusicBrainz**: query by `album`+`artist`. Structured positions/discs. Existing.
- **Discogs**: query by `album`+`artist` or release id; `https://api.discogs.com/`, token via header. Strong on vinyl `position` strings (`A1`,`B2`,`Digi 1`).
- **Embedded tags**: read the album's own files via `mutagen` — no query, source of truth independent of Rekordbox sync.

### The Hadone scenario (the acceptance case)
`album` empty, `artist` = `A1 hadone`/`B1. Hadone`/`Digi 1. hadone`, `title` carries `_MASTER_24_CharlesAccarisi`. → Browser grouping fails; MB search fails. **Only the Bandcamp-URL-then-fuzzy-discover path recovers this.** Side positions (`A1..B2`, `Digi 1..3`) map to track numbers 1–8.

## PLAN

### Phase A — Source abstraction (`src/kiku/metadata/`)
- `models.py`: `RecordingCandidate(position, disc, title, artist, length_ms)`, `ReleaseCandidate(source, source_id, url, album, artist, label, year, recordings[])`.
- `sources/base.py`: `MetadataSource` protocol — `name`, `search(album, artist) -> list[ReleaseCandidate]`, `fetch_url(url) -> ReleaseCandidate | None`, `available() -> bool`.
- `sources/musicbrainz.py`: wrap existing client (move the recording-extraction logic out of the route).
- `sources/bandcamp.py`: `httpx` GET + `bs4`/regex extract `data-tralbum` + `ld+json`; positions from order.
- `sources/discogs.py`: `httpx` to Discogs API with token from config; `available()` false when no token.
- `sources/tags.py`: `mutagen` read from a set of file paths; one `ReleaseCandidate` from common album fields.
- `sources/__init__.py`: `SOURCE_REGISTRY`, `get_source(name)`, `available_sources()`.

### Phase B — Correction engine (`src/kiku/metadata/correct.py`)
- `build_correction(db_tracks, candidate) -> list[TrackCorrection]`: align via `match_tracklist`, produce per-track `{track_id, field: {old, new}}` for title/artist/album/label/year/track_number/disc_number + `confidence`.
- `discover_tracks_for_release(session, candidate, like=None) -> list[Track]`: fuzzy-match candidate recordings against library titles to recover ungrouped albums (Hadone path).
- `apply_correction(session, corrections, fields) -> int`: write only selected, only where new≠old and new non-empty; update/insert `AlbumMetadata` with `source`+`source_ref`.

### Phase C — API (extend `albums.py`)
- `GET /api/albums/{album_key}/sources` → available sources.
- `POST /api/albums/{album_key}/match` `?source=` body `{url?, query?}` → candidates with full-field per-track diff preview (new schema `MetadataMatchResponse`, supersedes MB-specific preview; MB route delegates).
- `POST /api/albums/{album_key}/apply` body `{source, source_ref, fields[], mappings[{track_id, title?, artist?, album?, label?, year?, track_number?, disc_number?}]}` → writes via `apply_correction`.
- Keep old MB endpoints working (delegate to new engine) so the current UI doesn't break mid-migration.

### Phase D — CLI (`kiku fix-album`)
- `kiku fix-album [QUERY] --url URL --source {bandcamp,musicbrainz,discogs,tags} --album-key KEY --like PATH_GLOB --candidate N --fields ... --dry-run --yes`
- Target resolution: `--album-key` | `--url` (discover by fuzzy title, optional `--like` scope) | `QUERY`+`--artist`.
- Render rich diff table (old→new, confidence-colored), confirm unless `--yes`.

### Phase E — Frontend (album browser)
- Extend the MusicBrainz match modal into a generic "Fix metadata" flow: source dropdown (Bandcamp URL input / MB+Discogs search / Tags), full-field diff table with per-field checkboxes, Apply selected.
- Add a "Fix metadata" affordance reachable from `AlbumDetail`.

### Phase F — Tests
- Per-source parser tests against captured fixtures (Bandcamp HTML, Discogs JSON, MB JSON, a tagged sample file).
- `build_correction` diff correctness; `apply_correction` writes only confirmed fields; `discover_tracks_for_release` recovers the Hadone-shaped case.

### Migration
- Alembic: add `source`, `source_ref` to `album_metadata` (nullable; backfill `source='musicbrainz'` where `mb_release_id` set).

## OUTCOME (implemented)

Delivered all six phases; 36 tests pass (4 API + 19 engine/source unit + 13 existing album tests still green).

- **Engine** `src/kiku/metadata/`: `ReleaseCandidate`/`RecordingCandidate`/`TrackCorrection` models; `sources/` with bandcamp (URL scrape of `data-tralbum`+`ld+json`), musicbrainz (wraps existing client), discogs (API + token), tags (mutagen); `correct.py` (`build_correction`, `discover_tracks_for_release`, `apply_correction`); `service.py` orchestration; `album_key.py` shared with the API route (de-duplicated).
- **Discovery precision fix**: switched from `token_set_ratio` (rewards subset titles → "You" matched "Bite the Hand That Feeds You") to `token_sort_ratio` at a 0.85 threshold.
- **CLI** `kiku fix-album`: `--url` / `--album-key` / query, source auto-inferred from URL, rich before→after diff, `--dry-run`/`--yes`. Validated live on the real Hadone Bandcamp release (discovered the 5 vinyl tracks, filled the `disc_number` the manual fix had missed).
- **API**: `GET /api/albums/sources`, `POST /{album_key}/match-source`, `POST /{album_key}/apply-correction` (writes only confirmed, non-empty, changed fields scoped to the album; records provenance).
- **UI**: `FixMetadataModal.svelte` (source picker → diff with per-field toggles → apply) wired into `AlbumDetail` next to the MusicBrainz button. `svelte-check`: 0 errors.
- **Migration** `f6a7b8c9d0e1`: `source`+`source_ref` on `album_metadata`, applied.

### Notes / follow-ups
- Spec **number collision**: another concurrent branch (`vibe-aware-sets`) used `016` for "album-artwork-enrichment" and `017` for vibe work; this spec is also numbered 016. Orchestrator should renumber on merge to keep history clean.
- Discogs source is code-complete but inert until a token is set: `kiku config set discogs.token <TOKEN>`.
- `tags` source depends on the files being reachable at their stored `file_path` (external drive mounted).
