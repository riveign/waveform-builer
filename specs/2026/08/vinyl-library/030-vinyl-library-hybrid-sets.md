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

**Scope: SLICE 1 — "a record exists, and it is plannable."** The deck-change
penalty, the vinyl ratio control, the changeover markers in the set view, and
AcousticBrainz enrichment are all **deferred to a slice-2 spec**. Research R2
demoted enrichment from mechanism to garnish; the DJ types the BPM, so slice 1
is: make the row exist, make it honest about where its numbers came from, make
the file-shaped features degrade instead of half-work, and change nothing about
an existing digital build.

### Decisions this plan settles

1. **Export behavior for fileless tracks: skip and report** (Human Section asked
   for one behavior; this is it). A Rekordbox XML entry with `Location=""` is a
   corrupt row, not a degraded one, and pyrekordbox will happily write it. Both
   exporters therefore omit fileless tracks from the playlist body and return
   what they skipped. M3U8 additionally leaves a `# kiku:vinyl …` comment naming
   the record and the side, because M3U8 *has* a comment mechanism and Rekordbox
   ignores it — the DJ opening the file sees "pull B2" instead of a silent hole.
   An `#EXTINF` line is never emitted without its path line.
2. **Risk 3 is closed by making the beam-search pool digital-by-default.**
   `_get_candidate_pool` gains `include_vinyl: bool = False`. Until the ratio
   control ships, a routine `kiku build` returns exactly what it returned before
   the migration. `insights.py` (Taste DNA, `kiku gaps`) is deliberately **not**
   filtered — a record you own should stop the gap report recommending it, which
   is the whole point of the feature.
3. **`medium` is backfilled, never left NULL — and every query still coalesces.**
   `func.coalesce(Track.medium, "digital")` is used at the filter sites, because
   `Track.medium != "vinyl"` silently drops NULL rows in SQL and that is exactly
   the kind of bug that eats a library.
4. **No `server_default` on the new columns.** `tests/test_migrations.py`
   compares the migrated schema against the ORM and only excludes `modify_type`
   noise; a server default would show up as `modify_default` drift. The migration
   backfills with an explicit `UPDATE` instead.
5. **The import path in slice 1 is the CLI** (`kiku vinyl add`), which is exactly
   what the Human Section's Behavior list describes. The only frontend work is
   the badge and the medium filter it also names — both additive to existing
   recipes (the `SetRoleBadge` pip, the `role-toggle` row), so there is no new
   surface needing a design-and-approve pass.
6. **`duplicate_of_track_id` gets its column but not its detector.** Design §4's
   fuzzy duplicate link is real work with a real failure mode (a wrong link
   collapses two different records); the column lands now so slice 2 can fill it
   without a second migration.

### Files

- `alembic/versions/a2b4c6d8e0f1_add_vinyl_medium_and_releases.py` *(new)*
  - Revision `a2b4c6d8e0f1`, down_revision `c2d3e4f5a6b7` (current head).
  - Creates `vinyl_releases`; adds 8 columns to `tracks` and `source` to
    `audio_features`; backfills `medium='digital'` and `source='essentia'`.
- `src/kiku/db/models.py`
  - L36-70: `Track` gains the 8 vinyl columns + `__table_args__`.
  - L86-120: `AudioFeatures` gains `source`.
  - New `VinylRelease` model after `AlbumMetadata`.
- `src/kiku/vinyl/__init__.py`, `src/kiku/vinyl/position.py` *(new)*
  - `parse_position("B2") -> (2, 2)`; `"Digi 1" -> (None, 1)`; `"A" -> (1, 1)`.
- `src/kiku/vinyl/importer.py` *(new)*
  - `search_releases`, `build_preview`, `apply_import`, `set_manual_bpm_key`.
- `src/kiku/metadata/models.py`
  - L27-33: `RecordingCandidate` gains `mbid`, `position_raw`.
  - L36-49: `ReleaseCandidate` gains `catalog_number`, `country`, `format`, `cover_url`.
- `src/kiku/metadata/sources/discogs.py`
  - L93-121: retain the raw `position` string and derive side/index from it;
    carry catno/country/format/cover onto the candidate.
- `src/kiku/metadata/sources/musicbrainz.py`
  - L52-66: stop discarding `track["recording"]["id"]`.
- `src/kiku/setbuilder/planner.py`
  - L86-103: `_get_candidate_pool(..., include_vinyl=False)`.
- `src/kiku/export/utils.py`
  - New `SkippedTrack` / `ExportResult` dataclasses.
- `src/kiku/export/m3u8.py` L52-85, `src/kiku/export/rekordbox_xml.py` L69-78
  - Skip fileless tracks; return `ExportResult`.
- `src/kiku/cli.py` L725-767 (export callers), new `vinyl` group at end of file.
- `src/kiku/api/routes/export.py` L29, L68 — unwrap `ExportResult`.
- `src/kiku/visualization/callbacks.py` L591 — unwrap `ExportResult`.
- `src/kiku/db/store.py` L91-206 — `medium` filter on `search_tracks`.
- `src/kiku/api/schemas.py` L36-67 — `TrackResponse` vinyl fields.
- `src/kiku/api/routes/tracks.py` L64-92, L98-135 — map + accept `medium`.
- `frontend/src/lib/api/tracks.ts` L4-22 — `medium` search param.
- `frontend/src/lib/components/library/VinylPip.svelte` *(new)*
- `frontend/src/lib/components/library/TrackTable.svelte` L1-13, L126-133 — pip in the title cell.
- `frontend/src/lib/components/library/SearchFilters.svelte` — medium select + chip + clear.
- `tests/test_vinyl_position.py`, `tests/test_vinyl_import.py`,
  `tests/test_vinyl_sync_regression.py`, `tests/test_export_fileless.py`,
  `tests/test_planner.py` *(one added test)*


### Tasks

#### Task 1 — Alembic migration: vinyl_releases + medium columns
Tools: editor

Create `alembic/versions/a2b4c6d8e0f1_add_vinyl_medium_and_releases.py` with EXACTLY this content:

````diff
--- /dev/null
+++ b/alembic/versions/a2b4c6d8e0f1_add_vinyl_medium_and_releases.py
@@
+"""add vinyl_releases table and medium columns to tracks
+
+Revision ID: a2b4c6d8e0f1
+Revises: c2d3e4f5a6b7
+Create Date: 2026-09-10 10:00:00.000000
+
+"""
+
+from typing import Sequence, Union
+
+from alembic import op
+import sqlalchemy as sa
+
+
+# revision identifiers, used by Alembic.
+revision: str = "a2b4c6d8e0f1"
+down_revision: Union[str, None] = "c2d3e4f5a6b7"
+branch_labels: Union[str, Sequence[str], None] = None
+depends_on: Union[str, Sequence[str], None] = None
+
+
+def upgrade() -> None:
+    op.create_table(
+        "vinyl_releases",
+        sa.Column("id", sa.Integer(), nullable=False),
+        sa.Column("discogs_release_id", sa.String(), nullable=True),
+        sa.Column("mb_release_id", sa.String(), nullable=True),
+        sa.Column("title", sa.String(), nullable=True),
+        sa.Column("artist", sa.String(), nullable=True),
+        sa.Column("label", sa.String(), nullable=True),
+        sa.Column("catalog_number", sa.String(), nullable=True),
+        sa.Column("year", sa.Integer(), nullable=True),
+        sa.Column("country", sa.String(), nullable=True),
+        sa.Column("format", sa.String(), nullable=True),
+        sa.Column("rpm", sa.Integer(), nullable=True),
+        sa.Column("side_count", sa.Integer(), nullable=True),
+        sa.Column("cover_url", sa.String(), nullable=True),
+        sa.Column("acquired_on", sa.String(), nullable=True),
+        sa.Column("notes", sa.Text(), nullable=True),
+        sa.Column("created_at", sa.String(), nullable=True),
+        sa.PrimaryKeyConstraint("id"),
+        sa.UniqueConstraint("discogs_release_id", name="uq_vinyl_release_discogs_id"),
+    )
+
+    op.add_column("tracks", sa.Column("medium", sa.String(), nullable=True))
+    op.add_column("tracks", sa.Column("vinyl_release_id", sa.Integer(), nullable=True))
+    op.add_column("tracks", sa.Column("vinyl_position", sa.String(), nullable=True))
+    op.add_column("tracks", sa.Column("mb_recording_id", sa.String(), nullable=True))
+    op.add_column("tracks", sa.Column("bpm_source", sa.String(), nullable=True))
+    op.add_column("tracks", sa.Column("key_source", sa.String(), nullable=True))
+    op.add_column("tracks", sa.Column("enrichment_status", sa.String(), nullable=True))
+    op.add_column("tracks", sa.Column("duplicate_of_track_id", sa.Integer(), nullable=True))
+
+    # A record you own is one physical object: one side position per pressing.
+    # Digital rows leave both columns NULL, and SQLite treats NULLs as distinct,
+    # so this constrains vinyl only.
+    op.create_index(
+        "uq_track_vinyl_side",
+        "tracks",
+        ["vinyl_release_id", "vinyl_position"],
+        unique=True,
+    )
+    op.create_index("ix_tracks_medium", "tracks", ["medium"])
+
+    op.add_column("audio_features", sa.Column("source", sa.String(), nullable=True))
+
+    # Backfill, so nothing downstream ever meets a NULL medium. Everything that
+    # existed before this migration came from a file.
+    op.execute("UPDATE tracks SET medium = 'digital' WHERE medium IS NULL")
+    op.execute("UPDATE audio_features SET source = 'essentia' WHERE source IS NULL")
+
+
+def downgrade() -> None:
+    op.drop_column("audio_features", "source")
+    op.drop_index("ix_tracks_medium", table_name="tracks")
+    op.drop_index("uq_track_vinyl_side", table_name="tracks")
+    op.drop_column("tracks", "duplicate_of_track_id")
+    op.drop_column("tracks", "enrichment_status")
+    op.drop_column("tracks", "key_source")
+    op.drop_column("tracks", "bpm_source")
+    op.drop_column("tracks", "mb_recording_id")
+    op.drop_column("tracks", "vinyl_position")
+    op.drop_column("tracks", "vinyl_release_id")
+    op.drop_column("tracks", "medium")
+    op.drop_table("vinyl_releases")
````

Verification:
- `source .venv/bin/activate && python -m pytest tests/test_migrations.py -x -q` — all three tests pass (they build the schema from base and diff it against the ORM, so this will FAIL until Task 2 lands; run it after Task 2).
- `grep -c "down_revision" alembic/versions/*.py` — no other revision may claim `c2d3e4f5a6b7` as its parent.


#### Task 2 — models.py: Track vinyl columns, AudioFeatures.source, VinylRelease
Tools: editor

Diff:
````diff
--- a/src/kiku/db/models.py
+++ b/src/kiku/db/models.py
@@
 class Track(Base):
     __tablename__ = "tracks"
 
     id = Column(Integer, primary_key=True)
     rb_id = Column(String, unique=True)
@@
     energy_predicted = Column(String)  # Predicted energy tag from autotag classifier
     energy_confidence = Column(Float)  # Prediction confidence 0-1
     energy_source = Column(String)  # "manual", "auto", or "approved"
 
+    # --- Vinyl (spec 030) ---------------------------------------------------
+    # A record on the shelf is a track row with no file. Everything below is
+    # NULL for a digital row except `medium`, which is backfilled to "digital".
+    medium = Column(String, index=True, default="digital")  # "digital" | "vinyl"
+    vinyl_release_id = Column(Integer, ForeignKey("vinyl_releases.id"))
+    vinyl_position = Column(String)  # raw side string: "A1", "B2", "Digi 1"
+    mb_recording_id = Column(String)  # the AcousticBrainz key, for slice 2
+    bpm_source = Column(String)  # "rekordbox" | "essentia" | "acousticbrainz" | "manual"
+    key_source = Column(String)  # same ladder — "manual" outranks everything
+    enrichment_status = Column(String)  # "pending" | "enriched" | "no_match" | "manual"
+    duplicate_of_track_id = Column(Integer, ForeignKey("tracks.id"))
+
+    __table_args__ = (
+        # One side position per pressing. Digital rows leave both NULL and SQLite
+        # counts NULLs as distinct, so this only ever constrains vinyl.
+        Index("uq_track_vinyl_side", "vinyl_release_id", "vinyl_position", unique=True),
+        Index("ix_tracks_medium", "medium"),
+    )
+
     audio_features = relationship(
         "AudioFeatures", back_populates="track", uselist=False, cascade="all, delete-orphan"
     )
+
+    @property
+    def is_vinyl(self) -> bool:
+        """True when this track lives on the shelf, not on disk."""
+        return self.medium == "vinyl"
 
     @property
     def resolved_energy_zone(self) -> tuple[str | None, str, float]:
