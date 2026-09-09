#!/usr/bin/env python3
"""Measure what AcousticBrainz actually knows about a crate of records.

Step 1 of the vinyl build order (`specs/2026/08/vinyl-library/`). Nothing else in
spec 030 is worth building until this number exists, because it decides the shape
of the import UI: "confirm what we found" if coverage is high, "fill in what we
couldn't" if it is not.

The measurement separates two failure modes that are easy to conflate and have
completely different fixes:

  * **unresolved** — MusicBrainz could not identify the record at all. Fixed by a
    better identity hop (Discogs release → MB URL relation), or by hand.
  * **no submission** — MB knows the recording, AcousticBrainz has never been fed
    it. No identity work fixes this; only a rip-and-analyze or manual entry does.

Reporting one number for both would hide which problem the DJ actually has.

Each of BPM, key and the mood/danceability models is counted separately, because
they come from different AcousticBrainz endpoints and a record can hit one and
miss the other — and because they buy different things. BPM is what puts a track
into the beam-search pool at all (`planner.py:92`); the moods only refine it.

Usage:
    # The real measurement — one "Artist - Album" per line, records off the shelf.
    python scripts/ab_coverage_spike.py --input my_crate.txt

    # A stand-in sample from the digital library, for a number today. The
    # library is NOT the crate, but it is the same population: small-label
    # electronic, EPs, edits. Treat the result as an upper bound and say so.
    python scripts/ab_coverage_spike.py --from-library 25
"""

from __future__ import annotations

import argparse
import json
import random
import sqlite3
import sys
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from kiku.musicbrainz.client import MusicBrainzClient  # noqa: E402

AB_BASE = "https://acousticbrainz.org/api/v1"
# The documented ceiling for the batch endpoints.
AB_BATCH = 25
AB_TIMEOUT_S = 45.0
# MB's own search score, 0-100. Below this the release is a guess, not a match,
# and a guess here silently attaches another record's BPM and mood.
MIN_MB_SCORE = 85
# MusicBrainz answers a burst with 503 and expects you to back off. Its 1 req/s
# limit is an *average*, not a licence to send exactly one per second forever —
# a 25-record run trips it within a dozen calls. A 503 is a "come back later",
# never a miss, and counting it as one would understate coverage badly.
MB_RETRIES = 5
MB_BACKOFF_S = 2.0

MOOD_MODELS = ("mood_happy", "mood_sad", "mood_aggressive", "mood_relaxed")


def with_retry(fn, *args, **kwargs):
    """Run an MB call, backing off on 503. Re-raises anything else untouched."""
    delay = MB_BACKOFF_S
    for attempt in range(MB_RETRIES):
        try:
            return fn(*args, **kwargs)
        except httpx.HTTPStatusError as err:
            if err.response.status_code != 503 or attempt == MB_RETRIES - 1:
                raise
            print(f"        · MusicBrainz asked us to wait {delay:.0f}s", flush=True)
            time.sleep(delay)
            delay *= 2
    raise AssertionError("unreachable")


@dataclass
class TrackResult:
    title: str
    mbid: str
    bpm: float | None = None
    key: str | None = None
    danceability: float | None = None
    moods: dict[str, float] = field(default_factory=dict)

    @property
    def has_bpm(self) -> bool:
        return self.bpm is not None

    @property
    def has_key(self) -> bool:
        return self.key is not None

    @property
    def has_moods(self) -> bool:
        """All four mood models plus danceability — a partial set is not usable
        on the same axes as an Essentia-analyzed track."""
        return self.danceability is not None and all(m in self.moods for m in MOOD_MODELS)


@dataclass
class RecordResult:
    artist: str
    album: str
    #: 'ok' | 'unresolved' | 'low_confidence' | 'no_tracklist' | 'error'
    status: str
    mb_score: int | None = None
    mb_release_id: str | None = None
    mb_title: str | None = None
    tracks: list[TrackResult] = field(default_factory=list)
    note: str | None = None


