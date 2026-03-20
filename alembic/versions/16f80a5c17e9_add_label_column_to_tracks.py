"""add label column to tracks

Revision ID: 16f80a5c17e9
Revises: 455598dafd10
Create Date: 2026-03-20 19:07:27.305077

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '16f80a5c17e9'
down_revision: Union[str, None] = '455598dafd10'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('tracks', sa.Column('label', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('tracks', 'label')
