"""add vinyl_releases table and medium columns to tracks

Revision ID: a2b4c6d8e0f1
Revises: c2d3e4f5a6b7
Create Date: 2026-09-10 10:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a2b4c6d8e0f1"
down_revision: Union[str, None] = "c2d3e4f5a6b7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "vinyl_releases",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("discogs_release_id", sa.String(), nullable=True),
        sa.Column("mb_release_id", sa.String(), nullable=True),
        sa.Column("title", sa.String(), nullable=True),
        sa.Column("artist", sa.String(), nullable=True),
        sa.Column("label", sa.String(), nullable=True),
        sa.Column("catalog_number", sa.String(), nullable=True),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column("country", sa.String(), nullable=True),
        sa.Column("format", sa.String(), nullable=True),
        sa.Column("rpm", sa.Integer(), nullable=True),
        sa.Column("side_count", sa.Integer(), nullable=True),
        sa.Column("cover_url", sa.String(), nullable=True),
        sa.Column("acquired_on", sa.String(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("discogs_release_id", name="uq_vinyl_release_discogs_id"),
    )

    op.add_column("tracks", sa.Column("medium", sa.String(), nullable=True))
    op.add_column("tracks", sa.Column("vinyl_release_id", sa.Integer(), nullable=True))
    op.add_column("tracks", sa.Column("vinyl_position", sa.String(), nullable=True))
    op.add_column("tracks", sa.Column("mb_recording_id", sa.String(), nullable=True))
    op.add_column("tracks", sa.Column("bpm_source", sa.String(), nullable=True))
    op.add_column("tracks", sa.Column("key_source", sa.String(), nullable=True))
    op.add_column("tracks", sa.Column("enrichment_status", sa.String(), nullable=True))
    op.add_column("tracks", sa.Column("duplicate_of_track_id", sa.Integer(), nullable=True))

    # SQLite cannot attach a foreign key via ALTER, so the columns go in plain and
    # batch mode rebuilds the table with the constraints. Same shape as
    # c2d3e4f5a6b7, which exists because the previous round of this skipped it and
    # left a migrated database disagreeing with the ORM.
    with op.batch_alter_table("tracks") as batch_op:
        batch_op.create_foreign_key(
            "fk_tracks_vinyl_release_id", "vinyl_releases", ["vinyl_release_id"], ["id"]
        )
        batch_op.create_foreign_key(
            "fk_tracks_duplicate_of_track_id", "tracks", ["duplicate_of_track_id"], ["id"]
        )

    # A record you own is one physical object: one side position per pressing.
    # Digital rows leave both columns NULL, and SQLite treats NULLs as distinct,
    # so this constrains vinyl only.
    op.create_index(
        "uq_track_vinyl_side",
        "tracks",
        ["vinyl_release_id", "vinyl_position"],
        unique=True,
    )
    op.create_index("ix_tracks_medium", "tracks", ["medium"])

    op.add_column("audio_features", sa.Column("source", sa.String(), nullable=True))

    # Backfill, so nothing downstream ever meets a NULL medium. Everything that
    # existed before this migration came from a file.
    op.execute("UPDATE tracks SET medium = 'digital' WHERE medium IS NULL")
    op.execute("UPDATE audio_features SET source = 'essentia' WHERE source IS NULL")


def downgrade() -> None:
    op.drop_column("audio_features", "source")
    op.drop_index("ix_tracks_medium", table_name="tracks")
    op.drop_index("uq_track_vinyl_side", table_name="tracks")
    with op.batch_alter_table("tracks") as batch_op:
        batch_op.drop_constraint("fk_tracks_duplicate_of_track_id", type_="foreignkey")
        batch_op.drop_constraint("fk_tracks_vinyl_release_id", type_="foreignkey")
    op.drop_column("tracks", "duplicate_of_track_id")
    op.drop_column("tracks", "enrichment_status")
    op.drop_column("tracks", "key_source")
    op.drop_column("tracks", "bpm_source")
    op.drop_column("tracks", "mb_recording_id")
    op.drop_column("tracks", "vinyl_position")
    op.drop_column("tracks", "vinyl_release_id")
    op.drop_column("tracks", "medium")
    op.drop_table("vinyl_releases")
