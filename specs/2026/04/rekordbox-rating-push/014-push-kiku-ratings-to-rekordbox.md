# Human Section
Critical: any text/subsection here cannot be modified by AI.

## High-Level Objective (HLO)

Build a one-way push that writes Kiku-edited ratings into Rekordbox 6/7's `master.db` via `pyrekordbox`, and harden the existing rating-preservation guard so RB sync never overwrites a rating the DJ set in Kiku. The DJ rates in Kiku, not in Rekordbox — this closes the loop so star ratings travel back to the rig and survive every future sync. Treat the DJ's library as the lesson: their ratings are first-class signal, never something to silently churn.

## Mid-Level Objectives (MLO)

1. **PROBE** the Rekordbox rating scale before writing anything — short manual verification (rate 5 known tracks 1-5 in the Rekordbox UI, read back via `pyrekordbox`) to confirm `1..5` vs `51..255` mapping. Hardcode the resolved mapping in code.
2. **CREATE** a new module `src/kiku/export/rekordbox_db.py` that writes `DjmdContent.Rating` for one track at a time. Mirror the naming and structure of `src/kiku/export/rekordbox_xml.py`.
3. **ADD** a CLI command `kiku rekordbox push-ratings` with `--dry-run` (default), `--commit`, `--all`, and `--since <ISO timestamp>` flags. Default scope is "Kiku-edited only" (`rating_source='kiku'`).
4. **ADD** a frontend Settings page button "Push Ratings to Rekordbox" with preview table (track → old RB rating → new Kiku rating), explicit confirmation, and progress feedback.
5. **GUARD** the push with pre-flight safety gates:
   - REFUSE if the Rekordbox process is running (bubble `pyrekordbox`'s existing exception with a clear "what to try" message).
   - BACKUP `master.db`, `master.db-wal`, `master.db-shm` to `~/.kiku/backups/rekordbox/<ISO timestamp>/` before any write. Backup is mandatory and atomic — if it fails, the push aborts.
   - DETECT cloud-sync paths (Dropbox, iCloud Drive, OneDrive, Google Drive). Refuse with a hard error unless `--force-cloud-sync` is passed; warn loudly even then.
6. **MATCH** tracks by file path using the existing `normalize_path()` from `src/kiku/db/paths.py`. Do not invent a second matching path.
7. **HARDEN** rating preservation during RB → Kiku sync — promote the existing implicit `rating_source='kiku'` skip-overwrite (today at `src/kiku/db/sync.py:208-211`) to an explicit acceptance criterion with a regression test.
8. **ADD** a config option `rating_lock` (TOML at `~/.kiku/config.toml` and API at `/api/config/rating-lock`) with values `none` (current behavior — only protect Kiku-set ratings) or `kiku` (treat ALL ratings as Kiku-owned, never overwritten by RB sync regardless of `rating_source`). Default: `none`.
9. **DOCUMENT** rollback — a step-by-step "how to restore `master.db` from `~/.kiku/backups/rekordbox/<ts>/` if push goes wrong" lives next to the new module and is referenced from CLI `--help`.

## Details (DT)

### Background — read these, don't inline them

This spec stands on prior research. Treat these as the source of truth for the design and current state; do not duplicate their content here:

- **Plan**: `tmp/mux/20260425-1739-rekordbox-ratings-export/deliverable/PLAN.md` — full design and phasing.
- **Audit**: `tmp/mux/20260425-1739-rekordbox-ratings-export/audit/001-kiku-rating-state.md` — current state, 69 Kiku-edited tracks, existing `rating_source='kiku'` guard at `src/kiku/db/sync.py:208-211`.
- **Research — XML import**: `tmp/mux/20260425-1739-rekordbox-ratings-export/research/001-rekordbox-rating-import.md` — XML import regression notes.
- **Research — direct write**: `tmp/mux/20260425-1739-rekordbox-ratings-export/research/002-pyrekordbox-direct-write.md` — `pyrekordbox` direct-write API, encryption status, scale probe.

### The DJ's constraint (verbatim)

> "I want to make sure I don't lose my rating here by overriding from Rekordbox because I don't use that feature."

The DJ does not rate in Rekordbox. The push is one-way: Kiku → Rekordbox. RB sync must never silently overwrite a Kiku rating. This is not a nice-to-have — it's the core reason the feature exists.

### Scope

**In scope (v1):**
- One-way push of star ratings (1-5 stars) from Kiku to Rekordbox `master.db`.
- CLI and Settings UI entry points.
- Pre-flight safety: process check, mandatory backup, cloud-sync detection.
- Config-driven rating preservation hardening (`rating_lock`).
- Rollback documentation.

**Out of scope (v1):**
- Comments, hot cues, beat grid, memory cues, tags.
- Two-way merge (RB ratings flowing back into Kiku as a primary source).
- USB/SD card PDB writes (Pioneer's binary export format — see prior CDJ history shelved decision).
- Bulk rating editing in Kiku — this only ships the push, not new editing surfaces.

### Constraints

- `pyrekordbox` is already a dependency (used by `src/kiku/export/rekordbox_xml.py`).
- Rekordbox 6 and 7 both use SQLCipher-encrypted `master.db`. `pyrekordbox` handles decryption when Rekordbox has been run at least once on the host. Do not roll our own crypto.
- The push must be safe to run repeatedly — re-pushing the same Kiku rating to the same RB row is a no-op write (or skipped if values match).
- Path matching uses `normalize_path()` from `src/kiku/db/paths.py` so cross-platform aliases (`/Volumes/SSD/Musica` etc.) keep working.
- All async operations use `handlePromise` + error guard (TS) or wrapped exceptions (Python). Re-raise — never swallow.

### Files to create

- `src/kiku/export/rekordbox_db.py` — push module (mirrors `rekordbox_xml.py` shape).
- `src/kiku/export/rekordbox_db_rollback.md` — rollback runbook (referenced from CLI `--help`).
- `tests/test_rekordbox_db_push.py` — unit + integration tests.
- `tests/test_rating_preservation.py` — regression test for sync overwrite guard (covers both `rating_lock` modes).
- `frontend/src/lib/components/settings/PushRatingsPanel.svelte` — Settings UI.

### Files to modify

- `src/kiku/cli/__init__.py` (or wherever CLI commands register) — add `rekordbox push-ratings` subcommand.
- `src/kiku/db/sync.py` — extend `rating_source='kiku'` guard with `rating_lock` config check.
- `src/kiku/config/__init__.py` (or equivalent TOML loader) — add `rating_lock` field.
- `src/kiku/api/routes/config.py` — add `GET/PUT /api/config/rating-lock`.
- `src/kiku/api/schemas.py` — add `RatingLockMode` enum + request/response shapes.
- `frontend/src/lib/api/config.ts` — add `getRatingLock()` / `setRatingLock()`.
- `frontend/src/routes/settings/+page.svelte` — mount the new panel.

### Pre-flight gates (mandatory order)

1. **Cloud-sync detection** — inspect resolved `master.db` path for Dropbox / iCloud Drive / OneDrive / Google Drive markers. Refuse with `RatingPushError` unless `--force-cloud-sync`. Even with the override, log a loud warning.
2. **Rekordbox process check** — `pyrekordbox` already raises when the app is open. Catch its specific exception and re-raise as `RatingPushError` with a "close Rekordbox and try again" message.
3. **Backup** — copy `master.db`, `master.db-wal`, `master.db-shm` (whichever exist) to `~/.kiku/backups/rekordbox/<ISO timestamp>/`. Verify byte counts match. If backup fails, the push aborts before any write.
4. **Dry-run preview** — default mode. Builds the push plan (tracks + old → new ratings) without writing. `--commit` performs the writes.

### Push scope rules

- Default: only push tracks where `rating_source='kiku'` AND the Kiku rating differs from the RB rating.
- `--all` — push every track in Kiku that has a non-null rating, regardless of `rating_source` (use case: first-time migration after enabling `rating_lock=kiku`).
- `--since <ISO timestamp>` — limit to tracks edited in Kiku after the timestamp.
- Tracks with no file path match in RB are reported in the dry-run summary, never silently dropped.

### Rating preservation acceptance criteria

These are testable, not aspirational:

1. **Default mode (`rating_lock=none`)**: when RB sync encounters a track with `rating_source='kiku'` and a different RB rating, the Kiku rating is preserved. The new RB value is logged but not written. (This is today's behavior — promote it to a regression test.)
2. **Locked mode (`rating_lock=kiku`)**: when RB sync encounters ANY track with a Kiku rating set (regardless of `rating_source`), the Kiku rating is preserved. RB ratings can never overwrite.
3. **Push idempotence**: running `push-ratings --commit` twice in a row produces zero writes on the second run (values already match).
4. **Backup precedes write**: any test that triggers a write must verify the backup directory exists with the expected files before any DB mutation.

### CLI shape

```
kiku rekordbox push-ratings [--dry-run | --commit] [--all | --since <ISO>] [--force-cloud-sync]
```

- `--dry-run` is the default. Prints the plan and exits 0.
- `--commit` performs the writes. Requires explicit confirmation prompt unless `--yes` is passed.
- Output uses Kiku voice: lead with the interesting finding (e.g., "12 tracks ready to push, 2 already match, 1 missing in Rekordbox"), not a count dump.

### UI shape

- Settings page section "Rekordbox sync".
- Button: "Push Ratings to Rekordbox" → opens preview modal.
- Modal shows a table: Track | RB rating (current) | Kiku rating (new) | Status (will write / matches / not found).
- Two-step confirmation: "Preview" → "Push N ratings". Dropbox/iCloud detection blocks the second button with an inline warning + override toggle.
- Toggle: `rating_lock` mode (`none` / `kiku`) with one-sentence explanation each.

### Testing

**Unit tests (Python):**
- `rekordbox_db.py` push planner returns correct deltas for: matching ratings (skip), differing ratings (write), missing tracks (report).
- Cloud-sync path detector recognizes Dropbox / iCloud / OneDrive / Google Drive on macOS and Linux.
- Backup function copies all three files atomically and refuses to proceed on partial copy.
- Rating scale mapping: confirm 1..5 round-trip after probe (parametrized 1, 2, 3, 4, 5).

**Integration tests (Python):**
- Sync guard: pre-seed a track with `rating_source='kiku', rating=4`, simulate RB sync delivering `rating=2`, assert Kiku rating unchanged. Run twice — once with `rating_lock=none`, once with `rating_lock=kiku` (using `rating_source='rekordbox'` for the second case to prove `kiku` mode locks regardless of source).
- Push idempotence: push once with `--commit`, push again, assert second run plans zero writes.

**E2E tests (frontend):**
- Settings panel renders current `rating_lock` value and persists changes via `/api/config/rating-lock`.
- Preview modal blocks the "Push" button when cloud-sync detection fires (mock backend response).

### Open questions (defer to RESEARCH/PLAN)

- Does `pyrekordbox` write to `master.db-wal` or fold writes into `master.db` directly? Answer drives backup verification logic.
- Should `--all` migration mode also flip `rating_source` to `'kiku'` for every pushed row, so subsequent pushes stay narrow? Probably yes; confirm during PLAN.
- Cloud-sync detection on Windows is out of scope for v1 (Kiku is currently macOS/Linux). Confirm with the DJ that Windows can wait.

## Behavior

You are a senior AI engineer building a feature where the cost of a bug is permanent loss of the DJ's curation work. Bias toward refusal: when in doubt, abort the push and report. Every code path that touches `master.db` must be reachable only after the backup has been verified. Every error message follows Kiku voice — what happened, why, what to try — and never blames the DJ. Re-raise exceptions; never swallow them. When two product principles conflict, "Show the Why" and "Your Library Is the Lesson" outrank speed.

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
