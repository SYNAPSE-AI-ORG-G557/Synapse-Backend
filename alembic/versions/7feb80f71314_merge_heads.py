"""merge heads

Revision ID: 7feb80f71314
Revises: a1b2c3d4e5f6, add_schedule_tables
Create Date: 2025-10-12 20:05:48.393728

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7feb80f71314'
down_revision: Union[str, Sequence[str], None] = ('a1b2c3d4e5f6', 'add_schedule_tables')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