def resolve_release(mb: MusicBrainzClient, artist: str, album: str) -> RecordResult:
    """Album + artist → an MB release and its recording MBIDs.

    This is the fuzzy fallback path from the design's Stage 2. The exact path
    (Discogs release → MB URL relation) needs a Discogs token and identifies a
    *pressing*; for measuring feature coverage the recording is what matters, and
    every pressing of a recording shares its MBID.
    """
    result = RecordResult(artist=artist, album=album, status="error")

    releases = with_retry(mb.search_releases, album, artist, limit=3)
    if not releases:
        result.status = "unresolved"
        result.note = "MusicBrainz returned no release for this album + artist"
        return result

    best = releases[0]
    result.mb_score = best.get("score")
    result.mb_release_id = best.get("id")
    result.mb_title = best.get("title")

    if (result.mb_score or 0) < MIN_MB_SCORE:
        result.status = "low_confidence"
        result.note = f"top MB hit scored {result.mb_score}, below {MIN_MB_SCORE}"
        return result

    detail = with_retry(mb.get_release, result.mb_release_id)
    for medium in detail.get("media") or []:
        for track in medium.get("tracks") or []:
            recording = track.get("recording") or {}
            mbid = recording.get("id")
            if mbid:
                result.tracks.append(
                    TrackResult(title=recording.get("title") or track.get("title") or "?", mbid=mbid)
                )

    if not result.tracks:
        result.status = "no_tracklist"
        result.note = "MB release carries no recordings"
        return result

    result.status = "ok"
    return result


def _batches(items: list[str], size: int):
    for i in range(0, len(items), size):
        yield items[i : i + size]


def enrich(client: httpx.Client, tracks: list[TrackResult]) -> None:
    """Fill BPM/key/moods in place from the two AcousticBrainz batch endpoints.

    A miss is a track whose MBID simply is not in the dataset — AcousticBrainz
    stopped accepting submissions in 2022. It returns 200 with the MBID absent
    from the body rather than an error, so absence is read, not caught.
    """
    by_mbid = {t.mbid: t for t in tracks}
    ids = list(by_mbid)

    for batch in _batches(ids, AB_BATCH):
        joined = ";".join(batch)

        low = client.get(f"{AB_BASE}/low-level", params={"recording_ids": joined})
        low.raise_for_status()
        for mbid, offsets in low.json().items():
            doc = next(iter(offsets.values()), {})
            track = by_mbid.get(mbid)
            if track is None:
                continue
            track.bpm = (doc.get("rhythm") or {}).get("bpm")
            tonal = doc.get("tonal") or {}
            if tonal.get("key_key"):
                track.key = f"{tonal['key_key']} {tonal.get('key_scale', '')}".strip()

        high = client.get(f"{AB_BASE}/high-level", params={"recording_ids": joined})
        high.raise_for_status()
        for mbid, offsets in high.json().items():
            doc = next(iter(offsets.values()), {})
            track = by_mbid.get(mbid)
            if track is None:
                continue
            hl = doc.get("highlevel") or {}
            dance = (hl.get("danceability") or {}).get("all") or {}
            if "danceable" in dance:
                track.danceability = dance["danceable"]
            for model in MOOD_MODELS:
                allv = (hl.get(model) or {}).get("all") or {}
                # The positive side of each binary model, e.g. mood_happy.happy.
                positive = model.split("_", 1)[1]
                if positive in allv:
                    track.moods[model] = allv[positive]


def sample_library(db_path: Path, n: int) -> list[tuple[str, str]]:
    """Albums from the digital library, as a stand-in when there is no crate list."""
    con = sqlite3.connect(db_path)
    try:
        rows = con.execute(
            """
            SELECT artist, album
            FROM tracks
            WHERE album IS NOT NULL AND album != ''
              AND artist IS NOT NULL AND artist != ''
            GROUP BY album, artist
            HAVING COUNT(*) >= 3
            ORDER BY RANDOM()
            LIMIT ?
            """,
            (n,),
        ).fetchall()
    finally:
        con.close()
    return [(a, b) for a, b in rows]


def read_input(path: Path) -> list[tuple[str, str]]:
    """One record per line, `Artist - Album`. Blank lines and # comments ignored."""
    records: list[tuple[str, str]] = []
    for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        for sep in (" — ", " – ", " - "):
            if sep in line:
                artist, album = line.split(sep, 1)
                records.append((artist.strip(), album.strip()))
                break
        else:
            raise ValueError(f"{path}:{lineno}: expected 'Artist - Album', got {line!r}")
    return records


