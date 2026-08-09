"""create hunt_sessions and hunt_tracks

These two tables were only ever created by ``Base.metadata.create_all()``, never
by a migration, while ``c3d4e5f6a7b8`` went on to ``ALTER TABLE hunt_tracks``.
A migration run from base therefore raised ``no such table: hunt_tracks``.

This revision is inserted *before* ``c3d4e5f6a7b8`` and so creates the tables in
their pre-``c3d4e5f6a7b8`` shape: without ``external_url`` / ``external_id``,
which that revision adds.

Databases already stamped at a later revision treat this as an applied ancestor
and never run it — correct, since ``create_all`` had already made the tables.

Revision ID: b1c2d3e4f5a6
Revises: a1c3e5f7d902
Create Date: 2026-08-09

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b1c2d3e4f5a6"
down_revision: Union[str, None] = "a1c3e5f7d902"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "hunt_sessions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("url", sa.String(), nullable=False),
        sa.Column("platform", sa.String(), nullable=True),
        sa.Column("title", sa.String(), nullable=True),
        sa.Column("uploader", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("track_count", sa.Integer(), nullable=True),
        sa.Column("owned_count", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "hunt_tracks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("raw_text", sa.String(), nullable=True),
        sa.Column("artist", sa.String(), nullable=True),
        sa.Column("title", sa.String(), nullable=True),
        sa.Column("remix_info", sa.String(), nullable=True),
        sa.Column("original_artist", sa.String(), nullable=True),
        sa.Column("original_title", sa.String(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("source", sa.String(), nullable=True),
        sa.Column("timestamp_sec", sa.Float(), nullable=True),
        sa.Column("matched_track_id", sa.Integer(), nullable=True),
        sa.Column("match_score", sa.Float(), nullable=True),
        sa.Column("acquisition_status", sa.String(), nullable=True),
        sa.Column("purchase_links", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["session_id"], ["hunt_sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["matched_track_id"], ["tracks.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("hunt_tracks")
    op.drop_table("hunt_sessions")