````

**Note for the implementer:** `Track` already declares `album` and `file_path` with
`index=True`; those become named indexes automatically and are unaffected by adding
`__table_args__`. Do not move them into `__table_args__`.

Second diff — `AudioFeatures.source`:
````diff
--- a/src/kiku/db/models.py
+++ b/src/kiku/db/models.py
@@
     verified_bpm = Column(Float)
     verified_key = Column(String)
     analyzed_at = Column(String)
+    # What produced these numbers. The table recorded *when* but never *what*,
+    # which is the only thing that can later prove the two pipelines share a scale.
+    source = Column(String)  # "essentia" | "acousticbrainz"
     # Waveform data for visualization
     waveform_overview = Column(LargeBinary)  # ~1000 float32 peak-downsampled RMS
````

Third diff — the `VinylRelease` model, inserted immediately after `class AlbumMetadata`
(i.e. after its `cover_fetched_at` line, before `def _set_wal_mode`):
````diff
--- a/src/kiku/db/models.py
+++ b/src/kiku/db/models.py
@@
     cover_source = Column(String)  # "embedded" | "caa" | "itunes" | "deezer"
     cover_fetched_at = Column(DateTime)
 
 
+class VinylRelease(Base):
+    """One physical pressing the DJ owns.
+
+    Kiku has no albums table — `album_key()` groups on the fly. That works for
+    browsing but cannot hold catalog number, RPM, country or acquisition date,
+    because those are facts about an object you own once, not about a track.
+    """
+
+    __tablename__ = "vinyl_releases"
+
+    id = Column(Integer, primary_key=True)
+    discogs_release_id = Column(String)
+    mb_release_id = Column(String)
+    title = Column(String)
+    artist = Column(String)
+    label = Column(String)
+    catalog_number = Column(String)
+    year = Column(Integer)
+    country = Column(String)
+    format = Column(String)  # e.g. 'Vinyl, 12", 33 ⅓ RPM, EP'
+    rpm = Column(Integer)
+    side_count = Column(Integer)
+    cover_url = Column(String)
+    acquired_on = Column(String)  # ISO date the record joined the shelf
+    notes = Column(Text)
+    created_at = Column(String, default=lambda: datetime.now().isoformat())
+
+    __table_args__ = (
+        UniqueConstraint("discogs_release_id", name="uq_vinyl_release_discogs_id"),
+    )
+
+
 def _set_wal_mode(dbapi_conn, connection_record):
````

Verification:
- `source .venv/bin/activate && python -m pytest tests/test_migrations.py -x -q` — **all three pass**. `test_migrated_schema_matches_the_orm` is the real check: it fails on any mismatch between Task 1 and Task 2.
- `source .venv/bin/activate && python -c "from kiku.db.models import VinylRelease, Track; print(Track.medium, VinylRelease.__tablename__)"`


#### Task 3 — src/kiku/vinyl/position.py: the side parser
Tools: editor

Create `src/kiku/vinyl/__init__.py`:
````diff
--- /dev/null
+++ b/src/kiku/vinyl/__init__.py
@@
+"""Vinyl library — records the DJ owns on the shelf rather than on disk."""
````

Create `src/kiku/vinyl/position.py`:
````diff
--- /dev/null
+++ b/src/kiku/vinyl/position.py
@@
+"""Turn a pressing's side string into something you can sort by.
+
+`vinyl_position` keeps the raw Discogs string because that is what is printed
+on the label and what the DJ reads when pulling the record. Ordering comes from
+parsing it into the two columns Kiku already sorts albums by:
+
+    disc_number  = side ordinal   (A=1, B=2, C=3, D=4 …)
+    track_number = index within that side
+
+For a 2×LP this makes `disc_number` mean *side*, not *disc*. That is deliberate:
+the side is the unit of DJ action — you flip a side, you never flip a disc.
+"""
+
+from __future__ import annotations
+
+import re
+
+# "A1", "B2", "AA1", "C", "12", "Digi 1", "CD1-3"
+_SIDE_RE = re.compile(r"^\s*([A-Za-z]{1,2})\s*[-.]?\s*(\d+)?\s*$")
+_TRAILING_NUM_RE = re.compile(r"(\d+)\s*$")
+
+
+def parse_position(raw: str | None) -> tuple[int | None, int | None]:
+    """Return (side_ordinal, index_within_side) for a raw position string.
+
+    >>> parse_position("A1")
+    (1, 1)
+    >>> parse_position("B2")
+    (2, 2)
+    >>> parse_position("C")
+    (3, None)
+    >>> parse_position("AA3")        # double-letter sides on a 3xLP
+    (27, 3)
+    >>> parse_position("Digi 1")     # digital-only bonus track, no side
+    (None, 1)
+    >>> parse_position("4")
+    (None, 4)
+    >>> parse_position(None)
+    (None, None)
+    """
+    if not raw or not raw.strip():
+        return (None, None)
+
+    text = raw.strip()
+    m = _SIDE_RE.match(text)
+    if m:
+        side = _side_ordinal(m.group(1))
+        idx = int(m.group(2)) if m.group(2) else None
+        return (side, idx)
+
+    # Anything else ("Digi 1", "CD1-3", "Bonus 2") has no pressing side. Keep the
+    # trailing number so the track still orders sensibly after the sides.
+    tail = _TRAILING_NUM_RE.search(text)
+    return (None, int(tail.group(1)) if tail else None)
+
+
+def _side_ordinal(letters: str) -> int:
+    """A=1 … Z=26, AA=27 … — base-26 so a 3xLP's sides stay in order."""
+    value = 0
+    for ch in letters.upper():
+        value = value * 26 + (ord(ch) - ord("A") + 1)
+    return value
+
+
+def side_letter(ordinal: int | None) -> str | None:
+    """Inverse of `_side_ordinal`, for display: 1 -> 'A', 27 -> 'AA'."""
+    if not ordinal or ordinal < 1:
+        return None
+    out = ""
+    n = ordinal
+    while n > 0:
+        n, rem = divmod(n - 1, 26)
+        out = chr(ord("A") + rem) + out
+    return out
````

Verification:
- `source .venv/bin/activate && python -m pytest --doctest-modules src/kiku/vinyl/position.py -q`


#### Task 4 — metadata shapes: carry the MBID, the raw side, and the catalog facts
Tools: editor

4a — `src/kiku/metadata/models.py`:
````diff
--- a/src/kiku/metadata/models.py
+++ b/src/kiku/metadata/models.py
@@
 @dataclass
 class RecordingCandidate:
     """One track as described by a source."""
 
     title: str
     position: int | None = None
     disc: int | None = None
     artist: str | None = None  # per-track artist (compilations / remixers)
     length_ms: int | None = None
+    # MusicBrainz recording id. Present in the MB response and previously thrown
+    # away; it is the only key AcousticBrainz accepts (slice 2).
+    mbid: str | None = None
+    # The pressing's own position string — "A1", "B2", "Digi 1". Display truth
+    # for vinyl; `position`/`disc` above are the sortable derivation of it.
+    position_raw: str | None = None
 
 
 @dataclass
 class ReleaseCandidate:
     """One release (album/EP) as described by a source."""
 
     source: str  # "bandcamp" | "musicbrainz" | "discogs" | "tags"
     source_id: str  # MB release id, Discogs release id, bandcamp URL, "embedded"
     album: str | None = None
     artist: str | None = None
     label: str | None = None
     year: int | None = None
     url: str | None = None
+    # Catalog facts about a physical object. Discogs knows these; nobody else
+    # reliably does. They are what a `vinyl_releases` row is made of.
+    catalog_number: str | None = None
+    country: str | None = None
+    format: str | None = None  # 'Vinyl, 12", 33 ⅓ RPM, EP'
+    cover_url: str | None = None
     recordings: list[RecordingCandidate] = field(default_factory=list)
````

4b — `src/kiku/metadata/sources/musicbrainz.py`, stop discarding the recording id:
````diff
--- a/src/kiku/metadata/sources/musicbrainz.py
+++ b/src/kiku/metadata/sources/musicbrainz.py
@@
                 length = tr.get("length")
                 recordings.append(
                     RecordingCandidate(
                         title=title,
                         position=int(pos),
                         disc=disc_no,
                         length_ms=int(length) if length else None,
+                        mbid=(tr.get("recording") or {}).get("id"),
+                        position_raw=str(pos),
                     )
                 )
````

4c — `src/kiku/metadata/sources/discogs.py`, keep the side string instead of
counting past it, and carry the catalog facts:
````diff
--- a/src/kiku/metadata/sources/discogs.py
+++ b/src/kiku/metadata/sources/discogs.py
@@
     def _to_candidate(self, full: dict, release_id: int) -> ReleaseCandidate:
         recordings: list[RecordingCandidate] = []
-        pos = 0
+        from kiku.vinyl.position import parse_position
+
+        seq = 0
         for tr in full.get("tracklist", []) or []:
             if (tr.get("type_") or "track") != "track":
                 continue  # skip headings / index tracks
             title = (tr.get("title") or "").strip()
             if not title:
                 continue
-            pos += 1
+            seq += 1
+            raw = (tr.get("position") or "").strip() or None
+            side, index = parse_position(raw)
+            # A pressing without a readable position still needs a stable order,
+            # so fall back to the sequence we walked the tracklist in.
             recordings.append(
                 RecordingCandidate(
                     title=title,
-                    position=pos,
-                    disc=1,
+                    position=index if index is not None else seq,
+                    disc=side if side is not None else 1,
                     length_ms=_duration_to_ms(tr.get("duration")),
+                    position_raw=raw,
                 )
             )
 
         labels = full.get("labels") or []
         label = labels[0].get("name") if labels and labels[0].get("name") else None
+        catno = labels[0].get("catno") if labels and labels[0].get("catno") else None
         artists = full.get("artists") or []
         artist = _join_artists(artists)
+        formats = full.get("formats") or []
+        fmt = _format_text(formats[0]) if formats else None
+        images = full.get("images") or []
+        cover = images[0].get("uri") if images and images[0].get("uri") else None
 
         return ReleaseCandidate(
             source=self.name,
             source_id=str(release_id),
             url=full.get("uri") or f"https://www.discogs.com/release/{release_id}",
             album=(full.get("title") or "").strip() or None,
             artist=artist,
             label=label,
             year=full.get("year") or None,
+            catalog_number=catno,
+            country=full.get("country") or None,
+            format=fmt,
+            cover_url=cover,
             recordings=recordings,
         )
@@
 def _join_artists(artists: list[dict]) -> str | None:
````

And append this helper at the end of `discogs.py`, after `_duration_to_ms`:
````diff
--- a/src/kiku/metadata/sources/discogs.py
+++ b/src/kiku/metadata/sources/discogs.py
@@
 def _duration_to_ms(text: str | None) -> int | None:
     if not text:
         return None
     m = _DURATION_RE.match(text.strip())
     if not m:
         return None
     return (int(m.group(1)) * 60 + int(m.group(2))) * 1000
+
+
+def _format_text(fmt: dict) -> str | None:
+    """Flatten Discogs' format object into the string printed on a sleeve.
+
+    {"name": "Vinyl", "descriptions": ["12\"", "33 ⅓ RPM", "EP"]}
+        -> 'Vinyl, 12", 33 ⅓ RPM, EP'
+    """
+    parts = [(fmt.get("name") or "").strip()]
+    parts += [d.strip() for d in (fmt.get("descriptions") or []) if d and d.strip()]
+    out = ", ".join(p for p in parts if p)
+    return out or None
+
+
+def rpm_from_format(fmt_text: str | None) -> int | None:
+    """Pull the RPM out of a Discogs format string, when it says one."""
+    if not fmt_text:
+        return None
+    if "45 RPM" in fmt_text:
+        return 45
+    if "33" in fmt_text and "RPM" in fmt_text:
+        return 33
+    if "78 RPM" in fmt_text:
+        return 78
+    return None
````

Verification:
- `source .venv/bin/activate && python -m pytest tests/test_metadata_sources.py -x -q` — existing source tests still pass.
- The Discogs change alters `position`/`disc` for **digital** `kiku fix-album --source discogs`
  runs too: an album whose tracklist is `A1/A2/B1` now proposes `disc_number=1,2`
  instead of `disc_number=1` throughout. That is more correct for a vinyl release
  and is exactly what `CORRECTABLE_FIELDS` exists to let the DJ confirm or reject
  in the diff preview. Call it out in the commit message.


#### Task 5 — src/kiku/vinyl/importer.py: search → preview → apply
Tools: editor

Create `src/kiku/vinyl/importer.py` with EXACTLY this content:

