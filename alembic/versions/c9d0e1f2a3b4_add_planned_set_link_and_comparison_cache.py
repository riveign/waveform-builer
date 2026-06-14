"""add planned set link and comparison cache

Revision ID: c9d0e1f2a3b4
Revises: b8c9d0e1f2a3
Create Date: 2026-06-10

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c9d0e1f2a3b4'
down_revision: Union[str, None] = 'b8c9d0e1f2a3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Sets table: played -> planned link + cached comparison report
    op.add_column('sets', sa.Column('planned_set_id', sa.Integer(), nullable=True))
    op.add_column('sets', sa.Column('comparison_cache', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('sets', 'comparison_cache')
    op.drop_column('sets', 'planned_set_id')
