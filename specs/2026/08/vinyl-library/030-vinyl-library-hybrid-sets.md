# Human Section
Critical: any text/subsection here cannot be modified by AI.

## High-Level Objective (HLO)
Let the DJ add records they own on **vinyl** to the Kiku library by hand — type an album name, pick the right release, and have Kiku fill in the tracklist, side positions, durations, label, year, and then BPM, key, danceability and mood per track — so the set builder can plan **hybrid sets** that move deliberately between the turntables and the CDJs instead of pretending the crate doesn't exist.

Today the library is whatever Rekordbox knows about, which means it is whatever exists as a file. Every record on the shelf is invisible to Taste DNA, to `kiku gaps`, to beam search, and to every transition the tool teaches. That is a real hole in a tool whose whole claim is that it helps you understand *your* library: for a DJ who plays both formats, the digital-only picture is not a smaller version of the truth, it is a distorted one — gaps get reported that the shelf already fills, and the arc Kiku plans can never include the record that would obviously have gone there.

The insight that makes this cheap: **the set builder does not need audio files.** Its candidate pool is `Track.bpm IS NOT NULL AND Track.bpm > 0` (`src/kiku/setbuilder/planner.py:92`) and nothing in `planner.py`, `scoring.py`, or `constraints.py` reads `file_path`; `scoring.py:317-321` already degrades from `audio_features.energy` to the resolved zone to a neutral 0.5. A vinyl track carrying BPM, key and duration is a first-class citizen of beam search the moment it exists as a row. The work is therefore **getting good rows in**, **stopping the file-shaped features from breaking on them**, and **teaching the planner that a format change costs something**.

## Mid-Level Objectives (MLO)
- ADD a `medium` column to `Track` (`"digital"` default, `"vinyl"`) plus `vinyl_position` (the side string — `A1`, `B2`, `Digi 1`), via an Alembic migration. Backfill every existing row to `"digital"`. Alembic is the sole schema authority here (`src/kiku/db/models.py:_init_schema`) — no `create_all`.
- ADD a manual release-import path: search a release by album (+ optional artist) across the existing sources, show candidates, let the DJ pick one, and write one `Track` row per recording with `medium="vinyl"`, `album`, `artist`, `label`, `release_year`, `track_number`, `disc_number`, `duration_sec`, and `vinyl_position`. Discogs is the preferred source for vinyl because it carries real side positions; MusicBrainz is the fallback and the MBID carrier.
- ADD an enrichment step that fills `bpm`, `key`, and an `AudioFeatures` row (`danceability`, `mood_happy`, `mood_sad`, `mood_aggressive`, `mood_relaxed`) from **AcousticBrainz**, keyed by the MusicBrainz **recording** MBID. Derive `vibe_brightness`/`vibe_density` through the existing `kiku.vibe` path so vinyl tracks score on the same axes as everything else.
- ADD `mbid` to `RecordingCandidate` (`src/kiku/metadata/models.py`) and populate it in `MusicBrainzSource._to_candidate` from `track["recording"]["id"]` — the field is already in the MB response and currently discarded. Discogs releases reach an MBID by a secondary MB search on album+artist.
- ENSURE enrichment is honest about misses: AcousticBrainz froze in 2022, so recent and underground vinyl will have no submission. A track with no BPM must land in the library **flagged and editable**, never silently guessed. Manual BPM/key entry is the always-available fallback and must set a source marker so it is never overwritten by a later enrichment pass.
- ADD medium-aware set planning: a target vinyl ratio and a **deck-change penalty** in the beam-search scoring so a hybrid set groups records into runs instead of alternating formats every track. The penalty must be a bounded soft bias in the shape of the existing `_ROLE_SPAN` / `_VIBE_SPAN` / `_ARTIST_SPAN` nudges (`src/kiku/setbuilder/planner.py`) — it biases close calls, it never removes a track from the pool.
- ADD the changeover to the set view: a vinyl badge on the track row and an explicit marker on the transition strip where the format changes, with the side to cue (`B2`) shown so the DJ knows what to pull.
- ENSURE file-shaped features fail gracefully rather than half-work on fileless tracks: audio streaming (`src/kiku/api/routes/audio.py:35`) already 404s correctly; **`kiku export` must not emit a broken `Location`** — Rekordbox XML (`src/kiku/export/rekordbox_xml.py:71`) and M3U8 (`src/kiku/export/m3u8.py:81`) currently fall back to `""` for a missing path. Decide and implement one behavior: skip vinyl tracks from the exported playlist and report the skips, or emit them as a comment line. Waveform, cue points, playback, and the transition inspector must degrade with a stated reason, not an empty chart.
- ENSURE `kiku sync` never touches vinyl rows. Reconciliation today matches on `rb_id` then normalized `file_path` (`src/kiku/db/sync.py:157-158`) and deletes nothing, so vinyl survives — add a regression test that pins this, because it is the one silent-data-loss risk in the feature.
- ENSURE library stats, `kiku gaps`, and Taste DNA can be read per-medium (digital / vinyl / both), so the gap report stops recommending records the DJ already owns.
- ENSURE `cd frontend && npx svelte-check --tsconfig ./tsconfig.json` passes and the Python test suite is green.