````diff
--- /dev/null
+++ b/src/kiku/vinyl/importer.py
@@
+"""Put a record you own on the shelf into the library.
+
+Shaped after `kiku fix-album` (`metadata/correct.py`): look it up, see the whole
+thing before anything is written, then apply. The difference is what the DJ is
+confirming. `fix-album` shows "here is what we found, is it right?"; this shows
+"here is the tracklist, now tell us the BPMs" — because the AcousticBrainz spike
+(spec Research R1) found a BPM for 1 recording in 54. Nobody is going to fill
+those in for you.
+"""
+
+from __future__ import annotations
+
+from dataclasses import dataclass, field
+from datetime import datetime
+
+from sqlalchemy.orm import Session
+
+from kiku.db.models import Track, VinylRelease
+from kiku.metadata.models import ReleaseCandidate
+from kiku.vinyl.position import parse_position
+
+# Sources that can answer "what is on this record?". Discogs first: it is the
+# only one that knows side positions, and Research R2 moved its value from
+# enrichment to exactly these catalog facts.
+VINYL_SOURCES: tuple[str, ...] = ("discogs", "musicbrainz")
+
+
+@dataclass
+class PreviewRow:
+    """One side of the record, as it would land."""
+
+    position_raw: str | None
+    side: int | None
+    index: int | None
+    title: str
+    artist: str | None
+    duration_sec: float | None
+    existing_track_id: int | None = None  # already imported — this is a re-import
+
+
+@dataclass
+class ImportPreview:
+    candidate: ReleaseCandidate
+    rows: list[PreviewRow] = field(default_factory=list)
+    existing_release_id: int | None = None
+
+    @property
+    def is_reimport(self) -> bool:
+        return self.existing_release_id is not None
+
+    @property
+    def new_count(self) -> int:
+        return sum(1 for r in self.rows if r.existing_track_id is None)
+
+
+class NoVinylSource(RuntimeError):
+    """No configured source can look a record up right now."""
+
+
+def search_releases(
+    album: str,
+    artist: str = "",
+    *,
+    source_name: str = "discogs",
+    limit: int = 5,
+) -> list[ReleaseCandidate]:
+    """Find pressings matching an album name."""
+    from kiku.metadata.sources import get_source
+
+    src = get_source(source_name)
+    if not src.available():
+        raise NoVinylSource(
+            f"{source_name} isn't set up yet — "
+            "`kiku config set discogs.token <TOKEN>` and try again."
+        )
+    return src.search(album, artist, limit=limit)
+
+
+def fetch_release_url(url: str, *, source_name: str = "discogs") -> ReleaseCandidate | None:
+    """Build a candidate straight from a Discogs release URL."""
+    from kiku.metadata.sources import get_source
+
+    src = get_source(source_name)
+    if not src.available():
+        raise NoVinylSource(
+            f"{source_name} isn't set up yet — "
+            "`kiku config set discogs.token <TOKEN>` and try again."
+        )
+    return src.fetch_url(url)
+
+
+def build_preview(session: Session, candidate: ReleaseCandidate) -> ImportPreview:
+    """Show the whole record before a single row is written."""
+    existing_release = _find_existing_release(session, candidate)
+    preview = ImportPreview(
+        candidate=candidate,
+        existing_release_id=existing_release.id if existing_release else None,
+    )
+
+    by_position: dict[str, Track] = {}
+    if existing_release:
+        for tr in session.query(Track).filter(Track.vinyl_release_id == existing_release.id):
+            if tr.vinyl_position:
+                by_position[tr.vinyl_position] = tr
+
+    for rec in candidate.recordings:
+        raw = rec.position_raw
+        side, index = parse_position(raw)
+        if side is None and index is None:
+            side, index = rec.disc, rec.position
+        preview.rows.append(
+            PreviewRow(
+                position_raw=raw,
+                side=side,
+                index=index,
+                title=rec.title,
+                artist=rec.artist or candidate.artist,
+                duration_sec=(rec.length_ms / 1000.0) if rec.length_ms else None,
+                existing_track_id=(by_position.get(raw).id if raw and raw in by_position else None),
+            )
+        )
+    return preview
+
+
+def apply_import(
+    session: Session,
+    candidate: ReleaseCandidate,
+    *,
+    acquired_on: str | None = None,
+    notes: str | None = None,
+) -> VinylRelease:
+    """Write the pressing and one track row per side position.
+
+    Idempotent by `discogs_release_id`: adding the same record twice updates the
+    sides you already have rather than growing a second copy of the shelf.
+    """
+    from kiku.metadata.sources.discogs import rpm_from_format
+
+    release = _find_existing_release(session, candidate)
+    if release is None:
+        release = VinylRelease()
+        session.add(release)
+
+    if candidate.source == "discogs":
+        release.discogs_release_id = candidate.source_id
+    elif candidate.source == "musicbrainz":
+        release.mb_release_id = candidate.source_id
+
+    release.title = candidate.album
+    release.artist = candidate.artist
+    release.label = candidate.label
+    release.catalog_number = candidate.catalog_number
+    release.year = candidate.year
+    release.country = candidate.country
+    release.format = candidate.format
+    release.rpm = rpm_from_format(candidate.format)
+    release.cover_url = candidate.cover_url
+    if acquired_on:
+        release.acquired_on = acquired_on
+    if notes:
+        release.notes = notes
+    session.flush()  # release.id
+
+    preview = build_preview(session, candidate)
+    sides: set[int] = set()
+    now = datetime.now().isoformat()
+
+    for row in preview.rows:
+        track = (
+            session.get(Track, row.existing_track_id)
+            if row.existing_track_id is not None
+            else None
+        )
+        if track is None:
+            track = Track(medium="vinyl", enrichment_status="pending")
+            session.add(track)
+
+        track.medium = "vinyl"
+        track.vinyl_release_id = release.id
+        track.vinyl_position = row.position_raw
+        track.title = row.title
+        track.artist = row.artist
+        track.album = candidate.album
+        track.label = candidate.label
+        track.release_year = candidate.year
+        track.disc_number = row.side
+        track.track_number = row.index
+        track.duration_sec = row.duration_sec
+        track.mb_recording_id = _mbid_for(candidate, row.position_raw, row.title)
+        track.last_synced = now
+        if track.enrichment_status is None:
+            track.enrichment_status = "pending"
+        if row.side:
+            sides.add(row.side)
+
+    release.side_count = len(sides) or None
+    session.commit()
+    return release
+
+
+def set_manual_bpm_key(
+    session: Session,
+    track_id: int,
+    *,
+    bpm: float | None = None,
+    key: str | None = None,
+) -> Track:
+    """The DJ types the number. That marker is the top of the provenance ladder.
+
+    `manual` outranks essentia, rekordbox and acousticbrainz, so a later
+    enrichment pass can read this and know to leave it alone.
+    """
+    track = session.get(Track, track_id)
+    if track is None:
+        raise ValueError(f"No track with id {track_id}")
+
+    if bpm is not None:
+        if bpm <= 0 or bpm > 300:
+            raise ValueError(f"{bpm} doesn't look like a BPM — expected 1–300")
+        track.bpm = float(bpm)
+        track.bpm_source = "manual"
+    if key is not None and key.strip():
+        track.key = key.strip()
+        track.key_source = "manual"
+    if track.bpm:
+        track.enrichment_status = "manual"
+    session.commit()
+    return track
+
+
+def _find_existing_release(
+    session: Session, candidate: ReleaseCandidate
+) -> VinylRelease | None:
+    if candidate.source == "discogs":
+        return (
+            session.query(VinylRelease)
+            .filter(VinylRelease.discogs_release_id == candidate.source_id)
+            .first()
+        )
+    if candidate.source == "musicbrainz":
+        return (
+            session.query(VinylRelease)
+            .filter(VinylRelease.mb_release_id == candidate.source_id)
+            .first()
+        )
+    return None
+
+
+def _mbid_for(
+    candidate: ReleaseCandidate, position_raw: str | None, title: str
+) -> str | None:
+    """The recording MBID for this side, when the source carried one.
+
+    Discogs never does — the Discogs→MB hop is slice-2 work (Research R3 leaves
+    it the highest-value unmeasured question), so this stays NULL for a Discogs
+    import and the row simply has no AcousticBrainz key. That is honest, not a gap.
+    """
+    for rec in candidate.recordings:
+        if rec.mbid and (
+            (position_raw and rec.position_raw == position_raw) or rec.title == title
+        ):
+            return rec.mbid
+    return None
````

Verification:
- `source .venv/bin/activate && python -c "from kiku.vinyl.importer import apply_import, build_preview; print('ok')"`
- Covered by the unit tests in Task 11.


#### Task 6 — `kiku vinyl` CLI group
Tools: editor

Append this to the END of `src/kiku/cli.py` (after `fix_album`'s final line,
`console.print(f"[bold green]Fixed {touched} track(s).[/] {candidate.album or ''}")`).
`console`, `Table` and `click` are already imported at module scope — do not re-import them.

````diff
--- a/src/kiku/cli.py
+++ b/src/kiku/cli.py
@@
     touched = apply_correction(
         session,
         corrections,
         fields=chosen_fields,
         candidate=candidate,
         album_key=album_key,
     )
     console.print(f"[bold green]Fixed {touched} track(s).[/] {candidate.album or ''}")
