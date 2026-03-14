"""initial schema

Revision ID: 455598dafd10
Revises:
Create Date: 2026-03-14 16:47:45.786459

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '455598dafd10'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'tracks',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('rb_id', sa.String, unique=True),
        sa.Column('title', sa.String),
        sa.Column('artist', sa.String),
        sa.Column('album', sa.String),
        sa.Column('rb_genre', sa.String),
        sa.Column('dir_genre', sa.String),
        sa.Column('dir_energy', sa.String),
        sa.Column('bpm', sa.Float),
        sa.Column('key', sa.String),
        sa.Column('rating', sa.Integer),
        sa.Column('color', sa.String),
        sa.Column('comment', sa.Text),
        sa.Column('duration_sec', sa.Float),
        sa.Column('file_path', sa.String),
        sa.Column('file_hash', sa.String),
        sa.Column('date_added', sa.String),
        sa.Column('play_count', sa.Integer, default=0),
        sa.Column('release_year', sa.Integer),
        sa.Column('acquired_month', sa.String),
        sa.Column('playlist_tags', sa.Text),
        sa.Column('last_synced', sa.String),
        sa.Column('energy_predicted', sa.String),
        sa.Column('energy_confidence', sa.Float),
        sa.Column('energy_source', sa.String),
    )

    op.create_table(
        'audio_features',
        sa.Column('track_id', sa.Integer, sa.ForeignKey('tracks.id'), primary_key=True),
        sa.Column('energy', sa.Float),
        sa.Column('danceability', sa.Float),
        sa.Column('loudness_lufs', sa.Float),
        sa.Column('spectral_centroid', sa.Float),
        sa.Column('spectral_complexity', sa.Float),
        sa.Column('mood_happy', sa.Float),
        sa.Column('mood_sad', sa.Float),
        sa.Column('mood_aggressive', sa.Float),
        sa.Column('mood_relaxed', sa.Float),
        sa.Column('ml_genre', sa.String),
        sa.Column('ml_genre_confidence', sa.Float),
        sa.Column('energy_intro', sa.Float),
        sa.Column('energy_body', sa.Float),
        sa.Column('energy_outro', sa.Float),
        sa.Column('mfcc_mean', sa.LargeBinary),
        sa.Column('mfcc_var', sa.LargeBinary),
        sa.Column('verified_bpm', sa.Float),
        sa.Column('verified_key', sa.String),
        sa.Column('analyzed_at', sa.String),
        sa.Column('waveform_overview', sa.LargeBinary),
        sa.Column('waveform_detail', sa.LargeBinary),
        sa.Column('waveform_sr', sa.Integer),
        sa.Column('waveform_hop', sa.Integer),
        sa.Column('beat_positions', sa.LargeBinary),
        sa.Column('band_low', sa.LargeBinary),
        sa.Column('band_midlow', sa.LargeBinary),
        sa.Column('band_midhigh', sa.LargeBinary),
        sa.Column('band_high', sa.LargeBinary),
        sa.Column('band_low_overview', sa.LargeBinary),
        sa.Column('band_midlow_overview', sa.LargeBinary),
        sa.Column('band_midhigh_overview', sa.LargeBinary),
        sa.Column('band_high_overview', sa.LargeBinary),
    )

    op.create_table(
        'sets',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('name', sa.String),
        sa.Column('created_at', sa.String),
        sa.Column('duration_min', sa.Integer),
        sa.Column('energy_profile', sa.Text),
        sa.Column('genre_filter', sa.Text),
    )

    op.create_table(
        'set_tracks',
        sa.Column('set_id', sa.Integer, sa.ForeignKey('sets.id'), primary_key=True),
        sa.Column('position', sa.Integer, primary_key=True),
        sa.Column('track_id', sa.Integer, sa.ForeignKey('tracks.id')),
        sa.Column('transition_score', sa.Float),
    )

    op.create_table(
        'transition_cues',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('set_id', sa.Integer, sa.ForeignKey('sets.id', ondelete='CASCADE'), nullable=False),
        sa.Column('track_id', sa.Integer, sa.ForeignKey('tracks.id'), nullable=False),
        sa.Column('position', sa.Integer, nullable=False),
        sa.Column('name', sa.String, nullable=False),
        sa.Column('cue_type', sa.String, nullable=False),
        sa.Column('start_sec', sa.Float, nullable=False),
        sa.Column('end_sec', sa.Float),
        sa.Column('hot_cue_num', sa.Integer, default=-1),
        sa.Column('color', sa.String),
        sa.Column('created_at', sa.String),
    )


def downgrade() -> None:
    op.drop_table('transition_cues')
    op.drop_table('set_tracks')
    op.drop_table('sets')
    op.drop_table('audio_features')
    op.drop_table('tracks')
