# Human Section
Critical: any text/subsection here cannot be modified by AI.

## High-Level Objective (HLO)

Build a "Track Hunter" feature that extracts tracklists from published DJ sets (SoundCloud, YouTube, Mixcloud, etc.) by parsing copyright metadata, descriptions, and user comments — then deploys agents to locate purchase/download sources for each identified track (and the original if it's a remix). The goal is to turn set inspiration into library acquisition: hear a set you love, hunt down every track in it.

## Mid-Level Objectives (MLO)

- **EXTRACT** tracklists from DJ set URLs by parsing:
  - Copyright/license metadata (SoundCloud, YouTube Content ID)
  - Set descriptions (artist-curated tracklists)
  - User comments (crowd-sourced track IDs, timestamps + track names)
  - Shazam/AudD-style audio fingerprinting as fallback (stretch goal)
- **NORMALIZE** extracted track data: resolve artist aliases, strip remix suffixes to find originals, deduplicate across sources, match against existing library
- **HUNT** for acquisition sources using agents that search:
  - Beatport, Juno Download, Bandcamp, Traxsource (purchase)
  - SoundCloud (free downloads, buy links)
  - Artist/label direct stores
  - Flag tracks already owned in the DJ's library
- **PRESENT** hunt results in the UI:
  - Tracklist view with match confidence per track
  - Source links with price/format info where available
  - "Already in your library" badges for owned tracks
  - Gap analysis: "You're missing 4 of 12 tracks from this set"
- **STORE** hunt sessions persistently so DJs can revisit and track acquisition progress
- **TEACH** — align with Kiku's "Show the Why" principle: explain what makes this set's track selection interesting (genre flow, energy arc, key progression) so the DJ learns from the curator, not just copies them

## Details (DT)

### Data Sources & Parsing Strategy

- **SoundCloud**: API for track metadata, description field often has tracklist, comments have timestamps + "ID?" requests and answers
- **YouTube**: Description field tracklists, Content ID copyright claims in video details, comments
- **Mixcloud**: Native tracklist support (API provides it directly)
- **1001Tracklists**: Scraping as gold-standard reference (many sets already catalogued)

### Normalization Challenges

- Artist names vary: "Bicep" vs "BICEP" vs "Bicep (IE)"
- Remix attribution: "Track Name (Artist Remix)" → need both remix AND original
- Bootlegs/edits: may not have official releases — flag as "unreleased/edit"
- Multiple versions: Original Mix, Extended Mix, Radio Edit — prefer Extended for DJing

### Agent Architecture

- Each hunt spawns a "hunt session" stored in DB
- Agents work asynchronously: submit URL → get results as they resolve
- Rate limiting and caching for external API calls
- Results ranked by confidence: exact match > fuzzy match > possible match

### Integration with Existing Kiku

- Matched tracks link to existing library entries (by artist+title fuzzy match)
- Unowned tracks can be added to a "want list" / shopping list
- Hunt results can seed a new set (import the tracklist order as a set template)

### Technical Constraints

- External APIs may require keys (Beatport, SoundCloud) — config-based
- Respect rate limits and terms of service
- Audio fingerprinting (AudD/Shazam) is a stretch goal — start with text parsing
- CLI: `kiku hunt <url>` to start a hunt session
- API: `POST /api/hunt` with URL, `GET /api/hunt/{id}` for results

### Testing

- Unit tests for tracklist parsers (description, comments, copyright)
- Unit tests for artist/title normalization
- Integration tests with mocked API responses (SoundCloud, YouTube)
- E2E: submit a known set URL → verify extracted tracklist matches expected

## Behavior

You are building a feature that embodies Kiku's craft mentorship philosophy. The hunter isn't just a scraper — it's a tool that helps DJs understand WHY a set works by breaking it down into its components. When presenting results, always show the set's arc (energy flow, genre progression) alongside the tracklist. Frame it as "learning from the greats" not "copying playlists."

# AI Section
Critical: AI can ONLY modify this section.

## Research

### Codebase Analysis

**Existing patterns to follow:**

- **DB Models** (`src/kiku/db/models.py`): Track, Set, SetTrack, TransitionCue, AudioFeatures. New models (HuntSession, HuntTrack) follow same SQLAlchemy Base pattern.
- **API Routes** (`src/kiku/api/routes/`): FastAPI routers with `Depends(get_db)`, Pydantic schemas in `schemas.py`. SSE pattern exists for long-running ops (set building). Hunt will use SSE for progressive results.
- **CLI** (`src/kiku/cli.py`): Click commands, Rich console output. `kiku hunt <url>` follows existing patterns.
- **Config** (`src/kiku/config.py`): TOML-based at `~/.kiku/config.toml`. API keys for YouTube, Discogs go here.
- **Parsing** (`src/kiku/parsing/directory.py`): Regex-based tag extraction. New `src/kiku/parsing/tracklist.py` for description/comment parsing.
- **Tests** (`tests/api/conftest.py`): In-memory SQLite with seed data, TestClient with overridden deps. Hunt tests follow same pattern with mocked external calls.
- **Frontend**: Svelte 5 runes, `fetchJson()` client, stores in `*.svelte.ts`. New `hunting` tab + store.

**Key integration points:**

- `search_tracks()` in `store.py` for matching extracted tracks against local library (artist+title fuzzy match)
- `Track.artist`, `Track.title` fields for library matching
- `src/kiku/api/main.py` `create_app()` to register hunt router
- `frontend/src/lib/types/index.ts` for new TypeScript interfaces

### External API Research

| Source | Access | Auth | Best For | Priority |
|--------|--------|------|----------|----------|
| **yt-dlp** | Free | None | Extract descriptions/chapters/comments from SC+YT+MC | **P0** |
| **1001Tracklists** | Scraping | None | Pre-built tracklists with purchase links | **P0** |
| **YouTube Data API v3** | Free, 10K units/day | API key | Structured comments (supplement yt-dlp) | **P1** |
| **MusicBrainz** | Free, 1 req/sec | User-Agent header | Artist alias resolution, recording lookup | **P1** |
| **Discogs** | Free, 60 req/min | API key+secret | Release/label ID, electronic music catalog | **P1** |
| **Mixcloud API** | Free | None | Mix metadata (tracklists restricted by licensing) | **P2** |
| **Beatport/Traxsource/Bandcamp/Juno** | No public API | N/A | Search URL generation only | **P3** |

**Key findings:**

1. **yt-dlp is the foundation.** No API keys needed. Extracts description, chapters, comments from SoundCloud, YouTube, and Mixcloud URLs via `yt_dlp.YoutubeDL({"skip_download": True, "getcomments": True})`. Python library: `pip install yt-dlp`.

2. **1001Tracklists is the gold mine.** No official API — scraping required. Has crowd-sourced tracklists for thousands of sets with purchase links already attached. Python scrapers exist (`leandertolksdorf/1001-tracklists-api`). Anti-bot protections require rate limiting + user-agent rotation.

3. **YouTube Content ID claims are NOT accessible** via public API. The Content ID API requires YouTube Partner status. However, YouTube's auto-generated "Music in this video" text appears in descriptions — parseable.

4. **SoundCloud API is effectively closed** to new developers. yt-dlp handles extraction by emulating browser requests with a scraped client_id.

5. **Mixcloud** exposes partial tracklists (timestamps restricted by licensing). REST API: replace `mixcloud.com/` with `api.mixcloud.com/`.

6. **MusicBrainz** (`musicbrainzngs` library) is best for resolving artist aliases and finding original versions of remixes. Free, 1 req/sec rate limit handled by library.

7. **Discogs** (`python3-discogs-client`) has outstanding electronic music coverage. 60 req/min authenticated. Ideal for label/release identification.

8. **Purchase stores** (Beatport, Traxsource, Bandcamp, Juno) — no practical APIs available. **Generate search URLs instead** — zero dependencies, always works:
   - Beatport: `https://www.beatport.com/search?q={artist}+{title}`
   - Traxsource: `https://www.traxsource.com/search?term={query}`
   - Bandcamp: `https://bandcamp.com/search?q={query}`
   - Juno: `https://www.junodownload.com/search/?q%5Ball%5D%5B%5D={query}`

### Dependencies Required

```
yt-dlp           # URL metadata extraction (SC, YT, MC)
musicbrainzngs   # Artist/recording resolution
beautifulsoup4   # 1001Tracklists scraping
thefuzz          # Fuzzy string matching (artist+title)
```

Optional (P1+):
```
python3-discogs-client   # Discogs catalog (needs API key)
google-api-python-client # YouTube Data API (needs API key)
```

### Strategy

**Phase 1 — Extract (P0):**
- New module `src/kiku/hunting/` with:
  - `extractor.py` — URL router: detect platform (SC/YT/MC/1001TL), dispatch to platform-specific extractor
  - `parsers/youtube.py` — Parse description tracklists (timestamp + "Artist - Title" patterns)
  - `parsers/soundcloud.py` — Parse description + comments for track IDs
  - `parsers/tracklist_1001.py` — Scrape 1001Tracklists search results
  - `parsers/common.py` — Shared regex patterns for "Artist - Title", timestamp extraction, remix detection
- New DB models: `HuntSession` (url, platform, status, created_at) and `HuntTrack` (session_id, position, raw_text, artist, title, remix_info, confidence, matched_track_id, acquisition_status)
- CLI: `kiku hunt <url>` — runs extraction + matching
- API: `POST /api/hunt` (SSE for progressive results), `GET /api/hunt/{id}`, `GET /api/hunts`

**Phase 2 — Normalize & Match (P1):**
- `resolver.py` — Normalize artist names (case, aliases via MusicBrainz), strip remix suffixes to find originals
- Library matching: fuzzy match extracted tracks against `Track.artist` + `Track.title` using `thefuzz`
- Mark tracks as `owned`, `unowned`, or `partial_match`

**Phase 3 — Hunt Sources (P1):**
- `sources.py` — Generate purchase search URLs for unowned tracks (Beatport, Traxsource, Bandcamp, Juno)
- Optional Discogs integration for label/release context
- "Want list" persistence in DB

**Phase 4 — Teach (P2):**
- Analyze extracted tracklist for energy arc, genre flow, key progression (using Kiku's existing scoring)
- Present "what makes this set work" alongside the tracklist

**Frontend:**
- New tab "Hunt" (key 5) with URL input
- HuntResults.svelte: tracklist table with confidence, owned badges, source links
- HuntHistory.svelte: past hunt sessions
- Store: `hunting.svelte.ts`

**Testing strategy:**
- Unit tests for each parser (canned descriptions/comments → expected tracklist)
- Unit tests for artist/title normalization and fuzzy matching
- Integration tests with mocked yt-dlp output and 1001TL HTML
- API tests following existing `conftest.py` pattern with seeded hunt data
- E2E: submit URL → verify extracted tracklist in UI

## Plan
<!-- Filled by /spec PLAN -->

## Plan Review
<!-- Filled if required to validate plan -->

## Implement
<!-- Filled by /spec IMPLEMENT -->

## Test Evidence & Outputs
<!-- Filled by explicit testing after /spec IMPLEMENT -->

## Updated Doc
<!-- Filled by explicit documentation updates after /spec IMPLEMENT -->

## Post-Implement Review
<!-- Filled by /spec REVIEW -->