+
+
+@cli.group("vinyl")
+def vinyl_group():
+    """Records you own on the shelf — the half of your library with no files."""
+
+
+@vinyl_group.command("add")
+@click.argument("query", required=False)
+@click.option("--url", default=None, help="Discogs release URL, if you have it")
+@click.option(
+    "--source",
+    "source_name",
+    default="discogs",
+    type=click.Choice(["discogs", "musicbrainz"]),
+    help="Where to read the tracklist from (Discogs knows the side positions)",
+)
+@click.option("--artist", "-a", default=None, help="Artist, to sharpen the search")
+@click.option(
+    "--candidate",
+    "candidate_index",
+    default=None,
+    type=int,
+    help="Pick the Nth pressing (0-based) instead of being asked",
+)
+@click.option("--acquired", default=None, help="When it joined the shelf (YYYY-MM-DD)")
+@click.option("--notes", default=None, help="Anything worth remembering about this copy")
+@click.option("--dry-run", is_flag=True, help="Show the record without writing anything")
+@click.option("--yes", "-y", is_flag=True, help="Skip confirmation and add it")
+@click.option(
+    "--no-fill",
+    is_flag=True,
+    help="Skip the BPM/key pass — the record lands unplannable until you come back",
+)
+def vinyl_add(
+    query, url, source_name, artist, candidate_index, acquired, notes, dry_run, yes, no_fill
+):
+    """Add a record from your shelf.
+
+    \b
+    Examples:
+      kiku vinyl add "Klockworks 38" -a Alarico
+      kiku vinyl add --url https://www.discogs.com/release/12345
+      kiku vinyl add "Sandwell District" --candidate 1 -y
+    """
+    from kiku.db.models import get_session
+    from kiku.metadata.sources.base import LookupUnsupported, SourceUnavailable
+    from kiku.vinyl.importer import (
+        NoVinylSource,
+        apply_import,
+        build_preview,
+        fetch_release_url,
+        search_releases,
+    )
+
+    if not query and not url:
+        console.print("[yellow]Which record?[/] Pass an album name or a --url.")
+        return
+
+    session = get_session()
+    try:
+        if url:
+            console.print(f"[cyan]Reading that pressing off {source_name}…[/]")
+            candidates = [c for c in [fetch_release_url(url, source_name=source_name)] if c]
+        else:
+            console.print(f"[cyan]Looking for '{query}' on {source_name}…[/]")
+            candidates = search_releases(
+                query, artist or "", source_name=source_name, limit=5
+            )
+    except (NoVinylSource, SourceUnavailable) as e:
+        console.print(f"[red]{e}[/]")
+        return
+    except LookupUnsupported as e:
+        console.print(f"[yellow]{e}[/]")
+        return
+
+    if not candidates:
+        console.print(
+            "[yellow]Nothing came back for that.[/] Try the catalogue number, "
+            "or paste the Discogs URL with --url."
+        )
+        return
+
+    if candidate_index is None and len(candidates) > 1:
+        table = Table(title="Which pressing?")
+        table.add_column("#", justify="right", style="dim")
+        table.add_column("Release")
+        table.add_column("Artist")
+        table.add_column("Label / cat#")
+        table.add_column("Year", justify="right")
+        table.add_column("Format")
+        table.add_column("Sides", justify="right")
+        for i, c in enumerate(candidates):
+            table.add_row(
+                str(i),
+                c.album or "—",
+                c.artist or "—",
+                " · ".join(x for x in (c.label, c.catalog_number) if x) or "—",
+                str(c.year or "—"),
+                c.format or "—",
+                str(c.track_count),
+            )
+        console.print(table)
+        candidate_index = click.prompt("Pick one", type=int, default=0)
+
+    idx = candidate_index or 0
+    if idx < 0 or idx >= len(candidates):
+        console.print(f"[red]There's no #{idx} in that list.[/]")
+        return
+    candidate = candidates[idx]
+
+    preview = build_preview(session, candidate)
+    console.print(
+        f"\n[bold]{candidate.album or '—'}[/] · {candidate.artist or '—'}"
+        f" · {candidate.label or '—'} {candidate.catalog_number or ''}"
+        f" · {candidate.year or '—'}  [dim]({candidate.format or 'format unknown'})[/]"
+    )
+
+    table = Table(title="Re-import — sides you already have are marked" if preview.is_reimport else "Sides")
+    table.add_column("Side", style="bold")
+    table.add_column("Title")
+    table.add_column("Artist", style="dim")
+    table.add_column("Length", justify="right")
+    table.add_column("", style="dim")
+    for row in preview.rows:
+        length = f"{int(row.duration_sec // 60)}:{int(row.duration_sec % 60):02d}" if row.duration_sec else "—"
+        table.add_row(
+            row.position_raw or "—",
+            row.title,
+            row.artist or "—",
+            length,
+            "already on the shelf" if row.existing_track_id else "",
+        )
+    console.print(table)
+
+    if dry_run:
+        console.print("[dim]Dry run — nothing written.[/]")
+        return
+
+    if not yes and not click.confirm(f"Add {preview.new_count} side(s) to your library?", default=True):
+        console.print("[dim]Left your library untouched.[/]")
+        return
+
+    release = apply_import(session, candidate, acquired_on=acquired, notes=notes)
+    console.print(
+        f"[bold green]{candidate.album or 'That record'} is on the shelf.[/] "
+        f"[dim]release #{release.id}[/]"
+    )
+
+    # The spike found a BPM for 1 recording in 54 (spec Research R1). Nobody is
+    # going to enrich these — so the fill pass is the import, not an afterthought.
+    if no_fill:
+        console.print(
+            "[dim]No BPMs yet, so it can't be planned into a set. "
+            f"`kiku vinyl fill {release.id}` when you're ready.[/]"
+        )
+        return
+    _vinyl_fill(session, release.id)
+
+
+@vinyl_group.command("fill")
+@click.argument("release_id", type=int, required=False)
+def vinyl_fill(release_id):
+    """Type the BPM and key for sides that don't have them yet."""
+    from kiku.db.models import get_session
+
+    _vinyl_fill(get_session(), release_id)
+
+
+def _vinyl_fill(session, release_id: int | None) -> None:
+    """Walk the unplannable vinyl rows and ask for a BPM. Enter skips one."""
+    from kiku.db.models import Track
+    from kiku.vinyl.importer import set_manual_bpm_key
+
+    q = session.query(Track).filter(Track.medium == "vinyl")
+    if release_id is not None:
+        q = q.filter(Track.vinyl_release_id == release_id)
+    rows = [t for t in q.order_by(Track.disc_number, Track.track_number, Track.id) if not t.bpm]
+
+    if not rows:
+        console.print("[green]Every side has a BPM — they're all plannable.[/]")
+        return
+
+    console.print(
+        f"\n[bold]{len(rows)} side(s) still need a BPM.[/] "
+        "[dim]Press Enter to skip one; Ctrl-C to stop.[/]"
+    )
+    filled = 0
+    for tr in rows:
+        label = f"{tr.vinyl_position or '—'}  {tr.artist or '?'} — {tr.title or '?'}"
+        try:
+            bpm = click.prompt(f"  {label}\n    BPM", default="", show_default=False)
+            if not bpm.strip():
+                continue
+            key = click.prompt("    Key (Camelot or musical, Enter to skip)", default="", show_default=False)
+            set_manual_bpm_key(
+                session, tr.id, bpm=float(bpm), key=key.strip() or None
+            )
+            filled += 1
+        except (ValueError, TypeError):
+            console.print("    [yellow]That doesn't look like a BPM — skipping this one.[/]")
+        except (KeyboardInterrupt, click.Abort):
+            console.print("\n[dim]Stopped. What you typed is saved.[/]")
+            break
+
+    console.print(f"\n[bold green]{filled} side(s) can now be planned into a set.[/]")
+
+
+@vinyl_group.command("bpm")
+@click.argument("track_id", type=int)
+@click.argument("bpm", type=float)
+@click.option("--key", "-k", default=None, help="Musical or Camelot key")
+def vinyl_bpm(track_id, bpm, key):
+    """Set one side's BPM by hand."""
+    from kiku.db.models import get_session
+    from kiku.vinyl.importer import set_manual_bpm_key
+
+    session = get_session()
+    try:
+        tr = set_manual_bpm_key(session, track_id, bpm=bpm, key=key)
+    except ValueError as e:
+        console.print(f"[red]{e}[/]")
+        return
+    console.print(
+        f"[green]{tr.vinyl_position or '—'} {tr.artist or '?'} — {tr.title or '?'}[/] "
+        f"is {tr.bpm:g} BPM{f' in {tr.key}' if tr.key else ''}."
+    )
+
+
+@vinyl_group.command("list")
+def vinyl_list():
+    """The shelf, and how much of it Kiku can actually plan with."""
+    from kiku.db.models import Track, VinylRelease, get_session
+
+    session = get_session()
+    releases = session.query(VinylRelease).order_by(VinylRelease.artist, VinylRelease.title).all()
+    if not releases:
+        console.print(
+            "[dim]No records yet. `kiku vinyl add \"<album>\"` puts the first one on the shelf.[/]"
+        )
+        return
+
+    table = Table(title=f"{len(releases)} record(s) on the shelf")
+    table.add_column("#", justify="right", style="dim")
+    table.add_column("Release")
+    table.add_column("Artist")
+    table.add_column("Label / cat#")
+    table.add_column("Year", justify="right")
+    table.add_column("Sides", justify="right")
+    table.add_column("Plannable", justify="right")
+
+    unplannable = 0
+    for r in releases:
+        tracks = session.query(Track).filter(Track.vinyl_release_id == r.id).all()
+        with_bpm = sum(1 for t in tracks if t.bpm)
+        unplannable += len(tracks) - with_bpm
+        table.add_row(
+            str(r.id),
+            r.title or "—",
+            r.artist or "—",
+            " · ".join(x for x in (r.label, r.catalog_number) if x) or "—",
+            str(r.year or "—"),
+            str(len(tracks)),
+            f"{with_bpm}/{len(tracks)}",
+        )
+    console.print(table)
+    if unplannable:
+        console.print(
+            f"[dim]{unplannable} side(s) have no BPM yet, so the builder can't reach them. "
+            "`kiku vinyl fill` fixes that.[/]"
+        )
````

Verification:
- `source .venv/bin/activate && kiku vinyl --help` lists `add`, `bpm`, `fill`, `list`.
- `source .venv/bin/activate && kiku vinyl list` on the real library prints the empty-shelf line.


#### Task 7 — planner: close Risk 3, digital-by-default
Tools: editor

Risk 3 (Human Section L34): `planner.py:92` has no medium filter, so the moment a
vinyl row gets a BPM it joins the beam-search pool and a routine `kiku build`
starts returning records the DJ can't cue on a CDJ. Until the vinyl-ratio control
ships in slice 2, the pool stays digital unless asked.

Diff:
````diff
--- a/src/kiku/setbuilder/planner.py
+++ b/src/kiku/setbuilder/planner.py
@@
 def _get_candidate_pool(
     session: Session,
     genres: list[str] | None = None,
     bpm_range: tuple[float, float] | None = None,
+    include_vinyl: bool = False,
 ) -> list[Track]:
-    """Get filtered candidate pool."""
-    q = session.query(Track).filter(Track.bpm.isnot(None), Track.bpm > 0)
+    """Get filtered candidate pool.
+
+    Vinyl is excluded by default (spec 030, Risk 3). A record with a BPM is a
+    perfectly good candidate — that is the whole finding — but until the vinyl
+    ratio and the deck-change penalty exist, dropping records into an ordinary
+    digital build would be a surprise, not a feature. Slice 2 turns this on.
+    """
+    q = session.query(Track).filter(Track.bpm.isnot(None), Track.bpm > 0)
+
+    if not include_vinyl:
+        # coalesce, not `!= "vinyl"` — in SQL a NULL medium would fail that
+        # comparison and the row would vanish from the pool.
+        q = q.filter(func.coalesce(Track.medium, "digital") != "vinyl")
 
     if genres:
````

**No import change needed.** `planner.py:9` already reads
`from sqlalchemy import func, or_` — verified against the file. Do not add an import.

Verification:
- `source .venv/bin/activate && python -m pytest tests/test_planner.py tests/test_filler.py -x -q`
- `kiku.setbuilder.filler` calls `_get_candidate_pool` positionally
  (`filler.py:120`, keyword args only) so the new keyword-only default is safe there.

#### Task 8 — export: never write a broken Location
Tools: editor

8a — `src/kiku/export/utils.py`, add the result shapes at the top of the file
(after the `_PATH_ALIASES` block, before `def export_path`):
````diff
--- a/src/kiku/export/utils.py
+++ b/src/kiku/export/utils.py
@@
 from __future__ import annotations
 
 import re
+from dataclasses import dataclass, field
 from pathlib import Path
 
 # Path aliases: (macOS prefix, Linux prefix).
 # Reverse of sync.py's _PATH_ALIASES — export converts Linux back to macOS.
 _PATH_ALIASES: list[tuple[str, str]] = [
     ("/Volumes/", "/run/media/mantis/"),
 ]
 
 
+@dataclass
+class SkippedTrack:
+    """A track that couldn't go in the playlist, and why."""
+
+    track_id: int
+    title: str
+    artist: str | None
+    reason: str  # human-readable: "on vinyl — side B2"
+
+
+@dataclass
+class ExportResult:
+    """Where the file went, and what didn't make it in.
+
+    Rekordbox reads a missing Location as a corrupt entry, not a placeholder, so
+    a fileless track is left out of the playlist and reported here instead —
+    the DJ finds out at export time rather than on the booth screen.
+    """
+
+    path: str
+    skipped: list[SkippedTrack] = field(default_factory=list)
+
+
+def skip_reason(track) -> str | None:
+    """Why this track can't be exported to a file-based playlist, or None."""
+    if track.file_path:
+        return None
+    if track.medium == "vinyl":
+        side = f" — side {track.vinyl_position}" if track.vinyl_position else ""
+        return f"on vinyl{side}"
+    return "no file on disk"
+
+
 def export_path(file_path: str, target_platform: str = "macos") -> str:
````

8b — `src/kiku/export/m3u8.py`:
````diff
--- a/src/kiku/export/m3u8.py
+++ b/src/kiku/export/m3u8.py
@@
 from kiku.config import DATA_DIR
 from kiku.db.models import Set
-from kiku.export.utils import export_path, sanitize_filename
+from kiku.export.utils import (
+    ExportResult,
+    SkippedTrack,
+    export_path,
+    sanitize_filename,
+    skip_reason,
+)
 
 
 def export_set_to_m3u8(
     set_: Set,
     output_path: str | None = None,
     *,
     target_platform: str = "macos",
     with_metadata: bool = False,
-) -> str:
+) -> ExportResult:
@@
     Returns
     -------
-    str
-        Path to the written M3U8 file.
+    ExportResult
+        The written file's path, plus any tracks left out because they have no
+        file — records on the shelf get a comment line naming the side instead.
     """
     tracks_in_set = sorted(set_.tracks, key=lambda st: st.position)
     set_name = set_.name or "set"
 
     lines: list[str] = ["#EXTM3U"]
+    skipped: list[SkippedTrack] = []
 
     for st in tracks_in_set:
         track = st.track
 
+        # A fileless track can't carry a path, and an #EXTINF without one
+        # corrupts the playlist. M3U8 has comments, so leave a note instead —
+        # Rekordbox ignores it, the DJ reading the file sees what to pull.
+        reason = skip_reason(track)
+        if reason:
+            skipped.append(
+                SkippedTrack(
+                    track_id=track.id,
+                    title=track.title or "Unknown Title",
+                    artist=track.artist,
+                    reason=reason,
+                )
+            )
+            lines.append(
+                f"# kiku:vinyl {track.artist or 'Unknown Artist'} - "
+                f"{track.title or 'Unknown Title'} ({reason})"
+            )
+            continue
+
         # Duration: integer seconds, -1 if unknown
         duration = int(track.duration_sec) if track.duration_sec else -1
@@
         # File path: absolute, forward slashes, platform-aliased
-        file_path = track.file_path or ""
-        file_path = export_path(file_path, target_platform)
+        file_path = export_path(track.file_path, target_platform)
         file_path = file_path.replace("\\", "/")
         lines.append(file_path)
@@
     out = Path(output_path)
     out.parent.mkdir(parents=True, exist_ok=True)
     out.write_text("\n".join(lines) + "\n", encoding="utf-8")
 
-    return str(out)
+    return ExportResult(path=str(out), skipped=skipped)
````

8c — `src/kiku/export/rekordbox_xml.py`:
````diff
--- a/src/kiku/export/rekordbox_xml.py
+++ b/src/kiku/export/rekordbox_xml.py
@@
 from kiku.config import DATA_DIR
 from kiku.db.models import Set
-from kiku.export.utils import export_path
+from kiku.export.utils import ExportResult, SkippedTrack, export_path, skip_reason
@@
 def export_set_to_xml(
     set_: Set,
     output_path: str | None = None,
     transition_cues: dict[int, list[dict]] | None = None,
-) -> str:
+) -> ExportResult:
@@
     Returns
     -------
-    str
-        Path to the written XML file.
+    ExportResult
+        The written file's path, plus any tracks left out for having no file.
+        Rekordbox treats an empty Location as a corrupt entry, so they are
+        omitted rather than written blank.
     """
