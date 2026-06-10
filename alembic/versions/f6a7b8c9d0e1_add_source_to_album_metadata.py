"""add source + source_ref to album_metadata

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-06-07 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f6a7b8c9d0e1'
down_revision: Union[str, None] = 'e5f6a7b8c9d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('album_metadata', sa.Column('source', sa.String(), nullable=True))
    op.add_column('album_metadata', sa.Column('source_ref', sa.String(), nullable=True))
    # Backfill: existing rows came from the MusicBrainz-only flow.
    op.execute(
        "UPDATE album_metadata "
        "SET source = 'musicbrainz', source_ref = mb_release_id "
        "WHERE mb_release_id IS NOT NULL AND source IS NULL"
    )


def downgrade() -> None:
    op.drop_column('album_metadata', 'source_ref')
    op.drop_column('album_metadata', 'source')
