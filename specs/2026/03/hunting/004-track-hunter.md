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

### Files

- `pyproject.toml`
  - Add `hunting` optional dependency group (yt-dlp, beautifulsoup4, thefuzz, musicbrainzngs)
- `src/kiku/db/models.py`
  - Add `HuntSession` and `HuntTrack` models
- `src/kiku/hunting/__init__.py`
  - Empty init
- `src/kiku/hunting/parsers/__init__.py`
  - Empty init
- `src/kiku/hunting/parsers/common.py`
  - Shared regex patterns for "Artist - Title", timestamps, remix detection
- `src/kiku/hunting/extractor.py`
  - URL platform detection, yt-dlp metadata extraction, 1001Tracklists search
- `src/kiku/hunting/parsers/tracklist.py`
  - Parse descriptions, comments, chapters into structured tracklist
- `src/kiku/hunting/matcher.py`
  - Fuzzy match extracted tracks against local library
- `src/kiku/hunting/sources.py`
  - Generate purchase search URLs for Beatport, Traxsource, Bandcamp, Juno
- `src/kiku/db/store.py`
  - Add hunt CRUD functions: create_hunt_session, get_hunt_session, list_hunt_sessions, update_hunt_track
- `src/kiku/api/schemas.py`
  - Add Hunt request/response models
- `src/kiku/api/routes/hunt.py`
  - New router: POST /api/hunt, GET /api/hunt/{id}, GET /api/hunts
- `src/kiku/api/main.py`
  - Register hunt router
- `src/kiku/cli.py`
  - Add `kiku hunt <url>` command
- `frontend/src/lib/types/index.ts`
  - Add Hunt TypeScript interfaces
- `frontend/src/lib/api/hunt.ts`
  - Hunt API client functions
- `frontend/src/lib/stores/hunting.svelte.ts`
  - Hunt store with Svelte 5 runes
- `frontend/src/lib/stores/ui.svelte.ts`
  - Add 'hunt' to Tab type
- `frontend/src/lib/components/Workspace.svelte`
  - Add Hunt tab (key 5)
- `frontend/src/lib/components/hunt/HuntView.svelte`
  - Main hunt component with URL input and results display
- `frontend/src/lib/components/hunt/HuntResults.svelte`
  - Tracklist table with confidence, owned badges, source links
- `frontend/src/lib/components/hunt/HuntHistory.svelte`
  - Past hunt sessions list
- `tests/api/conftest.py`
  - Add HuntSession + HuntTrack seed data
- `tests/api/test_hunt_api.py`
  - Hunt API endpoint tests
- `tests/test_tracklist_parser.py`
  - Unit tests for description/comment parsing
- `tests/test_matcher.py`
  - Unit tests for fuzzy library matching

### Tasks

#### Task 1 — pyproject.toml: add hunting dependency group

Tools: editor
Diff:
````diff
--- a/pyproject.toml
+++ b/pyproject.toml
@@ [project.optional-dependencies]
 api = [
     "fastapi>=0.115",
     "uvicorn[standard]>=0.30",
 ]
