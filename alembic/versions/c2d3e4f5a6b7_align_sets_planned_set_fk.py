"""add the sets.planned_set_id -> sets.id foreign key

``c9d0e1f2a3b4`` added ``sets.planned_set_id`` with a plain ``add_column``, because
SQLite cannot attach a foreign key via ALTER. The ORM has always declared the FK, so
a migrated database and a ``create_all`` database disagreed on the ``sets`` schema.

Batch mode rebuilds the table with the constraint and copies the rows across.

Revision ID: c2d3e4f5a6b7
Revises: e1f2a3b4c5d6
Create Date: 2026-08-09

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c2d3e4f5a6b7'
down_revision: Union[str, None] = 'e1f2a3b4c5d6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('sets') as batch_op:
        batch_op.create_foreign_key(
            'fk_sets_planned_set_id', 'sets', ['planned_set_id'], ['id']
        )


def downgrade() -> None:
    with op.batch_alter_table('sets') as batch_op:
        batch_op.drop_constraint('fk_sets_planned_set_id', type_='foreignkey')
