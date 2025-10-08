"""empty message

Revision ID: d57cb324c744
Revises: ec41616f89a8
Create Date: 2025-09-23 17:49:19.192912

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd57cb324c744'
down_revision: Union[str, Sequence[str], None] = 'ec41616f89a8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
