"""add vinyl_twin_rejections — pairings the DJ said "not it" to

Revision ID: b3c5d7e9f1a2
Revises: a2b4c6d8e0f1
Create Date: 2026-09-13 10:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b3c5d7e9f1a2"
down_revision: Union[str, None] = "a2b4c6d8e0f1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "vinyl_twin_rejections",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("vinyl_track_id", sa.Integer(), nullable=False),
        sa.Column("digital_track_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["vinyl_track_id"], ["tracks.id"]),
        sa.ForeignKeyConstraint(["digital_track_id"], ["tracks.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("vinyl_track_id", "digital_track_id", name="uq_vinyl_twin_rejection"),
    )


def downgrade() -> None:
    op.drop_table("vinyl_twin_rejections")
