"""add track_affinities table

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-04-05 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, None] = 'c3d4e5f6a7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'track_affinities',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('track_a_id', sa.Integer(), nullable=False),
        sa.Column('track_b_id', sa.Integer(), nullable=False),
        sa.Column('affinity', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['track_a_id'], ['tracks.id']),
        sa.ForeignKeyConstraint(['track_b_id'], ['tracks.id']),
        sa.UniqueConstraint('track_a_id', 'track_b_id', name='uq_track_affinity_pair'),
    )
    op.create_index('ix_track_affinity_a', 'track_affinities', ['track_a_id'])
    op.create_index('ix_track_affinity_b', 'track_affinities', ['track_b_id'])


def downgrade() -> None:
    op.drop_index('ix_track_affinity_b', table_name='track_affinities')
    op.drop_index('ix_track_affinity_a', table_name='track_affinities')
    op.drop_table('track_affinities')
