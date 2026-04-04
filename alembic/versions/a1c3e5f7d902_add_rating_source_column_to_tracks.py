"""add rating_source column to tracks

Revision ID: a1c3e5f7d902
Revises: 4b88935a2dcc
Create Date: 2026-04-04 21:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1c3e5f7d902'
down_revision: Union[str, None] = '4b88935a2dcc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('tracks', sa.Column('rating_source', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('tracks', 'rating_source')