## Details (DT)

### Decisions already taken
- **Enrichment source: AcousticBrainz via MusicBrainz recording MBID.** Chosen because its features come from the same Essentia model family Kiku already runs locally (`models/mood_*-msd-musicnn-1.pb`), so a vinyl track's mood and danceability land on the *same scale* as an analyzed digital track. Anything else — a BPM-only web lookup, a hand-typed number — puts vinyl on a different measuring stick and quietly corrupts every comparison the tool makes.
- **Set-builder treatment: medium-aware planning** — a vinyl ratio target plus a deck-change penalty, with the changeover surfaced in the timeline. Not a filter, not a silent merge.
- **One `tracks` table, not a separate vinyl entity.** `TrackAffinity`, `SetTrack`, `TransitionCue`, the tinder queue, and every scoring path key off `Track.id`. A parallel table would fork all of them; a `medium` column forks none.

### Known risks, in priority order
1. **AcousticBrainz coverage is the whole feature's load-bearing assumption and it is unproven.** The dataset stopped accepting submissions in 2022 and is skewed toward well-known catalog. A DJ's vinyl crate is exactly the population most likely to miss: recent 12"s, small-label electronic, white labels. **This needs a spike before anything else is built** — take 20-30 real records off the shelf, resolve them to recording MBIDs, and measure the actual hit rate for BPM, key, and the mood models separately. If the hit rate is poor, the plan does not collapse (manual entry and a rip-and-analyze path both remain), but the shape of the UI changes from "confirm what we found" to "fill in what we couldn't", and that should be known before the UI is written.
2. **Two-hop identity resolution (Discogs release → MusicBrainz release → recording MBID → AcousticBrainz)** is a fuzzy match on top of a fuzzy match. Every hop needs a visible confidence and a manual override; a wrong MBID silently attaches another record's BPM and mood, which is worse than a blank.
3. **A vinyl track with a BPM enters the candidate pool immediately** — `planner.py:92` has no medium filter. Until the ratio control ships, a routine digital set build will start returning records. The migration and the planner change should land together, or the default ratio must be 0 until the control exists.
4. **Export is the sharpest edge.** A vinyl track exported to Rekordbox XML today gets `Location=""`. That is a corrupt playlist entry, not a graceful degradation.

### What already exists and should be reused, not rebuilt
- `src/kiku/metadata/sources/discogs.py` — a working Discogs client with token handling, release search, URL fetch, and duration parsing. Its own docstring names vinyl side positions as its strength. It currently discards `position` strings into an `int` — the raw `A1`/`B2` string is what `vinyl_position` needs.
- `src/kiku/metadata/sources/` registry, `MetadataSource` protocol, `ReleaseCandidate`/`RecordingCandidate` shapes, and the `available_sources()` UI descriptor. A new AcousticBrainz enricher is *not* a `MetadataSource` — it enriches recordings, it does not identify releases — so it belongs in a sibling module rather than the source registry.
- `src/kiku/musicbrainz/client.py` — already throttled to MB's rate limit, already fetches `inc=recordings+artist-credits+labels`.
- `src/kiku/metadata/correct.py` + `album_metadata` table — the existing per-album match/apply/skip machinery. A manual vinyl import is close kin to an album correction and should borrow its diff-preview-then-apply shape rather than inventing a second one.
- `src/kiku/energy.py`, `src/kiku/vibe.py` — the resolution paths that make a partially-known track scoreable.

### Open questions for the AI Section to answer
- Does a vinyl track without a BPM belong in the library at all, or in a staging state until it has one? (It has real value in Taste DNA and gap analysis even unscoreable, but it cannot be planned.)
- Where does manual per-track BPM/key entry live — the existing track detail view, or a dedicated post-import fill-in screen? The AcousticBrainz coverage spike should decide this.
- Should a rip-and-analyze path (line-in recording → existing `kiku analyze`) be a documented escape hatch for records that matter most? It is the only route to a waveform, cue points, and the transition inspector for vinyl.
- `duration_sec` from Discogs is the pressed length; the played length at a pitched BPM differs. Does the set's time budget need to account for that?

## Behavior
- `kiku vinyl add "Album Name"` searches the configured sources, prints candidates with track counts, and on selection writes the tracklist as vinyl rows with a rich before/after summary and `--dry-run`/`--yes`, matching `kiku fix-album`'s established shape.
- `kiku vinyl enrich` fills BPM/key/mood for vinyl rows missing them and reports per-track hit/miss.
- The library view gains a medium filter and a vinyl badge; search results show the side position where one exists.
- A build with a non-zero vinyl ratio returns a set whose records are grouped, with every format changeover marked in the timeline and the side to cue named.
- `kiku sync` after a vinyl import leaves every vinyl row untouched.

# AI Section

## Research

### R1 — The AcousticBrainz coverage spike (2026-09-09) — **the assumption is falsified**

