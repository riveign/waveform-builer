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
<!-- Filled by explicit documentation updates after /spec IMPLEMENT -->

## Post-Implement Review
<!-- Filled by /spec REVIEW -->