@@
     tracks_in_set = sorted(set_.tracks, key=lambda st: st.position)
     playlist = xml.add_playlist(set_.name or "DJ Set")
+    skipped: list[SkippedTrack] = []
 
     for st in tracks_in_set:
         track = st.track
 
-        # --- Gap 2: reverse path alias for macOS ---
-        location = export_path(track.file_path, "macos") if track.file_path else ""
+        # An empty Location is a corrupt playlist row, not a degraded one. A
+        # record on the shelf is reported back to the caller instead (spec 030).
+        reason = skip_reason(track)
+        if reason:
+            skipped.append(
+                SkippedTrack(
+                    track_id=track.id,
+                    title=track.title or "Unknown Title",
+                    artist=track.artist,
+                    reason=reason,
+                )
+            )
+            continue
+
+        # --- Gap 2: reverse path alias for macOS ---
+        location = export_path(track.file_path, "macos")
 
         # --- Gap 1: use rb_id when available ---
         track_id = int(track.rb_id) if track.rb_id else track.id
 
         # --- Gap 3: detect file format ---
-        kind = _detect_kind(track.file_path) if track.file_path else "MP3 File"
+        kind = _detect_kind(track.file_path)
@@
     Path(output_path).parent.mkdir(parents=True, exist_ok=True)
     xml.save(output_path)
 
-    return output_path
+    return ExportResult(path=output_path, skipped=skipped)
````

Verification:
- `source .venv/bin/activate && python -m pytest tests/test_export_fileless.py -x -q` (written in Task 11).


#### Task 9 — unwrap ExportResult at all four call sites
Tools: editor

9a — `src/kiku/cli.py`, the `export` command (both formats). Lead with the skips:
the DJ needs to know what to pull before they need to know where the file went.
````diff
--- a/src/kiku/cli.py
+++ b/src/kiku/cli.py
@@
     if fmt == "m3u8":
         from kiku.export.m3u8 import export_set_to_m3u8
 
-        output_path = export_set_to_m3u8(
+        result = export_set_to_m3u8(
             set_,
             output,
             target_platform=platform,
             with_metadata=with_metadata,
         )
-        track_count = len(set_.tracks)
-        console.print(f"[green]Exported {track_count} tracks to {output_path}[/]")
+        _report_export_skips(result)
+        track_count = len(set_.tracks) - len(result.skipped)
+        console.print(f"[green]Exported {track_count} tracks to {result.path}[/]")
         console.print("[dim]Import into Rekordbox: File > Import > Import Playlist[/]")
@@
-        output_path = export_set_to_xml(set_, output, transition_cues=transition_cues)
-        console.print(f"[green]Exported to {output_path}[/]")
+        result = export_set_to_xml(set_, output, transition_cues=transition_cues)
+        _report_export_skips(result)
+        console.print(f"[green]Exported to {result.path}[/]")
+
+
+def _report_export_skips(result) -> None:
+    """Say what didn't make it into the playlist, and why.
+
+    A record on the shelf has no file to point at. Silence here would mean
+    finding out in the booth.
+    """
+    if not result.skipped:
+        return
+    console.print(
+        f"\n[yellow]{len(result.skipped)} track(s) aren't in the playlist — "
+        "they have no file to point at:[/]"
+    )
+    for s in result.skipped:
+        console.print(f"  [dim]•[/] {s.artist or '?'} — {s.title}  [dim]({s.reason})[/]")
+    console.print("[dim]Pull those by hand — the playlist covers the rest.[/]")
````

9b — `src/kiku/api/routes/export.py`. `FileResponse` has no body to put the skips
in, so they go in a response header the frontend can read (already CORS-exposed?
No — add it to `expose_headers` in Task 9c).
````diff
--- a/src/kiku/api/routes/export.py
+++ b/src/kiku/api/routes/export.py
@@
 from fastapi import APIRouter, Depends, HTTPException
 from fastapi.responses import FileResponse
@@
     from kiku.export.m3u8 import export_set_to_m3u8
 
-    output_path = export_set_to_m3u8(
+    result = export_set_to_m3u8(
         s,
         target_platform=platform,
         with_metadata=with_metadata,
     )
     return FileResponse(
-        path=output_path,
+        path=result.path,
         media_type="audio/x-mpegurl",
         filename=f"{s.name or 'set'}.m3u8",
+        headers=_skip_headers(result),
     )
@@
-    output_path = export_set_to_xml(s, transition_cues=transition_cues)
+    result = export_set_to_xml(s, transition_cues=transition_cues)
     return FileResponse(
-        path=str(output_path),
+        path=result.path,
         media_type="application/xml",
         filename=f"{s.name or 'set'}.xml",
+        headers=_skip_headers(result),
     )
+
+
+def _skip_headers(result) -> dict[str, str]:
+    """Tracks with no file can't be in the playlist — say so in the response.
+
+    A downloaded file has nowhere to carry a message, so the count and the list
+    ride along as headers and the UI surfaces them next to the download.
+    """
+    if not result.skipped:
+        return {}
+    listing = "; ".join(
+        f"{s.artist or '?'} - {s.title} ({s.reason})" for s in result.skipped
+    )
+    return {
+        "X-Kiku-Skipped-Count": str(len(result.skipped)),
+        # Header values must be latin-1; a title with an em dash would 500 the
+        # response otherwise.
+        "X-Kiku-Skipped": listing.encode("ascii", "replace").decode("ascii"),
+    }
````

9c — `src/kiku/api/main.py`, let the browser read those headers:
````diff
--- a/src/kiku/api/main.py
+++ b/src/kiku/api/main.py
@@
-        expose_headers=["Content-Range", "Accept-Ranges", "Content-Length"],
+        expose_headers=[
+            "Content-Range",
+            "Accept-Ranges",
+            "Content-Length",
+            "X-Kiku-Skipped-Count",
+            "X-Kiku-Skipped",
+        ],
````

9d — `src/kiku/visualization/callbacks.py`:
````diff
--- a/src/kiku/visualization/callbacks.py
+++ b/src/kiku/visualization/callbacks.py
@@
             cues = _get_all_set_cues(session, set_id)
-            output_path = export_set_to_xml(set_, transition_cues=cues)
+            result = export_set_to_xml(set_, transition_cues=cues)
             return html.Div(
                 [
                     html.Span("Exported: ", style={"color": "#2ecc71", "fontWeight": "600"}),
-                    html.Code(output_path, style={"color": "#00d2ff"}),
+                    html.Code(result.path, style={"color": "#00d2ff"}),
                 ]
             )
````

Verification:
- `source .venv/bin/activate && grep -rn "export_set_to_m3u8\|export_set_to_xml" src/ --include=*.py` —
  every call site now reads `.path`, none assigns the return value straight to a path.
- `source .venv/bin/activate && python -m pytest tests/api -x -q`

#### Task 10 — surface the medium: store filter, API, frontend
Tools: editor

10a — `src/kiku/db/store.py`, a `medium` filter on `search_tracks`:
````diff
--- a/src/kiku/db/store.py
+++ b/src/kiku/db/store.py
@@
     set_role: str | list[str] | None = None,
+    medium: str | None = None,
     sort: str | None = None,
     search: str | None = None,
     limit: int = 50,
     offset: int = 0,
 ) -> tuple[list[Track], int]:
     """Search tracks with multiple filters.
 
     Returns (tracks, total_count) to support pagination.
     genre/key/artist/label accept a single string or list of strings (OR-matched).
     sort: "recent" | "plays"/"plays_asc" | "rating"/"rating_asc" | "bpm"/"bpm_asc"
         (bare name = descending, "_asc" suffix = ascending).
     search: free-text OR-match across title, artist, and label.
     plays_min/plays_max: filter by combined play count (Rekordbox + Kiku).
+    medium: "digital" | "vinyl" — omit to see the whole library, both formats.
     """
@@
     if set_role:
@@
         q = q.filter(or_(*[Track.set_roles.ilike(f'%"{r}"%') for r in roles]))
+    if medium:
+        # coalesce: rows written before spec 030's backfill would otherwise
+        # disappear from a "digital" filter for having a NULL medium.
+        q = q.filter(func.coalesce(Track.medium, "digital") == medium)
     if plays_min is not None:
````

10b — `src/kiku/api/schemas.py`, `TrackResponse`:
````diff
--- a/src/kiku/api/schemas.py
+++ b/src/kiku/api/schemas.py
@@
     playlist_tags: list[str] = []
     set_roles: list[str] = []
     genre_family: str | None = None
+    # Vinyl (spec 030). `medium` is always present; the rest are NULL for digital.
+    medium: str = "digital"
+    vinyl_position: str | None = None
+    vinyl_release_id: int | None = None
+    bpm_source: str | None = None
+    key_source: str | None = None
 
     model_config = {"from_attributes": True}
````

10c — `src/kiku/api/routes/tracks.py`, map the fields and accept the filter:
````diff
--- a/src/kiku/api/routes/tracks.py
+++ b/src/kiku/api/routes/tracks.py
@@
         playlist_tags=tags,
         set_roles=roles,
         genre_family=family,
+        medium=t.medium or "digital",
+        vinyl_position=t.vinyl_position,
+        vinyl_release_id=t.vinyl_release_id,
+        bpm_source=t.bpm_source,
+        key_source=t.key_source,
     )
@@
     set_role: list[str] | None = Query(None),
+    medium: str | None = None,
     sort: str | None = None,
     limit: int = 50,
     offset: int = 0,
     db: Session = Depends(get_db),
 ):
     tracks, total = search_tracks(
         db,
@@
         set_role=set_role,
+        medium=medium,
         sort=sort,
         limit=limit,
         offset=offset,
     )
@@
             plays_min,
             plays_max,
             set_role,
+            medium,
         )
     )
````

Verification:
- `source .venv/bin/activate && python -m pytest tests/api -x -q`
- `curl -s 'http://localhost:8000/api/tracks/search?medium=vinyl&limit=5' | head` returns only shelf rows.


#### Task 11 — frontend: the vinyl pip and the medium filter
Tools: editor

**Indentation is TABS** in every Svelte file here. Match the surrounding lines exactly.

