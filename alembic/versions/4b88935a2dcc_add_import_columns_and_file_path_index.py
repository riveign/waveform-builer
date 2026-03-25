"""add import columns and file_path index

Revision ID: 4b88935a2dcc
Revises: b57b41372f67
Create Date: 2026-03-25 21:04:32.035411

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4b88935a2dcc'
down_revision: Union[str, None] = 'b57b41372f67'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Sets table: import provenance + analysis columns
    op.add_column('sets', sa.Column('source', sa.String(), nullable=True))
    op.add_column('sets', sa.Column('source_ref', sa.Text(), nullable=True))
    op.add_column('sets', sa.Column('is_analyzed', sa.Integer(), server_default='0', nullable=True))
    op.add_column('sets', sa.Column('analysis_cache', sa.Text(), nullable=True))

    # SetTracks table: energy inference columns (Phase 2)
    op.add_column('set_tracks', sa.Column('inferred_energy', sa.Float(), nullable=True))
    op.add_column('set_tracks', sa.Column('inference_source', sa.String(), nullable=True))

    # Index on tracks.file_path for fast import matching
    op.create_index('ix_tracks_file_path', 'tracks', ['file_path'])


def downgrade() -> None:
    op.drop_index('ix_tracks_file_path', table_name='tracks')
    op.drop_column('set_tracks', 'inference_source')
    op.drop_column('set_tracks', 'inferred_energy')
    op.drop_column('sets', 'analysis_cache')
    op.drop_column('sets', 'is_analyzed')
    op.drop_column('sets', 'source_ref')
    op.drop_column('sets', 'source')