Risk 1 in the Human Section called AcousticBrainz coverage "the whole feature's
load-bearing assumption" and asked for a measurement before anything was built.
The measurement now exists: `scripts/ab_coverage_spike.py`.

**Result on a 25-album sample of the DJ's own digital library** — the same
population as the crate (small-label electronic, EPs, edits), and by the design's
own reasoning an *upper bound*, since records owned on vinyl skew newer and more
obscure still:

| | |
|---|---|
| Records asked about | 25 |
| Resolved to an MB release (score 100) | **10** |
| Not in MusicBrainz at all | **14** |
| Recordings resolved from those 10 | 54 |
| **Recordings with a BPM in AcousticBrainz** | **1 / 54 — 1.9%** |
| Recordings with a key | 1 / 54 |
| Recordings with all four moods + danceability | 1 / 54 |

The single hit is Bronski Beat's "Smalltown Boy" (1984) — a chart record reached
through a rework's tracklist. Every 2020s techno recording missed. That is
precisely the skew the Human Section predicted, arriving at full strength.

**This is not a plumbing failure.** The pipeline was verified end to end: the AB
API is live and serving (BPM, key, all four `mood_*` models and `danceability`
in the shape the design assumed), the batch endpoints work, and the one hit
returns real numbers through the same code path as every miss. A miss is a
literal `{"mbid_mapping":{}}` — the recording has never been submitted. Checked
by hand for Alarico — "AF 97" (Klockworks 38, 2022).

An early run was thrown away: 16 of 25 lookups came back `503`. MusicBrainz's
1 req/s is an *average*, not a licence to send one per second forever, and a 503
is "come back later", never a miss. The spike now backs off exponentially and
the number above is from a clean run.

### R2 — What this changes

1. **Enrichment is not the acquisition path. Manual entry is.** At ~2%, an
   "enrich and confirm" import would show the DJ 49 blank rows out of 50. The
   import must be built as *fill in what we couldn't*, with per-track BPM/key
   entry as the primary, first-class path — not the fallback the Human Section
   allowed for. This answers the open question "where does manual BPM/key entry
   live": it is the import screen itself, not a later visit to track detail.

2. **A second, larger identity problem sits in front of it.** 14 of 25 records
   are not in MusicBrainz *at all*. Even if AcousticBrainz were rich, the MBID
   hop would strand more than half the crate. The Discogs → MB URL-relation path
   (design Stage 2, path 1) is worth measuring separately, because Discogs
   catalogues underground electronic vinyl far better than MB does — but it
   cannot rescue enrichment, only identity and catalog facts (label, catno,
   side positions), which is where its real value now lies.

3. **The precedence ladder survives, with its rungs reweighted.** `manual` was
   rank 1 and stays there; `acousticbrainz` at rank 4 is now a rare bonus rather
   than the workhorse. Nothing in the design's provenance model needs to change —
   it was built for exactly this, which is why it should be kept.

4. **Rip-and-analyze stops being an escape hatch.** The Human Section asked
   whether it should be "a documented escape hatch for records that matter most".
   At 2% enrichment it is the only route to Essentia-grade features for vinyl,
   and the only route to a waveform, cue points and the transition inspector.
   It should be planned, not merely documented.

5. **The build order changes.** Steps 4 and 5 (identity resolution, enrichment)
   drop below the manual-entry UI. `vinyl_releases`, the `medium` column, the
   Discogs `position` retention and `vinyl/position.py` are all unaffected and
   still come first — they are what make a record exist at all.

**Recommendation:** proceed with the feature, but with AcousticBrainz demoted from
mechanism to garnish. The insight that makes spec 030 cheap is untouched — a
vinyl row with a BPM is a first-class citizen of beam search (`planner.py:92`)
regardless of where the BPM came from. The question was only ever who types it.
The answer is: the DJ, for now.

### R3 — Verified API facts (so the next stage need not re-check)

- `GET https://acousticbrainz.org/api/v1/low-level?recording_ids=<a>;<b>` — live,
  200s, batch works. `rhythm.bpm`, `tonal.key_key` + `tonal.key_scale`.
- `GET .../high-level?recording_ids=…` — 18 models present, including
  `danceability` and all four `mood_*` the design named. Each is a binary model;
  the positive side is keyed by the model's own suffix (`mood_happy.all.happy`).
- Batch of 25 accepted. Absence is a 200 with the MBID missing from the body,
  never an error — read it, don't catch it.
- MusicBrainz recording MBIDs live at `media[].tracks[].recording.id`, confirmed
  present and currently discarded by `MusicBrainzSource._to_candidate`.
- **Not verified:** the Discogs → MB URL-relation lookup. No Discogs token is
  configured (`~/.kiku/config.toml` does not exist, `KIKU_DISCOGS_TOKEN` unset),
  so Stage 2 path 1 remains unmeasured. It is now the highest-value open question.


## Plan

## Plan Review

## Implement

## Test Evidence & Outputs

## Updated Doc

## Post-Implement Review