def report(results: list[RecordResult], *, proxy: bool) -> None:
    print()
    print("═" * 78)
    print("  AcousticBrainz coverage — vinyl spike")
    print("═" * 78)

    resolved = [r for r in results if r.status == "ok"]
    all_tracks = [t for r in resolved for t in r.tracks]

    print(f"\n  Records asked about : {len(results)}")
    for status in ("ok", "low_confidence", "unresolved", "no_tracklist", "error"):
        n = sum(1 for r in results if r.status == status)
        if n:
            print(f"    {status:<16}: {n}")

    if not all_tracks:
        print("\n  No recordings resolved — nothing to measure. The identity hop is the")
        print("  problem here, not AcousticBrainz coverage.")
        return

    n = len(all_tracks)
    bpm = sum(t.has_bpm for t in all_tracks)
    key = sum(t.has_key for t in all_tracks)
    mood = sum(t.has_moods for t in all_tracks)
    nothing = sum(not (t.has_bpm or t.has_key or t.has_moods) for t in all_tracks)

    print(f"\n  Recordings resolved : {n} (across {len(resolved)} records)")
    print("\n  Hit rate, per feature — these are NOT interchangeable:")
    print(f"    BPM          : {bpm:>4}/{n}  {bpm / n:6.1%}   ← decides if it can be planned at all")
    print(f"    Key          : {key:>4}/{n}  {key / n:6.1%}")
    print(f"    Mood + dance : {mood:>4}/{n}  {mood / n:6.1%}   ← all 4 models + danceability")
    print(f"    Nothing      : {nothing:>4}/{n}  {nothing / n:6.1%}   ← needs manual entry or a rip")

    print("\n  Per record:")
    for r in results:
        if r.status != "ok":
            print(f"    ✗  {r.artist} — {r.album}  [{r.status}] {r.note or ''}")
            continue
        hits = sum(t.has_bpm for t in r.tracks)
        mark = "✓" if hits == len(r.tracks) else ("~" if hits else "✗")
        print(
            f"    {mark}  {r.artist} — {r.album}"
            f"  [{hits}/{len(r.tracks)} with BPM, MB score {r.mb_score}]"
        )

    print("\n" + "─" * 78)
    print("  What this means for the import UI")
    print("─" * 78)
    rate = bpm / n
    if rate >= 0.7:
        print("  Coverage is high. The import can lead with what it found and ask the DJ")
        print("  to confirm — 'here is the tracklist, here are the numbers, look right?'")
    elif rate >= 0.35:
        print("  Coverage is mixed. The import must be honest per track, not per record:")
        print("  found rows and blank rows side by side, with entry in the same place.")
    else:
        print("  Coverage is poor. Build the import as 'fill in what we couldn't' —")
        print("  manual BPM/key entry is the primary path, enrichment a bonus. The")
        print("  rip-and-analyze escape hatch stops being optional.")

    if proxy:
        print()
        print("  CAVEAT: this sampled the DIGITAL library, not the shelf. It is the same")
        print("  population (small-label electronic, EPs, edits) but records the DJ owns")
        print("  on vinyl skew newer and more obscure still. Treat this as an UPPER")
        print("  bound and re-run with --input once a real crate list exists.")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--input", type=Path, help="File of 'Artist - Album' lines (the real crate)")
    src.add_argument("--from-library", type=int, metavar="N", help="Sample N albums from the library instead")
    ap.add_argument("--db-path", type=Path, default=Path("data/dj_library.db"))
    ap.add_argument("--out", type=Path, default=Path("ab_coverage_spike.json"), help="Where to write the raw result")
    args = ap.parse_args()

    if args.input:
        records = read_input(args.input)
        proxy = False
    else:
        records = sample_library(args.db_path, args.from_library)
        proxy = True

    if not records:
        print("Nothing to look up.", file=sys.stderr)
        return 1

    print(f"Listening for {len(records)} records… (MusicBrainz is capped at 1 req/s, so this takes a minute)")

    results: list[RecordResult] = []
    started = time.monotonic()
    with MusicBrainzClient() as mb, httpx.Client(timeout=AB_TIMEOUT_S) as ab:
        for i, (artist, album) in enumerate(records, 1):
            print(f"  [{i}/{len(records)}] {artist} — {album}", flush=True)
            try:
                result = resolve_release(mb, artist, album)
                if result.status == "ok":
                    enrich(ab, result.tracks)
            except httpx.HTTPError as err:
                # Report and keep going: one dead lookup must not cost the whole
                # measurement, but it is never silently counted as a miss.
                result = RecordResult(artist=artist, album=album, status="error", note=str(err))
                print(f"        ! {err}", file=sys.stderr)
            results.append(result)

    report(results, proxy=proxy)
    args.out.write_text(json.dumps([asdict(r) for r in results], indent=2), encoding="utf-8")
    print(f"\n  Raw results: {args.out}  ({time.monotonic() - started:.0f}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
