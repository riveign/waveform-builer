"""add oauth_tokens table and external fields to hunt_tracks

Revision ID: c3d4e5f6a7b8
Revises: a1c3e5f7d902
Create Date: 2026-04-04 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, None] = 'a1c3e5f7d902'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'oauth_tokens',
        sa.Column('provider', sa.String(), nullable=False),
        sa.Column('access_token', sa.String(), nullable=False),
        sa.Column('refresh_token', sa.String(), nullable=True),
        sa.Column('expires_at', sa.String(), nullable=True),
        sa.Column('user_id', sa.String(), nullable=True),
        sa.Column('username', sa.String(), nullable=True),
        sa.Column('avatar_url', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('provider'),
    )
    op.add_column('hunt_tracks', sa.Column('external_url', sa.String(), nullable=True))
    op.add_column('hunt_tracks', sa.Column('external_id', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('hunt_tracks', 'external_id')
    op.drop_column('hunt_tracks', 'external_url')
    op.drop_table('oauth_tokens')
