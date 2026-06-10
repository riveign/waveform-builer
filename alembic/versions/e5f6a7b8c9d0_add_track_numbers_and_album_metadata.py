"""add track_number, disc_number, album_metadata

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-06-07 11:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("tracks", sa.Column("track_number", sa.Integer(), nullable=True))
    op.add_column("tracks", sa.Column("disc_number", sa.Integer(), nullable=True))
    op.create_index("ix_tracks_album", "tracks", ["album"])

    op.create_table(
        "album_metadata",
        sa.Column("album_key", sa.String(), nullable=False),
        sa.Column("album", sa.String(), nullable=False),
        sa.Column("album_artist", sa.String(), nullable=False),
        sa.Column("mb_release_id", sa.String(), nullable=True),
        sa.Column("last_matched_at", sa.DateTime(), nullable=True),
        sa.Column("match_status", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("album_key"),
    )


def downgrade() -> None:
    op.drop_table("album_metadata")
    op.drop_index("ix_tracks_album", table_name="tracks")
    op.drop_column("tracks", "disc_number")
    op.drop_column("tracks", "track_number")
