---
id: OBS-003
title: Schema management is split between Alembic and create_all, and Alembic is broken
type: OBS
date: 2026-08-09
depends-on: []
superseded-by: null
---

## C — Context

The repository ships an Alembic migration chain *and* a `Base.metadata.create_all()` call.
Which one is the real source of truth, and does the other one work?

> **Re-check 2026-08-09 — resolved by [[PLN-001]]/P1.** E1–E7 below record the state that
> motivated the fix; they are kept because `CLM-004` and `CLM-001` derive from them. What
> changed is in **K6**. Two further divergences (R1, R2 below) were found only once the
> invariant test existed, which is the case for K4.

## E — Evidence

- **E1 · Two mechanisms exist.** `src/kiku/db/models.py:304` calls
  `Base.metadata.create_all(engine)`. `alembic/versions/` contains 14 revisions.
- **E2 · The chain is linear.** Following `down_revision`, all 14 revisions form a single
  path from `455598dafd10` (base) to `e1f2a3b4c5d6` (head). No branching, no multiple heads.
- **E3 · The ORM declares 10 tables** (`grep '__tablename__' src/kiku/db/models.py`):
  `tracks`, `audio_features`, `sets`, `set_tracks`, `transition_cues`, `hunt_sessions`,
  `hunt_tracks`, `track_affinities`, `oauth_tokens`, `album_metadata`.
- **E4 · The migrations create 8 of them.** `op.create_table` appears 8 times across 4
  revisions, creating: `tracks`, `audio_features`, `sets`, `set_tracks`, `transition_cues`,
  `track_affinities`, `oauth_tokens`, `album_metadata`.
  **`hunt_sessions` and `hunt_tracks` are never created by any migration.**
- **E5 · A migration then mutates a table it never created.**
  `alembic/versions/c3d4e5f6a7b8_add_oauth_tokens_and_hunt_external_fields.py` calls
  `op.add_column('hunt_tracks', ...)` twice.
- **E6 · Reproduction — a fresh `alembic upgrade head` fails.** Against an empty database:

  ```
  sqlalchemy.exc.OperationalError: (sqlite3.OperationalError) no such table: hunt_tracks
  [SQL: ALTER TABLE hunt_tracks ADD COLUMN external_url VARCHAR]
  ```

  Reproduce:
  ```bash
  mkdir -p /tmp/fakehome/.kiku
  printf '[paths]\ndb_path = "/tmp/fresh.db"\n' > /tmp/fakehome/.kiku/config.toml
  rm -f /tmp/fresh.db && HOME=/tmp/fakehome alembic upgrade head
  ```
- **E7 · The DB URL has no environment override.** `src/kiku/config.py:37` resolves the
  path from `~/.kiku/config.toml` or a hardcoded default. There is no `KIKU_DB_PATH` or
  `DATABASE_URL` env var (contrast `KIKU_MUSIC_ROOTS`, which does exist, at `config.py:48`).

## K — Conclusions

- **K1 · `create_all` is the de-facto source of truth.** It is the only mechanism that can
  produce a complete schema (E3, E4, E6). Alembic is a partial, decorative parallel record.
- **K2 · The migration chain cannot be run from scratch.** Not "might drift" — it raises
  on a clean database (E6). Any environment that has never seen `create_all` cannot be
  provisioned from the repository.
- **K3 · The two mechanisms will diverge further by construction.** `create_all` silently
  no-ops on existing tables and never alters columns, so an ORM column added without a
  matching migration is invisible on the author's machine and absent everywhere else. This
  is the mechanism behind the previously observed `hunt` schema-drift 500s.
- **K4 · E7 makes the defect hard to notice.** Because there is no env override, every test
  and every dev command points at the same already-migrated database, so the broken path
  in K2 is never exercised. The bug is *structurally* invisible.
- **K5 · This blocks deployment.** Any story that involves running Kiku somewhere other
  than this laptop — the personal-server arc, a second machine, a container, a CI job with
  a real DB — is gated on K2. See [[CLM-003]] and [[PLN-001]].

- **K6 · Resolved 2026-08-09.** `hunt_sessions`/`hunt_tracks` had only ever existed via
  `create_all` (answering Q1), so a single repair revision sufficed rather than a chain
  rebuild:
  - `b1c2d3e4f5a6` creates both tables, inserted between `a1c3e5f7d902` and
    `c3d4e5f6a7b8` so the latter's `add_column` has something to alter.
  - `_init_schema()` now runs `alembic upgrade head` (stamping head on a pre-Alembic
    database) instead of `create_all`. Alembic is the sole authority.
  - `KIKU_DB_PATH` added at `config.py:37`, closing E7.
  - `tests/test_migrations.py` asserts the chain runs from base, that every ORM table has
    a migration, and that `compare_metadata` finds no structural drift.
  - Verified: fresh DB builds all 10 tables; the API serves requests against a
    from-nothing database; a copy of the real 4,328-track library upgrades with
    `integrity_check: ok` and all row counts unchanged; 429 tests pass.

- **R1 · Drift found by the new test: two indexes existed only in migrations.**
  `ix_tracks_file_path` (`4b88935a2dcc`) and `ix_tracks_album` (`e5f6a7b8c9d0`) were never
  declared on the ORM. Every `create_all` database therefore lacked both — including all
  426 test fixtures and any fresh install. `file_path` is the column scan and sync look up
  against 4,300+ rows, so the two schema paths differed in *performance*, not just in
  shape. Fixed by declaring `index=True` on both columns.
- **R2 · Drift found by the new test: a foreign key existed only in the ORM.**
  `c9d0e1f2a3b4` added `sets.planned_set_id` with a bare `add_column`, since SQLite cannot
  attach an FK via ALTER, while the ORM declared `ForeignKey("sets.id")`. Fixed by
  `c2d3e4f5a6b7`, a `batch_alter_table` rebuild.
- **K7** [R1, R2] ⇒ Both divergences had been in the tree for months and neither was
  visible to any person or test. They were surfaced within a minute of the invariant
  existing. This is the concrete evidence for `CLM-003/K4`: the defect was never the code,
  it was that nothing was looking.

## Q — Open

- ~~**Q1.** Was `hunt_sessions`/`hunt_tracks` ever migrated?~~ No — closed by K6.
- **Q2.** `_init_schema()` now requires the `alembic/` directory at `PROJECT_ROOT`, so a
  non-editable wheel install would raise. Acceptable while Kiku ships as a checkout;
  revisit if it is ever packaged.