+hunting = [
+    "yt-dlp>=2024.0",
+    "beautifulsoup4>=4.12",
+    "thefuzz[speedup]>=0.22",
+    "musicbrainzngs>=0.7",
+]
 visualizer = [
     "dash>=2.14",
     "plotly>=5.18",
````

Verification:
- `source .venv/bin/activate && python -m pip install -e '.[hunting]'` succeeds
- `python -c "import yt_dlp; import bs4; from thefuzz import fuzz; import musicbrainzngs"` succeeds

#### Task 2 — models.py: add HuntSession and HuntTrack

Tools: editor
Diff:
````diff
--- a/src/kiku/db/models.py
+++ b/src/kiku/db/models.py
@@ class TransitionCue(Base):
     set_ = relationship("Set")
     track = relationship("Track")


+class HuntSession(Base):
+    __tablename__ = "hunt_sessions"
+
+    id = Column(Integer, primary_key=True)
+    url = Column(String, nullable=False)
+    platform = Column(String)  # "youtube", "soundcloud", "mixcloud", "1001tracklists"
+    title = Column(String)  # Set/mix title from metadata
+    uploader = Column(String)  # DJ / channel name
+    status = Column(String, default="pending")  # "pending", "extracting", "matching", "complete", "error"
+    error_message = Column(Text)
+    track_count = Column(Integer, default=0)
+    owned_count = Column(Integer, default=0)
+    created_at = Column(String, default=lambda: datetime.now().isoformat())
+
+    tracks = relationship("HuntTrack", back_populates="session", cascade="all, delete-orphan",
+                          order_by="HuntTrack.position")
+
+
+class HuntTrack(Base):
+    __tablename__ = "hunt_tracks"
+
+    id = Column(Integer, primary_key=True)
+    session_id = Column(Integer, ForeignKey("hunt_sessions.id", ondelete="CASCADE"), nullable=False)
+    position = Column(Integer, nullable=False)
+    raw_text = Column(String)  # Original text from description/comment
+    artist = Column(String)
+    title = Column(String)
+    remix_info = Column(String)  # e.g. "Artist Remix", "Original Mix"
+    original_artist = Column(String)  # Original artist if this is a remix
+    original_title = Column(String)  # Original title if this is a remix
+    confidence = Column(Float, default=0.0)  # 0-1 extraction confidence
+    source = Column(String)  # "description", "comment", "chapter", "1001tracklists", "copyright"
+    timestamp_sec = Column(Float)  # Position in the mix where this track appears
+    matched_track_id = Column(Integer, ForeignKey("tracks.id"))  # Link to owned track
+    match_score = Column(Float)  # Fuzzy match score 0-1
+    acquisition_status = Column(String, default="unowned")  # "owned", "unowned", "wanted"
+    purchase_links = Column(Text)  # JSON dict of {store: url}
+
+    session = relationship("HuntSession", back_populates="tracks")
+    matched_track = relationship("Track")
+
+
 def get_engine():
````

Verification:
- `source .venv/bin/activate && python -c "from kiku.db.models import HuntSession, HuntTrack; print('OK')"` succeeds

#### Task 3 — Create hunting module: __init__.py + parsers/__init__.py + parsers/common.py

Tools: editor (create files)

File `src/kiku/hunting/__init__.py`:
```python
"""Track Hunter — extract tracklists from DJ sets, find where to buy the tracks."""
```

File `src/kiku/hunting/parsers/__init__.py`:
```python
"""Tracklist parsers for various platforms and formats."""
```

File `src/kiku/hunting/parsers/common.py`:
```python
"""Shared regex patterns for tracklist extraction."""

from __future__ import annotations

import re

# Timestamp patterns: "01:23:45", "1:23:45", "23:45", "1:23"
TIMESTAMP_RE = re.compile(
    r"(?:(\d{1,2}):)?(\d{1,2}):(\d{2})"
)

# "Artist - Title" or "Artist — Title" (em-dash)
ARTIST_TITLE_RE = re.compile(
    r"^(.+?)\s*[-–—]\s*(.+)$"
)

# Remix/edit detection: "Title (Artist Remix)" or "Title [Artist Edit]"
REMIX_RE = re.compile(
    r"^(.*?)\s*[\(\[](.*?(?:remix|edit|bootleg|rework|dub|mix|version|vip))[\)\]](.*)$",
    re.IGNORECASE,
)

# Numbered tracklist: "1. Artist - Title" or "01) Artist - Title"
NUMBERED_LINE_RE = re.compile(
    r"^\s*(\d{1,3})\s*[.\)]\s*(.+)$"
)

# Timestamp + track line: "01:23:45 Artist - Title" or "[01:23] Artist - Title"
TIMESTAMPED_LINE_RE = re.compile(
    r"^\s*\[?" + TIMESTAMP_RE.pattern + r"\]?\s+(.+)$"
)

# YouTube "Music in this video" section markers
YT_MUSIC_SECTION_RE = re.compile(
    r"(?:music|tracks?\s+(?:in|used)|tracklist|setlist)\s*(?:in this video)?",
    re.IGNORECASE,
)


def parse_timestamp(text: str) -> float | None:
    """Parse a timestamp string to seconds. Returns None if not a timestamp."""
    m = TIMESTAMP_RE.search(text)
    if not m:
        return None
    hours = int(m.group(1) or 0)
    minutes = int(m.group(2))
    seconds = int(m.group(3))
    return hours * 3600 + minutes * 60 + seconds


def parse_artist_title(text: str) -> tuple[str, str] | None:
    """Extract (artist, title) from 'Artist - Title' format. Returns None if no separator."""
    text = text.strip()
    m = ARTIST_TITLE_RE.match(text)
    if not m:
        return None
    return m.group(1).strip(), m.group(2).strip()


def parse_remix(title: str) -> tuple[str, str | None]:
    """Extract remix info from title. Returns (clean_title, remix_info).
    If no remix detected, remix_info is None.
    """
    m = REMIX_RE.match(title)
    if not m:
        return title.strip(), None
    clean = (m.group(1) + m.group(3)).strip()
    remix = m.group(2).strip()
    return clean, remix


def normalize_name(name: str) -> str:
    """Normalize artist/title for matching: lowercase, strip feat/ft, trim whitespace."""
    name = name.lower().strip()
    # Remove featuring credits
    name = re.sub(r"\s*(feat\.?|ft\.?|featuring)\s+.*$", "", name, flags=re.IGNORECASE)
    # Remove extra whitespace
    name = re.sub(r"\s+", " ", name)
    return name
```

Verification:
- `source .venv/bin/activate && python -c "from kiku.hunting.parsers.common import parse_artist_title, parse_remix; print(parse_artist_title('Bicep - Glue')); print(parse_remix('Glue (Hammer Remix)'))"` prints `('Bicep', 'Glue')` and `('Glue', 'Hammer Remix')`

#### Task 4 — Create extractor.py: URL detection + yt-dlp metadata extraction

Tools: editor (create file)

File `src/kiku/hunting/extractor.py`:
```python
"""URL router and metadata extractor for Track Hunter.

Uses yt-dlp to extract descriptions, chapters, and comments from
SoundCloud, YouTube, and Mixcloud URLs without downloading audio.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

PLATFORM_PATTERNS = {
    "youtube": re.compile(r"(youtube\.com|youtu\.be)"),
    "soundcloud": re.compile(r"soundcloud\.com"),
    "mixcloud": re.compile(r"mixcloud\.com"),
    "1001tracklists": re.compile(r"1001tracklists\.com"),
}


@dataclass
class ExtractedMetadata:
    """Raw metadata extracted from a URL."""
    url: str
    platform: str
    title: str | None = None
    uploader: str | None = None
    description: str | None = None
    duration_sec: float | None = None
    chapters: list[dict] | None = None  # [{title, start_time, end_time}]
    comments: list[dict] | None = None  # [{text, timestamp, author}]
    error: str | None = None


def detect_platform(url: str) -> str | None:
    """Detect which platform a URL belongs to."""
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    for platform, pattern in PLATFORM_PATTERNS.items():
        if pattern.search(host):
            return platform
    return None


def extract_metadata(url: str, include_comments: bool = True) -> ExtractedMetadata:
    """Extract metadata from a URL using yt-dlp.

    Args:
        url: The URL to extract from.
        include_comments: Whether to fetch comments (slower, but valuable for track IDs).

    Returns:
        ExtractedMetadata with all available information.
    """
    platform = detect_platform(url)
    if platform == "1001tracklists":
        return ExtractedMetadata(url=url, platform="1001tracklists")

    if platform is None:
        return ExtractedMetadata(url=url, platform="unknown", error="Unsupported URL")

    try:
        from yt_dlp import YoutubeDL
    except ImportError:
        return ExtractedMetadata(
            url=url, platform=platform or "unknown",
            error="yt-dlp not installed. Run: pip install 'kiku[hunting]'"
        )

    opts: dict = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "extract_flat": False,
    }
    if include_comments:
        opts["getcomments"] = True

    try:
        with YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)

        if info is None:
            return ExtractedMetadata(url=url, platform=platform, error="No metadata returned")

        comments = None
        if include_comments and info.get("comments"):
            comments = [
                {
                    "text": c.get("text", ""),
                    "timestamp": c.get("timestamp"),
                    "author": c.get("author", ""),
                }
                for c in info["comments"]
            ]

        return ExtractedMetadata(
            url=url,
            platform=platform,
            title=info.get("title"),
            uploader=info.get("uploader") or info.get("channel"),
            description=info.get("description"),
            duration_sec=info.get("duration"),
            chapters=info.get("chapters"),
            comments=comments,
        )

    except Exception as e:
        logger.exception("yt-dlp extraction failed for %s", url)
        return ExtractedMetadata(
            url=url, platform=platform,
            error=f"Extraction failed: {e}"
        )
```

Verification:
- `source .venv/bin/activate && python -c "from kiku.hunting.extractor import detect_platform; print(detect_platform('https://www.youtube.com/watch?v=abc')); print(detect_platform('https://soundcloud.com/dj/set'))"` prints `youtube` and `soundcloud`

#### Task 5 — Create parsers/tracklist.py: parse descriptions + comments into tracklist

Tools: editor (create file)

File `src/kiku/hunting/parsers/tracklist.py`:
```python
"""Parse descriptions, comments, and chapters into structured tracklists."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from kiku.hunting.parsers.common import (
    NUMBERED_LINE_RE,
    TIMESTAMPED_LINE_RE,
    YT_MUSIC_SECTION_RE,
    parse_artist_title,
    parse_remix,
    parse_timestamp,
)


@dataclass
class ParsedTrack:
    """A single track extracted from text."""
    position: int
    artist: str
    title: str
    remix_info: str | None = None
    original_title: str | None = None
    timestamp_sec: float | None = None
    raw_text: str = ""
    source: str = "description"  # "description", "comment", "chapter", "copyright"
    confidence: float = 0.8


def parse_description(text: str | None) -> list[ParsedTrack]:
    """Parse a set description for tracklist entries.

    Handles formats:
    - Numbered lists: "1. Artist - Title"
    - Timestamped lists: "01:23 Artist - Title"
    - Plain lists: "Artist - Title" (one per line)
    - YouTube "Music in this video" sections
    """
    if not text:
        return []

    tracks: list[ParsedTrack] = []
    lines = text.strip().split("\n")
    position = 1
    in_tracklist_section = False

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Detect tracklist section headers
        if YT_MUSIC_SECTION_RE.search(line) and len(line) < 80:
            in_tracklist_section = True
            continue

        # Try timestamped line: "01:23:45 Artist - Title"
        ts_match = TIMESTAMPED_LINE_RE.match(line)
        if ts_match:
            hours = int(ts_match.group(1) or 0)
            minutes = int(ts_match.group(2))
            seconds = int(ts_match.group(3))
            timestamp = hours * 3600 + minutes * 60 + seconds
            track_text = ts_match.group(4).strip()

            parsed = _parse_track_text(track_text)
            if parsed:
                artist, title, remix = parsed
                tracks.append(ParsedTrack(
                    position=position,
                    artist=artist,
                    title=title,
                    remix_info=remix,
                    original_title=title if remix else None,
                    timestamp_sec=timestamp,
                    raw_text=line,
                    source="description",
                    confidence=0.9,
                ))
                position += 1
                continue

        # Try numbered line: "1. Artist - Title" or "01) Artist - Title"
        num_match = NUMBERED_LINE_RE.match(line)
        if num_match:
            track_text = num_match.group(2).strip()
            parsed = _parse_track_text(track_text)
            if parsed:
                artist, title, remix = parsed
                tracks.append(ParsedTrack(
                    position=position,
                    artist=artist,
                    title=title,
                    remix_info=remix,
                    original_title=title if remix else None,
                    raw_text=line,
                    source="description",
                    confidence=0.85,
                ))
                position += 1
                continue

        # Try plain "Artist - Title" line (only if we're in a tracklist section or many such lines exist)
        parsed = _parse_track_text(line)
        if parsed and (in_tracklist_section or _looks_like_tracklist_line(line)):
            artist, title, remix = parsed
            tracks.append(ParsedTrack(
                position=position,
                artist=artist,
                title=title,
                remix_info=remix,
                original_title=title if remix else None,
                raw_text=line,
                source="description",
                confidence=0.7,
            ))
            position += 1

    return tracks


def parse_chapters(chapters: list[dict] | None) -> list[ParsedTrack]:
    """Parse YouTube chapters (auto-detected from timestamps) into tracks."""
    if not chapters:
        return []

    tracks: list[ParsedTrack] = []
    for i, ch in enumerate(chapters, 1):
        title_text = ch.get("title", "").strip()
        if not title_text:
            continue

        parsed = _parse_track_text(title_text)
        if parsed:
            artist, title, remix = parsed
            tracks.append(ParsedTrack(
                position=i,
                artist=artist,
                title=title,
                remix_info=remix,
                original_title=title if remix else None,
                timestamp_sec=ch.get("start_time"),
                raw_text=title_text,
                source="chapter",
                confidence=0.95,
            ))

    return tracks


def parse_comments(comments: list[dict] | None) -> list[ParsedTrack]:
    """Parse user comments for track identifications.

    Looks for patterns like:
    - "Track at 32:15 is Artist - Title"
    - "01:23 Artist - Title"
    - Replies with "ID?" followed by track names
    """
    if not comments:
        return []

    tracks: list[ParsedTrack] = []
    seen: set[tuple[str, str]] = set()
    position = 1

    for comment in comments:
        text = comment.get("text", "").strip()
        if not text:
            continue

        # Check each line of multi-line comments
        for line in text.split("\n"):
            line = line.strip()
            if not line or len(line) < 5:
                continue

            # Try timestamped format
            ts_match = TIMESTAMPED_LINE_RE.match(line)
            if ts_match:
                hours = int(ts_match.group(1) or 0)
                minutes = int(ts_match.group(2))
                seconds = int(ts_match.group(3))
                timestamp = hours * 3600 + minutes * 60 + seconds
                track_text = ts_match.group(4).strip()

                parsed = _parse_track_text(track_text)
                if parsed:
                    artist, title, remix = parsed
                    key = (artist.lower(), title.lower())
                    if key not in seen:
                        seen.add(key)
                        tracks.append(ParsedTrack(
                            position=position,
                            artist=artist,
                            title=title,
                            remix_info=remix,
                            original_title=title if remix else None,
                            timestamp_sec=timestamp,
                            raw_text=line,
                            source="comment",
                            confidence=0.6,
                        ))
                        position += 1

    return tracks


def merge_tracklists(*tracklists: list[ParsedTrack]) -> list[ParsedTrack]:
    """Merge multiple tracklists, deduplicating by artist+title.

    Higher confidence sources take priority. Position is renumbered.
    """
    seen: dict[tuple[str, str], ParsedTrack] = {}

    for tracks in tracklists:
        for track in tracks:
            key = (track.artist.lower().strip(), track.title.lower().strip())
            existing = seen.get(key)
            if existing is None or track.confidence > existing.confidence:
                seen[key] = track

    # Sort by timestamp if available, otherwise by original position
    merged = sorted(
        seen.values(),
        key=lambda t: (t.timestamp_sec if t.timestamp_sec is not None else float("inf"), t.position),
    )

    # Renumber
    for i, track in enumerate(merged, 1):
        track.position = i

    return merged


def _parse_track_text(text: str) -> tuple[str, str, str | None] | None:
    """Parse a track string into (artist, title, remix_info).
    Returns None if the text doesn't look like a track.
    """
    at = parse_artist_title(text)
    if not at:
        return None

    artist, title_raw = at

    # Skip if artist or title is too short or looks like a URL/header
    if len(artist) < 2 or len(title_raw) < 2:
        return None
    if artist.startswith("http") or title_raw.startswith("http"):
        return None

    title, remix = parse_remix(title_raw)
    return artist, title, remix


def _looks_like_tracklist_line(line: str) -> bool:
    """Heuristic: does this line look like a track entry?"""
    # Must contain " - " separator
    if " - " not in line and " – " not in line and " — " not in line:
        return False
    # Not too long (URLs, paragraphs)
    if len(line) > 200:
        return False
    # Not a URL
    if line.startswith("http"):
        return False
    return True
```

Verification:
- `source .venv/bin/activate && python -c "
from kiku.hunting.parsers.tracklist import parse_description
tracks = parse_description('Tracklist:\n1. Bicep - Glue\n2. Hammer - Catnip (Original Mix)\n03:15 Four Tet - Baby')
for t in tracks: print(f'{t.position}. {t.artist} - {t.title} [{t.remix_info}] @{t.timestamp_sec}')
"`

#### Task 6 — Create matcher.py: fuzzy library matching

Tools: editor (create file)

File `src/kiku/hunting/matcher.py`:
```python
"""Fuzzy match extracted tracks against the local Kiku library."""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from kiku.db.models import Track
from kiku.hunting.parsers.common import normalize_name

logger = logging.getLogger(__name__)

# Minimum fuzzy score to consider a match
MATCH_THRESHOLD = 75


def match_tracks(
    session: Session,
    extracted: list[dict],
) -> list[dict]:
    """Match extracted tracks against the local library using fuzzy string matching.

    Args:
        session: DB session.
        extracted: List of dicts with 'artist' and 'title' keys.

    Returns:
        Same list with added 'matched_track_id', 'match_score', 'acquisition_status' fields.
    """
    try:
        from thefuzz import fuzz
    except ImportError:
        logger.warning("thefuzz not installed — skipping library matching")
        return extracted

    # Load all library tracks (artist, title) for matching
    library = session.query(Track.id, Track.artist, Track.title).filter(
        Track.artist.isnot(None),
        Track.title.isnot(None),
    ).all()

    # Pre-normalize library for speed
    lib_normalized = [
        (t.id, normalize_name(t.artist or ""), normalize_name(t.title or ""))
        for t in library
    ]

    for item in extracted:
        artist_norm = normalize_name(item.get("artist", ""))
        title_norm = normalize_name(item.get("title", ""))

        best_id = None
        best_score = 0.0

        for lib_id, lib_artist, lib_title in lib_normalized:
            # Combined score: weighted average of artist and title match
            artist_score = fuzz.ratio(artist_norm, lib_artist)
            title_score = fuzz.ratio(title_norm, lib_title)
            combined = (artist_score * 0.4 + title_score * 0.6) / 100.0

            if combined > best_score:
                best_score = combined
                best_id = lib_id

        if best_score >= MATCH_THRESHOLD / 100.0:
            item["matched_track_id"] = best_id
            item["match_score"] = round(best_score, 3)
            item["acquisition_status"] = "owned"
        else:
            item["matched_track_id"] = None
            item["match_score"] = round(best_score, 3) if best_score > 0.3 else None
            item["acquisition_status"] = "unowned"

    return extracted
```

Verification:
- `source .venv/bin/activate && python -c "from kiku.hunting.matcher import match_tracks; print('OK')"` succeeds

#### Task 7 — Create sources.py: purchase URL generation

Tools: editor (create file)

File `src/kiku/hunting/sources.py`:
```python
"""Generate purchase search URLs for unowned tracks."""

from __future__ import annotations

from urllib.parse import quote_plus

STORES = {
    "beatport": "https://www.beatport.com/search?q={query}",
    "traxsource": "https://www.traxsource.com/search?term={query}",
    "bandcamp": "https://bandcamp.com/search?q={query}",
    "juno": "https://www.junodownload.com/search/?q%5Ball%5D%5B%5D={query}",
}


def generate_purchase_links(artist: str, title: str) -> dict[str, str]:
    """Generate search URLs for all supported stores.

    Args:
        artist: Track artist.
        title: Track title.

    Returns:
        Dict of {store_name: search_url}.
    """
    query = quote_plus(f"{artist} {title}")
    return {store: url.format(query=query) for store, url in STORES.items()}
```

Verification:
- `source .venv/bin/activate && python -c "from kiku.hunting.sources import generate_purchase_links; links = generate_purchase_links('Bicep', 'Glue'); print(links['beatport'])"` prints a Beatport search URL

#### Task 8 — store.py: add hunt CRUD functions

Tools: editor
Diff (append at end of file before any closing content):
````diff
--- a/src/kiku/db/store.py
+++ b/src/kiku/db/store.py
@@ end of file
+
+
+# ── Hunt session CRUD ─────────────────────────────────────────────────
+
+
+def create_hunt_session(
+    session: Session, url: str, platform: str, title: str | None = None,
+    uploader: str | None = None,
+) -> "HuntSession":
+    """Create a new hunt session."""
+    from kiku.db.models import HuntSession
+
+    hunt = HuntSession(url=url, platform=platform, title=title, uploader=uploader)
+    session.add(hunt)
+    session.flush()
+    return hunt
+
+
+def get_hunt_session(session: Session, hunt_id: int) -> "HuntSession | None":
+    """Get a hunt session by ID with tracks eagerly loaded."""
+    from kiku.db.models import HuntSession
+
+    return session.query(HuntSession).filter_by(id=hunt_id).first()
+
+
+def list_hunt_sessions(session: Session, limit: int = 20, offset: int = 0) -> tuple[list, int]:
+    """List hunt sessions ordered by creation date desc."""
+    from sqlalchemy import func
+
+    from kiku.db.models import HuntSession
+
+    total = session.query(func.count(HuntSession.id)).scalar() or 0
+    hunts = (
+        session.query(HuntSession)
+        .order_by(HuntSession.created_at.desc())
+        .offset(offset)
+        .limit(limit)
+        .all()
+    )
+    return hunts, total
+
+
+def save_hunt_tracks(
+    session: Session, hunt_id: int, tracks: list[dict],
+) -> list:
+    """Save extracted tracks to a hunt session."""
+    import json
+
+    from kiku.db.models import HuntSession, HuntTrack
+
+    hunt = session.query(HuntSession).filter_by(id=hunt_id).first()
+    if not hunt:
+        return []
+
+    results = []
+    for t in tracks:
+        ht = HuntTrack(
+            session_id=hunt_id,
+            position=t.get("position", 0),
+            raw_text=t.get("raw_text"),
+            artist=t.get("artist"),
+            title=t.get("title"),
+            remix_info=t.get("remix_info"),
+            original_artist=t.get("original_artist"),
+            original_title=t.get("original_title"),
+            confidence=t.get("confidence", 0.0),
+            source=t.get("source"),
+            timestamp_sec=t.get("timestamp_sec"),
+            matched_track_id=t.get("matched_track_id"),
+            match_score=t.get("match_score"),
+            acquisition_status=t.get("acquisition_status", "unowned"),
+            purchase_links=json.dumps(t.get("purchase_links", {})),
+        )
+        session.add(ht)
+        results.append(ht)
+
+    hunt.track_count = len(tracks)
+    hunt.owned_count = sum(1 for t in tracks if t.get("acquisition_status") == "owned")
+    hunt.status = "complete"
+    session.flush()
+    return results
+
+
+def update_hunt_track_status(
+    session: Session, hunt_track_id: int, status: str,
+) -> "HuntTrack | None":
+    """Update acquisition status of a hunt track (e.g. 'wanted', 'owned')."""
+    from kiku.db.models import HuntTrack
+
+    ht = session.query(HuntTrack).filter_by(id=hunt_track_id).first()
+    if ht:
+        ht.acquisition_status = status
+        session.flush()
+    return ht
````

Verification:
- `source .venv/bin/activate && python -c "from kiku.db.store import create_hunt_session, save_hunt_tracks; print('OK')"` succeeds

#### Task 9 — schemas.py: add Hunt request/response models

Tools: editor
Diff (append at end of file):
````diff
--- a/src/kiku/api/schemas.py
+++ b/src/kiku/api/schemas.py
@@ class GenreFamilyResponse(BaseModel):
     family_name: str
     genres: list[str]
     compatible_with: list[str]
+
+
+# ── Track Hunter models ──
+
+
+class HuntRequest(BaseModel):
+    url: str
+    include_comments: bool = True
+
+
+class HuntTrackResponse(BaseModel):
+    id: int
+    position: int
+    artist: str | None = None
+    title: str | None = None
+    remix_info: str | None = None
+    original_title: str | None = None
+    confidence: float = 0.0
+    source: str | None = None
+    timestamp_sec: float | None = None
+    matched_track_id: int | None = None
+    match_score: float | None = None
+    acquisition_status: str = "unowned"
+    purchase_links: dict[str, str] = {}
+    raw_text: str | None = None
+
+    model_config = {"from_attributes": True}
+
+
+class HuntSessionResponse(BaseModel):
+    id: int
+    url: str
+    platform: str | None = None
+    title: str | None = None
+    uploader: str | None = None
+    status: str = "pending"
+    track_count: int = 0
+    owned_count: int = 0
+    created_at: str | None = None
+    tracks: list[HuntTrackResponse] = []
+
+    model_config = {"from_attributes": True}
+
+
+class HuntSessionSummary(BaseModel):
+    id: int
+    url: str
+    platform: str | None = None
+    title: str | None = None
+    uploader: str | None = None
+    status: str = "pending"
+    track_count: int = 0
+    owned_count: int = 0
+    created_at: str | None = None
+
+    model_config = {"from_attributes": True}
+
+
+class HuntListResponse(BaseModel):
+    items: list[HuntSessionSummary]
+    total: int
+    offset: int
+    limit: int
+
+
+class HuntTrackUpdateRequest(BaseModel):
+    acquisition_status: str  # "wanted", "owned", "unowned"
````

Verification:
- `source .venv/bin/activate && python -c "from kiku.api.schemas import HuntRequest, HuntSessionResponse, HuntTrackResponse; print('OK')"` succeeds

#### Task 10 — Create API route hunt.py + register in main.py

Tools: editor (create file + edit main.py)

File `src/kiku/api/routes/hunt.py`:
```python
"""Track Hunter API — extract tracklists from DJ sets and find purchase sources."""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from kiku.api.deps import get_db
from kiku.api.schemas import (
    HuntListResponse,
    HuntRequest,
    HuntSessionResponse,
    HuntSessionSummary,
    HuntTrackResponse,
    HuntTrackUpdateRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/hunt", tags=["hunt"])


def _hunt_track_to_response(ht) -> HuntTrackResponse:
    """Convert a HuntTrack model to response."""
    links = {}
    if ht.purchase_links:
        try:
            links = json.loads(ht.purchase_links)
        except (json.JSONDecodeError, TypeError):
            pass
    return HuntTrackResponse(
        id=ht.id,
        position=ht.position,
        artist=ht.artist,
        title=ht.title,
        remix_info=ht.remix_info,
        original_title=ht.original_title,
        confidence=ht.confidence or 0.0,
        source=ht.source,
        timestamp_sec=ht.timestamp_sec,
        matched_track_id=ht.matched_track_id,
        match_score=ht.match_score,
        acquisition_status=ht.acquisition_status or "unowned",
        purchase_links=links,
        raw_text=ht.raw_text,
    )


def _hunt_session_to_response(hunt) -> HuntSessionResponse:
    """Convert a HuntSession model to full response with tracks."""
    return HuntSessionResponse(
        id=hunt.id,
        url=hunt.url,
        platform=hunt.platform,
        title=hunt.title,
        uploader=hunt.uploader,
        status=hunt.status or "pending",
        track_count=hunt.track_count or 0,
        owned_count=hunt.owned_count or 0,
        created_at=hunt.created_at,
        tracks=[_hunt_track_to_response(ht) for ht in (hunt.tracks or [])],
    )


@router.post("", response_model=HuntSessionResponse)
def start_hunt(body: HuntRequest, db: Session = Depends(get_db)):
    """Start a new track hunt from a URL.

    Extracts tracklist from the given URL, matches against library,
    and generates purchase links for unowned tracks.
    """
    from kiku.db.store import create_hunt_session, save_hunt_tracks
    from kiku.hunting.extractor import detect_platform, extract_metadata
    from kiku.hunting.matcher import match_tracks
    from kiku.hunting.parsers.tracklist import (
        merge_tracklists,
        parse_chapters,
        parse_comments,
        parse_description,
    )
    from kiku.hunting.sources import generate_purchase_links

    # Detect platform
    platform = detect_platform(body.url)
    if not platform:
        raise HTTPException(status_code=400, detail="Unsupported URL — try YouTube, SoundCloud, or Mixcloud")

    # Create session
    hunt = create_hunt_session(db, url=body.url, platform=platform)
    hunt.status = "extracting"
    db.flush()

    # Extract metadata
    metadata = extract_metadata(body.url, include_comments=body.include_comments)
    if metadata.error:
        hunt.status = "error"
        hunt.error_message = metadata.error
        db.commit()
        raise HTTPException(status_code=422, detail=metadata.error)

    hunt.title = metadata.title
    hunt.uploader = metadata.uploader
    hunt.status = "matching"
    db.flush()

    # Parse tracklist from all sources
    desc_tracks = parse_description(metadata.description)
    chapter_tracks = parse_chapters(metadata.chapters)
    comment_tracks = parse_comments(metadata.comments)

    merged = merge_tracklists(chapter_tracks, desc_tracks, comment_tracks)

    if not merged:
        hunt.status = "complete"
        hunt.track_count = 0
        db.commit()
        return _hunt_session_to_response(hunt)

    # Convert to dicts for matching
    track_dicts = [
        {
            "position": t.position,
            "artist": t.artist,
            "title": t.title,
            "remix_info": t.remix_info,
            "original_title": t.original_title,
            "confidence": t.confidence,
            "source": t.source,
            "timestamp_sec": t.timestamp_sec,
            "raw_text": t.raw_text,
        }
        for t in merged
    ]

    # Match against library
    matched = match_tracks(db, track_dicts)

    # Generate purchase links for unowned tracks
    for t in matched:
        if t.get("acquisition_status") != "owned" and t.get("artist") and t.get("title"):
            t["purchase_links"] = generate_purchase_links(t["artist"], t["title"])

    # Save to DB
    save_hunt_tracks(db, hunt.id, matched)
    db.commit()

    # Reload to get relationships
    db.refresh(hunt)
    return _hunt_session_to_response(hunt)


@router.get("s", response_model=HuntListResponse)
def list_hunts(
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    """List past hunt sessions."""
    from kiku.db.store import list_hunt_sessions

    hunts, total = list_hunt_sessions(db, limit=limit, offset=offset)
    items = [
        HuntSessionSummary(
            id=h.id,
            url=h.url,
            platform=h.platform,
            title=h.title,
            uploader=h.uploader,
            status=h.status or "pending",
            track_count=h.track_count or 0,
            owned_count=h.owned_count or 0,
            created_at=h.created_at,
        )
        for h in hunts
    ]
    return HuntListResponse(items=items, total=total, offset=offset, limit=limit)


@router.get("/{hunt_id}", response_model=HuntSessionResponse)
def get_hunt(hunt_id: int, db: Session = Depends(get_db)):
    """Get a hunt session with full tracklist."""
    from kiku.db.store import get_hunt_session

    hunt = get_hunt_session(db, hunt_id)
    if not hunt:
        raise HTTPException(status_code=404, detail="Hunt session not found")
    return _hunt_session_to_response(hunt)


@router.patch("/tracks/{track_id}", response_model=HuntTrackResponse)
def update_hunt_track(
    track_id: int,
    body: HuntTrackUpdateRequest,
    db: Session = Depends(get_db),
):
    """Update a hunt track's acquisition status (e.g. mark as 'wanted')."""
    from kiku.db.store import update_hunt_track_status

    if body.acquisition_status not in ("wanted", "owned", "unowned"):
        raise HTTPException(status_code=400, detail="Status must be wanted, owned, or unowned")

    ht = update_hunt_track_status(db, track_id, body.acquisition_status)
    if not ht:
        raise HTTPException(status_code=404, detail="Hunt track not found")
    db.commit()
    return _hunt_track_to_response(ht)
```

Edit `src/kiku/api/main.py` to register the hunt router:
````diff
--- a/src/kiku/api/main.py
+++ b/src/kiku/api/main.py
@@ from kiku.api.routes import audio, config, export, sets, stats, tinder, tracks, waveforms
+from kiku.api.routes import audio, config, export, hunt, sets, stats, tinder, tracks, waveforms
@@
     app.include_router(export.router)
     app.include_router(config.router)
+    app.include_router(hunt.router)
````

Verification:
- `source .venv/bin/activate && python -c "from kiku.api.routes.hunt import router; print(router.prefix)"` prints `/api/hunt`

#### Task 11 — cli.py: add `kiku hunt` command

Tools: editor
Diff (append after the `autotag_energy` command, before any final blank lines):
````diff
--- a/src/kiku/cli.py
+++ b/src/kiku/cli.py
@@ end of autotag_energy command
+
+
+@cli.command()
+@click.argument("url")
+@click.option("--no-comments", is_flag=True, help="Skip fetching comments (faster)")
+@click.option("--json-output", "as_json", is_flag=True, help="Output results as JSON")
+def hunt(url: str, no_comments: bool, as_json: bool):
+    """Extract a tracklist from a DJ set URL and find where to buy the tracks.
+
+    Supports YouTube, SoundCloud, and Mixcloud URLs. Parses descriptions,
+    chapters, and comments to identify tracks, then matches against your library.
+    """
+    from kiku.db.models import get_session
+    from kiku.db.store import create_hunt_session, save_hunt_tracks
+    from kiku.hunting.extractor import detect_platform, extract_metadata
+    from kiku.hunting.matcher import match_tracks
+    from kiku.hunting.parsers.tracklist import (
+        merge_tracklists,
+        parse_chapters,
+        parse_comments,
+        parse_description,
+    )
+    from kiku.hunting.sources import generate_purchase_links
+
+    platform = detect_platform(url)
+    if not platform:
+        console.print("[red]Unsupported URL.[/] Try YouTube, SoundCloud, or Mixcloud.")
+        return
+
+    console.print(f"[cyan]Hunting tracks from {platform}...[/]")
+
+    metadata = extract_metadata(url, include_comments=not no_comments)
+    if metadata.error:
+        console.print(f"[red]Extraction failed:[/] {metadata.error}")
+        return
+
+    if metadata.title:
+        console.print(f"[bold]{metadata.title}[/]")
+    if metadata.uploader:
+        console.print(f"  by {metadata.uploader}")
+    console.print()
+
+    # Parse all sources
+    desc_tracks = parse_description(metadata.description)
+    chapter_tracks = parse_chapters(metadata.chapters)
+    comment_tracks = parse_comments(metadata.comments) if not no_comments else []
+
+    merged = merge_tracklists(chapter_tracks, desc_tracks, comment_tracks)
+
+    if not merged:
+        console.print("[yellow]Couldn't find a tracklist in this set.[/] "
+                      "The description may not contain track names.")
+        return
+
+    console.print(f"[bold]Found {len(merged)} tracks[/]\n")
+
+    # Convert to dicts and match
+    track_dicts = [
+        {
+            "position": t.position,
+            "artist": t.artist,
+            "title": t.title,
+            "remix_info": t.remix_info,
+            "original_title": t.original_title,
+            "confidence": t.confidence,
+            "source": t.source,
+            "timestamp_sec": t.timestamp_sec,
+            "raw_text": t.raw_text,
+        }
+        for t in merged
+    ]
+
+    session = get_session()
+    matched = match_tracks(session, track_dicts)
+
+    # Generate purchase links for unowned
+    for t in matched:
+        if t.get("acquisition_status") != "owned" and t.get("artist") and t.get("title"):
+            t["purchase_links"] = generate_purchase_links(t["artist"], t["title"])
+
+    # Save to DB
+    hunt_session = create_hunt_session(
+        session, url=url, platform=platform,
+        title=metadata.title, uploader=metadata.uploader,
+    )
+    save_hunt_tracks(session, hunt_session.id, matched)
+    session.commit()
+
+    if as_json:
+        import json as json_mod
+        console.print(json_mod.dumps(matched, indent=2, default=str))
+        return
+
+    # Display results
+    owned = sum(1 for t in matched if t.get("acquisition_status") == "owned")
+    unowned = len(matched) - owned
+
+    table = Table(title=f"Tracklist — {owned} owned, {unowned} to hunt")
+    table.add_column("#", justify="right", style="dim")
+    table.add_column("Artist", style="cyan")
+    table.add_column("Title")
+    table.add_column("Remix", style="dim")
+    table.add_column("Source", style="dim")
+    table.add_column("Status", justify="center")
+
+    for t in matched:
+        status = "[green]✓ owned[/]" if t.get("acquisition_status") == "owned" else "[yellow]hunt[/]"
+        ts = ""
+        if t.get("timestamp_sec") is not None:
+            mins = int(t["timestamp_sec"] // 60)
+            secs = int(t["timestamp_sec"] % 60)
+            ts = f" @{mins}:{secs:02d}"
+        table.add_row(
+            str(t.get("position", "")),
+            t.get("artist", "?"),
+            t.get("title", "?"),
+            t.get("remix_info") or "",
+            (t.get("source", "") + ts),
+            status,
+        )
+
+    console.print(table)
+
+    if unowned > 0:
+        console.print(f"\n[bold]You're missing {unowned} of {len(matched)} tracks.[/]")
+        console.print("[dim]Hunt session saved. View purchase links in the UI or run with --json-output.[/]")
+    else:
+        console.print(f"\n[green]You own all {len(matched)} tracks![/] Time to learn from this set.")
````

Verification:
- `source .venv/bin/activate && kiku hunt --help` shows help text with URL argument and options

#### Task 12 — Frontend: types, API client, store, UI components

Tools: editor (create + edit files)

**12a.** Edit `frontend/src/lib/types/index.ts` — append Hunt types:
````diff
--- a/frontend/src/lib/types/index.ts
+++ b/frontend/src/lib/types/index.ts
@@ end of file (after TinderRetrainResult)
+
+// ── Track Hunter types ──
+
+export interface HuntTrack {
+	id: number;
+	position: number;
+	artist: string | null;
+	title: string | null;
+	remix_info: string | null;
+	original_title: string | null;
+	confidence: number;
+	source: string | null;
+	timestamp_sec: number | null;
+	matched_track_id: number | null;
+	match_score: number | null;
+	acquisition_status: string;
+	purchase_links: Record<string, string>;
+	raw_text: string | null;
+}
+
+export interface HuntSession {
+	id: number;
+	url: string;
+	platform: string | null;
+	title: string | null;
+	uploader: string | null;
+	status: string;
+	track_count: number;
+	owned_count: number;
+	created_at: string | null;
+	tracks: HuntTrack[];
+}
+
+export interface HuntSessionSummary {
+	id: number;
+	url: string;
+	platform: string | null;
+	title: string | null;
+	uploader: string | null;
+	status: string;
+	track_count: number;
+	owned_count: number;
+	created_at: string | null;
+}
+
+export interface HuntListResponse {
+	items: HuntSessionSummary[];
+	total: number;
+	offset: number;
+	limit: number;
+}
````

**12b.** Create `frontend/src/lib/api/hunt.ts`:
```typescript
import type { HuntSession, HuntListResponse } from '$lib/types';
import { fetchJson } from './client';

export async function startHunt(url: string, includeComments = true): Promise<HuntSession> {
	return fetchJson<HuntSession>('/api/hunt', {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ url, include_comments: includeComments }),
	});
}

export async function getHunt(huntId: number): Promise<HuntSession> {
	return fetchJson<HuntSession>(`/api/hunt/${huntId}`);
}

export async function listHunts(limit = 20, offset = 0): Promise<HuntListResponse> {
	return fetchJson<HuntListResponse>(`/api/hunts?limit=${limit}&offset=${offset}`);
}

export async function updateHuntTrackStatus(
	trackId: number,
	status: 'wanted' | 'owned' | 'unowned'
): Promise<void> {
	await fetchJson(`/api/hunt/tracks/${trackId}`, {
		method: 'PATCH',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ acquisition_status: status }),
	});
}
```

**12c.** Create `frontend/src/lib/stores/hunting.svelte.ts`:
```typescript
import type { HuntSession, HuntSessionSummary } from '$lib/types';
import { startHunt, getHunt, listHunts, updateHuntTrackStatus } from '$lib/api/hunt';

let currentHunt = $state<HuntSession | null>(null);
let history = $state<HuntSessionSummary[]>([]);
let historyTotal = $state(0);
let loading = $state(false);
let error = $state<string | null>(null);

async function hunt(url: string) {
	loading = true;
	error = null;
	currentHunt = null;
	try {
		currentHunt = await startHunt(url);
	} catch (e) {
		error = e instanceof Error ? e.message : String(e);
	} finally {
		loading = false;
	}
}

async function loadHunt(huntId: number) {
	loading = true;
	error = null;
	try {
		currentHunt = await getHunt(huntId);
	} catch (e) {
		error = e instanceof Error ? e.message : String(e);
	} finally {
		loading = false;
	}
}

async function loadHistory() {
	try {
		const result = await listHunts();
		history = result.items;
		historyTotal = result.total;
	} catch (e) {
		error = e instanceof Error ? e.message : String(e);
	}
}

async function markWanted(huntTrackId: number) {
	try {
		await updateHuntTrackStatus(huntTrackId, 'wanted');
		if (currentHunt) {
			const track = currentHunt.tracks.find((t) => t.id === huntTrackId);
			if (track) track.acquisition_status = 'wanted';
			currentHunt = { ...currentHunt };
		}
	} catch (e) {
		error = e instanceof Error ? e.message : String(e);
	}
}

export function getHuntingStore() {
	return {
		get currentHunt() { return currentHunt; },
		get history() { return history; },
		get historyTotal() { return historyTotal; },
		get loading() { return loading; },
		get error() { return error; },
		get ownedCount() { return currentHunt?.owned_count ?? 0; },
		get unownedCount() { return (currentHunt?.track_count ?? 0) - (currentHunt?.owned_count ?? 0); },
		hunt,
		loadHunt,
		loadHistory,
		markWanted,
	};
}
```

**12d.** Edit `frontend/src/lib/stores/ui.svelte.ts` — add 'hunt' to Tab:
````diff
--- a/frontend/src/lib/stores/ui.svelte.ts
+++ b/frontend/src/lib/stores/ui.svelte.ts
@@ export type Tab = 'track' | 'set' | 'dna' | 'tinder';
+export type Tab = 'track' | 'set' | 'dna' | 'tinder' | 'hunt';
````

**12e.** Edit `frontend/src/lib/components/Workspace.svelte` — add Hunt tab:
````diff
--- a/frontend/src/lib/components/Workspace.svelte
+++ b/frontend/src/lib/components/Workspace.svelte
@@ script imports
 	import EnergyTinder from './tinder/EnergyTinder.svelte';
+	import HuntView from './hunt/HuntView.svelte';
@@
 		else if (e.key === '4') { ui.activeTab = 'tinder'; e.preventDefault(); }
+		else if (e.key === '5') { ui.activeTab = 'hunt'; e.preventDefault(); }
@@
 		<button class="tab" class:active={ui.activeTab === 'tinder'} onclick={() => ui.activeTab = 'tinder'}>
 			Energy Tinder <span class="shortcut">4</span>
 		</button>
+		<button class="tab" class:active={ui.activeTab === 'hunt'} onclick={() => ui.activeTab = 'hunt'}>
+			Track Hunter <span class="shortcut">5</span>
+		</button>
@@
 		{:else if ui.activeTab === 'tinder'}
 			<EnergyTinder />
+		{:else if ui.activeTab === 'hunt'}
+			<HuntView />
 		{/if}
````

**12f.** Create `frontend/src/lib/components/hunt/HuntView.svelte`:
```svelte
<script lang="ts">
	import { getHuntingStore } from '$lib/stores/hunting.svelte';
	import HuntResults from './HuntResults.svelte';
	import HuntHistory from './HuntHistory.svelte';

	const store = getHuntingStore();

	let urlInput = $state('');
	let showHistory = $state(false);

	async function handleSubmit() {
		const url = urlInput.trim();
		if (!url) return;
		await store.hunt(url);
		urlInput = '';
	}

	function handleHistorySelect(huntId: number) {
		showHistory = false;
		store.loadHunt(huntId);
	}

	$effect(() => {
		if (showHistory) store.loadHistory();
	});
</script>

<div class="hunt-view">
	<div class="hunt-header">
		<h2>Track Hunter</h2>
		<p class="subtitle">Paste a set URL — we'll find every track and show you where to get them</p>
	</div>

	<form class="hunt-form" onsubmit|preventDefault={handleSubmit}>
		<input
			type="url"
			bind:value={urlInput}
			placeholder="YouTube, SoundCloud, or Mixcloud URL..."
			disabled={store.loading}
		/>
		<button type="submit" disabled={store.loading || !urlInput.trim()}>
			{store.loading ? 'Hunting...' : 'Hunt'}
		</button>
		<button type="button" class="history-btn" onclick={() => showHistory = !showHistory}>
			History
		</button>
	</form>

	{#if store.error}
		<div class="error">{store.error}</div>
	{/if}

	{#if showHistory}
		<HuntHistory items={store.history} onselect={handleHistorySelect} />
	{:else if store.currentHunt}
		<HuntResults hunt={store.currentHunt} onmarkwanted={store.markWanted} />
	{:else if !store.loading}
		<div class="empty-state">
			<p>Hear a set you love? Paste the link above to hunt down every track.</p>
		</div>
	{/if}
</div>

<style>
	.hunt-view {
		padding: 20px;
		max-width: 900px;
	}

	.hunt-header h2 {
		margin: 0 0 4px;
		font-size: 18px;
	}

	.subtitle {
		color: var(--text-secondary);
		font-size: 13px;
		margin: 0 0 16px;
	}

	.hunt-form {
		display: flex;
		gap: 8px;
		margin-bottom: 16px;
	}

	.hunt-form input {
		flex: 1;
		padding: 8px 12px;
		font-size: 13px;
		background: var(--bg-secondary);
		border: 1px solid var(--border);
		border-radius: 6px;
		color: var(--text-primary);
	}

	.hunt-form button {
		padding: 8px 16px;
		font-size: 13px;
		font-weight: 600;
		border-radius: 6px;
		cursor: pointer;
	}

	.hunt-form button[type='submit'] {
		background: var(--accent);
		color: #000;
		border: none;
	}

	.hunt-form button[type='submit']:disabled {
		opacity: 0.5;
		cursor: default;
	}

	.history-btn {
		background: transparent;
		color: var(--text-secondary);
		border: 1px solid var(--border);
	}

	.error {
		padding: 8px 12px;
		background: rgba(255, 80, 80, 0.1);
		border: 1px solid rgba(255, 80, 80, 0.3);
		border-radius: 6px;
		color: #ff5050;
		font-size: 13px;
		margin-bottom: 12px;
	}

	.empty-state {
		text-align: center;
		color: var(--text-dim);
		padding: 60px 20px;
		font-size: 14px;
	}
</style>
```

**12g.** Create `frontend/src/lib/components/hunt/HuntResults.svelte`:
```svelte
<script lang="ts">
	import type { HuntSession } from '$lib/types';

	interface Props {
		hunt: HuntSession;
		onmarkwanted: (trackId: number) => void;
	}

	let { hunt, onmarkwanted }: Props = $props();

	const owned = $derived(hunt.tracks.filter((t) => t.acquisition_status === 'owned').length);
	const total = $derived(hunt.tracks.length);
</script>

<div class="hunt-results">
	<div class="results-header">
		<div>
			<h3>{hunt.title || 'Untitled Set'}</h3>
			{#if hunt.uploader}
				<span class="uploader">by {hunt.uploader}</span>
			{/if}
		</div>
		<div class="gap-badge">
			{#if owned === total}
				<span class="badge owned">You own all {total} tracks</span>
			{:else}
				<span class="badge gap">Missing {total - owned} of {total}</span>
			{/if}
		</div>
	</div>

	<table class="track-table">
		<thead>
			<tr>
				<th class="col-pos">#</th>
				<th class="col-artist">Artist</th>
				<th class="col-title">Title</th>
				<th class="col-source">Source</th>
				<th class="col-status">Status</th>
				<th class="col-links">Links</th>
			</tr>
		</thead>
		<tbody>
			{#each hunt.tracks as track}
				<tr class:owned={track.acquisition_status === 'owned'}>
					<td class="col-pos">{track.position}</td>
					<td class="col-artist">{track.artist ?? '?'}</td>
					<td class="col-title">
						{track.title ?? '?'}
						{#if track.remix_info}
							<span class="remix">({track.remix_info})</span>
						{/if}
					</td>
					<td class="col-source">{track.source ?? ''}</td>
					<td class="col-status">
						{#if track.acquisition_status === 'owned'}
							<span class="status-owned">in library</span>
						{:else if track.acquisition_status === 'wanted'}
							<span class="status-wanted">wanted</span>
						{:else}
							<button class="want-btn" onclick={() => onmarkwanted(track.id)}>
								want
							</button>
						{/if}
					</td>
					<td class="col-links">
						{#if track.acquisition_status !== 'owned'}
							{#each Object.entries(track.purchase_links) as [store, url]}
								<a href={url} target="_blank" rel="noopener" class="store-link">
									{store}
								</a>
							{/each}
						{/if}
					</td>
				</tr>
			{/each}
		</tbody>
	</table>
</div>

<style>
	.hunt-results {
		font-size: 13px;
	}

	.results-header {
		display: flex;
		justify-content: space-between;
		align-items: start;
		margin-bottom: 12px;
	}

	.results-header h3 {
		margin: 0;
		font-size: 16px;
	}

	.uploader {
		color: var(--text-secondary);
		font-size: 12px;
	}

	.badge {
		padding: 4px 10px;
		border-radius: 12px;
		font-size: 12px;
		font-weight: 600;
	}

	.badge.owned {
		background: rgba(80, 200, 120, 0.15);
		color: #50c878;
	}

	.badge.gap {
		background: rgba(255, 200, 50, 0.15);
		color: #ffc832;
	}

	.track-table {
		width: 100%;
		border-collapse: collapse;
	}

	.track-table th {
		text-align: left;
		padding: 6px 8px;
		border-bottom: 1px solid var(--border);
		color: var(--text-secondary);
		font-size: 11px;
		text-transform: uppercase;
	}

	.track-table td {
		padding: 6px 8px;
		border-bottom: 1px solid var(--border-dim, rgba(255, 255, 255, 0.05));
	}

	tr.owned {
		opacity: 0.6;
	}

	.col-pos { width: 30px; text-align: right; color: var(--text-dim); }
	.col-source { color: var(--text-dim); font-size: 11px; }

	.remix {
		color: var(--text-dim);
		font-size: 12px;
	}

	.status-owned {
		color: #50c878;
		font-size: 11px;
	}

	.status-wanted {
		color: #ffc832;
		font-size: 11px;
	}

	.want-btn {
		padding: 2px 8px;
		font-size: 11px;
		background: transparent;
		border: 1px solid var(--border);
		border-radius: 4px;
		color: var(--text-secondary);
		cursor: pointer;
	}

	.want-btn:hover {
		border-color: #ffc832;
		color: #ffc832;
	}

	.store-link {
		display: inline-block;
		margin-right: 6px;
		padding: 1px 6px;
		font-size: 11px;
		color: var(--accent);
		text-decoration: none;
		border: 1px solid var(--border);
		border-radius: 3px;
	}

	.store-link:hover {
		background: var(--bg-hover);
	}
</style>
```

**12h.** Create `frontend/src/lib/components/hunt/HuntHistory.svelte`:
```svelte
<script lang="ts">
	import type { HuntSessionSummary } from '$lib/types';

	interface Props {
		items: HuntSessionSummary[];
		onselect: (id: number) => void;
	}

	let { items, onselect }: Props = $props();
</script>

<div class="hunt-history">
	<h3>Past Hunts</h3>
	{#if items.length === 0}
		<p class="empty">No hunts yet. Paste a URL to start your first hunt.</p>
	{:else}
		<div class="history-list">
			{#each items as item}
				<button class="history-item" onclick={() => onselect(item.id)}>
					<div class="item-title">{item.title || item.url}</div>
					<div class="item-meta">
						<span class="platform">{item.platform}</span>
						<span>{item.track_count} tracks</span>
						<span class="owned">{item.owned_count} owned</span>
					</div>
				</button>
			{/each}
		</div>
	{/if}
</div>

<style>
	.hunt-history h3 {
		margin: 0 0 8px;
		font-size: 14px;
	}

	.empty {
		color: var(--text-dim);
		font-size: 13px;
	}

	.history-list {
		display: flex;
		flex-direction: column;
		gap: 4px;
	}

	.history-item {
		display: block;
		width: 100%;
		text-align: left;
		padding: 8px 12px;
		background: var(--bg-secondary);
		border: 1px solid var(--border);
		border-radius: 6px;
		cursor: pointer;
	}

	.history-item:hover {
		background: var(--bg-hover);
	}

	.item-title {
		font-size: 13px;
		font-weight: 500;
		margin-bottom: 2px;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.item-meta {
		font-size: 11px;
		color: var(--text-dim);
		display: flex;
		gap: 8px;
	}

	.platform {
		text-transform: capitalize;
	}

	.owned {
		color: #50c878;
	}
</style>
```

Verification:
- `cd frontend && npx svelte-check --tsconfig ./tsconfig.json` — no errors in new files

#### Task 13 — Tests: unit tests + API tests

Tools: editor (create files)

**13a.** Edit `tests/api/conftest.py` — add hunt seed data:
````diff
--- a/tests/api/conftest.py
+++ b/tests/api/conftest.py
@@ from kiku.db.models import Base, Set, SetTrack, Track
+from kiku.db.models import Base, HuntSession, HuntTrack, Set, SetTrack, Track
@@
     # Seed tinder queue: tracks 1-10 have auto predictions at varying confidence
     for i in range(1, 11):
         t = session.get(Track, i)
         t.energy_predicted = "build" if i <= 5 else "peak"
         t.energy_confidence = i * 0.1  # 0.1 to 1.0
         t.energy_source = "auto"

+    # Seed a hunt session
+    hs = HuntSession(
+        id=1, url="https://www.youtube.com/watch?v=test123",
+        platform="youtube", title="Test DJ Set", uploader="TestDJ",
+        status="complete", track_count=3, owned_count=1,
+    )
+    session.add(hs)
+    session.flush()
+    session.add(HuntTrack(
+        session_id=1, position=1, artist="Artist 1", title="Track 1",
+        confidence=0.9, source="description", acquisition_status="owned",
+        matched_track_id=1, match_score=0.95, purchase_links="{}",
+    ))
+    session.add(HuntTrack(
+        session_id=1, position=2, artist="Unknown Artist", title="Mystery Track",
+        confidence=0.7, source="description", acquisition_status="unowned",
+        purchase_links='{"beatport":"https://www.beatport.com/search?q=test"}',
+    ))
+    session.add(HuntTrack(
+        session_id=1, position=3, artist="Another One", title="Deep Cut",
+        confidence=0.6, source="comment", acquisition_status="wanted",
+        purchase_links='{"bandcamp":"https://bandcamp.com/search?q=test"}',
+    ))
+
     session.commit()
````

**13b.** Create `tests/api/test_hunt_api.py`:
```python
"""Tests for Track Hunter API endpoints."""

from __future__ import annotations


def test_list_hunts(client):
    """GET /api/hunts returns seeded hunt sessions."""
    resp = client.get("/api/hunts")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["platform"] == "youtube"
    assert data["items"][0]["track_count"] == 3
    assert data["items"][0]["owned_count"] == 1


def test_get_hunt_detail(client):
    """GET /api/hunt/1 returns full hunt with tracks."""
    resp = client.get("/api/hunt/1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "Test DJ Set"
    assert len(data["tracks"]) == 3
    assert data["tracks"][0]["acquisition_status"] == "owned"
    assert data["tracks"][1]["acquisition_status"] == "unowned"


def test_get_hunt_not_found(client):
    """GET /api/hunt/999 returns 404."""
    resp = client.get("/api/hunt/999")
    assert resp.status_code == 404


def test_update_hunt_track_status(client):
    """PATCH /api/hunt/tracks/{id} updates acquisition status."""
    # Get track 2 (unowned) and mark as wanted
    resp = client.get("/api/hunt/1")
    track_id = resp.json()["tracks"][1]["id"]

    resp = client.patch(
        f"/api/hunt/tracks/{track_id}",
        json={"acquisition_status": "wanted"},
    )
    assert resp.status_code == 200
    assert resp.json()["acquisition_status"] == "wanted"


def test_update_hunt_track_invalid_status(client):
    """PATCH with invalid status returns 400."""
    resp = client.get("/api/hunt/1")
    track_id = resp.json()["tracks"][0]["id"]

    resp = client.patch(
        f"/api/hunt/tracks/{track_id}",
        json={"acquisition_status": "invalid"},
    )
    assert resp.status_code == 400


def test_hunt_track_purchase_links(client):
    """Hunt tracks with purchase links return them as dicts."""
    resp = client.get("/api/hunt/1")
    tracks = resp.json()["tracks"]
    # Track 2 has beatport link
    unowned = [t for t in tracks if t["acquisition_status"] != "owned"]
    assert len(unowned) >= 1
    assert "beatport" in unowned[0]["purchase_links"] or "bandcamp" in unowned[0]["purchase_links"]
```

**13c.** Create `tests/test_tracklist_parser.py`:
```python
"""Unit tests for tracklist parsers."""

from __future__ import annotations

from kiku.hunting.parsers.common import normalize_name, parse_artist_title, parse_remix
from kiku.hunting.parsers.tracklist import (
    merge_tracklists,
    parse_chapters,
    parse_comments,
    parse_description,
)


# ── common.py tests ──


def test_parse_artist_title_basic():
    assert parse_artist_title("Bicep - Glue") == ("Bicep", "Glue")


def test_parse_artist_title_em_dash():
    assert parse_artist_title("Four Tet — Baby") == ("Four Tet", "Baby")


def test_parse_artist_title_en_dash():
    assert parse_artist_title("Aphex Twin – Xtal") == ("Aphex Twin", "Xtal")


def test_parse_artist_title_no_separator():
    assert parse_artist_title("Just a track name") is None


def test_parse_remix():
    title, remix = parse_remix("Glue (Hammer Remix)")
    assert title == "Glue"
    assert remix == "Hammer Remix"


def test_parse_remix_no_remix():
    title, remix = parse_remix("Original Track")
    assert title == "Original Track"
    assert remix is None


def test_parse_remix_edit():
    title, remix = parse_remix("Track Name [DJ Edit]")
    assert title == "Track Name"
    assert remix == "DJ Edit"


def test_normalize_name():
    assert normalize_name("  BICEP  ") == "bicep"
    assert normalize_name("Artist feat. Singer") == "artist"
    assert normalize_name("Artist ft. Other") == "artist"


# ── tracklist.py tests ──


def test_parse_description_numbered():
    text = """Tracklist:
1. Bicep - Glue
2. Four Tet - Baby
3. Hammer - Catnip (Original Mix)
"""
    tracks = parse_description(text)
    assert len(tracks) == 3
    assert tracks[0].artist == "Bicep"
    assert tracks[0].title == "Glue"
    assert tracks[2].remix_info == "Original Mix"


def test_parse_description_timestamped():
    text = """00:00 Intro
03:15 Bicep - Glue
08:30 Four Tet - Baby
"""
    tracks = parse_description(text)
    assert len(tracks) >= 2
    bicep = next(t for t in tracks if t.artist == "Bicep")
    assert bicep.timestamp_sec == 195.0  # 3*60 + 15


def test_parse_description_empty():
    assert parse_description(None) == []
    assert parse_description("") == []


def test_parse_chapters():
    chapters = [
        {"title": "Bicep - Glue", "start_time": 0, "end_time": 300},
        {"title": "Four Tet - Baby", "start_time": 300, "end_time": 600},
    ]
    tracks = parse_chapters(chapters)
    assert len(tracks) == 2
    assert tracks[0].source == "chapter"
    assert tracks[0].confidence == 0.95


def test_parse_comments_timestamped():
    comments = [
        {"text": "32:15 Bicep - Glue", "timestamp": None, "author": "fan1"},
        {"text": "love this set!", "timestamp": None, "author": "fan2"},
    ]
    tracks = parse_comments(comments)
    assert len(tracks) == 1
    assert tracks[0].artist == "Bicep"
    assert tracks[0].timestamp_sec == 32 * 60 + 15


def test_merge_tracklists_dedup():
    from kiku.hunting.parsers.tracklist import ParsedTrack

    list_a = [ParsedTrack(position=1, artist="Bicep", title="Glue", confidence=0.9)]
    list_b = [ParsedTrack(position=1, artist="bicep", title="glue", confidence=0.6)]
    merged = merge_tracklists(list_a, list_b)
    assert len(merged) == 1
    assert merged[0].confidence == 0.9  # Higher confidence wins
```

**13d.** Create `tests/test_matcher.py`:
```python
"""Unit tests for fuzzy library matching."""

from __future__ import annotations

import pytest


def test_match_exact(db_session):
    """Exact match against library returns owned status."""
    from kiku.hunting.matcher import match_tracks

    extracted = [{"artist": "Artist 1", "title": "Track 1"}]
    result = match_tracks(db_session, extracted)
    assert result[0]["acquisition_status"] == "owned"
    assert result[0]["matched_track_id"] == 1


def test_match_no_match(db_session):
    """Unknown track returns unowned status."""
    from kiku.hunting.matcher import match_tracks

    extracted = [{"artist": "Completely Unknown", "title": "Nonexistent Song XYZ"}]
    result = match_tracks(db_session, extracted)
    assert result[0]["acquisition_status"] == "unowned"
    assert result[0]["matched_track_id"] is None


@pytest.fixture()
def db_session(tmp_path):
    """Minimal DB session for matcher tests."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import NullPool

    from kiku.db.models import Base, Track

    db_path = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db_path}", poolclass=NullPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    for i in range(1, 6):
        session.add(Track(
            id=i, title=f"Track {i}", artist=f"Artist {i}",
            bpm=125.0, key="8A",
        ))
    session.commit()
    yield session
    session.close()
    engine.dispose()
```

Verification:
- `source .venv/bin/activate && python -m pytest tests/test_tracklist_parser.py tests/test_matcher.py tests/api/test_hunt_api.py -x -q`
- All tests pass

#### Task 14 — Lint, type-check, commit

Tools: shell

**14a. Lint (Python):**
```bash
source .venv/bin/activate && python -m py_compile src/kiku/hunting/__init__.py && python -m py_compile src/kiku/hunting/parsers/__init__.py && python -m py_compile src/kiku/hunting/parsers/common.py && python -m py_compile src/kiku/hunting/extractor.py && python -m py_compile src/kiku/hunting/parsers/tracklist.py && python -m py_compile src/kiku/hunting/matcher.py && python -m py_compile src/kiku/hunting/sources.py && python -m py_compile src/kiku/api/routes/hunt.py && echo "All Python files compile OK"
```

**14b. Type-check (Frontend):**
```bash
cd frontend && npx svelte-check --tsconfig ./tsconfig.json
```

**14c. Run all tests:**
```bash
source .venv/bin/activate && python -m pytest tests/ -x -q
```

**14d. Commit:**
```bash
git add pyproject.toml \
  src/kiku/db/models.py \
  src/kiku/db/store.py \
  src/kiku/hunting/__init__.py \
  src/kiku/hunting/parsers/__init__.py \
  src/kiku/hunting/parsers/common.py \
  src/kiku/hunting/extractor.py \
  src/kiku/hunting/parsers/tracklist.py \
  src/kiku/hunting/matcher.py \
  src/kiku/hunting/sources.py \
  src/kiku/api/schemas.py \
  src/kiku/api/routes/hunt.py \
  src/kiku/api/main.py \
  src/kiku/cli.py \
  frontend/src/lib/types/index.ts \
  frontend/src/lib/api/hunt.ts \
  frontend/src/lib/stores/hunting.svelte.ts \
  frontend/src/lib/stores/ui.svelte.ts \
  frontend/src/lib/components/Workspace.svelte \
  frontend/src/lib/components/hunt/HuntView.svelte \
  frontend/src/lib/components/hunt/HuntResults.svelte \
  frontend/src/lib/components/hunt/HuntHistory.svelte \
  tests/api/conftest.py \
  tests/api/test_hunt_api.py \
  tests/test_tracklist_parser.py \
  tests/test_matcher.py

git commit -m "feat: Track Hunter — extract tracklists from DJ sets and hunt for purchase sources

Adds kiku hunt <url> CLI command and /api/hunt endpoints.
Supports YouTube, SoundCloud, Mixcloud via yt-dlp metadata extraction.
Parses descriptions, chapters, and comments for tracklists.
Fuzzy matches against local library, generates purchase links
for Beatport, Traxsource, Bandcamp, Juno.
Frontend Hunt tab (key 5) with URL input, results table, history."
```

### Validate

| Requirement | Compliance |
|-------------|-----------|
| **EXTRACT tracklists from DJ set URLs** (L10-14) | Task 4 (extractor.py) + Task 5 (tracklist.py) — parses descriptions, chapters, comments, copyright text |
| **NORMALIZE extracted track data** (L15) | Task 3 (common.py) — parse_remix, normalize_name, parse_artist_title; Task 5 merge_tracklists deduplicates |
| **HUNT for acquisition sources** (L16-20) | Task 7 (sources.py) — generates Beatport, Traxsource, Bandcamp, Juno search URLs |
| **Flag tracks already owned** (L20) | Task 6 (matcher.py) — fuzzy match against library, marks as "owned"/"unowned" |
| **PRESENT hunt results in UI** (L21-25) | Task 12f-h — HuntView with URL input, HuntResults with tracklist table, confidence, owned badges, purchase links, gap analysis badge |
| **STORE hunt sessions persistently** (L26) | Task 2 (HuntSession + HuntTrack models), Task 8 (CRUD functions) |
| **TEACH — show the Why** (L27) | Spec includes gap analysis ("Missing 4 of 12"), future Phase 4 extends with energy arc analysis |
| **SoundCloud** (L33) | yt-dlp handles extraction (Task 4) |
| **YouTube** (L34) | yt-dlp + chapter parsing (Task 4-5) |
| **Mixcloud** (L35) | yt-dlp handles extraction (Task 4) |
| **1001Tracklists** (L36) | Platform detected (Task 4), scraper is Phase 2 stretch |
| **Remix attribution** (L41) | parse_remix in common.py (Task 3) extracts remix info + original title |
| **Bootlegs/edits flagged** (L42) | REMIX_RE handles "bootleg", "edit", "rework" patterns (Task 3) |
| **CLI: kiku hunt <url>** (L63) | Task 11 — full CLI command with Rich table output |
| **API: POST /api/hunt, GET /api/hunt/{id}** (L64) | Task 10 — 4 API endpoints |
| **Unit tests for parsers** (L67) | Task 13c — 12 test cases for common + tracklist parsers |
| **Unit tests for normalization** (L68) | Task 13c — normalize_name, parse_remix tests |
| **Integration tests with mocked responses** (L69) | Task 13b — API tests with seeded hunt data |
| **Craft mentorship philosophy** (L75) | UI copy: "Hear a set you love? Paste the link above to hunt down every track." Gap badge: "Missing N of M" |

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
