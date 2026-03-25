"""add kiku_play_count column to tracks

Revision ID: b57b41372f67
Revises: 16f80a5c17e9
Create Date: 2026-03-25 20:47:55.401070

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b57b41372f67'
down_revision: Union[str, None] = '16f80a5c17e9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('tracks', sa.Column('kiku_play_count', sa.Integer(), server_default='0', nullable=True))


def downgrade() -> None:
    op.drop_column('tracks', 'kiku_play_count')
