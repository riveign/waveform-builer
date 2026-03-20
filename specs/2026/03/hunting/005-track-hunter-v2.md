# Human Section
Critical: any text/subsection here cannot be modified by AI.

## High-Level Objective (HLO)

Evolve Track Hunter from a YouTube-focused extractor into a multi-source hunt engine that teaches DJs why a set works — not just what's in it. Improve extraction quality across platforms (1001Tracklists, SoundCloud, Mixcloud), strengthen library matching with artist alias resolution, and add the "teaching layer" that analyzes a hunted set's energy arc, genre flow, and key progression. The DJ should walk away understanding the curator's craft, not just holding a shopping list.

## Mid-Level Objectives (MLO)

- **EXTRACT** tracklists from 1001Tracklists (scraping), SoundCloud (Content ID equivalent), and Mixcloud (REST API) — expanding beyond YouTube
- **RESOLVE** artist aliases and remix variants via MusicBrainz lookup, so "Bicep" and "BICEP" match and remixes link to their originals
- **IMPROVE** library matching with normalized remix detection (strip "Original Mix"), BPM proximity as tiebreaker, and key/Camelot match bonus
- **ANALYZE** hunted tracklists using Kiku's existing scoring to reveal energy arc, genre flow, and key progression — show "what makes this set work"
- **IMPORT** hunt results as a set template: pre-populate owned tracks, mark gaps for the DJ to fill with their own alternatives
- **LINK** timestamps to source video (clickable → opens YouTube at that point) so the DJ can hear each track in context
- **AGGREGATE** wanted tracks across all hunt sessions into a unified want list / shopping list view
- **FIX** technical debt: add `requests` to `[hunting]` extras, harden Content ID scraping against YouTube JSON changes

## Details (DT)

### Current State (spec 004 — implemented)

- YouTube extraction via yt-dlp (description, chapters, comments)
- YouTube Content ID scraping (`ytInitialData` → `videoAttributeViewModel` cards)
- Fuzzy dedup in merge (thefuzz ≥85%), timestamp preservation across sources
- Library matching via artist+title fuzzy match
- Purchase search URL generation (Beatport, Traxsource, Bandcamp, Juno)
- Hunt tab UI with time column, owned badges, want button, purchase links

### 1001Tracklists Integration

- Scrape `1001tracklists.com/tracklist/` pages — crowd-sourced tracklists with timestamps and purchase links already attached
- Search fallback: if user provides a YouTube/SoundCloud URL, search 1001TL by set title to find matching tracklist
- Anti-bot: rate limit (1 req/2s), user-agent rotation, respect robots.txt
- Parser: BeautifulSoup on HTML, extract track rows (artist, title, label, timestamp, purchase URLs)

### SoundCloud Content ID

- Investigate whether yt-dlp exposes SoundCloud's auto-detected tracks
- If not, apply same `ytInitialData`-style scraping approach to SoundCloud's page JSON
- SoundCloud's API is effectively closed — scraping is the only path

### Mixcloud API

- REST endpoint: `https://api.mixcloud.com/{user}/{mix}/` returns JSON with `sections` containing track names
- Timestamps may be restricted by licensing (Mixcloud hides them) — extract track names even without times
- No auth required

### MusicBrainz Resolution

- `musicbrainzngs` is already a dependency but unused in hunt flow
- Use `search_recordings(query=f"{artist} {title}")` to:
  - Resolve artist name variants (case, aliases, "feat." vs "ft.")
  - Find original version of remixes (link remix → original recording)
- Rate limit: 1 req/sec (handled by library)

### Smarter Library Matching

- Strip "(Original Mix)", "(Extended Mix)", "(Radio Edit)" before fuzzy matching
- When multiple fuzzy matches exist (score >85%), use BPM proximity as tiebreaker
- Optional: Camelot key compatibility as bonus signal

### Set DNA Analysis (Teaching Layer)

- For owned tracks in a hunt, compute:
  - Energy arc (using `resolved_energy_zone` from track model)
  - Genre flow (family transitions using `RB_GENRE_TO_FAMILY`)
  - Key progression (Camelot wheel movement)
- Present as a mini DNA view alongside hunt results
- Frame as "here's why this set flows" — the Kiku differentiator

### Import as Set Template

- Button in HuntResults: "Build from this set"
- Creates a new Kiku set with:
  - Owned tracks placed at their positions
  - Gaps marked with placeholder entries showing the missing track info
- DJ can then use Replace Track to fill gaps with alternatives from their library

### Clickable Timestamps

- If source URL is YouTube, each timestamp in the time column links to `{url}&t={seconds}s`
- Opens in new tab so the DJ can hear the track in the original set context

### Want List Aggregation

- New view (or sub-tab in Hunt): aggregate all "wanted" tracks across all hunt sessions
- Group by store for efficient shopping
- De-duplicate across sessions (same track wanted from multiple hunts)

### Technical Debt

- Add `requests` to `[hunting]` extras in pyproject.toml (used by Content ID scraping)
- Content ID scraping: add fallback/retry logic, handle `ytInitialData` structure changes gracefully
- Consider switching to `urllib.request` (stdlib) to avoid the dependency

### Testing

- Unit tests for 1001Tracklists HTML parser (canned HTML → expected tracklist)
- Unit tests for Mixcloud API response parser (canned JSON → expected tracks)
- Unit tests for MusicBrainz resolution (mocked API → normalized names)
- Unit tests for improved fuzzy matching (remix stripping, BPM tiebreaker)
- Integration test: hunt with multiple sources merged correctly
- E2E: import hunt as set template → verify set created with correct tracks

## Behavior

You are building the next evolution of Kiku's Track Hunter — a feature that embodies the "Show the Why" principle. The teaching layer is the highest-value addition: when a DJ hunts a set, they should learn something about why the set works, not just get a list of tracks to buy. Prioritize the set DNA analysis and import-as-template features over additional platform integrations if scope needs trimming. Always frame results as "learning from the greats" not "copying playlists."

# AI Section
Critical: AI can ONLY modify this section.

## Research
<!-- Filled by /spec RESEARCH -->

## Plan
<!-- Filled by /spec PLAN -->

## Plan Review
<!-- Filled if required to validate plan -->

## Implement
<!-- Filled by /spec IMPLEMENT -->

## Test Evidence & Outputs
<!-- Filled by explicit testing after /spec IMPLEMENT -->

## Updated Doc
<!-- Filled by explicit documentation udpates after /spec IMPLEMENT -->

## Post-Implement Review
<!-- Filled by /spec REVIEW -->
