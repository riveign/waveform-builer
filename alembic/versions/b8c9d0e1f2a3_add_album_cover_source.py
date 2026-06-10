"""add cover_source + cover_fetched_at to album_metadata

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2
Create Date: 2026-06-08 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b8c9d0e1f2a3'
down_revision: Union[str, None] = 'a7b8c9d0e1f2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('album_metadata', sa.Column('cover_source', sa.String(), nullable=True))
    op.add_column('album_metadata', sa.Column('cover_fetched_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column('album_metadata', 'cover_fetched_at')
    op.drop_column('album_metadata', 'cover_source')
