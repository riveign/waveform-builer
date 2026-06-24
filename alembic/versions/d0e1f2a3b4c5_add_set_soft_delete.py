"""add set soft-delete (deleted_at)

Revision ID: d0e1f2a3b4c5
Revises: c9d0e1f2a3b4
Create Date: 2026-06-24

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd0e1f2a3b4c5'
down_revision: Union[str, None] = 'c9d0e1f2a3b4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Soft delete: NULL = active, ISO timestamp = when it was moved to trash.
    op.add_column('sets', sa.Column('deleted_at', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('sets', 'deleted_at')