11a — create `frontend/src/lib/components/library/VinylPip.svelte`:
````diff
--- /dev/null
+++ b/frontend/src/lib/components/library/VinylPip.svelte
@@
+<script lang="ts">
+	let {
+		position = null,
+	}: {
+		/** The side printed on the label — "A1", "B2". */
+		position?: string | null;
+	} = $props();
+
+	const tip = $derived(position ? `On vinyl — side ${position}` : 'On vinyl');
+</script>
+
+<span class="vinyl-pip" title={tip} role="img" aria-label={tip}>
+	<svg viewBox="0 0 16 16" width="13" height="13" aria-hidden="true">
+		<circle cx="8" cy="8" r="7" fill="none" stroke="currentColor" stroke-width="1.4" />
+		<circle cx="8" cy="8" r="3.2" fill="none" stroke="currentColor" stroke-width="1" opacity="0.6" />
+		<circle cx="8" cy="8" r="1.1" fill="currentColor" />
+	</svg>
+	{#if position}<span class="vinyl-pip__side">{position}</span>{/if}
+</span>
+
+<style>
+	.vinyl-pip {
+		display: inline-flex;
+		align-items: center;
+		gap: var(--space-2xs);
+		flex-shrink: 0;
+		color: var(--text-dim);
+		vertical-align: -2px;
+	}
+	.vinyl-pip__side {
+		font-size: var(--font-size-xs);
+		font-variant-numeric: tabular-nums;
+		letter-spacing: 0.02em;
+	}
+</style>
````

11b — `frontend/src/lib/components/library/TrackTable.svelte`. The pip rides in the
**title cell**, not a new column: the table's grid template is declared in three
places (`L224`, `L307`, `L380`) and a tenth column would have to be threaded
through all of them for a mark that is one glyph wide.
````diff
--- a/frontend/src/lib/components/library/TrackTable.svelte
+++ b/frontend/src/lib/components/library/TrackTable.svelte
@@
 	import StarRating from '../primitives/StarRating.svelte';
 	import SetRoleBadge from './SetRoleBadge.svelte';
+	import VinylPip from './VinylPip.svelte';
@@
 					<td class="col-title" title={track.title ?? ''}>
-						{track.title ?? '?'}
+						{#if track.medium === 'vinyl'}<VinylPip position={track.vinyl_position} />{/if}{track.title ?? '?'}
 					</td>
````

11c — `frontend/src/lib/api/tracks.ts`:
````diff
--- a/frontend/src/lib/api/tracks.ts
+++ b/frontend/src/lib/api/tracks.ts
@@
 	set_role?: string[];
+	medium?: string;
 	sort?: string;
 	limit?: number;
 	offset?: number;
 }
````

11d — `frontend/src/lib/components/library/SearchFilters.svelte`, four edits.

State (after the `setRoles` line):
````diff
--- a/frontend/src/lib/components/library/SearchFilters.svelte
+++ b/frontend/src/lib/components/library/SearchFilters.svelte
@@
 	let setRoles = $state<Set<string>>(new Set());
+	let medium = $state('');
 	let playsFilter = $state('');
````

Params:
````diff
--- a/frontend/src/lib/components/library/SearchFilters.svelte
+++ b/frontend/src/lib/components/library/SearchFilters.svelte
@@
 		if (setRoles.size > 0) params.set_role = [...setRoles];
+		if (medium) params.medium = medium;
 		if (playsFilter === 'unplayed') params.plays_max = 0;
````

"Has filters" + clear-all:
````diff
--- a/frontend/src/lib/components/library/SearchFilters.svelte
+++ b/frontend/src/lib/components/library/SearchFilters.svelte
@@
 		setRoles.size > 0 ||
+		medium !== '' ||
 		playsFilter !== '' ||
 		sort !== ''
 	);
@@
 		setRoles = new Set();
+		medium = '';
 		playsFilter = '';
 		sort = '';
 		onsearch({});
````

