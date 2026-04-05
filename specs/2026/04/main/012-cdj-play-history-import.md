# Human Section
Critical: any text/subsection here cannot be modified by AI.

## High-Level Objective (HLO)

Import CDJ/XDJ play history from USB sticks into Kiku so DJs can learn from their live sets. When a DJ plugs in the USB they gig with, Kiku reads which tracks were played, in what order, and when — turning every gig into a lesson about what worked and why.

## Mid-Level Objectives (MLO)

1. **READ** Pioneer USB play history from `PIONEER/rekordbox/export.pdb` (legacy Device Library format) — extract HISTORY playlists with track order and session dates
2. **MATCH** history tracks to Kiku library entries using the existing track matching pipeline (exact path → case-insensitive → fuzzy duration match)
3. **CREATE** sets in Kiku from each CDJ history session, preserving play order and session date
4. **SUPPORT** Rekordbox desktop history as a secondary source — read `DjmdHistory` + `DjmdSongHistory` tables via pyrekordbox for DJs who sync USB back to Rekordbox first
5. **EXPOSE** via CLI (`kiku import-history <usb-path>`) and API (`POST /api/sets/import/cdj-history`)
6. **DETECT** format automatically — PDB (legacy) vs Device Library Plus (encrypted SQLite on newer CDJs like CDJ-3000)
7. **TRIGGER** auto-analysis on imported history sets so the DJ immediately sees transition scores and teaching moments

## Details (DT)

### Pioneer USB Structure
- USB sticks exported from Rekordbox have `PIONEER/rekordbox/export.pdb` (DeviceSQL binary format)
- CDJs write history rows directly into `export.pdb` during playback — no separate history files
- History playlists are named by date (e.g., "HISTORY 001") containing tracks in play order
- Track registered after ~60s of selection/playback on deck
- Max 999 tracks per history session

### Data Available per Session
- Track list in play order (track_id references into the track table)
- Session date (from playlist name)
- Full track metadata via track table join (title, artist, BPM, key, genre, duration, file_path)
- **NOT available**: per-track timestamps, play counts (CDJs don't update play_count on USB)

### Device Library Plus (Newer CDJs)
- CDJ-3000, XDJ-XZ with recent firmware use encrypted SQLite (`PIONEER/rekordbox/master.db`)
- pyrekordbox can decrypt with SQLCipher via `[unlocked]` extra
- History stored in SQLite tables rather than PDB binary format
- `rbox` library also supports this format

### Existing Kiku Capabilities
- pyrekordbox v0.4.4 already installed (sync, ANLZ waveform import, XML export)
- USB mount access pattern proven via `kiku import-waveforms` (reads `PIONEER/USBANLZ`)
- Track matching pipeline exists from M3U8 import (exact → nocase → fuzzy ±10s)
- Auto-analysis pipeline exists from set-analysis feature (spec 011)
- DB has `play_count` + `kiku_play_count` columns, but no session-level history table

### Phasing
- **Phase 1**: PDB history reader — covers most CDJ gigs (CDJ-2000NXS2, XDJ-1000MK2, etc.)
- **Phase 2**: Rekordbox desktop history — read from `DjmdHistory`/`DjmdSongHistory` tables
- **Phase 3**: Device Library Plus — encrypted SQLite for CDJ-3000 and newer

### Dependencies
- PDB parsing: `crate_digger` (Java) or Kaitai Struct + `rekordbox_pdb.ksy` (Python-compilable) or write minimal parser using Deep Symmetry's reverse-engineering docs
- Device Library Plus: pyrekordbox `[unlocked]` extra + SQLCipher

### Testing
- Unit tests: PDB parser with fixture data (sample export.pdb with known history)
- Integration tests: import flow from USB path → matched tracks → created set
- E2E: plug USB, run CLI, verify set appears in frontend with analysis

## Behavior

You are a senior backend engineer building on Kiku's existing import infrastructure. Reuse the track matching pipeline from M3U8 import (`src/kiku/import_playlist/service.py`). Follow the same patterns as `import-waveforms` for USB mount detection. Sets created from CDJ history should be marked with `source='cdj_history'` and trigger auto-analysis like M3U8 imports do.

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