Active chip (immediately after the `{#each [...setRoles]}` block):
````diff
--- a/frontend/src/lib/components/library/SearchFilters.svelte
+++ b/frontend/src/lib/components/library/SearchFilters.svelte
@@
 			{#each [...setRoles] as role (role)}
 				<Chip value={SET_ROLE_LABELS[role]} size="sm" removable removeLabel="Clear {SET_ROLE_LABELS[role]} filter" onremove={() => toggleSetRole(role)} />
 			{/each}
+			{#if medium}
+				<Chip value={medium === 'vinyl' ? 'On vinyl' : 'Digital'} size="sm" removable removeLabel="Clear format filter" onremove={() => { medium = ''; searchNow(); }} />
+			{/if}
 			{#if playsFilter}
````

The control itself — a new `field-group` inserted between the Rating group's
closing `</div>` and `<div class="field-group field-group--role">`:
````diff
--- a/frontend/src/lib/components/library/SearchFilters.svelte
+++ b/frontend/src/lib/components/library/SearchFilters.svelte
@@
 						<option value="5">5</option>
 					</select>
 				</div>
+				<div class="field-group">
+					<span class="section-label">Format</span>
+					<select class="small-select" bind:value={medium} onchange={() => searchNow()} title="Files, records, or the whole library">
+						<option value="">Everything</option>
+						<option value="digital">Digital</option>
+						<option value="vinyl">On vinyl</option>
+					</select>
+				</div>
 				<div class="field-group field-group--role">
 					<span class="section-label">Set role</span>
````

11e — regenerate the API types so `Track` carries the new fields:
- `cd frontend && npm run gen:api`
  (Requires the Python env; the script builds the OpenAPI doc from the app.)

Verification:
- `cd frontend && npx svelte-check --tsconfig ./tsconfig.json` — 0 errors.
- `cd frontend && git diff --stat src/lib/api/schema.d.ts` — shows the five new
  `TrackResponse` fields and the `medium` query param.


#### Task 12 — unit tests
Tools: editor

Every test file uses the established fixture shape: a per-test SQLite file built
with `Base.metadata.create_all` (test DBs are throwaway; `tests/test_migrations.py`
is what guards the real chain).

12a — create `tests/test_vinyl_position.py`:
````diff
--- /dev/null
+++ b/tests/test_vinyl_position.py
@@
+"""Side strings are display truth; these are the sortable derivation of them."""
+
+from __future__ import annotations
+
+import pytest
+
+from kiku.vinyl.position import parse_position, side_letter
+
+
+@pytest.mark.parametrize(
+    "raw,expected",
+    [
+        ("A1", (1, 1)),
+        ("A2", (1, 2)),
+        ("B1", (2, 1)),
+        ("D4", (4, 4)),
+        ("a1", (1, 1)),
+        (" B2 ", (2, 2)),
+        ("C", (3, None)),
+        ("AA1", (27, 1)),
+        ("A-1", (1, 1)),
+        ("Digi 1", (None, 1)),
+        ("CD1-3", (None, 3)),
+        ("4", (None, 4)),
+        ("", (None, None)),
+        (None, (None, None)),
+    ],
+)
+def test_parse_position(raw, expected):
+    assert parse_position(raw) == expected
+
+
+def test_sides_sort_in_pressing_order():
+    """A record's sides must order A, B, C, D — not alphabetically by string."""
+    raws = ["B1", "A2", "A1", "C1", "B2"]
+    ordered = sorted(raws, key=lambda r: tuple(x or 0 for x in parse_position(r)))
+    assert ordered == ["A1", "A2", "B1", "B2", "C1"]
+
+
+def test_side_letter_round_trips():
+    for raw in ("A1", "B2", "Z1", "AA1"):
+        side, _ = parse_position(raw)
+        assert raw.startswith(side_letter(side))
+
+
+def test_a_non_side_position_never_claims_a_side():
+    """'Digi 1' is a download code, not a side. It must not become side 4."""
+    side, index = parse_position("Digi 1")
+    assert side is None
+    assert index == 1
````

12b — create `tests/test_vinyl_import.py`:
````diff
--- /dev/null
+++ b/tests/test_vinyl_import.py
@@
+"""Importing a record you own, and the provenance that keeps its numbers honest."""
+
+from __future__ import annotations
+
+import pytest
+from sqlalchemy import create_engine
+from sqlalchemy.orm import sessionmaker
+from sqlalchemy.pool import NullPool
+
+from kiku.db.models import Base, Track, VinylRelease
+from kiku.metadata.models import RecordingCandidate, ReleaseCandidate
+from kiku.vinyl.importer import apply_import, build_preview, set_manual_bpm_key
+
+
+@pytest.fixture()
+def session(tmp_path):
+    engine = create_engine(f"sqlite:///{tmp_path / 'v.db'}", poolclass=NullPool)
+    Base.metadata.create_all(engine)
+    s = sessionmaker(bind=engine)()
+    yield s
+    s.close()
+
+
+def _twelve_inch() -> ReleaseCandidate:
+    return ReleaseCandidate(
+        source="discogs",
+        source_id="4242",
+        album="AF 97",
+        artist="Alarico",
+        label="Klockworks",
+        catalog_number="KW38",
+        year=2022,
+        country="Germany",
+        format='Vinyl, 12", 33 ⅓ RPM, EP',
+        recordings=[
+            RecordingCandidate(title="AF 97", position=1, disc=1, position_raw="A1", length_ms=372000),
+            RecordingCandidate(title="Distorted Reality", position=2, disc=1, position_raw="A2"),
+            RecordingCandidate(title="Nine Six", position=1, disc=2, position_raw="B1"),
+        ],
+    )
+
+
+def test_import_writes_one_row_per_side(session):
+    release = apply_import(session, _twelve_inch())
+
+    tracks = session.query(Track).order_by(Track.disc_number, Track.track_number).all()
+    assert [t.vinyl_position for t in tracks] == ["A1", "A2", "B1"]
+    assert all(t.medium == "vinyl" for t in tracks)
+    assert all(t.file_path is None for t in tracks)
+    assert all(t.vinyl_release_id == release.id for t in tracks)
+    assert [t.disc_number for t in tracks] == [1, 1, 2]
+    assert release.side_count == 2
+    assert release.rpm == 33
+    assert release.catalog_number == "KW38"
+
+
+def test_a_record_without_a_bpm_is_flagged_not_guessed(session):
+    """Research R1: 1 recording in 54 had a BPM. A blank must stay a blank."""
+    apply_import(session, _twelve_inch())
+    tracks = session.query(Track).all()
+    assert all(t.bpm is None for t in tracks)
+    assert all(t.enrichment_status == "pending" for t in tracks)
+
+
+def test_manual_bpm_marks_its_provenance(session):
+    apply_import(session, _twelve_inch())
+    track = session.query(Track).filter_by(vinyl_position="A1").one()
+
+    set_manual_bpm_key(session, track.id, bpm=136.0, key="8A")
+
+    session.refresh(track)
+    assert track.bpm == 136.0
+    assert track.bpm_source == "manual"
+    assert track.key_source == "manual"
+    assert track.enrichment_status == "manual"
+
+
+def test_manual_bpm_rejects_a_number_that_isnt_one(session):
+    apply_import(session, _twelve_inch())
+    track = session.query(Track).first()
+    with pytest.raises(ValueError):
+        set_manual_bpm_key(session, track.id, bpm=0)
+    with pytest.raises(ValueError):
+        set_manual_bpm_key(session, track.id, bpm=1200)
+
+
+def test_adding_the_same_record_twice_doesnt_duplicate_the_shelf(session):
+    """The unique discogs id is what makes re-import safe (design §3)."""
+    apply_import(session, _twelve_inch())
+    apply_import(session, _twelve_inch())
+
+    assert session.query(VinylRelease).count() == 1
+    assert session.query(Track).count() == 3
+
+
+def test_reimport_keeps_the_bpm_you_typed(session):
+    apply_import(session, _twelve_inch())
+    track = session.query(Track).filter_by(vinyl_position="A1").one()
+    set_manual_bpm_key(session, track.id, bpm=136.0)
+
+    apply_import(session, _twelve_inch())
+
+    again = session.query(Track).filter_by(vinyl_position="A1").one()
+    assert again.bpm == 136.0
+    assert again.bpm_source == "manual"
+
+
+def test_preview_marks_sides_already_on_the_shelf(session):
+    apply_import(session, _twelve_inch())
+    preview = build_preview(session, _twelve_inch())
+    assert preview.is_reimport
+    assert preview.new_count == 0
+    assert all(r.existing_track_id is not None for r in preview.rows)
+
+
+def test_a_vinyl_row_with_a_bpm_is_a_normal_track(session):
+    """The finding that makes spec 030 cheap — nothing about scoring reads a file."""
+    from kiku.setbuilder.camelot import harmonic_score
+    from kiku.setbuilder.scoring import bpm_compatibility
+
+    apply_import(session, _twelve_inch())
+    track = session.query(Track).filter_by(vinyl_position="A1").one()
+    set_manual_bpm_key(session, track.id, bpm=136.0, key="8A")
+
+    digital = Track(title="A file", bpm=137.0, key="9A", medium="digital")
+    assert harmonic_score(track.key, digital.key) > 0
+    assert bpm_compatibility(track.bpm, digital.bpm) > 0
````

12c — create `tests/test_vinyl_sync_regression.py`:
````diff
--- /dev/null
+++ b/tests/test_vinyl_sync_regression.py
@@
+"""`kiku sync` must never touch a record on the shelf.
+
+This is the one silent-data-loss risk in spec 030 (Human Section L20).
+Reconciliation matches on `rb_id` then normalized `file_path` — a vinyl row has
+neither, so it should be invisible to sync. Nothing enforces that today except
+the shape of two queries, which is exactly why it is pinned here: a future
+"clean up orphans" pass would eat the crate without a single failing test.
+"""
+
+from __future__ import annotations
+
+import pytest
+from sqlalchemy import create_engine
+from sqlalchemy.orm import sessionmaker
+from sqlalchemy.pool import NullPool
+
+from kiku.db.models import Base, Track
+from kiku.db.sync import _backfill_filename_track_numbers
+
+
+@pytest.fixture()
+def session(tmp_path):
+    engine = create_engine(f"sqlite:///{tmp_path / 's.db'}", poolclass=NullPool)
+    Base.metadata.create_all(engine)
+    s = sessionmaker(bind=engine)()
+    yield s
+    s.close()
+
+
+@pytest.fixture()
+def shelf(session):
+    session.add(
+        Track(
+            medium="vinyl",
+            title="AF 97",
+            artist="Alarico",
+            album="AF 97",
+            vinyl_position="A1",
+            disc_number=1,
+            track_number=1,
+            bpm=136.0,
+            bpm_source="manual",
+            enrichment_status="manual",
+        )
+    )
+    session.commit()
+    return session.query(Track).filter_by(medium="vinyl").one()
+
+
+def test_a_vinyl_row_is_unreachable_by_rb_id_match(session, shelf):
+    """Sync's first lookup is `filter_by(rb_id=...)`. Vinyl has no rb_id."""
+    assert shelf.rb_id is None
+    assert session.query(Track).filter_by(rb_id="12345").first() is None
+
+
+def test_a_vinyl_row_is_unreachable_by_file_path_match(session, shelf):
+    """Sync's fallback is `filter_by(file_path=...)`. Vinyl has no path.
+
+    A NULL file_path must never be matched by a path lookup — if it were, the
+    first Rekordbox track with an empty FolderPath would overwrite a record.
+    """
+    assert shelf.file_path is None
+    assert session.query(Track).filter_by(file_path="").first() is None
+    assert session.query(Track).filter_by(file_path="/Volumes/SSD/x.aiff").first() is None
+
+
+def test_the_track_number_backfill_cannot_scramble_a_side(session, shelf):
+    """`_backfill_filename_track_numbers` only touches rows with a file_path."""
+    shelf.track_number = None
+    session.commit()
+
+    _backfill_filename_track_numbers(session)
+
+    session.refresh(shelf)
+    assert shelf.track_number is None  # untouched — it has no filename to read
+    assert shelf.vinyl_position == "A1"
+
+
+def test_sync_never_deletes(session, shelf):
+    """Reconciliation adds and updates; it has no delete path. Pin that."""
+    import inspect
+
+    from kiku.db import sync as sync_mod
+
+    source = inspect.getsource(sync_mod)
+    assert ".delete()" not in source, (
+        "sync.py grew a delete path — a vinyl row has no rb_id and no file_path, "
+        "so any 'remove what Rekordbox no longer has' pass would eat the shelf."
+    )
````

12d — create `tests/test_export_fileless.py`:
````diff
--- /dev/null
+++ b/tests/test_export_fileless.py
@@
+"""A track with no file must not become a corrupt playlist row."""
+
+from __future__ import annotations
+
+import pytest
+from sqlalchemy import create_engine
+from sqlalchemy.orm import sessionmaker
+from sqlalchemy.pool import NullPool
+
+from kiku.db.models import Base, Set, SetTrack, Track
+from kiku.export.m3u8 import export_set_to_m3u8
+
+
+@pytest.fixture()
+def session(tmp_path):
+    engine = create_engine(f"sqlite:///{tmp_path / 'e.db'}", poolclass=NullPool)
+    Base.metadata.create_all(engine)
+    s = sessionmaker(bind=engine)()
+    yield s
+    s.close()
+
+
+@pytest.fixture()
+def hybrid_set(session):
+    digital = Track(
+        title="A file", artist="Someone", bpm=134.0,
+        file_path="/run/media/mantis/SSD/Musica/a.aiff", duration_sec=360.0,
+        medium="digital",
+    )
+    record = Track(
+        title="AF 97", artist="Alarico", bpm=136.0, duration_sec=372.0,
+        medium="vinyl", vinyl_position="A1",
+    )
+    session.add_all([digital, record])
+    session.flush()
+    s = Set(name="Hybrid")
+    session.add(s)
+    session.flush()
+    session.add_all([
+        SetTrack(set_id=s.id, position=0, track_id=digital.id),
+        SetTrack(set_id=s.id, position=1, track_id=record.id),
+    ])
+    session.commit()
+    return s
+
+
+def test_m3u8_leaves_the_record_out_and_says_so(session, hybrid_set, tmp_path):
+    out = tmp_path / "hybrid.m3u8"
+    result = export_set_to_m3u8(hybrid_set, str(out))
+
+    assert len(result.skipped) == 1
+    assert result.skipped[0].title == "AF 97"
+    assert "A1" in result.skipped[0].reason
+
+
+def test_m3u8_never_writes_an_extinf_without_a_path(session, hybrid_set, tmp_path):
+    """The bug this closes: an #EXTINF followed by an empty line is corrupt."""
+    out = tmp_path / "hybrid.m3u8"
+    export_set_to_m3u8(hybrid_set, str(out))
+    lines = out.read_text().splitlines()
+
+    for i, line in enumerate(lines):
+        if line.startswith("#EXTINF"):
+            nxt = lines[i + 1]
+            assert nxt and not nxt.startswith("#"), f"#EXTINF with no path at line {i}"
+    assert "" not in lines
+
+
+def test_m3u8_names_the_side_to_pull(session, hybrid_set, tmp_path):
+    out = tmp_path / "hybrid.m3u8"
+    export_set_to_m3u8(hybrid_set, str(out))
+    text = out.read_text()
+
+    assert "# kiku:vinyl" in text
+    assert "AF 97" in text
+    assert "A1" in text
+
+
+def test_a_digital_only_set_reports_nothing_skipped(session, tmp_path):
+    track = Track(
+        title="A file", artist="Someone", bpm=134.0,
+        file_path="/run/media/mantis/SSD/Musica/a.aiff", medium="digital",
+    )
+    session.add(track)
+    session.flush()
+    s = Set(name="Digital")
+    session.add(s)
+    session.flush()
+    session.add(SetTrack(set_id=s.id, position=0, track_id=track.id))
+    session.commit()
+
+    result = export_set_to_m3u8(s, str(tmp_path / "d.m3u8"))
+    assert result.skipped == []
+
+
+def test_a_track_whose_file_vanished_is_skipped_too(session, tmp_path):
+    """Not a vinyl-only guard — any fileless row would have exported blank."""
+    from kiku.export.utils import skip_reason
+
+    orphan = Track(title="Lost", artist="Someone", medium="digital", file_path=None)
+    assert skip_reason(orphan) == "no file on disk"
````

12e — add one test to `tests/test_planner.py`, appended at the end of the file:
````diff
--- a/tests/test_planner.py
+++ b/tests/test_planner.py
@@
+def test_vinyl_stays_out_of_an_ordinary_build(session, library):
+    """Risk 3: a record with a BPM is plannable the moment it exists.
+
+    That is the finding spec 030 rests on — and exactly why it must be opt-in
+    until the vinyl ratio and deck-change penalty ship. A routine build has to
+    return the same thing it returned before the migration.
+    """
+    from kiku.setbuilder.planner import _get_candidate_pool
+
+    session.add(
+        Track(
+            title="AF 97", artist="Alarico", bpm=136.0, key="8A",
+            medium="vinyl", vinyl_position="A1", bpm_source="manual",
+        )
+    )
+    session.commit()
+
+    default_pool = _get_candidate_pool(session)
+    assert all(t.medium != "vinyl" for t in default_pool)
+
+    opted_in = _get_candidate_pool(session, include_vinyl=True)
+    assert any(t.medium == "vinyl" for t in opted_in)
+
+
+def test_a_null_medium_is_still_digital(session):
+    """Rows written before the backfill must not vanish from the pool.
+
+    `Track.medium != "vinyl"` would drop them: in SQL, NULL fails that
+    comparison. The pool coalesces instead.
+    """
+    from kiku.setbuilder.planner import _get_candidate_pool
+
+    session.add(Track(title="Old row", artist="X", bpm=130.0, key="8A", medium=None))
+    session.commit()
+
+    assert len(_get_candidate_pool(session)) == 1
````

Verification:
- `source .venv/bin/activate && python -m pytest tests/ -x -q` — the whole suite green.


#### Task 13 — E2E: a record goes from Discogs to a plannable row
Tools: editor + shell

13a — create `tests/test_vinyl_e2e.py`. This walks the whole feature on a real
migrated database with a stubbed Discogs wire, so the migration, the source, the
importer, the pool guard and the exporter are all exercised together:
````diff
--- /dev/null
+++ b/tests/test_vinyl_e2e.py
@@
+"""End to end: a record on the shelf becomes a row the builder can reach.
+
+Runs against a database built by the real migration chain, not `create_all`, so
+the columns under test are the ones a DJ's library will actually get.
+"""
+
+from __future__ import annotations
+
+import httpx
+import pytest
+from sqlalchemy import create_engine
+from sqlalchemy.orm import sessionmaker
+from sqlalchemy.pool import NullPool
+
+from alembic import command
+from alembic.config import Config
+from kiku.config import PROJECT_ROOT
+from kiku.db.models import Track, VinylRelease
+from kiku.metadata.sources.discogs import DiscogsSource
+from kiku.setbuilder.planner import _get_candidate_pool
+from kiku.vinyl.importer import apply_import, set_manual_bpm_key
+
+RELEASE_JSON = {
+    "id": 4242,
+    "title": "AF 97",
+    "year": 2022,
+    "country": "Germany",
+    "uri": "https://www.discogs.com/release/4242",
+    "artists": [{"name": "Alarico", "join": ""}],
+    "labels": [{"name": "Klockworks", "catno": "KW38"}],
+    "formats": [{"name": "Vinyl", "descriptions": ['12"', "33 ⅓ RPM", "EP"]}],
+    "images": [{"uri": "https://img.discogs.com/af97.jpg"}],
+    "tracklist": [
+        {"type_": "heading", "position": "", "title": "Side A"},
+        {"type_": "track", "position": "A1", "title": "AF 97", "duration": "6:12"},
+        {"type_": "track", "position": "A2", "title": "Distorted Reality", "duration": "5:48"},
+        {"type_": "track", "position": "B1", "title": "Nine Six", "duration": "6:30"},
+        {"type_": "track", "position": "Digi 1", "title": "AF 97 (Edit)", "duration": "4:02"},
+    ],
+}
+
+
+@pytest.fixture()
+def migrated_session(tmp_path, monkeypatch):
+    db_path = tmp_path / "e2e.db"
+    monkeypatch.setenv("KIKU_DB_PATH", str(db_path))
+    cfg = Config(str(PROJECT_ROOT / "alembic.ini"))
+    cfg.set_main_option("script_location", str(PROJECT_ROOT / "alembic"))
+    command.upgrade(cfg, "head")
+
+    engine = create_engine(f"sqlite:///{db_path}", poolclass=NullPool)
+    s = sessionmaker(bind=engine)()
+    yield s
+    s.close()
+    engine.dispose()
+
+
+@pytest.fixture()
+def discogs() -> DiscogsSource:
+    def handler(request: httpx.Request) -> httpx.Response:
+        if request.url.path == "/releases/4242":
+            return httpx.Response(200, json=RELEASE_JSON)
+        if request.url.path == "/database/search":
+            return httpx.Response(200, json={"results": [{"id": 4242}]})
+        return httpx.Response(404, json={})
+
+    return DiscogsSource(token="test-token", transport=httpx.MockTransport(handler))
+
+
+def test_shelf_to_set(migrated_session, discogs):
+    session = migrated_session
+
+    # 1. Look the record up.
+    candidates = discogs.search("AF 97", "Alarico", limit=1)
+    assert len(candidates) == 1
+    candidate = candidates[0]
+    assert candidate.catalog_number == "KW38"
+    assert candidate.format == 'Vinyl, 12", 33 ⅓ RPM, EP'
+    # The heading row is not a track; the download-only bonus is.
+    assert [r.position_raw for r in candidate.recordings] == ["A1", "A2", "B1", "Digi 1"]
+
+    # 2. It lands on the shelf, flagged, with nothing invented.
+    release = apply_import(session, candidate, acquired_on="2026-09-10")
+    assert session.query(VinylRelease).count() == 1
+    assert release.rpm == 33
+    assert release.side_count == 2  # A and B — "Digi 1" is not a side
+
+    rows = session.query(Track).filter(Track.medium == "vinyl").all()
+    assert len(rows) == 4
+    assert all(t.bpm is None and t.enrichment_status == "pending" for t in rows)
+
+    # 3. Before a BPM exists, the builder cannot reach it — and neither can an
+    #    opt-in build, because there is nothing to plan with.
+    assert _get_candidate_pool(session, include_vinyl=True) == []
+
+    # 4. The DJ types the number. That is the import path (Research R2).
+    a1 = session.query(Track).filter_by(vinyl_position="A1").one()
+    set_manual_bpm_key(session, a1.id, bpm=136.0, key="8A")
+
+    # 5. Now it is a first-class candidate — but only when asked for (Risk 3).
+    assert _get_candidate_pool(session) == []
+    pool = _get_candidate_pool(session, include_vinyl=True)
+    assert [t.vinyl_position for t in pool] == ["A1"]
+    assert pool[0].bpm_source == "manual"
+
+    # 6. Adding the same pressing again doesn't grow a second shelf, and doesn't
+    #    forget what was typed.
+    apply_import(session, candidate)
+    assert session.query(VinylRelease).count() == 1
+    assert session.query(Track).filter(Track.medium == "vinyl").count() == 4
+    session.refresh(a1)
+    assert a1.bpm == 136.0
+
+
+def test_existing_digital_library_is_untouched_by_the_migration(migrated_session):
+    """Every row that existed before spec 030 reads as digital, and still plans."""
+    session = migrated_session
+    session.add(
+        Track(
+            title="A file", artist="Someone", bpm=134.0, key="8A",
+            file_path="/run/media/mantis/SSD/Musica/a.aiff",
+        )
+    )
+    session.commit()
+
+    row = session.query(Track).one()
+    assert row.medium is None or row.medium == "digital"
+    assert len(_get_candidate_pool(session)) == 1
````

13b — the manual pass against the real Discogs API, run once by hand with the
token now configured (this is what closes Research R3's unmeasured hop for
*catalog identity*, even though the MB URL-relation question stays slice-2):
```bash
source .venv/bin/activate
kiku config show | grep -i discogs          # confirm the token is there
kiku vinyl add "AF 97" -a Alarico --dry-run # candidate list + tracklist, nothing written
kiku vinyl add "AF 97" -a Alarico -y --no-fill
kiku vinyl list                             # 0/N plannable
kiku vinyl bpm <track_id> 136 -k 8A
kiku vinyl list                             # 1/N plannable
kiku build --name "vinyl guard check" --duration 30   # must contain NO vinyl rows
kiku export "vinyl guard check" --format m3u8         # no skips reported
```

Then, with the record hand-added to a set through the UI, confirm the export
honesty path:
```bash
source .venv/bin/activate && kiku export "<set with a record in it>" --format rekordbox
# expect: the yellow "aren't in the playlist" block naming the side to pull,
# and an XML whose entries all have a non-empty Location.
```

Frontend pass (`cd frontend && npm run dev`, backend on :8000):
- Library → Format → **On vinyl** shows only the record; **Digital** shows the rest;
  **Everything** shows both.
- The vinyl row carries the pip and its side in the Title column.
- The active-filter chip reads "On vinyl" and clears cleanly.

#### Task 14 — lint, format, type-check
Tools: shell

```bash
source .venv/bin/activate && ruff check --fix \
  src/kiku/db/models.py \
  src/kiku/db/store.py \
  src/kiku/vinyl/__init__.py \
  src/kiku/vinyl/position.py \
  src/kiku/vinyl/importer.py \
  src/kiku/metadata/models.py \
  src/kiku/metadata/sources/discogs.py \
  src/kiku/metadata/sources/musicbrainz.py \
  src/kiku/setbuilder/planner.py \
  src/kiku/export/utils.py \
  src/kiku/export/m3u8.py \
  src/kiku/export/rekordbox_xml.py \
  src/kiku/api/main.py \
  src/kiku/api/schemas.py \
  src/kiku/api/routes/tracks.py \
  src/kiku/api/routes/export.py \
  src/kiku/visualization/callbacks.py \
  src/kiku/cli.py \
  alembic/versions/a2b4c6d8e0f1_add_vinyl_medium_and_releases.py \
  tests/test_vinyl_position.py tests/test_vinyl_import.py \
  tests/test_vinyl_sync_regression.py tests/test_export_fileless.py \
  tests/test_vinyl_e2e.py tests/test_planner.py
```

**CI runs `ruff format --check` — this is not optional and it has bitten this repo
before** (commit `0331a24`, "ruff format the three test files CI flagged"):
```bash
source .venv/bin/activate && ruff format <the same file list>
source .venv/bin/activate && ruff format --check src/ tests/ alembic/
```

Then:
```bash
source .venv/bin/activate && python -m pytest tests/ -q
cd frontend && npx svelte-check --tsconfig ./tsconfig.json
```

Expectations: ruff clean, `ruff format --check` reports no files would be
reformatted, the full Python suite green (~426 + ~30 new), svelte-check 0 errors.

#### Task 15 — commit
Tools: git

```bash
BRANCH=$(git rev-parse --abbrev-ref HEAD); [ "$BRANCH" != "main" ] || { echo 'ERROR: On main' >&2; exit 2; }
git add -- \
  alembic/versions/a2b4c6d8e0f1_add_vinyl_medium_and_releases.py \
  src/kiku/db/models.py src/kiku/db/store.py \
  src/kiku/vinyl/ \
  src/kiku/metadata/models.py \
  src/kiku/metadata/sources/discogs.py src/kiku/metadata/sources/musicbrainz.py \
  src/kiku/setbuilder/planner.py \
  src/kiku/export/utils.py src/kiku/export/m3u8.py src/kiku/export/rekordbox_xml.py \
  src/kiku/api/main.py src/kiku/api/schemas.py \
  src/kiku/api/routes/tracks.py src/kiku/api/routes/export.py \
  src/kiku/visualization/callbacks.py src/kiku/cli.py \
  frontend/src/lib/api/tracks.ts frontend/src/lib/api/schema.d.ts \
  frontend/src/lib/components/library/VinylPip.svelte \
  frontend/src/lib/components/library/TrackTable.svelte \
  frontend/src/lib/components/library/SearchFilters.svelte \
  tests/test_vinyl_position.py tests/test_vinyl_import.py \
  tests/test_vinyl_sync_regression.py tests/test_export_fileless.py \
  tests/test_vinyl_e2e.py tests/test_planner.py
git commit -m "spec(030): IMPLEMENT - the records on your shelf are part of your library"
```

Commit body should note the two behavior changes that reach existing features:
`kiku fix-album --source discogs` now proposes real side positions for
`disc_number`, and both exporters skip fileless tracks instead of writing an
empty `Location`.


### Validate

Every Human Section requirement, and where this plan answers it. **Slice 2** means
deliberately deferred by the slicing decision at the top of this Plan, not dropped.

**Mid-Level Objectives**

| Spec | Requirement | How this plan complies |
|---|---|---|
| L12 | `medium` + `vinyl_position` via Alembic, backfill to `digital`, no `create_all` | Task 1 adds both (plus 6 more design columns) and runs the `UPDATE` backfill; Task 2 mirrors them in the ORM; `tests/test_migrations.py` proves the two agree. |
| L13 | Manual release-import writing one Track row per recording with the named fields | Task 5 `apply_import` writes `medium`, `album`, `artist`, `label`, `release_year`, `track_number`, `disc_number`, `duration_sec`, `vinyl_position`; Task 6 is the CLI over it; Discogs is the default source, MusicBrainz the fallback. |
| L14 | AcousticBrainz enrichment + vibe derivation | **Slice 2.** Research R1 measured 1.9% coverage; building an enricher first would put the DJ in front of 49 blank rows in 50. The columns it needs (`mb_recording_id`, `bpm_source`, `enrichment_status`, `audio_features.source`) all land in Task 1, so slice 2 needs no second migration. |
| L15 | `RecordingCandidate.mbid`, populated from `track["recording"]["id"]` | Task 4a adds the field; Task 4b populates it. The Discogs→MB secondary search is slice 2 (Research R3 leaves it the highest-value unmeasured hop). |
| L16 | Misses land flagged and editable, never guessed; manual entry sets a source marker enrichment can't overwrite | Task 5: rows land `enrichment_status="pending"` with `bpm IS NULL`; `set_manual_bpm_key` writes `bpm_source="manual"` / `key_source="manual"` / `enrichment_status="manual"`, the top rung of the ladder. Pinned by `test_a_record_without_a_bpm_is_flagged_not_guessed` and `test_reimport_keeps_the_bpm_you_typed`. |
| L17 | Vinyl ratio + deck-change penalty as a bounded soft bias | **Slice 2.** Task 7 ships the honest interim: `include_vinyl=False`, so nothing changes for an existing build until the bias exists. |
| L18 | Vinyl badge on the track row + changeover marker on the transition strip | Badge: Task 11a/11b (`VinylPip`, side shown). Changeover marker on the transition strip: **slice 2**, alongside the penalty that creates the changeover. |
| L19 | `kiku export` must not emit a broken `Location`; one behavior, decided | Task 8 decides **skip and report** (rationale in Decisions §1), implements it in both exporters, and Task 9 surfaces it in CLI, API and the Dash view. Pinned by `tests/test_export_fileless.py`, including "no `#EXTINF` without a path". |
| L20 | `kiku sync` never touches vinyl; add the regression test | Task 12c pins all three routes: no `rb_id` match, no `file_path` match, and the filename backfill can't reach a fileless row — plus a guard that fails if `sync.py` ever grows a delete path. |
| L21 | Stats / `kiku gaps` / Taste DNA readable per-medium | **Partly slice 2.** `search_tracks` gains the `medium` filter (Task 10a) and the API exposes it (10c), so the library is readable per-medium today. `insights.py` is deliberately left unfiltered so an owned record already stops the gap report recommending it; the explicit digital/vinyl/both toggle on stats ships with the ratio control. |
| L22 | `svelte-check` passes, Python suite green | Task 14 runs both, plus `ruff format --check` because CI enforces it. |

**Details — risks**

| Spec | Risk | How this plan complies |
|---|---|---|
| L32 | AcousticBrainz coverage unproven; spike first | Done in RESEARCH (R1). This plan is the rewrite that finding forced: manual entry is the import, not the fallback. |
| L33 | Two-hop identity is fuzzy; every hop needs confidence + override | Slice 1 takes **zero** fuzzy hops — Discogs release id is exact, and `_mbid_for` only ever carries an MBID the source itself supplied. Nothing is guessed, so nothing needs an override yet. The confidence UI lands with the Discogs→MB hop in slice 2. |
| L34 | Vinyl enters the pool immediately; land the planner change with the migration, or default the ratio to 0 | Task 7 lands in the same commit as Task 1. `include_vinyl=False` **is** the ratio-0 default. Pinned by `test_vinyl_stays_out_of_an_ordinary_build` and, for pre-backfill rows, `test_a_null_medium_is_still_digital`. |
| L35 | Export is the sharpest edge | Task 8, above. |

**Details — open questions answered**

- *L45 — does a vinyl track without a BPM belong in the library at all?* **Yes, in the
  library, flagged `pending`.** It is real to Taste DNA, to `kiku gaps` and to
  browsing the moment it exists; a staging table would fork every one of those.
  It is invisible only to the one thing it genuinely can't do — beam search —
  and that falls out of `Track.bpm > 0` for free, no staging state required.
  `kiku vinyl list` shows the plannable count so the gap is never silent.
- *L46 — where does manual BPM/key entry live?* **On the import path itself.**
  `kiku vinyl add` walks into the fill pass automatically unless `--no-fill`;
  `kiku vinyl fill` resumes it; `kiku vinyl bpm` fixes one side. Research R2
  answered this: at 2% enrichment, "come back to track detail later" means never.
- *L47 — should rip-and-analyze be an escape hatch?* **It should be planned, not
  documented** (Research R2.4) — it is the only route to a waveform, cue points
  and the transition inspector for vinyl. It is **slice 2** work; nothing in
  slice 1 blocks it, since a rip attaches a `file_path` and an `AudioFeatures`
  row to a track that already exists.
- *L48 — pressed length vs played length at a pitched BPM?* **Not in slice 1.**
  `duration_sec` stores the pressed length from Discogs, which is right for
  display and honest about its source. The set's time budget only drifts once
  records are actually being planned into sets — i.e. with the vinyl ratio — so
  the pitched-duration correction belongs to slice 2 and is noted here so it
  isn't rediscovered as a bug.

**Behavior**

| Spec | Behavior | How this plan complies |
|---|---|---|
| L51 | `kiku vinyl add` — candidates with track counts, selection, rich summary, `--dry-run`/`--yes`, `fix-album`'s shape | Task 6, modelled line-for-line on `fix_album`: `Table` of candidates, preview table of sides, `--dry-run`, `--yes`, confirm-by-default. |
| L52 | `kiku vinyl enrich` with per-track hit/miss | **Slice 2** — the command only makes sense once there is something to enrich from. `kiku vinyl fill` is its slice-1 counterpart and reports the same per-side outcome. |
| L53 | Library view: medium filter, vinyl badge, side position in results | Task 10 (API + store) and Task 11 (filter, pip, side string in the pip). |
| L54 | Non-zero vinyl ratio groups records, changeover marked, side named | **Slice 2.** |
| L55 | `kiku sync` after a vinyl import leaves vinyl untouched | Task 12c. |


## Plan Review

## Implement

## Test Evidence & Outputs

## Updated Doc

## Post-Implement Review
